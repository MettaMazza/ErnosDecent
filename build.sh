#!/bin/bash
# ErnosDecent — Cross-Platform Build Script
# Compiles node.ep and patches the C runtime to ignore SIGPIPE
# Supports: macOS (ARM64/x86_64), Linux (x86_64/aarch64)
# Usage: bash build.sh

set -e

# ── Shared C-runtime injector (single source of truth) ───────────────────────
# The ErnosPlain compiler emits forward declarations for a set of runtime helpers
# but not their bodies; build.sh injects the bodies. The NODE build and the TEST
# build used to each carry a hand-copied subset of these injections, which drifted:
# the test build never injected ep_cancel_*, ep_json_escape, or async_wait_readable_
# timeout, so the whole cognitive-agent test suite failed to LINK (undefined symbols)
# and could never run — masking every regression. This one function is now the ONLY
# place the additive helpers are defined, and BOTH builds call it, so they cannot
# diverge again. Injected before the 2nd ep_net_send (a point where the runtime
# types EpFuture/EpReadReadyArgs/EpTask are already defined). Idempotent.
inject_additive_helpers() {
    local CFILE="$1"
    if grep -aq "long long cast_borrow_to_map(long long b) {" "$CFILE"; then
        echo "[*] additive helpers already present in $CFILE."
        return 0
    fi
    CFILE="$CFILE" python3 -c "
import os
cfile = os.environ['CFILE']
with open(cfile, 'r') as f:
    content = f.read()
inject = '''
long long cast_borrow_to_map(long long b) {
    return b;
}

long long cast_int_to_map(long long i) {
    return i;
}

long long cast_map_to_int(long long m) {
    return m;
}

/* Global cancel-all flag (see node build notes). */
volatile long long ep_cancel_all_flag = 0;
long long ep_cancel_set(long long v) {
    ep_cancel_all_flag = v;
    return 0;
}
long long ep_cancel_get(long long dummy) {
    return ep_cancel_all_flag;
}

/* SAFETY: cancel EPOCH — a monotonic latch replacing the consume-once flag for
   halt-EVERYTHING semantics. The old flag was consumed (set back to 0) by the FIRST
   loop that saw it, so with a main agent + sub-agents + a background coordinator
   running concurrently, exactly ONE halted and the rest kept working. With the epoch,
   every run captures the value at its start and halts when the current value is
   GREATER — nothing consumes, every concurrent run sees the same stop, and runs
   started AFTER the stop are unaffected. Atomics because the web thread bumps while
   the agent thread reads. */
volatile long long ep_cancel_all_epoch = 0;
long long ep_cancel_epoch_get(long long dummy) {
    (void)dummy;
    return __atomic_load_n((long long*)&ep_cancel_all_epoch, __ATOMIC_SEQ_CST);
}
long long ep_cancel_epoch_bump(long long dummy) {
    (void)dummy;
    return __atomic_add_fetch((long long*)&ep_cancel_all_epoch, 1, __ATOMIC_SEQ_CST);
}

/* One-pass O(n) JSON string escaper (replaces the O(n^2) pure-.ep version). */
long long ep_json_escape(long long s_ptr) {
    const char* s = (const char*)s_ptr;
    if (!s) return (long long)strdup(\"\");
    size_t len = strlen(s);
    char* out = (char*)malloc(len * 6 + 1);
    if (!out) return (long long)strdup(\"\");
    static const char hexd[] = \"0123456789abcdef\";
    size_t j = 0;
    size_t i;
    for (i = 0; i < len; i++) {
        unsigned char c = (unsigned char)s[i];
        if (c == 34)      { out[j++]=92; out[j++]=34;  }
        else if (c == 92) { out[j++]=92; out[j++]=92;  }
        else if (c == 10) { out[j++]=92; out[j++]=110; }
        else if (c == 13) { out[j++]=92; out[j++]=114; }
        else if (c == 9)  { out[j++]=92; out[j++]=116; }
        else if (c < 32)  { out[j++]=92; out[j++]=117; out[j++]=48; out[j++]=48; out[j++]=hexd[(c>>4)&15]; out[j++]=hexd[c&15]; }
        else              { out[j++]=(char)c; }
    }
    out[j] = 0;
    long long r = (long long)strdup(out);
    free(out);
    return r;
}

/* THREAD OWNERSHIP OF THE ASYNC LOOP (root fix for the sub-agent hangs).
   The event loop (run queue + kqueue + timers) is single-threaded state with NO locks.
   Sub-agent WORKER THREADS used to create read/timer tasks on the shared kqueue and
   pump the loop concurrently from ep_await_future. kqueue hands each event to WHICHEVER
   thread is parked in kevent(), so worker A's readiness event could be consumed by
   another thread: A's future got completed, but A stayed parked in kevent() with no
   event of its own, holding a fully-buffered LLM response until ANY new process I/O
   (e.g. the operator's next command — the cancel) woke it. That is the observed
   sub-agents-hang-then-complete-instantly-on-the-next-message bug, and the
   unsynchronized run-queue linked list was a latent corruption risk on top.
   Invariant restored: ONLY the loop-owner thread (main — captured by the constructor,
   which runs on the main thread at load) may create loop tasks or pump the loop.
   Non-owner threads wait with plain poll()/nanosleep (correct in a dedicated OS thread)
   and get a PRE-COMPLETED future, which ep_await_future returns from immediately
   without ever touching the loop. */
#include <poll.h>
#include <pthread.h>
static pthread_t ep_loop_owner_thread;
__attribute__((constructor)) static void ep_capture_loop_owner(void) {
    ep_loop_owner_thread = pthread_self();
}
static EpFuture* ep_make_completed_future(long long value) {
    EpFuture* fut = (EpFuture*)malloc(sizeof(EpFuture));
    fut->completed = 1; fut->value = value; fut->waiting_task = NULL; fut->chan = 0;
    { EpGCObject* _go = ep_gc_register(fut, EP_OBJ_STRUCT); if(_go) _go->num_fields = 3; }
    return fut;
}

/* Awaitable readable-OR-timeout future. */
static long long ep_readto_read_step(void* r) {
    EpReadReadyArgs* a = (EpReadReadyArgs*)r;
    if (a && a->fut && !a->fut->completed) {
        a->fut->completed = 1; a->fut->value = 1;
        if (a->fut->waiting_task) { ep_task_enqueue(a->fut->waiting_task); a->fut->waiting_task = NULL; }
    }
    return 0;
}
static long long ep_readto_timer_step(void* r) {
    EpReadReadyArgs* a = (EpReadReadyArgs*)r;
    if (a && a->fut && !a->fut->completed) {
        a->fut->completed = 1; a->fut->value = 0;
        if (a->fut->waiting_task) { ep_task_enqueue(a->fut->waiting_task); a->fut->waiting_task = NULL; }
    }
    return 0;
}
long long async_wait_readable_timeout(long long fd, long long timeout_ms) {
    if (!pthread_equal(pthread_self(), ep_loop_owner_thread)) {
        /* Worker thread: NEVER touch the shared loop — plain poll, pre-completed future. */
        struct pollfd p; p.fd = (int)fd; p.events = POLLIN; p.revents = 0;
        int r = poll(&p, 1, (int)timeout_ms);
        return (long long)ep_make_completed_future(r > 0 ? 1 : 0);
    }
    EpFuture* fut = (EpFuture*)malloc(sizeof(EpFuture));
    fut->completed = 0; fut->value = 0; fut->waiting_task = NULL; fut->chan = 0;
    { EpGCObject* _go = ep_gc_register(fut, EP_OBJ_STRUCT); if(_go) _go->num_fields = 3; }
    EpReadReadyArgs* rargs = (EpReadReadyArgs*)malloc(sizeof(EpReadReadyArgs));
    rargs->fut = fut;
    EpTask* rtask = (EpTask*)malloc(sizeof(EpTask));
    rtask->step = ep_readto_read_step; rtask->args = rargs;
    rtask->args_size_bytes = sizeof(EpReadReadyArgs);
    rtask->fut = NULL; rtask->state = 0; rtask->is_cancelled = 0; rtask->parent = ep_current_task;
    ep_async_register_read((int)fd, rtask);
    EpReadReadyArgs* targs = (EpReadReadyArgs*)malloc(sizeof(EpReadReadyArgs));
    targs->fut = fut;
    EpTask* ttask = (EpTask*)malloc(sizeof(EpTask));
    ttask->step = ep_readto_timer_step; ttask->args = targs;
    ttask->args_size_bytes = sizeof(EpReadReadyArgs);
    ttask->fut = NULL; ttask->state = 0; ttask->is_cancelled = 0; ttask->parent = ep_current_task;
    ep_async_register_timer(timeout_ms, ttask);
    return (long long)fut;
}

/* Awaitable pure sleep: a future completed by a timer task after ms. Lets EP code wait
   without blocking the single-threaded async loop — ep_sleep_ms stalls EVERY task for
   the duration; awaiting this yields, so sibling agent tasks (and their LLM reads)
   keep running. Reuses the readable-timeout plumbing's timer half. Used by
   bridge_wait_result so a Discord RPC wait cannot freeze the node.
   THREAD-AWARE like async_wait_readable_timeout: a worker thread nanosleeps and gets a
   pre-completed future instead of registering a timer on the loop it must not touch. */
/* Phase A: set a socket non-blocking (the IPC LISTEN socket, so the accept task can
   wait via the event loop) and force one BLOCKING (each ACCEPTED client socket —
   Darwin inherits O_NONBLOCK on accept, which made every per-connection command read
   return empty and fail auth). Returns 0 ok, -1 on error. */
long long ep_net_set_nonblocking(long long fd) {
    int flags = fcntl((int)fd, F_GETFL, 0);
    if (flags < 0) return -1;
    if (fcntl((int)fd, F_SETFL, flags | O_NONBLOCK) < 0) return -1;
    return 0;
}
long long ep_net_set_blocking(long long fd) {
    int flags = fcntl((int)fd, F_GETFL, 0);
    if (flags < 0) return -1;
    if (fcntl((int)fd, F_SETFL, flags & ~O_NONBLOCK) < 0) return -1;
    return 0;
}

long long ep_async_sleep_ms(long long ms) {
    if (!pthread_equal(pthread_self(), ep_loop_owner_thread)) {
        /* Worker thread: NEVER touch the shared loop — plain sleep, pre-completed future. */
        struct timespec ts; ts.tv_sec = ms / 1000; ts.tv_nsec = (ms % 1000) * 1000000L;
        nanosleep(&ts, NULL);
        return (long long)ep_make_completed_future(0);
    }
    EpFuture* fut = (EpFuture*)malloc(sizeof(EpFuture));
    fut->completed = 0; fut->value = 0; fut->waiting_task = NULL; fut->chan = 0;
    { EpGCObject* _go = ep_gc_register(fut, EP_OBJ_STRUCT); if(_go) _go->num_fields = 3; }
    EpReadReadyArgs* targs = (EpReadReadyArgs*)malloc(sizeof(EpReadReadyArgs));
    targs->fut = fut;
    EpTask* ttask = (EpTask*)malloc(sizeof(EpTask));
    ttask->step = ep_readto_timer_step; ttask->args = targs;
    ttask->args_size_bytes = sizeof(EpReadReadyArgs);
    ttask->fut = NULL; ttask->state = 0; ttask->is_cancelled = 0; ttask->parent = ep_current_task;
    ep_async_register_timer(ms, ttask);
    return (long long)fut;
}

/* Read a file binary-safe (length-aware) and return base64 — for embedding a generated
   image into a multimodal LLM request. ep_base64_encode is strlen-based (truncates at NULs). */
long long ep_file_to_base64(long long path_ptr) {
    const char* path = (const char*)path_ptr;
    if (!path) return (long long)strdup(\"\");
    FILE* f = fopen(path, \"rb\");
    if (!f) return (long long)strdup(\"\");
    fseek(f, 0, SEEK_END); long sz = ftell(f); fseek(f, 0, SEEK_SET);
    if (sz <= 0) { fclose(f); return (long long)strdup(\"\"); }
    unsigned char* buf = (unsigned char*)malloc((size_t)sz);
    if (!buf) { fclose(f); return (long long)strdup(\"\"); }
    size_t rd = fread(buf, 1, (size_t)sz, f); fclose(f);
    static const char b64[] = \"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/\";
    size_t olen = 4 * ((rd + 2) / 3);
    char* out = (char*)malloc(olen + 1);
    if (!out) { free(buf); return (long long)strdup(\"\"); }
    size_t i, j;
    for (i = 0, j = 0; i < rd; ) {
        unsigned int oa = i < rd ? buf[i++] : 0;
        unsigned int ob = i < rd ? buf[i++] : 0;
        unsigned int oc = i < rd ? buf[i++] : 0;
        unsigned int tr = (oa << 16) + (ob << 8) + oc;
        out[j++] = b64[(tr >> 18) & 0x3F];
        out[j++] = b64[(tr >> 12) & 0x3F];
        out[j++] = b64[(tr >> 6) & 0x3F];
        out[j++] = b64[tr & 0x3F];
    }
    int mod = (int)(rd % 3);
    if (mod == 1) { out[olen-1] = 61; out[olen-2] = 61; }
    else if (mod == 2) { out[olen-1] = 61; }
    out[olen] = 0;
    free(buf);
    long long r = (long long)strdup(out); free(out);
    return r;
}

'''
pat = 'long long ep_net_send(long long fd, const char* data) {'
first = content.find(pat)
second = content.find(pat, first + 1)
if second > 0:
    content = content[:second] + inject + content[second:]
else:
    raise SystemExit('ERROR: could not find second ep_net_send in ' + cfile + ' — additive helpers not injected')

# THREAD-SAFE RUN QUEUE: the compiler emits an unlocked linked-list run queue, which
# worker threads can still touch via un-awaited async dispatch (e.g. a sub-agent tool
# calling generate_image enqueues the poll chain from its worker thread while the main
# thread pumps). Same root hazard family as the stolen-kevent-wakeup bug — an
# unsynchronized cross-thread mutation of loop state. Guard both queue ops with a mutex
# (pthread.h is included well before these functions in the emitted C).
old_q = '''static void ep_task_enqueue(EpTask* task) {
    if (!task) return;
    task->next = NULL;
    if (ep_run_queue_tail) {
        ep_run_queue_tail->next = task;
        ep_run_queue_tail = task;
    } else {
        ep_run_queue_head = ep_run_queue_tail = task;
    }
}

static EpTask* ep_task_dequeue(void) {
    if (!ep_run_queue_head) return NULL;
    EpTask* task = ep_run_queue_head;
    ep_run_queue_head = ep_run_queue_head->next;
    if (!ep_run_queue_head) ep_run_queue_tail = NULL;
    return task;
}'''
new_q = '''static pthread_mutex_t ep_run_queue_lock = PTHREAD_MUTEX_INITIALIZER;
static void ep_task_enqueue(EpTask* task) {
    if (!task) return;
    pthread_mutex_lock(&ep_run_queue_lock);
    task->next = NULL;
    if (ep_run_queue_tail) {
        ep_run_queue_tail->next = task;
        ep_run_queue_tail = task;
    } else {
        ep_run_queue_head = ep_run_queue_tail = task;
    }
    pthread_mutex_unlock(&ep_run_queue_lock);
}

static EpTask* ep_task_dequeue(void) {
    pthread_mutex_lock(&ep_run_queue_lock);
    EpTask* task = ep_run_queue_head;
    if (task) {
        ep_run_queue_head = task->next;
        if (!ep_run_queue_head) ep_run_queue_tail = NULL;
    }
    pthread_mutex_unlock(&ep_run_queue_lock);
    return task;
}'''
if old_q in content:
    content = content.replace(old_q, new_q, 1)
    print('Injected additive runtime helpers + THREAD-SAFE run queue into ' + cfile)
elif new_q in content:
    print('Injected additive runtime helpers into ' + cfile + ' (run queue already thread-safe)')
else:
    raise SystemExit('ERROR: run-queue pattern not found in ' + cfile + ' — refusing an unlocked build')

with open(cfile, 'w') as f:
    f.write(content)
"
}

