#!/bin/bash
# ErnosDecent — Cross-Platform Build Script
# Compiles node.ep and patches the C runtime to ignore SIGPIPE
# Supports: macOS (ARM64/x86_64), Linux (x86_64/aarch64)
# Usage: bash build.sh

set -e

if [ "$1" = "test" ] || [ "$1" = "--test" ]; then
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
    
    set +e
    $ERNOS decent_agent/test_agent.ep 2>&1
    set -e

    # Step 1b: Patch conflicting mutex declarations and inject cast_borrow_to_map, cast_map_to_int and ep_net_send_raw
    python3 -c "
with open('decent_agent/test_agent_compiled.c', 'r') as f:
    content = f.read()
content = content.replace('long long ep_mutex_lock(long long);', '')
content = content.replace('long long ep_mutex_unlock(long long);', '')
inject = '''
long long cast_borrow_to_map(long long b) {
    return b;
}

long long cast_map_to_int(long long m) {
    return m;
}

long long ep_net_send_raw(long long fd, long long buf, long long count) {
    if (count <= 0 || buf == 0) return 0;
    const char* p = (const char*)buf;
    long long total = 0;
    while (total < count) {
        ssize_t n = send((int)fd, p + total, (size_t)(count - total), 0);
        if (n <= 0) break;
        total += n;
    }
    return total;
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
        content = inject + content
with open('decent_agent/test_agent_compiled.c', 'w') as f:
    f.write(content)
print('Patched conflicting mutex declarations and injected cast_borrow_to_map/cast_map_to_int/ep_net_send_raw in test_agent_compiled.c')
"

    
    # Setup library paths
    CFLAGS="-O2 -lpthread -DEP_HAS_SQLITE -lsqlite3 -Wno-int-conversion -Wno-parentheses-equality"
    OS="$(uname -s)"
    case "$OS" in
        Darwin)
            if [ -d "/opt/homebrew/lib" ]; then
                CFLAGS="$CFLAGS -L/opt/homebrew/lib -lsodium -L/opt/homebrew/opt/openssl/lib -lcrypto"
            elif [ -d "/usr/local/lib" ]; then
                CFLAGS="$CFLAGS -L/usr/local/lib -lsodium -L/usr/local/opt/openssl/lib -lcrypto"
            else
                CFLAGS="$CFLAGS -lsodium -lcrypto"
            fi
            ;;
        Linux)
            CFLAGS="$CFLAGS -lsodium -lcrypto -lm"
            ;;
    esac
    
    clang decent_agent/test_agent_compiled.c -o ./decent_agent/test_agent $CFLAGS 2>&1
    if [ "$OS" = "Darwin" ]; then
        codesign --force -s - ./decent_agent/test_agent 2>/dev/null || true
    fi
    echo "[+] Build complete: ./decent_agent/test_agent"
    echo "[*] Running tests..."
    ./decent_agent/test_agent
    
    echo ""
    echo "[*] Building GitDec Host Election Test Suite..."
    $ERNOS decent_net/test_host_election.ep 2>&1
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
set +e
ERNOS_OUT=$($ERNOS node.ep 2>&1)
set -e
echo "$ERNOS_OUT" | tail -6
# Fail loud if the compiler aborted before emitting fresh C. Cover BOTH classes that
# leave a stale node_compiled.c behind: type errors AND codegen/safety errors (e.g.
# "Code Generation Error", "Safety Error", "Compilation failed"). The latter do NOT
# contain "type error", so a grep for only that would silently relink the stale C.
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

# Step 2b: Inject ep_net_send_raw — binary-safe send (no strlen truncation)
# WebSocket frame headers contain null bytes (e.g., extended length 0x00 0x8A).
# ep_net_send uses strlen which stops at null bytes, truncating the frame.
# This function sends exactly 'count' bytes regardless of content.
# Note: there are TWO ep_net_send definitions (wasm stub + real).
# We inject before the SECOND one (the real non-wasm version).
if grep -q "long long ep_net_send_raw(long long fd, long long buf, long long count) {" node_compiled.c; then
    echo "[*] ep_net_send_raw already present."
else
    python3 -c "
import re
with open('node_compiled.c', 'r') as f:
    content = f.read()
inject = '''
// Binary-safe send: sends exactly 'count' bytes regardless of null bytes.
// ep_net_send uses strlen which truncates at nulls - fatal for WS frames.
long long ep_net_send_raw(long long fd, long long buf, long long count) {
    if (count <= 0 || buf == 0) return 0;
    const char* p = (const char*)buf;
    long long total = 0;
    while (total < count) {
        ssize_t n = send((int)fd, p + total, (size_t)(count - total), 0);
        if (n <= 0) break;
        total += n;
    }
    return total;
}

