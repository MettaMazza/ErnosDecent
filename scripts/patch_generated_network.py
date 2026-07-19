#!/usr/bin/env python3

"""Repair checked compiler-runtime defects in emitted C.

gethostbyname() returns shared static storage. Concurrent Ernos networking calls
can overwrite that storage between lookup and memcpy, which produced a
misaligned pointer read and an intermittent SIGSEGV in the stress suite.

The compiler's bundled SHA-256/MD5 byte assembly also left-shifts promoted signed
ints. Bytes with the high bit set trigger undefined behavior before assignment to
the unsigned destination. Cast every byte before shifting.

The compiler also records the address of init_ep_args()'s temporary argc parameter
as the main thread's stack boundary. That frame is gone after initialization, so a
later conservative minor-GC scan can cross outside the mapped stack and segfault.
Resolve the real pthread stack boundary on each supported native platform.

Older compiler builds do not emit the native binary-safe ep_net_send_raw helper;
newer builds do, but may use different parameter names. Detect definitions by C
shape and native-section position rather than spelling so the patch stays
idempotent and never introduces a duplicate definition.
"""

from pathlib import Path
import re
import sys


MARKER = "/* ERNOSDECENT_THREAD_SAFE_DNS */"
SHIFT_MARKER = "/* ERNOSDECENT_UNSIGNED_BYTE_SHIFTS */"
RAW_SEND_MARKER = "/* ERNOSDECENT_NATIVE_RAW_SEND */"
STACK_BOTTOM_MARKER = "/* ERNOSDECENT_PLATFORM_STACK_BOTTOM */"
FUNCTION_SEND = re.compile(
    r"\blong\s+long\s+ep_net_send\s*\([^;{}]*\)\s*\{",
    re.DOTALL,
)
FUNCTION_RAW_SEND = re.compile(
    r"\blong\s+long\s+ep_net_send_raw\s*\([^;{}]*\)\s*\{",
    re.DOTALL,
)
RAW_SEND_IMPLEMENTATION = """/* ERNOSDECENT_NATIVE_RAW_SEND */
long long ep_net_send_raw(long long fd, long long data_ptr, long long count) {
    if (data_ptr == 0 || count <= 0) return 0;
    const char* data = (const char*)data_ptr;
    long long off = 0;
    while (off < count) {
#ifdef _WIN32
        int chunk = count - off > INT_MAX ? INT_MAX : (int)(count - off);
        int n = send((int)fd, data + off, chunk, 0);
        if (n < 0 && WSAGetLastError() == WSAEINTR) continue;
#else
        ssize_t n = send((int)fd, data + off, (size_t)(count - off), 0);
        if (n < 0 && errno == EINTR) continue;
#endif
        if (n <= 0) break;
        off += (long long)n;
    }
    return off;
}

"""
UNSAFE_SHA256_WORD = (
    "        m[i] = (data[j] << 24) | (data[j + 1] << 16) | "
    "(data[j + 2] << 8) | (data[j + 3]);"
)
SAFE_SHA256_WORD = (
    f"        {SHIFT_MARKER}\n"
    "        m[i] = ((unsigned int)data[j] << 24) | "
    "((unsigned int)data[j + 1] << 16) | "
    "((unsigned int)data[j + 2] << 8) | (unsigned int)data[j + 3];"
)
UNSAFE_MD5_WORD = (
    "        x[i] = (block[j]) | (block[j+1] << 8) | "
    "(block[j+2] << 16) | (block[j+3] << 24);"
)
SAFE_MD5_WORD = (
    "        x[i] = (unsigned int)block[j] | "
    "((unsigned int)block[j+1] << 8) | "
    "((unsigned int)block[j+2] << 16) | "
    "((unsigned int)block[j+3] << 24);"
)
UNSAFE_RESOLUTION = re.compile(
    r"    struct hostent\* server = gethostbyname\(host\);\n"
    r"    if \(!server\) \{\n"
    r"(?P<failure>.*?)"
    r"    \}\n"
    r"    struct sockaddr_in serv_addr;\n"
    r"    memset\(&serv_addr, 0, sizeof\(serv_addr\)\);\n"
    r"    serv_addr\.sin_family = AF_INET;\n"
    r"    memcpy\(&serv_addr\.sin_addr\.s_addr, server->h_addr_list\[0\], server->h_length\);\n",
    re.DOTALL,
)
UNSAFE_MAIN_STACK_REGISTRATION = "    ep_gc_register_thread((void*)&argc);"
SAFE_MAIN_STACK_REGISTRATION = "    ep_gc_register_thread(ep_gc_platform_stack_bottom());"
INIT_ARGS_DEFINITION = "void init_ep_args(int argc, char** argv) {"
STACK_BOTTOM_IMPLEMENTATION = r'''/* ERNOSDECENT_PLATFORM_STACK_BOTTOM */
#if defined(__linux__)
/* GNU extension; declare explicitly because the compiler runtime's system headers
   may have been parsed before _GNU_SOURCE was enabled. */
extern int pthread_getattr_np(pthread_t thread, pthread_attr_t* attr);
#endif

static void* ep_gc_platform_stack_bottom(void) {
#if defined(__APPLE__)
    void* high = pthread_get_stackaddr_np(pthread_self());
    if (high) return high;
#elif defined(__linux__)
    pthread_attr_t attr;
    void* base = NULL;
    size_t size = 0;
    int attr_err = pthread_getattr_np(pthread_self(), &attr);
    if (attr_err == 0) {
        int stack_err = pthread_attr_getstack(&attr, &base, &size);
        int destroy_err = pthread_attr_destroy(&attr);
        if (stack_err == 0 && destroy_err == 0 && base && size > 0) {
            return (void*)((char*)base + size);
        }
        fprintf(stderr,
            "Runtime Error: could not resolve the main pthread stack boundary "
            "(getstack=%d, destroy=%d)\n", stack_err, destroy_err);
        abort();
    }
    fprintf(stderr,
        "Runtime Error: could not inspect the main pthread attributes (error=%d)\n",
        attr_err);
    abort();
#else
#error "ErnosDecent native runtime supports stack-boundary discovery on macOS and Linux"
#endif
    fprintf(stderr, "Runtime Error: main pthread stack boundary is unavailable\n");
    abort();
}

'''


