/* Cancellation-aware, bounded subprocess runner for the agent's run_command tool.
   This is injected into the generated node and cognitive-agent test C by build.sh.
   It deliberately does not replace stdlib run_command: background services started by
   node bootstrap keep their existing semantics, while model-issued commands are
   bounded, observable, and unable to inherit the node's listening sockets. */

#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#define EP_AGENT_CMD_MAX_OUTPUT (4U * 1024U * 1024U)
#define EP_AGENT_CMD_POLL_MS 50
#define EP_AGENT_CMD_TERM_GRACE_MS 500

static long long ep_agent_cmd_now_ms(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (long long)ts.tv_sec * 1000LL + (long long)(ts.tv_nsec / 1000000LL);
}

static void ep_agent_cmd_signal_group(pid_t pid, int sig) {
    if (pid <= 0) return;
    if (kill(-pid, sig) != 0 && errno == ESRCH) {
        (void)kill(pid, sig);
    }
}

static char* ep_agent_cmd_format(const char* status, const char* output,
                                 size_t output_len, int truncated) {
    const char* truncation = truncated
        ? "\n[run_command output truncated at 4194304 bytes; remaining output was drained.]"
        : "";
    size_t status_len = status ? strlen(status) : 0;
    size_t truncation_len = strlen(truncation);
    size_t separator_len = (status_len > 0 && output_len > 0) ? 1 : 0;
    char* result = (char*)malloc(status_len + separator_len + output_len + truncation_len + 1);
    if (!result) return strdup("[run_command failed: result allocation failed]");
    size_t pos = 0;
    if (status_len > 0) {
        memcpy(result + pos, status, status_len);
        pos += status_len;
    }
    if (separator_len > 0) result[pos++] = '\n';
    if (output_len > 0) {
        memcpy(result + pos, output, output_len);
        pos += output_len;
    }
    if (truncation_len > 0) {
        memcpy(result + pos, truncation, truncation_len);
        pos += truncation_len;
    }
    result[pos] = '\0';
    return result;
}