'''
# Find the second occurrence of ep_net_send (the real non-wasm one)
pat = 'long long ep_net_send(long long fd, const char* data) {'
first = content.find(pat)
second = content.find(pat, first + 1)
if second > 0:
    content = content[:second] + inject + content[second:]
    with open('node_compiled.c', 'w') as f:
        f.write(content)
    print('Injected ep_net_send_raw before non-wasm ep_net_send')
else:
    print('WARNING: could not find second ep_net_send')
"
    echo "[*] Injected ep_net_send_raw (binary-safe send)."
fi

# Step 2c: Inject cast_borrow_to_map & cast_map_to_int
if grep -q "long long cast_borrow_to_map(long long b) {" node_compiled.c; then
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
    print('WARNING: could not find second ep_net_send for cast_borrow_to_map')
"
    echo "[*] Injected cast_borrow_to_map/cast_map_to_int."
fi

# Step 2d: Patch conflicting mutex declarations & disable stdout/stderr buffering
python3 -c "
with open('node_compiled.c', 'r') as f:
    content = f.read()
content = content.replace('long long ep_mutex_lock(long long);', '')
content = content.replace('long long ep_mutex_unlock(long long);', '')
content = content.replace('int main(int argc, char** argv) {', 'int main(int argc, char** argv) {\\n    setvbuf(stdout, NULL, _IONBF, 0);\\n    setvbuf(stderr, NULL, _IONBF, 0);')
with open('node_compiled.c', 'w') as f:
    f.write(content)
print('Patched conflicting mutex declarations and disabled buffering in node_compiled.c')
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
    while (total < count) {
        ssize_t n = recv((int)fd, buf + total, count - total, 0);
        if (n <= 0) break;
        total += n;
    }
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
    print('WARNING: could not find second ep_net_recv_bytes')
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
    print('WARNING: could not find second ep_run_command')
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



# Step 3: Set platform-specific library paths and compile
CFLAGS="-O2 -lpthread -DEP_HAS_SQLITE -lsqlite3 -Wno-int-conversion -Wno-parentheses-equality"

case "$OS" in
    Darwin)
        # macOS: detect Homebrew prefix (ARM64 vs Intel)
        if [ -d "/opt/homebrew/lib" ]; then
            # Apple Silicon (ARM64)
            CFLAGS="$CFLAGS -L/opt/homebrew/lib -lsodium"
            CFLAGS="$CFLAGS -L/opt/homebrew/opt/openssl/lib -lcrypto"
        elif [ -d "/usr/local/lib" ]; then
            # Intel Mac (x86_64 Homebrew)
            CFLAGS="$CFLAGS -L/usr/local/lib -lsodium"
            CFLAGS="$CFLAGS -L/usr/local/opt/openssl/lib -lcrypto"
        else
            CFLAGS="$CFLAGS -lsodium -lcrypto"
        fi
        ;;
    Linux)
        # Linux: libraries from system paths
        CFLAGS="$CFLAGS -lsodium -lcrypto"
        # Some distros need explicit math lib
        CFLAGS="$CFLAGS -lm"
        ;;
    MINGW*|MSYS*|CYGWIN*|Windows_NT)
        echo "[-] Native Windows build is not supported by this script."
        echo "    On Windows, run ErnosDecent under WSL2 (Ubuntu) — it builds + runs"
        echo "    exactly like Linux. Install WSL2, open the Ubuntu shell, then:"
        echo "        sudo apt install -y clang libsodium-dev libssl-dev libsqlite3-dev"
        echo "        ./INSTALL.sh   (or bash build.sh if the toolchain is already installed)"
        exit 1
        ;;
    *)
        echo "[-] Unsupported OS: $OS"
        echo "    Supported: macOS, Linux, and Windows via WSL2."
        exit 1
        ;;
esac

echo "[*] Compiling with: clang node_compiled.c -o ./node $CFLAGS"
clang node_compiled.c -o ./node $CFLAGS 2>&1

# Step 4: Sign the binary (macOS requirement for notarization)
if [ "$OS" = "Darwin" ]; then
    codesign --force -s - ./node 2>/dev/null || true
fi

echo "[+] Build complete: ./node"
echo "[+] Platform: $OS $ARCH"