def replace_resolution(match: re.Match[str]) -> str:
    failure = match.group("failure")
    return (
        f"    {MARKER}\n"
        "    struct addrinfo ep_dns_hints;\n"
        "    struct addrinfo* ep_dns_results = NULL;\n"
        "    memset(&ep_dns_hints, 0, sizeof(ep_dns_hints));\n"
        "    ep_dns_hints.ai_family = AF_INET;\n"
        "    ep_dns_hints.ai_socktype = SOCK_STREAM;\n"
        "    int ep_dns_error = getaddrinfo(host, NULL, &ep_dns_hints, &ep_dns_results);\n"
        "    if (ep_dns_error != 0 || !ep_dns_results ||\n"
        "        ep_dns_results->ai_addrlen < sizeof(struct sockaddr_in)) {\n"
        "        if (ep_dns_results) freeaddrinfo(ep_dns_results);\n"
        f"{failure}"
        "    }\n"
        "    struct sockaddr_in serv_addr;\n"
        "    memcpy(&serv_addr, ep_dns_results->ai_addr, sizeof(serv_addr));\n"
        "    freeaddrinfo(ep_dns_results);\n"
    )


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: patch_generated_network.py <emitted.c>", file=sys.stderr)
        return 64

    generated_path = Path(sys.argv[1])
    if not generated_path.is_file():
        print(f"network runtime patch: emitted C not found: {generated_path}", file=sys.stderr)
        return 66

    content = generated_path.read_text()
    dns_replacements = 0
    if MARKER in content:
        if "gethostbyname(host)" in content:
            print("network runtime patch: mixed patched/unsafe resolver state", file=sys.stderr)
            return 1
        patched = content
    else:
        patched, dns_replacements = UNSAFE_RESOLUTION.subn(replace_resolution, content)
        if dns_replacements != 2:
            print(
                f"network runtime patch: expected 2 resolver sites, found {dns_replacements}; refusing partial patch",
                file=sys.stderr,
            )
            return 1
    if "gethostbyname(host)" in patched:
        print("network runtime patch: unsafe resolver site remains", file=sys.stderr)
        return 1

    if STACK_BOTTOM_MARKER in patched:
        if UNSAFE_MAIN_STACK_REGISTRATION in patched:
            print("GC stack-boundary patch: mixed patched/unsafe state", file=sys.stderr)
            return 1
        if patched.count(STACK_BOTTOM_MARKER) != 1 or patched.count(SAFE_MAIN_STACK_REGISTRATION) != 1:
            print("GC stack-boundary patch: malformed existing repair", file=sys.stderr)
            return 1
        stack_replacements = 0
    else:
        init_count = patched.count(INIT_ARGS_DEFINITION)
        registration_count = patched.count(UNSAFE_MAIN_STACK_REGISTRATION)
        if init_count != 1 or registration_count != 1:
            print(
                "GC stack-boundary patch: expected one init_ep_args definition and "
                f"one unsafe main registration, found {init_count} and {registration_count}",
                file=sys.stderr,
            )
            return 1
        patched = patched.replace(
            INIT_ARGS_DEFINITION,
            STACK_BOTTOM_IMPLEMENTATION + INIT_ARGS_DEFINITION,
        )
        patched = patched.replace(
            UNSAFE_MAIN_STACK_REGISTRATION,
            SAFE_MAIN_STACK_REGISTRATION,
        )
        stack_replacements = 1

    if SHIFT_MARKER in patched:
        if UNSAFE_SHA256_WORD in patched or UNSAFE_MD5_WORD in patched:
            print("integer-shift runtime patch: mixed patched/unsafe state", file=sys.stderr)
            return 1
        shift_replacements = 0
    else:
        sha_count = patched.count(UNSAFE_SHA256_WORD)
        md5_count = patched.count(UNSAFE_MD5_WORD)
        if sha_count != 1 or md5_count != 1:
            print(
                f"integer-shift runtime patch: expected one SHA-256 and one MD5 site, found {sha_count} and {md5_count}",
                file=sys.stderr,
            )
            return 1
        patched = patched.replace(UNSAFE_SHA256_WORD, SAFE_SHA256_WORD)
        patched = patched.replace(UNSAFE_MD5_WORD, SAFE_MD5_WORD)
        shift_replacements = 2

    send_definitions = list(FUNCTION_SEND.finditer(patched))
    if len(send_definitions) != 2:
        print(
            f"raw-send runtime patch: expected two ep_net_send definitions, found {len(send_definitions)}",
            file=sys.stderr,
        )
        return 1
    native_send_position = send_definitions[1].start()
    raw_definitions = list(FUNCTION_RAW_SEND.finditer(patched))
    native_raw_definitions = [
        match for match in raw_definitions if match.start() > native_send_position
    ]
    marker_count = patched.count(RAW_SEND_MARKER)
    if marker_count > 1:
        print(
            "raw-send runtime patch: duplicate injected-helper markers already present",
            file=sys.stderr,
        )
        return 1
    if marker_count == 1:
        marker_position = patched.index(RAW_SEND_MARKER)
        marked_raw_definitions = [
            match for match in raw_definitions
            if marker_position < match.start() < native_send_position
        ]
        if len(marked_raw_definitions) != 1:
            print(
                "raw-send runtime patch: injected marker does not identify exactly one helper",
                file=sys.stderr,
            )
            return 1
        raw_send_replacements = 0
    elif len(native_raw_definitions) > 1:
        print(
            "raw-send runtime patch: duplicate native ep_net_send_raw definitions already present",
            file=sys.stderr,
        )
        return 1
    elif native_raw_definitions:
        raw_send_replacements = 0
    else:
        patched = (
            patched[:native_send_position]
            + RAW_SEND_IMPLEMENTATION
            + patched[native_send_position:]
        )
        raw_send_replacements = 1

    generated_path.write_text(patched)
    print(
        f"Patched {dns_replacements} DNS resolver site(s) and "
        f"{shift_replacements} unsigned byte-shift site(s), repaired "
        f"{stack_replacements} GC stack boundary site(s); injected "
        f"{raw_send_replacements} native raw-send helper(s) in {generated_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