if [ "${1:-}" = "--inject-additive-runtime" ]; then
    if [ "$#" -ne 2 ] || [ ! -s "$2" ]; then
        echo "[-] Usage: build.sh --inject-additive-runtime <emitted.c>" >&2
        exit 64
    fi
    inject_additive_helpers "$2"
    exit 0
fi

# ── Shared: local image-generation FFI (libstable-diffusion, ggml/Metal) ─────────────
# The shim (decent_agent/vendor/sd/sd_ep_shim.c) is compiled into BOTH the node and the
# test build so image_gen.ep's `external define sd_ep_generate` always resolves — and the
# two never drift. The runtime is a required production dependency: a build without it
# stops with an actionable error and cannot emit a binary that advertises a non-working
# image generator.
SD_SHIM_SRC="decent_agent/vendor/sd/sd_ep_shim.cpp"
SD_LIB_DIR="$HOME/.ernosdecent/lib"
SD_CFLAGS=""
case "$(uname -s)" in
    Darwin)
        SD_LIBRARY="$SD_LIB_DIR/libstable-diffusion.dylib"
        SD_CXX_LIB="-lc++"
        ;;
    Linux)
        SD_LIBRARY="$SD_LIB_DIR/libstable-diffusion.so"
        SD_CXX_LIB="-lstdc++"
        ;;
    *)
        echo "[-] Unsupported image-runtime platform: $(uname -s)"
        exit 1
        ;;
