#include <errno.h>
#include <limits.h>
#include <poll.h>
#include <stddef.h>
#include <stdint.h>
#include <sys/socket.h>

/*
 * Binary-safe socket send used by the Ernos WebSocket implementation.  The
 * compiler's ep_net_send accepts a NUL-terminated string and therefore cannot
 * transmit frame headers or binary payloads containing zero bytes.
 *
 * Returns the exact byte count on success and a negative errno value on
 * failure.  A blocked socket is given a bounded 30-second writable wait so a
 * failed peer cannot stall the process indefinitely.
 */
#ifndef ERNOSDECENT_GENERATED_NET_SEND_RAW
long long ep_net_send_raw(long long fd_value, long long buffer_value, long long count_value) {
    if (fd_value < 0 || buffer_value == 0 || count_value < 0) {
        return -EINVAL;
    }
    if (count_value == 0) {
        return 0;
    }

    const unsigned char *buffer = (const unsigned char *)(intptr_t)buffer_value;
    size_t count = (size_t)count_value;
    size_t sent = 0;

#if defined(SO_NOSIGPIPE)
    int enabled = 1;
    if (setsockopt((int)fd_value, SOL_SOCKET, SO_NOSIGPIPE, &enabled, sizeof(enabled)) != 0) {
        return -errno;
    }
#endif

    while (sent < count) {
        size_t remaining = count - sent;
        if (remaining > (size_t)SSIZE_MAX) {
            remaining = (size_t)SSIZE_MAX;
        }
#if defined(MSG_NOSIGNAL)
        const int send_flags = MSG_NOSIGNAL;
#else
        const int send_flags = 0;
#endif
        ssize_t written = send((int)fd_value, buffer + sent, remaining, send_flags);
        if (written > 0) {
            sent += (size_t)written;
            continue;
        }
        if (written == 0) {
            return -EPIPE;
        }
        if (errno == EINTR) {
            continue;
        }
        if (errno == EAGAIN || errno == EWOULDBLOCK) {
            struct pollfd writable;
            writable.fd = (int)fd_value;
            writable.events = POLLOUT;
            writable.revents = 0;
            int ready;
            do {
                ready = poll(&writable, 1, 30000);
            } while (ready < 0 && errno == EINTR);
            if (ready > 0 && (writable.revents & POLLOUT) != 0) {
                continue;
            }
            if (ready == 0) {
                return -ETIMEDOUT;
            }
            return ready < 0 ? -errno : -EPIPE;
        }
        return -errno;
    }

    return (long long)sent;
}
#endif
