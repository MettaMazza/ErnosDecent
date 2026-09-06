#!/bin/bash
# ErnosDecent mandatory self-upgrade regression gate.
#
# The running node verifies this script and its manifest against hashes embedded in
# the live executable before invoking upgrade.sh. This script then verifies every
# protected gate/test file before executing the isolated deterministic suites.

set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
MANIFEST="$ROOT/config/upgrades/mandatory-regressions.sha256"

hash_file() {
    local path="$1"
    if command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$path" | awk '{print $1}'
    elif command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$path" | awk '{print $1}'
    else
        echo "[mandatory-gate] no SHA-256 utility is available." >&2
        return 1
    fi
}

verify_manifest() {
    [ -f "$MANIFEST" ] && [ ! -L "$MANIFEST" ] || {
        echo "[mandatory-gate] protected manifest is missing or is a symlink." >&2
        return 1
    }

    local version expected relative actual count
    version=$(sed -n 's/^version=//p' "$MANIFEST" | head -n 1)
    [ "$version" = "1" ] || {
        echo "[mandatory-gate] unsupported manifest version." >&2
        return 1
    }

    count=0
    while IFS=$'\t' read -r expected relative; do
        [ -n "$expected" ] || continue
        [ "$expected" != "version=1" ] || continue
        [[ "$expected" =~ ^[0-9a-f]{64}$ ]] || {
            echo "[mandatory-gate] malformed hash for ${relative:-unknown}." >&2
            return 1
        }
        [ -n "$relative" ] && [[ "$relative" != /* ]] && [[ "$relative" != *".."* ]] || {
            echo "[mandatory-gate] unsafe protected path: ${relative:-empty}." >&2
            return 1
        }
        [ -f "$ROOT/$relative" ] && [ ! -L "$ROOT/$relative" ] || {
            echo "[mandatory-gate] protected file missing or replaced by symlink: $relative" >&2
            return 1
        }
        actual=$(hash_file "$ROOT/$relative")
        [ "$actual" = "$expected" ] || {
            echo "[mandatory-gate] protected file changed: $relative" >&2
            echo "[mandatory-gate] expected=$expected actual=$actual" >&2
            return 1
        }
        count=$((count + 1))
    done < "$MANIFEST"

    [ "$count" -ge 20 ] || {
        echo "[mandatory-gate] manifest is incomplete ($count protected files)." >&2
        return 1
    }
    echo "[mandatory-gate] integrity verified for $count protected files."
}

verify_manifest
[ "${1:-}" = "--verify-only" ] && exit 0
[ $# -eq 0 ] || {
    echo "Usage: $0 [--verify-only]" >&2
    exit 2
}

cd "$ROOT"

echo "[mandatory-gate] checking protected source trees and scripts."
bash -n build.sh
bash -n upgrade.sh
bash -n run_node.sh
bash -n scripts/run_mandatory_regressions.sh
python3 -m py_compile decent_net/discord_bridge.py decent_net/discord_manager.py
ernos check decent_agent/compiler_tool.ep
ernos check decent_agent/llm.ep
ernos check decent_agent/tools.ep
ernos check decent_agent/self_extensions.ep
ernos check decent_agent/react_loop.ep
ernos check decent_agent/rights.ep
ernos check decent_agent/session.ep
ernos check decent_agent/prompt.ep
ernos check decent_store/continuity.ep
ernos check decent_web/web_server.ep
ernos check node.ep

echo "[mandatory-gate] running native cognitive and host-election suites."
bash build.sh test
echo "[mandatory-gate] bash decent_agent/run_test.sh decent_agent/test_rights.ep"
bash decent_agent/run_test.sh decent_agent/test_rights.ep

PYTHON_SUITES=(
    tests/test_discord_manager_readiness.py
    tests/test_discord_tts_toggle.py
    tests/test_final_reply_fallback.py
    tests/test_improvement_eval_context.py
    tests/test_improvement_test_gate.py
    tests/test_interaction_identity.py
    tests/test_mental_state_guidance.py
    tests/test_self_upgrade_transaction.py
    tests/test_turn_queue_and_visual_memory.py
)
for suite in "${PYTHON_SUITES[@]}"; do
    echo "[mandatory-gate] python3 $suite"
    python3 "$suite"
done

JAVASCRIPT_SUITES=(
    tests/test_webui_response_formatting.js
    tests/test_webui_tts_toggle.js
)
for suite in "${JAVASCRIPT_SUITES[@]}"; do
    echo "[mandatory-gate] node $suite"
    node "$suite"
done

echo "[mandatory-gate] bash tests/test_rights_restore.sh"
bash tests/test_rights_restore.sh

echo "[mandatory-gate] verifying every hash-frozen Echo-authored improvement regression."
python3 scripts/improvement_test_gate.py verify

git diff --check
echo "[mandatory-gate] all mandatory regressions passed."
