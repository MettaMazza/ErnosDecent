#!/usr/bin/env bash

set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "usage: scripts/compile_ep.sh <source.ep>" >&2
    exit 64
fi

source_file="$1"
if [ ! -f "$source_file" ]; then
    echo "compile error: source file not found: $source_file" >&2
    exit 66
fi

# The cognitive-agent suite imports the production image FFI and needs the same
# blocking, SQLite, session, and additive-runtime patches as the node. Route it
# through the shared agent-test build path so a generic link cannot drift from
# the production runtime or leave declared symbols unresolved.
if [ "$source_file" = "decent_agent/test_agent.ep" ]; then
    exec bash build.sh --compile-agent-test
fi

compiler=""
if command -v ernos >/dev/null 2>&1; then
    compiler="$(command -v ernos)"
elif [ -x "$HOME/.local/bin/ernos" ]; then
    compiler="$HOME/.local/bin/ernos"
elif [ -x /usr/local/bin/ernos ]; then
    compiler=/usr/local/bin/ernos
else
    echo "compile error: Ernos compiler not found" >&2
    exit 69
fi

compiled_c="${source_file%.ep}_compiled.c"
output_binary="${source_file%.ep}"
compiler_log="$(mktemp -t ernos-compile.XXXXXX)"
cleanup() {
    rm -f "$compiler_log"
}
trap cleanup EXIT

rm -f "$compiled_c"
set +e
"$compiler" "$source_file" >"$compiler_log" 2>&1
compiler_status=$?
set -e

runtime_sources=()
if [ "$compiler_status" -eq 0 ]; then
    cat "$compiler_log"
else
    cat "$compiler_log" >&2
    if ! grep -qE "ep_net_send_raw|ed_ws_|cast_(borrow_to_map|int_to_map|map_to_int)|async_wait_readable_timeout|ep_cancel_epoch_get|ep_file_to_base64|ep_json_escape" "$compiler_log"; then
        echo "compile error: Ernos failed for a reason other than a required ErnosDecent runtime bridge" >&2
        exit "$compiler_status"
    fi

    if grep -qE "cast_(borrow_to_map|int_to_map|map_to_int)|async_wait_readable_timeout|ep_cancel_epoch_get|ep_file_to_base64|ep_json_escape" "$compiler_log"; then
        bash build.sh --inject-additive-runtime "$compiled_c"
    fi
    runtime_sources=(runtime/ernosdecent_runtime.c runtime/websocket_runtime.c runtime/nostr_runtime.c)
fi
if [ ! -s "$compiled_c" ]; then
    echo "compile error: Ernos did not emit fresh C for $source_file" >&2
    exit 70
fi

python3 scripts/patch_generated_network.py "$compiled_c"

common_flags=(-O2 -lpthread -DEP_HAS_SQLITE -DERNOSDECENT_GENERATED_NET_SEND_RAW -lsqlite3 -Wno-int-conversion -Wno-parentheses-equality)
case "$(uname -s)" in
    Darwin)
        if [ -d /opt/homebrew/lib ]; then
            common_flags+=(-I/opt/homebrew/include -L/opt/homebrew/lib -lsodium -lsecp256k1 -I/opt/homebrew/opt/openssl/include -L/opt/homebrew/opt/openssl/lib -lcrypto)
        elif [ -d /usr/local/lib ]; then
            common_flags+=(-I/usr/local/include -L/usr/local/lib -lsodium -lsecp256k1 -I/usr/local/opt/openssl/include -L/usr/local/opt/openssl/lib -lcrypto)
        else
            common_flags+=(-lsodium -lsecp256k1 -lcrypto)
        fi
        ;;
    Linux)
        common_flags+=(-lsodium -lsecp256k1 -lcrypto -lm)
        ;;
    *)
        echo "compile error: unsupported operating system: $(uname -s)" >&2
        exit 71
        ;;
esac

if [ "${#runtime_sources[@]}" -gt 0 ]; then
    clang "$compiled_c" "${runtime_sources[@]}" -o "$output_binary" "${common_flags[@]}"
    build_mode="ErnosDecent runtime bridge and thread-safe DNS"
else
    clang "$compiled_c" -o "$output_binary" "${common_flags[@]}"
    build_mode="thread-safe generated runtime"
fi
if [ "$(uname -s)" = Darwin ]; then
    codesign --force -s - "$output_binary"
fi
echo "Successfully compiled with $build_mode: $output_binary"