esac
if [ ! -f "$SD_LIBRARY" ]; then
    echo "[-] Required image runtime missing: $SD_LIBRARY"
    exit 1
fi
SD_CFLAGS="-DSD_EP_HAVE_LIB -Idecent_agent/vendor/sd -L$SD_LIB_DIR -lstable-diffusion -Wl,-rpath,$SD_LIB_DIR $SD_CXX_LIB"
echo "[*] Image FFI: linking $SD_LIBRARY"

if [ "${1:-}" = "test" ] || [ "${1:-}" = "--test" ] || [ "${1:-}" = "--compile-agent-test" ]; then
    echo "[*] Building Cognitive Agent Test Suite..."
    
    # Locate compiler
    if command -v ernos &>/dev/null; then
        ERNOS="ernos"
    elif [ -f "$HOME/.local/bin/ernos" ]; then
        ERNOS="$HOME/.local/bin/ernos"
    elif [ -f "/usr/local/bin/ernos" ]; then
        ERNOS="/usr/local/bin/ernos"
    else
        echo "[-] Ernos compiler not found. Install it first."
        exit 1
    fi
    
    rm -f decent_agent/test_agent_compiled.c
    set +e
    AGENT_COMPILE_OUT=$($ERNOS decent_agent/test_agent.ep 2>&1)
    AGENT_COMPILE_STATUS=$?
    set -e
    printf '%s\n' "$AGENT_COMPILE_OUT"
    if [ ! -s decent_agent/test_agent_compiled.c ]; then
        echo "[-] Cognitive-agent compiler did not emit fresh C." >&2
        exit 1
    fi
    if [ "$AGENT_COMPILE_STATUS" -ne 0 ] && ! printf '%s\n' "$AGENT_COMPILE_OUT" | grep -qE "undefined symbol|Undefined symbols|undefined reference"; then
        echo "[-] Cognitive-agent compilation failed before the expected runtime-link stage." >&2
        exit "$AGENT_COMPILE_STATUS"
    fi
    python3 scripts/patch_generated_network.py decent_agent/test_agent_compiled.c

    # Step 1b: Patch conflicting mutex declarations and session helpers. The shared
    # generated-network patcher above owns ep_net_send_raw so compiler versions cannot
    # cause this block to double-define it.
    python3 -c "
with open('decent_agent/test_agent_compiled.c', 'r') as f:
    content = f.read()
content = content.replace('long long ep_mutex_lock(long long);', '')
content = content.replace('long long ep_mutex_unlock(long long);', '')
# NOTE: cast_borrow_to_map/cast_map_to_int (and cancel/json/async) are injected by the
# SHARED inject_additive_helpers() below, so they are NOT defined here (would double-define).
inject = '''
__thread char ep_active_session_id[256] = \"\";

long long tools_set_active_session(long long sid_ptr) {
    const char* sid = (const char*)sid_ptr;
    if (sid) {
        strncpy(ep_active_session_id, sid, sizeof(ep_active_session_id) - 1);
        ep_active_session_id[sizeof(ep_active_session_id) - 1] = '\\\\0';
    } else {
        ep_active_session_id[0] = '\\\\0';
    }
    return 0;
}
'''
pat = 'long long ep_net_send(long long fd, const char* data) {'
first = content.find(pat)
second = content.find(pat, first + 1)
if second > 0:
    content = content[:second] + inject + content[second:]
else:
    if first > 0:
        content = content[:first] + inject + content[first:]
    else:
        content = content + inject

# 1. Inject GC blocking helpers
content = content.replace(
    '#define EP_GC_UPDATE_TOP() { volatile int _dummy; ep_thread_local_top = (void*)&_dummy; }',
    '''#define EP_GC_UPDATE_TOP() { volatile int _dummy; ep_thread_local_top = (void*)&_dummy; }

static void ep_gc_enter_blocking(void) {
    EP_GC_UPDATE_TOP();
    if (ep_thread_slot >= 0) {
        pthread_mutex_lock(&ep_gc_mutex);
        ep_thread_active[ep_thread_slot] = 0;
        pthread_mutex_unlock(&ep_gc_mutex);
    }
}

static void ep_gc_exit_blocking(void) {
    if (ep_thread_slot >= 0) {
        pthread_mutex_lock(&ep_gc_mutex);
        while (ep_gc_stop_requested) {
            pthread_cond_wait(&ep_gc_resume_cond, &ep_gc_mutex);
        }
        ep_thread_active[ep_thread_slot] = 1;
        pthread_mutex_unlock(&ep_gc_mutex);
    }
}
'''
)

# 2. Wrap blocking calls in test_agent_compiled.c
def wrap_second_occ(content, sig, impl_sig, call_wrapper_body):
    first = content.find(sig)
    second = content.find(sig, first + 1)
    target = second if second > 0 else first
    if target > 0:
        wrapper = f'{impl_sig};\\n{sig} {{\\n{call_wrapper_body}\\n}}\\n'
        content = content[:target] + wrapper + impl_sig + content[target + len(sig):]
    return content

content = wrap_second_occ(content, 'long long ep_run_command(long long cmd_ptr)', 'long long ep_run_command_impl(long long cmd_ptr)', '    ep_gc_enter_blocking();\n    long long res = ep_run_command_impl(cmd_ptr);\n    ep_gc_exit_blocking();\n    return res;')
content = wrap_second_occ(content, 'long long ep_sleep_ms(long long ms)', 'long long ep_sleep_ms_impl(long long ms)', '    ep_gc_enter_blocking();\\n    long long res = ep_sleep_ms_impl(ms);\\n    ep_gc_exit_blocking();\\n    return res;')
content = wrap_second_occ(content, 'long long ep_net_accept(long long server_fd)', 'long long ep_net_accept_impl(long long server_fd)', '    ep_gc_enter_blocking();\\n    long long res = ep_net_accept_impl(server_fd);\\n    ep_gc_exit_blocking();\\n    return res;')
content = wrap_second_occ(content, 'char* ep_net_recv(long long fd, long long max_len)', 'char* ep_net_recv_impl(long long fd, long long max_len)', '    ep_gc_enter_blocking();\\n    char* res = ep_net_recv_impl(fd, max_len);\\n    ep_gc_exit_blocking();\\n    return res;')
content = wrap_second_occ(content, 'long long ep_http_request(long long method_val, long long url_val, long long headers_val, long long body_val)', 'long long ep_http_request_impl(long long method_val, long long url_val, long long headers_val, long long body_val)', '    ep_gc_enter_blocking();\\n    long long res = ep_http_request_impl(method_val, url_val, headers_val, body_val);\\n    ep_gc_exit_blocking();\\n    return res;')

