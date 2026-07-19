#!/usr/bin/env bash

set -euo pipefail

repo_dir=$(cd "$(dirname "$0")/.." && pwd)
cd "$repo_dir"

test_sources=(
    decent_id/test_keys.ep
    decent_id/test_did.ep
    decent_id/test_auth.ep
    decent_net/test_dht.ep
    decent_net/test_noise.ep
    decent_net/test_relay.ep
    decent_net/test_transport.ep
    decent_net/test_noise_transport.ep
    decent_net/test_dht_transport.ep
    decent_net/test_relay_transport.ep
    decent_net/test_host_election.ep
    decent_consensus/test_consensus.ep
    decent_msg/test_message.ep
    decent_msg/test_channel.ep
    decent_store/test_content.ep
    decent_store/test_crdt.ep
    decent_money/test_money.ep
    decent_media/test_media.ep
    decent_social/test_social.ep
    decent_ai/test_ai.ep
    decent_anon/test_anon_search.ep
    decent_pool/test_pool.ep
    decent_host/test_host.ep
    test_e2e.ep
    test_multinode.ep
    test_networking.ep
    test_persistence.ep
    test_security.ep
    test_stress.ep
    test_platform.ep
    test_raft_tcp.ep
    decent_cli/test_cli.ep
)

echo "=== Checking every native-target Ernos source ==="
native_checked=0
while IFS= read -r source_file; do
    if [ "$source_file" = "decent_web/app.ep" ]; then
        continue
    fi
    ernos --check "$source_file"
    native_checked=$((native_checked + 1))
done < <(rg --files -g '*.ep' | sort)
echo "Native Ernos checks passed: $native_checked"

echo "=== Building production node and browser application ==="
bash build.sh

echo "=== Compiling checked native test matrix ==="
for source_file in "${test_sources[@]}"; do
    bash scripts/compile_ep.sh "$source_file"
done

echo "=== Running checked native test matrix ==="
for source_file in "${test_sources[@]}"; do
    test_binary="${source_file%.ep}"
    bash scripts/run_test_checked.sh 120 "./$test_binary"
done

echo "=== Building and running cognitive-agent suite ==="
bash build.sh --compile-agent-test
bash scripts/run_test_checked.sh 180 ./decent_agent/test_agent

runtime_dir=$(mktemp -d -t ernos-release-runtime.XXXXXX)
cleanup_runtime_dir() {
    rm -rf "$runtime_dir"
}
trap cleanup_runtime_dir EXIT

echo "=== Building and running additive runtime suites ==="
clang runtime/test_websocket_runtime.c runtime/websocket_runtime.c runtime/ernosdecent_runtime.c \
    -o "$runtime_dir/test_websocket_runtime"
"$runtime_dir/test_websocket_runtime"

nostr_flags=(-lsecp256k1 -lcrypto)
case "$(uname -s)" in
    Darwin)
        if [ -d /opt/homebrew/lib ]; then
            nostr_flags=(-I/opt/homebrew/include -L/opt/homebrew/lib -I/opt/homebrew/opt/openssl/include -L/opt/homebrew/opt/openssl/lib -lsecp256k1 -lcrypto)
        elif [ -d /usr/local/lib ]; then
            nostr_flags=(-I/usr/local/include -L/usr/local/lib -I/usr/local/opt/openssl/include -L/usr/local/opt/openssl/lib -lsecp256k1 -lcrypto)
        fi
        ;;
    Linux)
        ;;
    *)
        echo "Unsupported release-check platform: $(uname -s)" >&2
        exit 1
        ;;
esac
clang runtime/test_nostr_runtime.c runtime/nostr_runtime.c "${nostr_flags[@]}" \
    -o "$runtime_dir/test_nostr_runtime"
"$runtime_dir/test_nostr_runtime"

echo "=== Checking shell syntax and worktree whitespace ==="
while IFS= read -r shell_file; do
    bash -n "$shell_file"
done < <(rg --files -g '*.sh' | sort)
git diff --check

echo "Release check passed: $native_checked Ernos checks, ${#test_sources[@]} native test binaries, cognitive-agent suite, and 2 runtime suites."
