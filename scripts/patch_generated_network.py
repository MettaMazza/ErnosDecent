#!/usr/bin/env python3

"""Repair checked compiler-runtime defects in emitted C.

gethostbyname() returns shared static storage. Concurrent Ernos networking calls
can overwrite that storage between lookup and memcpy, which produced a
misaligned pointer read and an intermittent SIGSEGV in the stress suite.

The compiler's bundled SHA-256/MD5 byte assembly also left-shifts promoted signed
ints. Bytes with the high bit set trigger undefined behavior before assignment to
the unsigned destination. Cast every byte before shifting.
"""

from pathlib import Path
import re
import sys


MARKER = "/* ERNOSDECENT_THREAD_SAFE_DNS */"
SHIFT_MARKER = "/* ERNOSDECENT_UNSIGNED_BYTE_SHIFTS */"
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

    generated_path.write_text(patched)
    print(
        f"Patched {dns_replacements} DNS resolver site(s) and "
        f"{shift_replacements} unsigned byte-shift site(s) in {generated_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