# 3. Inject SQLite thread-safety patch to test_agent_compiled.c
content = content.replace(
    'long long sql_execute(long long db, long long sql) {',
    'static pthread_mutex_t ep_sqlite_global_mutex = PTHREAD_MUTEX_INITIALIZER;\\nlong long sql_execute_impl(long long db, long long sql);\\nlong long sql_execute(long long db, long long sql) {\\n    ep_gc_enter_blocking();\n    pthread_mutex_lock(&ep_sqlite_global_mutex);\n    long long res = sql_execute_impl(db, sql);\\n    pthread_mutex_unlock(&ep_sqlite_global_mutex);\\n    ep_gc_exit_blocking();\\n    return res;\\n}\\nlong long sql_execute_impl(long long db, long long sql) {'
)
content = content.replace(
    'long long sql_query(long long db, long long sql) {',
    'long long sql_query_impl(long long db, long long sql);\\nlong long sql_query(long long db, long long sql) {\\n    ep_gc_enter_blocking();\n    pthread_mutex_lock(&ep_sqlite_global_mutex);\n    long long res = sql_query_impl(db, sql);\\n    pthread_mutex_unlock(&ep_sqlite_global_mutex);\\n    ep_gc_exit_blocking();\\n    return res;\\n}\\nlong long sql_query_impl(long long db, long long sql) {'
)
content = content.replace(
    'long long sql_execute_params(long long db, long long sql, long long params) {',
    'long long sql_execute_params_impl(long long db, long long sql, long long params);\\nlong long sql_execute_params(long long db, long long sql, long long params) {\\n    ep_gc_enter_blocking();\n    pthread_mutex_lock(&ep_sqlite_global_mutex);\n    ep_gc_exit_blocking();\\n    long long res = sql_execute_params_impl(db, sql, params);\\n    pthread_mutex_unlock(&ep_sqlite_global_mutex);\\n    return res;\\n}\\nlong long sql_execute_params_impl(long long db, long long sql, long long params) {'
)
content = content.replace(
    'long long sql_query_params(long long db, long long sql, long long params) {',
    'long long sql_query_params_impl(long long db, long long sql, long long params);\\nlong long sql_query_params(long long db, long long sql, long long params) {\\n    ep_gc_enter_blocking();\n    pthread_mutex_lock(&ep_sqlite_global_mutex);\n    ep_gc_exit_blocking();\\n    long long res = sql_query_params_impl(db, sql, params);\\n    pthread_mutex_unlock(&ep_sqlite_global_mutex);\\n    return res;\\n}\\nlong long sql_query_params_impl(long long db, long long sql, long long params) {'
)

with open('decent_agent/test_agent_compiled.c', 'w') as f:
    f.write(content)
print('Patched conflicting mutex declarations, test blocking barriers, and SQLite thread-safety in test_agent_compiled.c')
"

    # Additive runtime helpers (cast/cancel/json/async) via the SHARED injector — the root
    # fix for the cognitive-agent test suite failing to LINK: it never injected ep_cancel_*,
    # ep_json_escape, or async_wait_readable_timeout, so it never built and every regression
    # went unseen. Same function the node build uses; the two can no longer drift.
    inject_additive_helpers decent_agent/test_agent_compiled.c

    # Setup library paths
    CFLAGS="-O2 -lpthread -DEP_HAS_SQLITE -lsqlite3 -Wno-int-conversion -Wno-parentheses-equality"
    OS="$(uname -s)"
    case "$OS" in
        Darwin)
            if [ -d "/opt/homebrew/lib" ]; then
                CFLAGS="$CFLAGS -I/opt/homebrew/include -L/opt/homebrew/lib -lsodium -lsecp256k1 -I/opt/homebrew/opt/openssl/include -L/opt/homebrew/opt/openssl/lib -lcrypto"
            elif [ -d "/usr/local/lib" ]; then
                CFLAGS="$CFLAGS -I/usr/local/include -L/usr/local/lib -lsodium -lsecp256k1 -I/usr/local/opt/openssl/include -L/usr/local/opt/openssl/lib -lcrypto"
            else
                CFLAGS="$CFLAGS -lsodium -lsecp256k1 -lcrypto"
            fi
            ;;
        Linux)
            CFLAGS="$CFLAGS -lsodium -lsecp256k1 -lcrypto -lm"
            ;;
    esac
    
    clang decent_agent/test_agent_compiled.c runtime/websocket_runtime.c runtime/nostr_runtime.c $SD_SHIM_SRC -o ./decent_agent/test_agent $CFLAGS $SD_CFLAGS 2>&1
    if [ "$OS" = "Darwin" ]; then
        codesign --force -s - ./decent_agent/test_agent
    fi
    echo "[+] Build complete: ./decent_agent/test_agent"
    if [ "${1:-}" = "--compile-agent-test" ]; then
        exit 0
    fi
    echo "[*] Running tests..."
    ./decent_agent/test_agent
    
    echo ""
    echo "[*] Building GitDec Host Election Test Suite..."
    bash scripts/compile_ep.sh decent_net/test_host_election.ep
    echo "[*] Running GitDec Host Election tests..."
    ./decent_net/test_host_election
    
    exit 0
fi

echo "[*] Building ErnosDecent node..."

# Detect OS and architecture
OS="$(uname -s)"
ARCH="$(uname -m)"
echo "[*] Platform: $OS $ARCH"

# Find the Ernos compiler
if command -v ernos &>/dev/null; then
    ERNOS="ernos"
elif [ -f "$HOME/.local/bin/ernos" ]; then
    ERNOS="$HOME/.local/bin/ernos"
elif [ -f "/usr/local/bin/ernos" ]; then
    ERNOS="/usr/local/bin/ernos"
else
    echo "[-] Ernos compiler not found. Install it first."
    exit 1
fi

echo "[*] Using compiler: $ERNOS"

# Step 0: Compile frontend app.ep to app.js
echo "[*] Compiling frontend app.ep to app.js..."
$ERNOS emit decent_web/app.ep --js -o decent_web/app.js

# Step 1: Compile ErnosPlain -> C (the compiler's own link step is expected to
# fail because it doesn't know about the injected runtime functions; we patch and
# relink below). BUT we must FAIL LOUD if the type-checker aborted and no fresh C
# was emitted -- otherwise build.sh silently relinks a STALE node_compiled.c and
# ships a binary that doesn't match the source.
rm -f node_compiled.c
set +e
ERNOS_OUT=$($ERNOS node.ep 2>&1)
ERNOS_STATUS=$?
set -e
echo "$ERNOS_OUT" | tail -6
# Fail loud if the compiler aborted before emitting fresh C. Cover BOTH classes that
# leave a stale node_compiled.c behind: type errors AND codegen/safety errors (e.g.
# "Code Generation Error", "Safety Error", "Compilation failed"). The latter do NOT
# contain "type error", so a grep for only that would silently relink the stale C.
if [ ! -s node_compiled.c ]; then
    echo "[-] BUILD FAILED: 'ernos node.ep' did not emit fresh C."
    exit 1
fi
python3 scripts/patch_generated_network.py node_compiled.c
if [ "$ERNOS_STATUS" -ne 0 ] && ! printf '%s\n' "$ERNOS_OUT" | grep -qE "undefined symbol|Undefined symbols|undefined reference"; then
    echo "[-] BUILD FAILED: 'ernos node.ep' failed before the expected runtime-link stage."
    exit "$ERNOS_STATUS"
fi
if echo "$ERNOS_OUT" | grep -qE "type error\(s\) found|Code Generation Error|Safety Error|Compilation failed|Compiler Error"; then
    echo "[-] BUILD FAILED: 'ernos node.ep' aborted (type or codegen/safety error) and did NOT emit fresh C."
    echo "[-] Refusing to relink the stale node_compiled.c. Fix the error reported above first."
    exit 1
fi

# Step 2: Patch SIGPIPE ignore into the C runtime
# The ErnosPlain compiler's signal handler catches SIGFPE/SIGSEGV/SIGABRT
# but not SIGPIPE. Network daemons MUST ignore SIGPIPE to survive
# socket write failures (e.g., client disconnect mid-write).
if grep -q "SIGPIPE" node_compiled.c; then
    echo "[*] SIGPIPE already patched."
else
    # Use sed compatible with both macOS (BSD) and Linux (GNU)
    if [ "$OS" = "Darwin" ]; then
        sed -i '' 's/signal(SIGABRT, ep_signal_handler);/signal(SIGABRT, ep_signal_handler);\
#ifndef _WIN32\
    signal(SIGPIPE, SIG_IGN);\
#endif/' node_compiled.c
    else
        sed -i 's/signal(SIGABRT, ep_signal_handler);/signal(SIGABRT, ep_signal_handler);\n#ifndef _WIN32\n    signal(SIGPIPE, SIG_IGN);\n#endif/' node_compiled.c
    fi
    echo "[*] Patched SIGPIPE ignore."
fi

