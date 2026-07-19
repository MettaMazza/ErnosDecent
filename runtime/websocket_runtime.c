#include <errno.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <sys/random.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <unistd.h>

#define ED_WS_MAX_MESSAGE (10U * 1024U * 1024U)

extern long long ep_net_send_raw(long long fd, long long buffer, long long count);

static int ed_ws_random(void *buffer, size_t count) {
    unsigned char *out = (unsigned char *)buffer;
    while (count > 0) {
        size_t chunk = count > 256 ? 256 : count;
        if (getentropy(out, chunk) != 0) {
            return -errno;
        }
        out += chunk;
        count -= chunk;
    }
    return 0;
}

static int ed_ws_recv_exact(int fd, unsigned char *buffer, size_t count) {
    size_t received = 0;
    while (received < count) {
        ssize_t result = recv(fd, buffer + received, count - received, 0);
        if (result > 0) {
            received += (size_t)result;
            continue;
        }
        if (result == 0) {
            return -EPIPE;
        }
        if (errno == EINTR) {
            continue;
        }
        return -errno;
    }
    return 0;
}

static long long ed_ws_send_frame(int fd, int opcode, const unsigned char *payload,
                                  size_t payload_length, int masked) {
    if (fd < 0 || opcode < 0 || opcode > 15 || payload_length > ED_WS_MAX_MESSAGE) {
        return -EINVAL;
    }
    size_t header_length = payload_length < 126 ? 2 : (payload_length <= 65535 ? 4 : 10);
    size_t mask_length = masked ? 4 : 0;
    if (payload_length > SIZE_MAX - header_length - mask_length) {
        return -EOVERFLOW;
    }
    size_t frame_length = header_length + mask_length + payload_length;
    unsigned char *frame = (unsigned char *)malloc(frame_length == 0 ? 1 : frame_length);
    if (frame == NULL) {
        return -ENOMEM;
    }
    size_t position = 0;
    frame[position++] = (unsigned char)(0x80 | opcode);
    unsigned char mask_bit = masked ? 0x80 : 0;
    if (payload_length < 126) {
        frame[position++] = (unsigned char)(mask_bit | payload_length);
    } else if (payload_length <= 65535) {
        frame[position++] = (unsigned char)(mask_bit | 126);
        frame[position++] = (unsigned char)((payload_length >> 8) & 0xff);
        frame[position++] = (unsigned char)(payload_length & 0xff);
    } else {
        frame[position++] = (unsigned char)(mask_bit | 127);
        uint64_t length64 = (uint64_t)payload_length;
        for (int shift = 56; shift >= 0; shift -= 8) {
            frame[position++] = (unsigned char)((length64 >> shift) & 0xff);
        }
    }
    unsigned char mask[4] = {0, 0, 0, 0};
    if (masked) {
        int random_error = ed_ws_random(mask, sizeof(mask));
        if (random_error != 0) {
            free(frame);
            return random_error;
        }
        memcpy(frame + position, mask, sizeof(mask));
        position += sizeof(mask);
    }
    for (size_t index = 0; index < payload_length; index++) {
        unsigned char value = payload == NULL ? 0 : payload[index];
        frame[position + index] = masked ? (unsigned char)(value ^ mask[index % 4]) : value;
    }
    long long result = ep_net_send_raw(fd, (long long)(intptr_t)frame, (long long)frame_length);
    free(frame);
    return result == (long long)frame_length ? 0 : (result < 0 ? result : -EIO);
}

long long ed_ws_send_text(long long fd, long long message, long long masked) {
    const char *text = (const char *)(intptr_t)message;
    if (text == NULL) {
        return -EINVAL;
    }
    return ed_ws_send_frame((int)fd, 1, (const unsigned char *)text, strlen(text), masked != 0);
}

long long ed_ws_send_close(long long fd, long long masked) {
    return ed_ws_send_frame((int)fd, 8, NULL, 0, masked != 0);
}

long long ed_ws_set_timeout(long long fd, long long timeout_ms) {
    if (fd < 0 || timeout_ms <= 0) {
        return -EINVAL;
    }
    struct timeval timeout;
    timeout.tv_sec = (time_t)(timeout_ms / 1000);
    timeout.tv_usec = (suseconds_t)((timeout_ms % 1000) * 1000);
    if (setsockopt((int)fd, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout)) != 0) {
        return -errno;
    }
    if (setsockopt((int)fd, SOL_SOCKET, SO_SNDTIMEO, &timeout, sizeof(timeout)) != 0) {
        return -errno;
    }
    return 0;
}

