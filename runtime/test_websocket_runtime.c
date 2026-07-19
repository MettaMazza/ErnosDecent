#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

long long ed_ws_send_text(long long fd, long long message, long long masked);
char *ed_ws_read_text(long long fd, long long expect_masked);
char *ed_ws_generate_key(void);

static int check(int condition, const char *name) {
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", name);
        return 1;
    }
    printf("PASS: %s\n", name);
    return 0;
}

int main(void) {
    int failures = 0;
    int pair[2];
    if (socketpair(AF_UNIX, SOCK_STREAM, 0, pair) != 0) {
        perror("socketpair");
        return 1;
    }

    const char *client_message = "masked client payload";
    failures += check(ed_ws_send_text(pair[0], (long long)client_message, 1) == 0,
                      "masked client frame sends completely");
    char *received = ed_ws_read_text(pair[1], 1);
    failures += check(strcmp(received, client_message) == 0,
                      "server accepts and unmasks client frame");
    free(received);

    const char *server_message = "unmasked server payload";
    failures += check(ed_ws_send_text(pair[1], (long long)server_message, 0) == 0,
                      "unmasked server frame sends completely");
    received = ed_ws_read_text(pair[0], 0);
    failures += check(strcmp(received, server_message) == 0,
                      "client accepts server frame");
    free(received);
    close(pair[0]);
    close(pair[1]);

    if (socketpair(AF_UNIX, SOCK_STREAM, 0, pair) != 0) {
        perror("socketpair");
        return 1;
    }
    failures += check(ed_ws_send_text(pair[0], (long long)"invalid", 0) == 0,
                      "test sends an unmasked peer frame");
    received = ed_ws_read_text(pair[1], 1);
    failures += check(received[0] == '\0', "server rejects an unmasked client frame");
    free(received);
    close(pair[0]);
    close(pair[1]);

    char *key_one = ed_ws_generate_key();
    char *key_two = ed_ws_generate_key();
    failures += check(strlen(key_one) == 24 && key_one[22] == '=' && key_one[23] == '=',
                      "handshake nonce has the RFC 6455 base64 shape");
    failures += check(strcmp(key_one, key_two) != 0,
                      "handshake nonces are independently generated");
    free(key_one);
    free(key_two);

    printf("WebSocket runtime: %d failure(s)\n", failures);
    return failures == 0 ? 0 : 1;
}