# Step 2a2: Patch ep_signal_handler to write crash log to disk
# The runtime's default handler prints to stderr only. When the daemon runs
# detached (nohup) or the terminal is closed, crash info is lost. This patch
# adds file-based crash logging before _exit().
if grep -q "ep_crash_log_written" node_compiled.c; then
    echo "[*] Crash log patch already applied."
else
python3 -c "
import sys
import re
with open('node_compiled.c', 'r') as f:
    src = f.read()

pattern = r'static\s+void\s+ep_signal_handler\s*\(\s*int\s+sig\s*\)\s*\{'
match = re.search(pattern, src)
if match:
    start_idx = match.start()
    brace_idx = match.end() - 1
    brace_count = 1
    idx = brace_idx + 1
    while brace_count > 0 and idx < len(src):
        if src[idx] == '{':
            brace_count += 1
        elif src[idx] == '}':
            brace_count -= 1
        idx += 1
    end_idx = idx

    new_handler = '''static void ep_signal_handler(int sig) {
    if (ep_try_active) {
        ep_try_active = 0;
        longjmp(ep_try_buf, sig);
    }
    /* Outside try: print error, write crash log, and exit */
    static volatile int ep_crash_log_written = 0;
    if (ep_crash_log_written) _exit(128 + sig); /* prevent re-entry */
    ep_crash_log_written = 1;
    const char* name = sig == SIGSEGV ? \"segmentation fault (null pointer or invalid memory access)\"
                     : sig == SIGFPE  ? \"arithmetic error (division by zero)\"
                     : sig == SIGABRT ? \"aborted\"
                     : \"unknown signal\";
    fprintf(stderr, \"\\\\nRuntime Error: %s (signal %d)\\\\n\", name, sig);
    /* Write crash details to ~/.ernosdecent/crash.log */
    const char* home = getenv(\"HOME\");
    if (home) {
        char crash_path[512];
        snprintf(crash_path, sizeof(crash_path), \"%s/.ernosdecent/crash.log\", home);
        FILE* cf = fopen(crash_path, \"a\");
        if (cf) {
            time_t now = time(NULL);
            struct tm* t = localtime(&now);
            char ts[64];
            if (t) {
                strftime(ts, sizeof(ts), \"%Y-%m-%d %H:%M:%S\", t);
            } else {
                snprintf(ts, sizeof(ts), \"%lld\", (long long)now);
            }
            fprintf(cf, \"\\\\n=== CRASH at %s ===\\\\n\", ts);
            fprintf(cf, \"Signal: %d (%s)\\\\n\", sig, name);
#if defined(__APPLE__) || defined(__linux__)
            /* backtrace — best-effort, async-signal-unsafe but widely used in crash handlers */
            void* bt[64];
            int bt_n = backtrace(bt, 64);
            if (bt_n > 0) {
                fprintf(cf, \"Backtrace (%d frames):\\\\n\", bt_n);
                /* backtrace_symbols_fd writes to a file descriptor — fd from fileno */
                backtrace_symbols_fd(bt, bt_n, fileno(cf));
            }
#endif
            fclose(cf);
        }
    }
    /* Write to daemon/general log file if environment variable is set */
    const char* daemon_log = getenv(\"ERNOS_DAEMON_LOG\");
    if (!daemon_log || daemon_log[0] == '\\\\0') {
        daemon_log = getenv(\"ERNOS_LOG_FILE\");
    }
    if (daemon_log && daemon_log[0] != '\\\\0') {
        FILE* f = fopen(daemon_log, \"ab\");
        if (f) {
            time_t rawtime;
            time(&rawtime);
            struct tm * timeinfo = localtime(&rawtime);
            char time_buf[80];
            if (timeinfo) {
                strftime(time_buf, sizeof(time_buf), \"%Y-%m-%d %H:%M:%S\", timeinfo);
            } else {
                snprintf(time_buf, sizeof(time_buf), \"%lld\", (long long)rawtime);
            }
            fprintf(f, \"[%s] FATAL: Runtime Error: %s (signal %d)\\\\n\", time_buf, name, sig);
            fclose(f);
        }
    }
    _exit(128 + sig);
}'''

    src = src[:start_idx] + new_handler + src[end_idx:]
    # Add backtrace include if not present
    if '#include <execinfo.h>' not in src:
        src = src.replace('#include <signal.h>', '#include <signal.h>\\n#if defined(__APPLE__) || defined(__linux__)\\n#include <execinfo.h>\\n#endif')
    with open('node_compiled.c', 'w') as f:
        f.write(src)
    print('Patched ep_signal_handler dynamically in node_compiled.c')
else:
    raise SystemExit('ERROR: ep_signal_handler signature not found — refusing build without crash logging')
"
    echo "[*] Crash log patch applied."
fi

# Step 2b: ep_net_send_raw is owned by patch_generated_network.py above. It
# structurally detects the native definition emitted by newer compilers and injects
# exactly one for older compilers, independent of parameter names.

# Step 2c: Inject additive runtime helpers via the SHARED injector (single source of
# truth, also used by the test build so they cannot drift). The inline block below is
# kept only as a fallback and is now skipped by its own guard once the shared injector
# has run (grep finds cast_borrow_to_map already present).
inject_additive_helpers node_compiled.c
if grep -aq "long long cast_borrow_to_map(long long b) {" node_compiled.c; then
    echo "[*] cast_borrow_to_map already present."
else
    python3 -c "
with open('node_compiled.c', 'r') as f:
    content = f.read()
