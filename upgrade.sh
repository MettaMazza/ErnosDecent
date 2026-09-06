#!/bin/bash
# ErnosDecent transactional self-upgrade state manager.
#
# This script never kills or launches a process. run_node.sh is the sole runtime
# supervisor. The agent prepares and stages an immutable candidate here; after the
# current reply is durably published, the node exits with code 75 and run_node.sh
# activates the candidate, proves authenticated health, commits the rights receipt,
# or restores the exact pre-upgrade executable.

set -euo pipefail

ROOT=$(cd "$(dirname "$0")" && pwd)
STATE_DIR="$ROOT/config/upgrades"
LOG_DIR="$STATE_DIR/logs"
PREPARED="$STATE_DIR/prepared.env"
PENDING="$STATE_DIR/pending.env"
OUTCOME="$STATE_DIR/outcome.env"
CANDIDATE="$STATE_DIR/candidate.node"
ROLLBACK="$STATE_DIR/rollback.node"
FAILED="$STATE_DIR/failed-candidate.node"
PREPARE_LOCK="$STATE_DIR/prepare.lock"
GATE_MANIFEST="$STATE_DIR/mandatory-regressions.sha256"
GATE_RUNNER="$ROOT/scripts/run_mandatory_regressions.sh"
GATE_SEAL="${HOME}/.ernosdecent/mandatory-regressions.seal"

hash_file() {
    local path="$1"
    if command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$path" | awk '{print $1}'
    elif command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$path" | awk '{print $1}'
    else
        echo "[upgrade] no SHA-256 utility is available." >&2
        return 1
    fi
}

valid_hash() {
    [[ "$1" =~ ^[0-9a-f]{64}$ ]]
}

field() {
    local file="$1"
    local key="$2"
    sed -n "s/^${key}=//p" "$file" | head -n 1
}

write_atomic() {
    local destination="$1"
    local content="$2"
    local temporary
    temporary=$(mktemp "${destination}.tmp.XXXXXX")
    chmod 600 "$temporary"
    printf '%s\n' "$content" > "$temporary"
    mv -f "$temporary" "$destination"
}

verify_gate_integrity() {
    [ -f "$GATE_SEAL" ] && [ ! -L "$GATE_SEAL" ] || {
        echo "[upgrade] operator regression seal is missing or replaced." >&2
        return 1
    }
    [ -f "$GATE_MANIFEST" ] && [ ! -L "$GATE_MANIFEST" ] || {
        echo "[upgrade] mandatory regression manifest is missing or replaced." >&2
        return 1
    }
    [ -x "$GATE_RUNNER" ] && [ ! -L "$GATE_RUNNER" ] || {
        echo "[upgrade] mandatory regression runner is missing, non-executable, or replaced." >&2
        return 1
    }
    local expected actual
    expected=$(tr -d '\r\n ' < "$GATE_SEAL")
    actual=$(hash_file "$GATE_MANIFEST")
    valid_hash "$expected" || {
        echo "[upgrade] operator regression seal is malformed." >&2
        return 1
    }
    [ "$actual" = "$expected" ] || {
        echo "[upgrade] mandatory regression manifest differs from the operator seal." >&2
        return 1
    }
    (cd "$ROOT" && bash "$GATE_RUNNER" --verify-only)
}

