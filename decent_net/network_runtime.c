/* Native bodies for network externs emitted by ErnosPlain. The production node
   injects equivalent bodies while retargeting only its private control listeners;
   the integrated test binary links this file directly. */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef _WIN32
#include <winsock2.h>
#include <ws2tcpip.h>
#else
#include <arpa/inet.h>
#include <netdb.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>
#endif

long long ep_net_listen_loopback(long long port) {
    int socket_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (socket_fd < 0) return -1;
    int enabled = 1;
    setsockopt(socket_fd, SOL_SOCKET, SO_REUSEADDR, (const char*)&enabled, sizeof(enabled));
    struct sockaddr_in address;
    memset(&address, 0, sizeof(address));
    address.sin_family = AF_INET;
    address.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    address.sin_port = htons((uint16_t)port);
    if (bind(socket_fd, (struct sockaddr*)&address, sizeof(address)) < 0 ||
        listen(socket_fd, 10) < 0) {
#ifdef _WIN32
        closesocket(socket_fd);
#else
        close(socket_fd);
#endif
        return -1;
    }
    return socket_fd;
}

static long long public_dns_error(const char* detail) {
    const char* prefix = "Error: DNS ";
    const char* safe_detail = detail ? detail : "unknown resolution failure";
    size_t size = strlen(prefix) + strlen(safe_detail) + 1;
    char* result = (char*)malloc(size);
    if (!result) return (long long)strdup("Error: DNS memory allocation failed");
    snprintf(result, size, "%s%s", prefix, safe_detail);
    return (long long)result;
}

static int public_dns_valid_hostname(const char* host) {
    if (!host) return 0;
    size_t length = strlen(host);
    if (length == 0 || length > 253) return 0;
    size_t label_length = 0;
    for (size_t i = 0; i < length; ++i) {
        unsigned char c = (unsigned char)host[i];
        if (c == '.') {
            if (label_length == 0 || host[i - 1] == '-' ||
                (i + 1 < length && host[i + 1] == '.')) return 0;
            label_length = 0;
            continue;
        }
        if (!((c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') ||
              (c >= '0' && c <= '9') || c == '-')) return 0;
        if ((label_length == 0 && c == '-') || ++label_length > 63) return 0;
    }
    return host[length - 1] == '.' || (label_length > 0 && host[length - 1] != '-');
}

static int public_dns_ipv4_is_public(uint32_t network_address) {
    uint32_t address = ntohl(network_address);
    unsigned int first = (address >> 24) & 255U;
    unsigned int second = (address >> 16) & 255U;
    unsigned int third = (address >> 8) & 255U;
    unsigned int fourth = address & 255U;
    if (first == 0U || first == 10U || first == 127U) return 0;
    if (first == 100U && second >= 64U && second <= 127U) return 0;
    if (first == 169U && second == 254U) return 0;
    if (first == 172U && second >= 16U && second <= 31U) return 0;
    if (first == 192U && second == 0U && third == 0U && fourth != 9U && fourth != 10U) return 0;
    if (first == 192U && second == 0U && third == 2U) return 0;
    if (first == 192U && second == 88U && third == 99U) return 0;
    if (first == 192U && second == 168U) return 0;
    if (first == 198U && (second == 18U || second == 19U)) return 0;
    if (first == 198U && second == 51U && third == 100U) return 0;
    if (first == 203U && second == 0U && third == 113U) return 0;
    return first < 224U;
}

long long ep_net_resolve_public_ipv4(long long host_ptr) {
    const char* host = (const char*)host_ptr;
    if (!public_dns_valid_hostname(host)) return public_dns_error("hostname must be a valid ASCII DNS name or IPv4 literal");
    struct addrinfo hints;
    memset(&hints, 0, sizeof(hints));
    hints.ai_family = AF_INET;
    hints.ai_socktype = SOCK_STREAM;
    struct addrinfo* results = NULL;
    int resolution = getaddrinfo(host, NULL, &hints, &results);
    if (resolution != 0) return public_dns_error(gai_strerror(resolution));
    char selected[INET_ADDRSTRLEN] = {0};
    int answers = 0;
    int rejected = 0;
    for (struct addrinfo* current = results; current; current = current->ai_next) {
        if (!current->ai_addr || current->ai_family != AF_INET ||
            (size_t)current->ai_addrlen < sizeof(struct sockaddr_in)) continue;
        struct sockaddr_in ipv4;
        memcpy(&ipv4, current->ai_addr, sizeof(ipv4));
        ++answers;
        if (!public_dns_ipv4_is_public(ipv4.sin_addr.s_addr) ||
            (selected[0] == '\0' && !inet_ntop(AF_INET, &ipv4.sin_addr, selected, sizeof(selected)))) {
            rejected = 1;
            break;
        }
    }
    freeaddrinfo(results);
    if (rejected) return public_dns_error("hostname has a non-public or unrepresentable IPv4 answer");
    if (answers == 0 || selected[0] == '\0') return public_dns_error("hostname has no IPv4 answer");
    return (long long)strdup(selected);
}