char *ed_ws_generate_key(void) {
    unsigned char nonce[16];
    if (ed_ws_random(nonce, sizeof(nonce)) != 0) {
        return strdup("");
    }
    static const char alphabet[] =
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    char *encoded = (char *)malloc(25);
    if (encoded == NULL) {
        return strdup("");
    }
    size_t input = 0;
    size_t output = 0;
    while (input < sizeof(nonce)) {
        uint32_t a = nonce[input++];
        uint32_t b = input < sizeof(nonce) ? nonce[input++] : 0;
        uint32_t c = input < sizeof(nonce) ? nonce[input++] : 0;
        uint32_t triple = (a << 16) | (b << 8) | c;
        encoded[output++] = alphabet[(triple >> 18) & 63];
        encoded[output++] = alphabet[(triple >> 12) & 63];
        encoded[output++] = alphabet[(triple >> 6) & 63];
        encoded[output++] = alphabet[triple & 63];
    }
    encoded[22] = '=';
    encoded[23] = '=';
    encoded[24] = '\0';
    return encoded;
}

char *ed_ws_read_text(long long fd_value, long long expect_masked_value) {
    int fd = (int)fd_value;
    int expect_masked = expect_masked_value != 0;
    unsigned char *message = NULL;
    size_t message_length = 0;
    int message_opcode = 0;

    for (;;) {
        unsigned char header[2];
        if (ed_ws_recv_exact(fd, header, sizeof(header)) != 0) {
            free(message);
            return strdup("");
        }
        int final = (header[0] & 0x80) != 0;
        int reserved = header[0] & 0x70;
        int opcode = header[0] & 0x0f;
        int masked = (header[1] & 0x80) != 0;
        uint64_t payload_length = header[1] & 0x7f;
        if (reserved != 0 || masked != expect_masked) {
            ed_ws_send_frame(fd, 8, NULL, 0, !expect_masked);
            free(message);
            return strdup("");
        }
        if (payload_length == 126) {
            unsigned char extended[2];
            if (ed_ws_recv_exact(fd, extended, sizeof(extended)) != 0) {
                free(message);
                return strdup("");
            }
            payload_length = ((uint64_t)extended[0] << 8) | extended[1];
        } else if (payload_length == 127) {
            unsigned char extended[8];
            if (ed_ws_recv_exact(fd, extended, sizeof(extended)) != 0 || (extended[0] & 0x80) != 0) {
                free(message);
                return strdup("");
            }
            payload_length = 0;
            for (size_t index = 0; index < sizeof(extended); index++) {
                payload_length = (payload_length << 8) | extended[index];
            }
        }
        int control = opcode >= 8;
        if (payload_length > ED_WS_MAX_MESSAGE || (control && (!final || payload_length > 125))) {
            ed_ws_send_frame(fd, 8, NULL, 0, !expect_masked);
            free(message);
            return strdup("");
        }
        unsigned char mask[4] = {0, 0, 0, 0};
        if (masked && ed_ws_recv_exact(fd, mask, sizeof(mask)) != 0) {
            free(message);
            return strdup("");
        }
        unsigned char *payload = (unsigned char *)malloc((size_t)payload_length + 1);
        if (payload == NULL) {
            free(message);
            return strdup("");
        }
        if (payload_length > 0 && ed_ws_recv_exact(fd, payload, (size_t)payload_length) != 0) {
            free(payload);
            free(message);
            return strdup("");
        }
        for (size_t index = 0; index < (size_t)payload_length; index++) {
            if (masked) {
                payload[index] ^= mask[index % 4];
            }
            if (payload[index] == 0) {
                free(payload);
                free(message);
                ed_ws_send_frame(fd, 8, NULL, 0, !expect_masked);
                return strdup("");
            }
        }
        payload[payload_length] = '\0';

        if (opcode == 8) {
            ed_ws_send_frame(fd, 8, payload, (size_t)payload_length, !expect_masked);
            free(payload);
            free(message);
            return strdup("");
        }
        if (opcode == 9) {
            int pong_error = (int)ed_ws_send_frame(fd, 10, payload, (size_t)payload_length, !expect_masked);
            free(payload);
            if (pong_error != 0) {
                free(message);
                return strdup("");
            }
            return strdup("PING_HANDLED");
        }
        if (opcode == 10) {
            free(payload);
            return strdup("PONG_IGNORED");
        }
        if (opcode == 2 || (opcode != 0 && opcode != 1)) {
            free(payload);
            free(message);
            ed_ws_send_frame(fd, 8, NULL, 0, !expect_masked);
            return strdup("");
        }
        if (opcode == 1) {
            if (message_opcode != 0) {
                free(payload);
                free(message);
                return strdup("");
            }
            message_opcode = 1;
        } else if (message_opcode == 0) {
            free(payload);
            free(message);
            return strdup("");
        }
        if (payload_length > ED_WS_MAX_MESSAGE - message_length) {
            free(payload);
            free(message);
            return strdup("");
        }
        unsigned char *grown = (unsigned char *)realloc(message, message_length + (size_t)payload_length + 1);
        if (grown == NULL) {
            free(payload);
            free(message);
            return strdup("");
        }
        message = grown;
        memcpy(message + message_length, payload, (size_t)payload_length);
        message_length += (size_t)payload_length;
        message[message_length] = '\0';
        free(payload);
        if (final) {
            return (char *)message;
        }
    }
}