require_transaction() {
    [ -f "$PENDING" ] || { echo "[upgrade] no pending transaction." >&2; return 1; }
    local version state change_id candidate_hash rollback_hash gate_manifest_hash
    version=$(field "$PENDING" version)
    state=$(field "$PENDING" state)
    change_id=$(field "$PENDING" change_id)
    candidate_hash=$(field "$PENDING" candidate_hash)
    rollback_hash=$(field "$PENDING" rollback_hash)
    gate_manifest_hash=$(field "$PENDING" gate_manifest_hash)
    [ "$version" = "1" ] || { echo "[upgrade] unsupported transaction version." >&2; return 1; }
    [ "$state" = "pending" ] || { echo "[upgrade] transaction is not pending." >&2; return 1; }
    valid_hash "$change_id" || { echo "[upgrade] invalid protected change id." >&2; return 1; }
    valid_hash "$candidate_hash" || { echo "[upgrade] invalid candidate hash." >&2; return 1; }
    valid_hash "$rollback_hash" || { echo "[upgrade] invalid rollback hash." >&2; return 1; }
    valid_hash "$gate_manifest_hash" || { echo "[upgrade] invalid gate manifest hash." >&2; return 1; }
    [ "$(hash_file "$GATE_MANIFEST")" = "$gate_manifest_hash" ] || { echo "[upgrade] gate manifest changed after staging." >&2; return 1; }
    [ -x "$CANDIDATE" ] || { echo "[upgrade] candidate executable is missing." >&2; return 1; }
    [ -x "$ROLLBACK" ] || { echo "[upgrade] rollback executable is missing." >&2; return 1; }
    [ "$(hash_file "$CANDIDATE")" = "$candidate_hash" ] || { echo "[upgrade] candidate hash mismatch." >&2; return 1; }
    [ "$(hash_file "$ROLLBACK")" = "$rollback_hash" ] || { echo "[upgrade] rollback hash mismatch." >&2; return 1; }
}

prepare() {
    mkdir -p "$STATE_DIR" "$LOG_DIR"
    chmod 700 "$STATE_DIR" "$LOG_DIR"
    if ! mkdir "$PREPARE_LOCK" 2>/dev/null; then
        echo "[upgrade] another candidate preparation is active." >&2
        return 1
    fi
    trap 'rmdir "$PREPARE_LOCK" 2>/dev/null || true' EXIT INT TERM
    verify_gate_integrity
    [ ! -f "$PENDING" ] || { echo "[upgrade] a deployment transaction is already pending." >&2; return 1; }
    rm -f "$PREPARED" "$OUTCOME" "$CANDIDATE" "$ROLLBACK" "$FAILED"

    local candidate_tmp rollback_tmp candidate_hash rollback_hash gate_manifest_hash prepared_at cleanup_command
    candidate_tmp=$(mktemp "$STATE_DIR/candidate.node.tmp.XXXXXX")
    rollback_tmp=$(mktemp "$STATE_DIR/rollback.node.tmp.XXXXXX")
    printf -v cleanup_command 'rm -f %q %q; rmdir %q 2>/dev/null || true' "$candidate_tmp" "$rollback_tmp" "$PREPARE_LOCK"
    trap "$cleanup_command" EXIT INT TERM

    [ -x "$ROOT/node" ] || { echo "[upgrade] current node executable is missing." >&2; return 1; }
    cp -p "$ROOT/node" "$rollback_tmp"
    chmod 755 "$rollback_tmp"

    echo "[upgrade] running the complete operator-sealed mandatory regression gate."
    (cd "$ROOT" && bash "$GATE_RUNNER") > "$LOG_DIR/tests.log" 2>&1 || {
        echo "[upgrade] test gate failed; see $LOG_DIR/tests.log" >&2
        return 1
    }
    echo "[upgrade] building an isolated candidate executable."
    (cd "$ROOT" && ERNOS_NODE_OUTPUT="$candidate_tmp" bash build.sh) > "$LOG_DIR/build.log" 2>&1 || {
        echo "[upgrade] candidate build failed; see $LOG_DIR/build.log" >&2
        return 1
    }
    [ -x "$candidate_tmp" ] || { echo "[upgrade] build reported success without an executable candidate." >&2; return 1; }

    candidate_hash=$(hash_file "$candidate_tmp")
    rollback_hash=$(hash_file "$rollback_tmp")
    gate_manifest_hash=$(hash_file "$GATE_MANIFEST")
    valid_hash "$candidate_hash" || { echo "[upgrade] candidate hash could not be verified." >&2; return 1; }
    valid_hash "$rollback_hash" || { echo "[upgrade] rollback hash could not be verified." >&2; return 1; }
    valid_hash "$gate_manifest_hash" || { echo "[upgrade] gate manifest hash could not be verified." >&2; return 1; }
    prepared_at=$(date +%s)

    mv -f "$candidate_tmp" "$CANDIDATE"
    mv -f "$rollback_tmp" "$ROLLBACK"
    chmod 700 "$CANDIDATE" "$ROLLBACK"
    write_atomic "$PREPARED" "version=1
state=prepared
candidate_hash=$candidate_hash
rollback_hash=$rollback_hash
gate_manifest_hash=$gate_manifest_hash
prepared_at=$prepared_at"
    trap - EXIT INT TERM
    rmdir "$PREPARE_LOCK"
    echo "PREPARE_OK candidate_hash=$candidate_hash rollback_hash=$rollback_hash"
}