inject = '''
long long cast_borrow_to_map(long long b) {
    return b;
}

long long cast_map_to_int(long long m) {
    return m;
}

/* Global cancel-all flag. Set by the web thread (/api/cancel) and read by the ReAct
   loop at each turn boundary. A plain process global — deliberately NOT a SQLite row
   (avoids contending on the global SQLite mutex, which under DB-heavy turns delayed the
   cancel by seconds) and NOT an ErnosPlain map (avoids cross-thread mutation of a
   GC-managed object). A single word written/read atomically enough for a stop signal. */
volatile long long ep_cancel_all_flag = 0;
long long ep_cancel_set(long long v) {
    ep_cancel_all_flag = v;
    return 0;
}
long long ep_cancel_get(long long dummy) {
    return ep_cancel_all_flag;
}

/* One-pass JSON string escaper. The ErnosPlain get_character builtin is O(n) (it
   re-walks the string every call), so the pure-.ep json_escape_string looped
   O(n^2) over the prompt — escaping a ~42K-char turn prompt was ~1.8 billion char
   walks (~2s), and the ~63K observer prompt ~4 billion (~4s), on EVERY LLM call.
   That was the bulk of per-turn latency and had nothing to do with model/context/
   hardware. This does it in a single O(n) C pass. It also escapes control chars
   (below 32) as backslash-u sequences, which the old code silently dropped. Worst
   case every byte expands to 6 chars, so allocate len*6+1. */
long long ep_json_escape(long long s_ptr) {
    const char* s = (const char*)s_ptr;
    if (!s) return (long long)strdup(\"\");
    size_t len = strlen(s);
    char* out = (char*)malloc(len * 6 + 1);
    if (!out) return (long long)strdup(\"\");
    static const char hexd[] = \"0123456789abcdef\";
    size_t j = 0;
    size_t i;
    for (i = 0; i < len; i++) {
        unsigned char c = (unsigned char)s[i];
        if (c == 34)      { out[j++]=92; out[j++]=34;  }
        else if (c == 92) { out[j++]=92; out[j++]=92;  }
        else if (c == 10) { out[j++]=92; out[j++]=110; }
        else if (c == 13) { out[j++]=92; out[j++]=114; }
        else if (c == 9)  { out[j++]=92; out[j++]=116; }
        else if (c < 32)  { out[j++]=92; out[j++]=117; out[j++]=48; out[j++]=48; out[j++]=hexd[(c>>4)&15]; out[j++]=hexd[c&15]; }
        else              { out[j++]=(char)c; }
    }
    out[j] = 0;
    long long r = (long long)strdup(out);
    free(out);
    return r;
}

/* Awaitable readable-OR-timeout. Returns a future that completes with 1 when fd is
   readable, or 0 when timeout_ms elapses — whichever fires first. Built from the same
   primitives async_wait_readable uses (a future + a read task) plus a timer task on the
   SAME future, so the normal await state machine drives it with no nested event-loop
   pump. Without this, http_post_async read loop blocks forever if the LLM server
   accepts the connection then never responds, freezing the single-threaded daemon. The
   loser step is a no-op (guards on !completed) so there is no value clobber or double
   enqueue; each task self-frees when it eventually fires. */
#include <poll.h>
#include <pthread.h>
static pthread_t ep_loop_owner_thread;
__attribute__((constructor)) static void ep_capture_loop_owner(void) {
    ep_loop_owner_thread = pthread_self();
}
static EpFuture* ep_make_completed_future(long long value) {
    EpFuture* fut = (EpFuture*)malloc(sizeof(EpFuture));
    fut->completed = 1; fut->value = value; fut->waiting_task = NULL; fut->chan = 0;
    { EpGCObject* _go = ep_gc_register(fut, EP_OBJ_STRUCT); if(_go) _go->num_fields = 3; }
    return fut;
}
static long long ep_readto_read_step(void* r) {
    EpReadReadyArgs* a = (EpReadReadyArgs*)r;
    if (a && a->fut && !a->fut->completed) {
        a->fut->completed = 1; a->fut->value = 1;
        if (a->fut->waiting_task) { ep_task_enqueue(a->fut->waiting_task); a->fut->waiting_task = NULL; }
    }
    return 0;
}
static long long ep_readto_timer_step(void* r) {
    EpReadReadyArgs* a = (EpReadReadyArgs*)r;
    if (a && a->fut && !a->fut->completed) {
        a->fut->completed = 1; a->fut->value = 0;
        if (a->fut->waiting_task) { ep_task_enqueue(a->fut->waiting_task); a->fut->waiting_task = NULL; }
    }
    return 0;
}
long long async_wait_readable_timeout(long long fd, long long timeout_ms) {
    if (!pthread_equal(pthread_self(), ep_loop_owner_thread)) {
        /* Worker thread: NEVER touch the shared loop — plain poll, pre-completed future. */
        struct pollfd p; p.fd = (int)fd; p.events = POLLIN; p.revents = 0;
        int r = poll(&p, 1, (int)timeout_ms);
        return (long long)ep_make_completed_future(r > 0 ? 1 : 0);
    }
    EpFuture* fut = (EpFuture*)malloc(sizeof(EpFuture));
    fut->completed = 0; fut->value = 0; fut->waiting_task = NULL; fut->chan = 0;
    { EpGCObject* _go = ep_gc_register(fut, EP_OBJ_STRUCT); if(_go) _go->num_fields = 3; }
    EpReadReadyArgs* rargs = (EpReadReadyArgs*)malloc(sizeof(EpReadReadyArgs));
    rargs->fut = fut;
    EpTask* rtask = (EpTask*)malloc(sizeof(EpTask));
    rtask->step = ep_readto_read_step; rtask->args = rargs;
    rtask->args_size_bytes = sizeof(EpReadReadyArgs);
    rtask->fut = NULL; rtask->state = 0; rtask->is_cancelled = 0; rtask->parent = ep_current_task;
    ep_async_register_read((int)fd, rtask);
    EpReadReadyArgs* targs = (EpReadReadyArgs*)malloc(sizeof(EpReadReadyArgs));
    targs->fut = fut;
    EpTask* ttask = (EpTask*)malloc(sizeof(EpTask));
    ttask->step = ep_readto_timer_step; ttask->args = targs;
    ttask->args_size_bytes = sizeof(EpReadReadyArgs);
    ttask->fut = NULL; ttask->state = 0; ttask->is_cancelled = 0; ttask->parent = ep_current_task;
    ep_async_register_timer(timeout_ms, ttask);
    return (long long)fut;
}

'''
pat = 'long long ep_net_send(long long fd, const char* data) {'
first = content.find(pat)
second = content.find(pat, first + 1)
if second > 0:
    content = content[:second] + inject + content[second:]
    with open('node_compiled.c', 'w') as f:
        f.write(content)
    print('Injected cast_borrow_to_map/cast_map_to_int')
else:
    raise SystemExit('ERROR: could not find second ep_net_send for cast_borrow_to_map')
"
    echo "[*] Injected cast_borrow_to_map/cast_map_to_int."
fi

# Step 2d: Patch conflicting mutex declarations & disable stdout/stderr buffering, and inject GC blocking helpers
python3 -c "
with open('node_compiled.c', 'r') as f:
    content = f.read()
content = content.replace('long long ep_mutex_lock(long long);', '')
content = content.replace('long long ep_mutex_unlock(long long);', '')
content = content.replace('int main(int argc, char** argv) {', 'int main(int argc, char** argv) {\\n    setvbuf(stdout, NULL, _IONBF, 0);\\n    setvbuf(stderr, NULL, _IONBF, 0);')

content = content.replace(
    '#define EP_GC_UPDATE_TOP() { volatile int _dummy; ep_thread_local_top = (void*)&_dummy; }',
    '''#define EP_GC_UPDATE_TOP() { volatile int _dummy; ep_thread_local_top = (void*)&_dummy; }

static void ep_gc_enter_blocking(void) {
    EP_GC_UPDATE_TOP();
    if (ep_thread_slot >= 0) {
        pthread_mutex_lock(&ep_gc_mutex);
        ep_thread_active[ep_thread_slot] = 0;
        pthread_mutex_unlock(&ep_gc_mutex);
    }
}

static void ep_gc_exit_blocking(void) {
    if (ep_thread_slot >= 0) {
        pthread_mutex_lock(&ep_gc_mutex);
        while (ep_gc_stop_requested) {
            pthread_cond_wait(&ep_gc_resume_cond, &ep_gc_mutex);
        }
        ep_thread_active[ep_thread_slot] = 1;
        pthread_mutex_unlock(&ep_gc_mutex);
    }
}
'''
)

with open('node_compiled.c', 'w') as f:
    f.write(content)
print('Patched conflicting mutex declarations, buffering, and GC blocking helpers in node_compiled.c')
"

# Step 2e: Patch ep_net_recv_bytes to return NULL (0) on short reads
python3 -c "
with open('node_compiled.c', 'r') as f:
    content = f.read()
first = content.find('long long ep_net_recv_bytes')
second = content.find('long long ep_net_recv_bytes', first + 1)
if second > 0:
    idx = content.find('{', second)
    brace_count = 1
    idx += 1
    while brace_count > 0 and idx < len(content):
        if content[idx] == '{':
            brace_count += 1
        elif content[idx] == '}':
            brace_count -= 1
        idx += 1
    replacement = '''long long ep_net_recv_bytes(long long fd, long long count) {
    if (count <= 0) return 0;
    char* buf = (char*)malloc(count + 1);
    ssize_t total = 0;
    ep_gc_enter_blocking();
    while (total < count) {
        ssize_t n = recv((int)fd, buf + total, count - total, 0);
        if (n <= 0) break;
        total += n;
    }
    ep_gc_exit_blocking();
    if (total < count) {
        free(buf);
        return 0;
    }
    buf[total] = '\\\\0';
    ep_gc_register(buf, EP_OBJ_STRING);
    return (long long)buf;
}'''
    content = content[:second] + replacement + content[idx:]
    with open('node_compiled.c', 'w') as f:
        f.write(content)
    print('Patched ep_net_recv_bytes in node_compiled.c')
else:
    raise SystemExit('ERROR: could not find second ep_net_recv_bytes')
"

# Step 2f: Patch ep_run_command to be dynamic and overflow-safe
python3 -c "
with open('node_compiled.c', 'r') as f:
    content = f.read()
pat = 'long long ep_run_command(long long cmd_ptr) {'
first = content.find(pat)
second = content.find(pat, first + 1)
if second > 0:
    idx = content.find('{', second)
    brace_count = 1
    idx += 1
    while brace_count > 0 and idx < len(content):
        if content[idx] == '{':
            brace_count += 1
        elif content[idx] == '}':
            brace_count -= 1
        idx += 1
    replacement = '''long long ep_run_command(long long cmd_ptr) {
    const char* cmd = (const char*)cmd_ptr;
    FILE* fp = popen(cmd, \"r\");
    if (!fp) return (long long)\"\";
    size_t capacity = 65536;
    char* result = (char*)malloc(capacity);
    size_t total = 0;
    char buf[4096];
    while (fgets(buf, sizeof(buf), fp)) {
        size_t len = strlen(buf);
        if (total + len + 1 >= capacity) {
            capacity *= 2;
            while (total + len + 1 >= capacity) {
                capacity *= 2;
            }
            char* new_result = (char*)realloc(result, capacity);
            if (!new_result) {
                break;
            }
            result = new_result;
        }
        memcpy(result + total, buf, len);
        total += len;
    }
    result[total] = '\\\\0';
    pclose(fp);
    return (long long)result;
}'''
    content = content[:second] + replacement + content[idx:]
    with open('node_compiled.c', 'w') as f:
        f.write(content)
    print('Patched ep_run_command in node_compiled.c')