static long long ep_run_command_bounded_impl(long long cmd_ptr, long long timeout_ms,
                                              long long start_epoch) {
    const char* cmd = (const char*)cmd_ptr;
    if (!cmd || cmd[0] == '\0') {
        return (long long)strdup("[run_command failed: empty command]");
    }
    if (timeout_ms < 50) timeout_ms = 50;
    if (timeout_ms > 1800000) timeout_ms = 1800000;

    int output_pipe[2];
    if (pipe(output_pipe) != 0) {
        char failure[192];
        snprintf(failure, sizeof(failure), "[run_command failed: pipe: %s]", strerror(errno));
        return (long long)strdup(failure);
    }

    pid_t pid = fork();
    if (pid < 0) {
        int saved_errno = errno;
        close(output_pipe[0]);
        close(output_pipe[1]);
        char failure[192];
        snprintf(failure, sizeof(failure), "[run_command failed: fork: %s]", strerror(saved_errno));
        return (long long)strdup(failure);
    }

    if (pid == 0) {
        (void)setpgid(0, 0);
        (void)dup2(output_pipe[1], STDOUT_FILENO);
        (void)dup2(output_pipe[1], STDERR_FILENO);
        close(output_pipe[0]);
        close(output_pipe[1]);

        /* The old popen path leaked every node listener into tool children. Close all
           descriptors except stdio before exec so a tool can never keep Ernos ports
           occupied after the node exits or restarts. */
        long max_fd = sysconf(_SC_OPEN_MAX);
        if (max_fd < 0 || max_fd > 65536) max_fd = 65536;
        for (int fd = 3; fd < max_fd; fd++) close(fd);

        execl("/bin/sh", "sh", "-c", cmd, (char*)NULL);
        dprintf(STDERR_FILENO, "run_command exec failed: %s\n", strerror(errno));
        _exit(127);
    }

    (void)setpgid(pid, pid);
    close(output_pipe[1]);
    int old_flags = fcntl(output_pipe[0], F_GETFL, 0);
    if (old_flags >= 0) (void)fcntl(output_pipe[0], F_SETFL, old_flags | O_NONBLOCK);

    char* output = (char*)malloc(EP_AGENT_CMD_MAX_OUTPUT + 1);
    if (!output) {
        ep_agent_cmd_signal_group(pid, SIGKILL);
        close(output_pipe[0]);
        (void)waitpid(pid, NULL, 0);
        return (long long)strdup("[run_command failed: output allocation failed]");
    }

    size_t output_len = 0;
    int truncated = 0;
    int pipe_eof = 0;
    int child_done = 0;
    int child_status = 0;
    int timed_out = 0;
    int cancelled = 0;
    int termination_sent = 0;
    int kill_sent = 0;
    long long termination_at = 0;
    long long child_done_at = 0;
    const long long started_at = ep_agent_cmd_now_ms();

    while (!child_done || !pipe_eof) {
        char chunk[8192];
        for (;;) {
            ssize_t n = read(output_pipe[0], chunk, sizeof(chunk));
            if (n > 0) {
                size_t available = EP_AGENT_CMD_MAX_OUTPUT - output_len;
                size_t keep = (size_t)n < available ? (size_t)n : available;
                if (keep > 0) {
                    memcpy(output + output_len, chunk, keep);
                    output_len += keep;
                }
                if (keep < (size_t)n) truncated = 1;
                continue;
            }
            if (n == 0) pipe_eof = 1;
            if (n < 0 && errno != EAGAIN && errno != EWOULDBLOCK && errno != EINTR) {
                pipe_eof = 1;
            }
            break;
        }

        if (!child_done) {
            pid_t waited = waitpid(pid, &child_status, WNOHANG);
            if (waited == pid) {
                child_done = 1;
                child_done_at = ep_agent_cmd_now_ms();
            } else if (waited < 0 && errno == ECHILD) {
                child_done = 1;
                child_done_at = ep_agent_cmd_now_ms();
            }
        }

        long long now = ep_agent_cmd_now_ms();
        if (!termination_sent && ep_cancel_epoch_get(0) > start_epoch) {
            cancelled = 1;
            termination_sent = 1;
            termination_at = now;
            ep_agent_cmd_signal_group(pid, SIGTERM);
        }
        if (!termination_sent && now - started_at >= timeout_ms) {
            timed_out = 1;
            termination_sent = 1;
            termination_at = now;
            ep_agent_cmd_signal_group(pid, SIGTERM);
        }

        /* A shell can exit while a background descendant keeps the output pipe open.
           Clean the process group and close the pipe instead of waiting forever. */
        if (child_done && !pipe_eof && !termination_sent && now - child_done_at >= 100) {
            termination_sent = 1;
            termination_at = now;
            ep_agent_cmd_signal_group(pid, SIGTERM);
        }
        if (termination_sent && !kill_sent && !child_done &&
            now - termination_at >= EP_AGENT_CMD_TERM_GRACE_MS) {
            kill_sent = 1;
            ep_agent_cmd_signal_group(pid, SIGKILL);
        }
        if (child_done && !pipe_eof && termination_sent &&
            now - termination_at >= EP_AGENT_CMD_TERM_GRACE_MS) {
            pipe_eof = 1;
        }

        if (!child_done || !pipe_eof) {
            struct pollfd pfd;
            pfd.fd = output_pipe[0];
            pfd.events = POLLIN | POLLHUP;
            pfd.revents = 0;
            (void)poll(&pfd, 1, EP_AGENT_CMD_POLL_MS);
        }
    }

    if (!child_done) {
        ep_agent_cmd_signal_group(pid, SIGKILL);
        while (waitpid(pid, &child_status, 0) < 0 && errno == EINTR) {}
    }
    close(output_pipe[0]);
    output[output_len] = '\0';

    char status_text[256];
    status_text[0] = '\0';
    if (cancelled) {
        snprintf(status_text, sizeof(status_text),
                 "[run_command cancelled; subprocess group terminated]");
    } else if (timed_out) {
        snprintf(status_text, sizeof(status_text),
                 "[run_command timed out after %lld ms; subprocess group terminated]",
                 timeout_ms);
    } else if (WIFEXITED(child_status) && WEXITSTATUS(child_status) != 0) {
        snprintf(status_text, sizeof(status_text),
                 "[run_command failed: exit status %d]", WEXITSTATUS(child_status));
    } else if (WIFSIGNALED(child_status)) {
        snprintf(status_text, sizeof(status_text),
                 "[run_command failed: terminated by signal %d]", WTERMSIG(child_status));
    } else if (!WIFEXITED(child_status)) {
        snprintf(status_text, sizeof(status_text),
                 "[run_command failed: child status unavailable]");
    }

    char* result = ep_agent_cmd_format(status_text, output, output_len, truncated);
    free(output);
    return (long long)result;
}

long long ep_run_command_bounded(long long cmd_ptr, long long timeout_ms,
                                 long long start_epoch) {
    ep_gc_enter_blocking();
    long long result = ep_run_command_bounded_impl(cmd_ptr, timeout_ms, start_epoch);
    ep_gc_exit_blocking();
    return result;
}