stage() {
    local change_id="${1:-}"
    mkdir -p "$STATE_DIR"
    verify_gate_integrity
    valid_hash "$change_id" || { echo "[upgrade] stage requires a 64-character protected change id." >&2; return 1; }
    [ -f "$PREPARED" ] || { echo "[upgrade] no prepared candidate exists." >&2; return 1; }
    [ ! -f "$PENDING" ] || { echo "[upgrade] a deployment transaction is already pending." >&2; return 1; }

    local version state candidate_hash rollback_hash gate_manifest_hash prepared_at
    version=$(field "$PREPARED" version)
    state=$(field "$PREPARED" state)
    candidate_hash=$(field "$PREPARED" candidate_hash)
    rollback_hash=$(field "$PREPARED" rollback_hash)
    gate_manifest_hash=$(field "$PREPARED" gate_manifest_hash)
    prepared_at=$(field "$PREPARED" prepared_at)
    [ "$version" = "1" ] && [ "$state" = "prepared" ] || { echo "[upgrade] malformed prepared transaction." >&2; return 1; }
    valid_hash "$candidate_hash" && valid_hash "$rollback_hash" || { echo "[upgrade] malformed prepared hashes." >&2; return 1; }
    valid_hash "$gate_manifest_hash" && [ "$(hash_file "$GATE_MANIFEST")" = "$gate_manifest_hash" ] || { echo "[upgrade] prepared gate seal no longer matches." >&2; return 1; }
    [ -x "$CANDIDATE" ] && [ -x "$ROLLBACK" ] || { echo "[upgrade] prepared executables are missing." >&2; return 1; }
    [ "$(hash_file "$CANDIDATE")" = "$candidate_hash" ] || { echo "[upgrade] prepared candidate changed after validation." >&2; return 1; }
    [ "$(hash_file "$ROLLBACK")" = "$rollback_hash" ] || { echo "[upgrade] prepared rollback changed after validation." >&2; return 1; }
    [ "$(hash_file "$ROOT/node")" = "$rollback_hash" ] || { echo "[upgrade] live executable changed during preparation; rebuild against the current state." >&2; return 1; }

    write_atomic "$PENDING" "version=1
state=pending
change_id=$change_id
candidate_hash=$candidate_hash
rollback_hash=$rollback_hash
gate_manifest_hash=$gate_manifest_hash
prepared_at=$prepared_at
staged_at=$(date +%s)"
    rm -f "$PREPARED"
    echo "STAGE_OK change_id=$change_id candidate_hash=$candidate_hash"
}

activate() {
    verify_gate_integrity
    require_transaction
    local candidate_hash rollback_hash current_hash replacement
    candidate_hash=$(field "$PENDING" candidate_hash)
    rollback_hash=$(field "$PENDING" rollback_hash)
    current_hash=$(hash_file "$ROOT/node")
    if [ "$current_hash" = "$candidate_hash" ]; then
        echo "ACTIVATE_OK candidate already active"
        return 0
    fi
    [ "$current_hash" = "$rollback_hash" ] || { echo "[upgrade] current executable matches neither transaction side; refusing replacement." >&2; return 1; }
    replacement=$(mktemp "$ROOT/node.upgrade.XXXXXX")
    cp -p "$CANDIDATE" "$replacement"
    chmod 755 "$replacement"
    [ "$(hash_file "$replacement")" = "$candidate_hash" ] || { rm -f "$replacement"; echo "[upgrade] replacement copy failed hash verification." >&2; return 1; }
    mv -f "$replacement" "$ROOT/node"
    [ "$(hash_file "$ROOT/node")" = "$candidate_hash" ] || { echo "[upgrade] active executable failed post-swap verification." >&2; return 1; }
    echo "ACTIVATE_OK candidate_hash=$candidate_hash"
}