else:
    raise SystemExit('ERROR: could not find second ep_run_command')
"

# Step 2g: Bind the local control plane to loopback (security hardening).
# ep_net_listen() binds INADDR_ANY (0.0.0.0), exposing every listener to the
# whole network. The IPC control port and the (currently unauthenticated) Web
# UI must NOT be reachable off-box, so we add ep_net_listen_loopback() (binds
# 127.0.0.1) and retarget ONLY those two call sites. P2P/DHT/relay keep using
# ep_net_listen() because remote peers legitimately connect to them.
python3 -c "
import sys
with open('node_compiled.c', 'r') as f:
    content = f.read()

if 'ep_net_listen_loopback' in content:
    print('[*] ep_net_listen_loopback already present.')
else:
    pat = 'long long ep_net_listen(long long port) {'
    first = content.find(pat)
    second = content.find(pat, first + 1)
    target = second if second > 0 else first
    if target < 0:
        sys.exit('SECURITY PATCH FAILED: ep_net_listen definition not found; refusing to ship a publicly-bound node.')
    else:
        inject = '''
// Loopback-only TCP listener (binds 127.0.0.1). Used for the IPC control plane
// and the unauthenticated Web UI so they are not exposed to the network.
// P2P/DHT/relay keep ep_net_listen (INADDR_ANY) so remote peers can reach them.
long long ep_net_listen_loopback(long long port) {
    int sockfd = socket(AF_INET, SOCK_STREAM, 0);
    if (sockfd < 0) return -1;
    int opt = 1;
    setsockopt(sockfd, SOL_SOCKET, SO_REUSEADDR, (const char*)&opt, sizeof(opt));
    struct sockaddr_in serv_addr;
    memset(&serv_addr, 0, sizeof(serv_addr));
    serv_addr.sin_family = AF_INET;
    serv_addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    serv_addr.sin_port = htons(port);
    if (bind(sockfd, (struct sockaddr*)&serv_addr, sizeof(serv_addr)) < 0) {
#ifdef _WIN32
        closesocket(sockfd);
#else
        close(sockfd);
#endif
        return -1;
    }
    if (listen(sockfd, 10) < 0) {
#ifdef _WIN32
        closesocket(sockfd);
#else
        close(sockfd);
#endif
        return -1;
    }
    return sockfd;
}

'''
        content = content[:target] + inject + content[target:]

        applied_ipc = False
        applied_web = False

        # IPC control plane -> loopback (token is unique in the generated C)
        ipc_old = 'listen_fd = ep_net_listen(ipc_port);'
        ipc_new = 'listen_fd = ep_net_listen_loopback(ipc_port);'
        n_ipc = content.count(ipc_old)
        if n_ipc != 1:
            sys.exit('SECURITY PATCH FAILED: expected exactly 1 IPC listen site, found ' + str(n_ipc) + '; refusing to ship a publicly-bound node.')
        content = content.replace(ipc_old, ipc_new)
        applied_ipc = True

        # Web UI: change ONLY the ep_net_listen call inside start_server()
        ss = content.find('long long start_server(long long port) {')
        if ss < 0:
            sys.exit('SECURITY PATCH FAILED: start_server not found; refusing to ship a publicly-bound Web UI.')
        call = content.find('ep_net_listen(port);', ss)
        if call < 0:
            sys.exit('SECURITY PATCH FAILED: ep_net_listen call inside start_server not found; refusing to ship a publicly-bound Web UI.')
        old_call = 'ep_net_listen(port);'
        content = content[:call] + 'ep_net_listen_loopback(port);' + content[call + len(old_call):]
        applied_web = True

        with open('node_compiled.c', 'w') as f:
            f.write(content)
        print('[*] Bound IPC + Web UI to loopback (127.0.0.1); P2P/DHT/relay remain public.')
"

# Step 2h: Inject tools_set_active_session and refactor ep_http_request in node_compiled.c
python3 -c "
with open('node_compiled.c', 'r') as f:
    content = f.read()

if 'ep_active_session_id' in content:
    print('[*] tools_set_active_session already present.')
else:
    inject_decl = '''
#include <errno.h>
#include <fcntl.h>
#include <unistd.h>

long long react_check_cancel(long long, long long); /* (session_id, run_epoch) - epoch latch, see react_loop.ep */
long long ep_cancel_epoch_get(long long);
long long react_request_cancel(long long);
long long ptr_to_str(long long);

__thread char ep_active_session_id[256] = \"\";

long long tools_set_active_session(long long sid_ptr) {
    const char* sid = (const char*)sid_ptr;
    if (sid) {
        strncpy(ep_active_session_id, sid, sizeof(ep_active_session_id) - 1);
        ep_active_session_id[sizeof(ep_active_session_id) - 1] = '\\\\0';
    } else {
        ep_active_session_id[0] = '\\\\0';
    }
    return 0;
}

'''
    pat_http = 'long long ep_http_request(long long method_val, long long url_val, long long headers_val, long long body_val) {'
    first_http = content.find(pat_http)
    second_http = content.find(pat_http, first_http + 1)
    target_http = second_http if second_http > 0 else first_http
    if target_http > 0:
        content = content[:target_http] + inject_decl + content[target_http:]
        
        # Replace the recv loop in the second ep_http_request
        old_recv_loop = '''    char recv_buf[4096];
    ssize_t n;
    while ((n = recv(sockfd, recv_buf, sizeof(recv_buf), 0)) > 0) {
        if (resp_len + n >= resp_cap) {
            resp_cap *= 2;
            char* new_resp = realloc(resp, resp_cap);
            if (!new_resp) {
                free(resp);
                close(sockfd);
                return (long long)strdup(\"Error: memory allocation failed\");
            }
            resp = new_resp;
        }
        memcpy(resp + resp_len, recv_buf, n);
        resp_len += n;
    }
    resp[resp_len] = '\\\\0';
    close(sockfd);'''

        new_recv_loop = '''    // Set socket to non-blocking mode
    fcntl(sockfd, F_SETFL, O_NONBLOCK);

    char recv_buf[4096];
    ssize_t n;
    int aborted = 0;
    long long rc_epoch = ep_cancel_epoch_get(0); /* epoch at read start: any Stop after this aborts */
    while (1) {
        if (ep_active_session_id[0] != '\\\\0') {
            long long gc_sid = ptr_to_str((long long)ep_active_session_id);
            if (react_check_cancel(gc_sid, rc_epoch) == 1) {
                aborted = 1;
                break;
            }
        }
        n = recv(sockfd, recv_buf, sizeof(recv_buf), 0);
        if (n > 0) {
            if (resp_len + n >= resp_cap) {
                resp_cap *= 2;
                char* new_resp = realloc(resp, resp_cap);
                if (!new_resp) {
                    free(resp);
                    close(sockfd);
                    return (long long)strdup(\"Error: memory allocation failed\");
                }
                resp = new_resp;
            }
            memcpy(resp + resp_len, recv_buf, n);
            resp_len += n;
        } else if (n == 0) {
            break;
        } else {
            if (errno == EAGAIN || errno == EWOULDBLOCK) {
                usleep(50000); // 50ms
                continue;
            } else {
                break;
            }
        }
    }
    if (aborted) {
        free(resp);
        close(sockfd);
        long long gc_sid = ptr_to_str((long long)ep_active_session_id);
        react_request_cancel(gc_sid);
        return (long long)strdup(\"Error: Request aborted by user\");
    }
    resp[resp_len] = '\\\\0';
    close(sockfd);'''

        if old_recv_loop in content:
            content = content.replace(old_recv_loop, new_recv_loop)
            with open('node_compiled.c', 'w') as f:
                f.write(content)
            print('[*] Patched HTTP Client non-blocking session check in node_compiled.c')
        else:
            print('Exact HTTP receive-loop pattern changed; trying the verified structural pattern.')
            import re
            loop_pattern = r'char\\\\s+recv_buf\\\\[4096\\\\];.*?while\\\\s*\\\\(\\\\(n\\\\s*=\\\\s*recv.*?close\\\\(sockfd\\\\);'
            content, count = re.subn(loop_pattern, new_recv_loop, content, flags=re.DOTALL)
            if count > 0:
                with open('node_compiled.c', 'w') as f:
                    f.write(content)
                print('[*] Patched HTTP Client non-blocking session check via regex in node_compiled.c')
            else:
                raise SystemExit('ERROR: HTTP client patch failed to locate recv loop target')
    else:
        raise SystemExit('ERROR: HTTP client patch failed to locate ep_http_request')