record_outcome() {
    local status="${1:-}"
    local detail="${2:-}"
    require_transaction
    [ "$status" = "applied" ] || [ "$status" = "failed" ] || { echo "[upgrade] invalid outcome status." >&2; return 1; }
    [[ "$detail" != *$'\n'* ]] || { echo "[upgrade] outcome detail must be one line." >&2; return 1; }
    detail=${detail//=/_}
    local change_id candidate_hash rollback_hash active_hash
    change_id=$(field "$PENDING" change_id)
    candidate_hash=$(field "$PENDING" candidate_hash)
    rollback_hash=$(field "$PENDING" rollback_hash)
    active_hash=$(hash_file "$ROOT/node")
    if [ "$status" = "applied" ]; then
        [ "$active_hash" = "$candidate_hash" ] || { echo "[upgrade] cannot record success for a non-candidate executable." >&2; return 1; }
    else
        [ "$active_hash" = "$rollback_hash" ] || { echo "[upgrade] cannot record rollback before the old executable is restored." >&2; return 1; }
    fi
    write_atomic "$OUTCOME" "version=1
status=$status
change_id=$change_id
candidate_hash=$candidate_hash
rollback_hash=$rollback_hash
active_hash=$active_hash
recorded_at=$(date +%s)
detail=$detail"
    echo "OUTCOME_OK status=$status change_id=$change_id active_hash=$active_hash"
}

rollback() {
    require_transaction
    local rollback_hash replacement
    rollback_hash=$(field "$PENDING" rollback_hash)
    if [ -f "$ROOT/node" ]; then
        mv -f "$ROOT/node" "$FAILED"
    fi
    replacement=$(mktemp "$ROOT/node.rollback.XXXXXX")
    cp -p "$ROLLBACK" "$replacement"
    chmod 755 "$replacement"
    [ "$(hash_file "$replacement")" = "$rollback_hash" ] || { rm -f "$replacement"; echo "[upgrade] rollback copy failed hash verification." >&2; return 1; }
    mv -f "$replacement" "$ROOT/node"
    [ "$(hash_file "$ROOT/node")" = "$rollback_hash" ] || { echo "[upgrade] rollback executable failed post-restore verification." >&2; return 1; }
    echo "ROLLBACK_OK rollback_hash=$rollback_hash"
}

discard_prepared() {
    [ ! -f "$PENDING" ] || { echo "[upgrade] cannot discard a pending deployment." >&2; return 1; }
    rm -f "$PREPARED" "$CANDIDATE" "$ROLLBACK" "$FAILED"
    echo "DISCARD_OK"
}

cleanup_committed() {
    [ -f "$OUTCOME" ] || { echo "[upgrade] no reconciled outcome exists." >&2; return 1; }
    rm -f "$PREPARED" "$PENDING" "$OUTCOME" "$CANDIDATE" "$ROLLBACK" "$FAILED"
    echo "CLEANUP_OK"
}

case "${1:-}" in
    prepare) prepare ;;
    stage) stage "${2:-}" ;;
    activate) activate ;;
    success) record_outcome applied "authenticated replacement health and rights reconciliation requested" ;;
    failure) record_outcome failed "${2:-replacement_failed_health_validation}" ;;
    rollback) rollback ;;
    discard) discard_prepared ;;
    cleanup) cleanup_committed ;;
    *)
        echo "Usage: $0 {prepare|stage CHANGE_ID|activate|success|failure [REASON]|rollback|discard|cleanup}" >&2
        exit 2
        ;;
esac