"

# Step 2i: Patch SQLite functions and wrap blocking calls to be thread-safe
python3 -c "
with open('node_compiled.c', 'r') as f:
    content = f.read()

# 1. Inject SQLite global mutex and wrap SQL functions
inject = '''static pthread_mutex_t ep_sqlite_global_mutex = PTHREAD_MUTEX_INITIALIZER;\\n'''

content = content.replace(
    'long long sql_execute(long long db, long long sql) {',
    inject + '''long long sql_execute_impl(long long db, long long sql);\\nlong long sql_execute(long long db, long long sql) {\\n    ep_gc_enter_blocking();\n    pthread_mutex_lock(&ep_sqlite_global_mutex);\n    long long res = sql_execute_impl(db, sql);\\n    pthread_mutex_unlock(&ep_sqlite_global_mutex);\\n    ep_gc_exit_blocking();\\n    return res;\\n}\\nlong long sql_execute_impl(long long db, long long sql) {'''
)

content = content.replace(
    'long long sql_query(long long db, long long sql) {',
    '''long long sql_query_impl(long long db, long long sql);\\nlong long sql_query(long long db, long long sql) {\\n    ep_gc_enter_blocking();\n    pthread_mutex_lock(&ep_sqlite_global_mutex);\n    long long res = sql_query_impl(db, sql);\\n    pthread_mutex_unlock(&ep_sqlite_global_mutex);\\n    ep_gc_exit_blocking();\\n    return res;\\n}\\nlong long sql_query_impl(long long db, long long sql) {'''
)

content = content.replace(
    'long long sql_execute_params(long long db, long long sql, long long params) {',
    '''long long sql_execute_params_impl(long long db, long long sql, long long params);\\nlong long sql_execute_params(long long db, long long sql, long long params) {\\n    ep_gc_enter_blocking();\n    pthread_mutex_lock(&ep_sqlite_global_mutex);\n    ep_gc_exit_blocking();\\n    long long res = sql_execute_params_impl(db, sql, params);\\n    pthread_mutex_unlock(&ep_sqlite_global_mutex);\\n    return res;\\n}\\nlong long sql_execute_params_impl(long long db, long long sql, long long params) {'''
)

content = content.replace(
    'long long sql_query_params(long long db, long long sql, long long params) {',
    '''long long sql_query_params_impl(long long db, long long sql, long long params);\\nlong long sql_query_params(long long db, long long sql, long long params) {\\n    ep_gc_enter_blocking();\n    pthread_mutex_lock(&ep_sqlite_global_mutex);\n    ep_gc_exit_blocking();\\n    long long res = sql_query_params_impl(db, sql, params);\\n    pthread_mutex_unlock(&ep_sqlite_global_mutex);\\n    return res;\\n}\\nlong long sql_query_params_impl(long long db, long long sql, long long params) {'''
)

# 2. Wrap blocking calls in node_compiled.c
def wrap_second_occ(content, sig, impl_sig, call_wrapper_body):
    first = content.find(sig)
    second = content.find(sig, first + 1)
    target = second if second > 0 else first
    if target > 0:
        wrapper = f'{impl_sig};\\n{sig} {{\\n{call_wrapper_body}\\n}}\\n'
        content = content[:target] + wrapper + impl_sig + content[target + len(sig):]
    return content

content = wrap_second_occ(content, 'long long ep_run_command(long long cmd_ptr)', 'long long ep_run_command_impl(long long cmd_ptr)', '    ep_gc_enter_blocking();\n    long long res = ep_run_command_impl(cmd_ptr);\n    ep_gc_exit_blocking();\n    return res;')
content = wrap_second_occ(content, 'long long ep_sleep_ms(long long ms)', 'long long ep_sleep_ms_impl(long long ms)', '    ep_gc_enter_blocking();\\n    long long res = ep_sleep_ms_impl(ms);\\n    ep_gc_exit_blocking();\\n    return res;')
content = wrap_second_occ(content, 'long long ep_net_accept(long long server_fd)', 'long long ep_net_accept_impl(long long server_fd)', '    ep_gc_enter_blocking();\\n    long long res = ep_net_accept_impl(server_fd);\\n    ep_gc_exit_blocking();\\n    return res;')
content = wrap_second_occ(content, 'char* ep_net_recv(long long fd, long long max_len)', 'char* ep_net_recv_impl(long long fd, long long max_len)', '    ep_gc_enter_blocking();\\n    char* res = ep_net_recv_impl(fd, max_len);\\n    ep_gc_exit_blocking();\\n    return res;')
content = wrap_second_occ(content, 'long long ep_http_request(long long method_val, long long url_val, long long headers_val, long long body_val)', 'long long ep_http_request_impl(long long method_val, long long url_val, long long headers_val, long long body_val)', '    ep_gc_enter_blocking();\\n    long long res = ep_http_request_impl(method_val, url_val, headers_val, body_val);\\n    ep_gc_exit_blocking();\\n    return res;')

with open('node_compiled.c', 'w') as f:
    f.write(content)
print('[+] Applied SQLite thread-safety and GC blocking barrier patches to node_compiled.c')
"

# Step 3: Set platform-specific library paths and compile
CFLAGS="-O2 -lpthread -DEP_HAS_SQLITE -lsqlite3 -Wno-int-conversion -Wno-parentheses-equality"

case "$OS" in
    Darwin)
        # macOS: detect Homebrew prefix (ARM64 vs Intel)
        if [ -d "/opt/homebrew/lib" ]; then
            # Apple Silicon (ARM64)
            CFLAGS="$CFLAGS -I/opt/homebrew/include -L/opt/homebrew/lib -lsodium -lsecp256k1"
            CFLAGS="$CFLAGS -I/opt/homebrew/opt/openssl/include -L/opt/homebrew/opt/openssl/lib -lcrypto"
        elif [ -d "/usr/local/lib" ]; then
            # Intel Mac (x86_64 Homebrew)
            CFLAGS="$CFLAGS -I/usr/local/include -L/usr/local/lib -lsodium -lsecp256k1"
            CFLAGS="$CFLAGS -I/usr/local/opt/openssl/include -L/usr/local/opt/openssl/lib -lcrypto"
        else
            CFLAGS="$CFLAGS -lsodium -lsecp256k1 -lcrypto"
        fi
        ;;
    Linux)
        # Linux: libraries from system paths
        CFLAGS="$CFLAGS -lsodium -lsecp256k1 -lcrypto"
        # Some distros need explicit math lib
        CFLAGS="$CFLAGS -lm"
        ;;
    MINGW*|MSYS*|CYGWIN*|Windows_NT)
        echo "[-] Native Windows build is not supported by this script."
        echo "    On Windows, run ErnosDecent under WSL2 (Ubuntu) — it builds + runs"
        echo "    exactly like Linux. Install WSL2, open the Ubuntu shell, then:"
        echo "        sudo apt install -y clang libsodium-dev libsecp256k1-dev libssl-dev libsqlite3-dev"
        echo "        ./INSTALL.sh   (or bash build.sh if the toolchain is already installed)"
        exit 1
        ;;
    *)
        echo "[-] Unsupported OS: $OS"
        echo "    Supported: macOS, Linux, and Windows via WSL2."
        exit 1
        ;;
esac

echo "[*] Compiling node with the checked WebSocket and image runtimes."
clang node_compiled.c runtime/websocket_runtime.c runtime/nostr_runtime.c $SD_SHIM_SRC -o ./node $CFLAGS $SD_CFLAGS 2>&1

# Step 4: Sign the binary (macOS requirement for notarization)
if [ "$OS" = "Darwin" ]; then
    codesign --force -s - ./node
fi

echo "[+] Build complete: ./node"
echo "[+] Platform: $OS $ARCH"
