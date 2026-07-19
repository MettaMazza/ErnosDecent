#!/usr/bin/env bash
# ErnosDecent — authenticated hot-swap upgrade with verified rollback.

set -euo pipefail

REPO_DIR=$(cd "$(dirname "$0")" && pwd)
CURRENT_BINARY="$REPO_DIR/node"
NEXT_BINARY="$REPO_DIR/node_next"
ROLLBACK_BINARY="$REPO_DIR/node_rollback"
IPC_TOKEN_FILE="$HOME/.ernosdecent/ipc-token"

if [ ! -x "$CURRENT_BINARY" ]; then
    echo "[UPGRADE] Current node binary is missing or not executable: $CURRENT_BINARY" >&2
    exit 1
fi
if [ ! -x "$NEXT_BINARY" ]; then
    echo "[UPGRADE] Candidate node binary is missing or not executable: $NEXT_BINARY" >&2
    exit 1
fi
if [ ! -r "$IPC_TOKEN_FILE" ]; then
    echo "[UPGRADE] IPC token is unavailable: $IPC_TOKEN_FILE" >&2
    exit 1
fi
IPC_TOKEN=$(tr -d '\r\n ' < "$IPC_TOKEN_FILE")
if [ -z "$IPC_TOKEN" ]; then
    echo "[UPGRADE] IPC token file is empty" >&2
    exit 1
fi

ipc_command() {
    printf 'AUTH %s %s\n' "$IPC_TOKEN" "$1" | nc -w 2 127.0.0.1 5000 2>/dev/null
}

wait_for_stop() {
    local attempt
    for attempt in $(seq 1 15); do
        if ! lsof -nP -iTCP:5000 -sTCP:LISTEN >/dev/null 2>&1; then
            return 0
        fi
        sleep 1
    done
    return 1
}

wait_for_health() {
    local attempt
    local response
    for attempt in $(seq 1 15); do
        sleep 1
        response=$(ipc_command "STATUS" || true)
        if echo "$response" | grep -q "status:active"; then
            return 0
        fi
        echo "[UPGRADE] Waiting for authenticated health status... ($attempt/15)"
    done
    return 1
}

stop_owned_pid() {
    local owned_pid="$1"
    if [ -n "$owned_pid" ] && kill -0 "$owned_pid" 2>/dev/null; then
        kill "$owned_pid" 2>/dev/null || true
        wait "$owned_pid" 2>/dev/null || true
    fi
}

echo "[UPGRADE] Saving the current binary for rollback..."
cp -p "$CURRENT_BINARY" "$ROLLBACK_BINARY"

if lsof -nP -iTCP:5000 -sTCP:LISTEN >/dev/null 2>&1; then
    echo "[UPGRADE] Requesting authenticated graceful shutdown..."
    stop_response=$(ipc_command "STOP" || true)
    if ! echo "$stop_response" | grep -q "status:stopping"; then
        echo "[UPGRADE] Running service did not accept the authenticated STOP command" >&2
        exit 1
    fi
    if ! wait_for_stop; then
        echo "[UPGRADE] Running service did not release port 5000; no forced port-based kill was attempted" >&2
        exit 1
    fi
fi

candidate_copy="$REPO_DIR/.node.upgrade.$$"
cp -p "$NEXT_BINARY" "$candidate_copy"
mv -f "$candidate_copy" "$CURRENT_BINARY"

echo "[UPGRADE] Launching candidate node..."
nohup "$CURRENT_BINARY" > "$REPO_DIR/daemon.log" 2>&1 &
NEW_PID=$!

if wait_for_health; then
    echo "[UPGRADE] Candidate node is active and authenticated health passed."
    exit 0
fi

echo "[UPGRADE] Candidate failed health validation; restoring rollback binary." >&2
stop_owned_pid "$NEW_PID"
if lsof -nP -iTCP:5000 -sTCP:LISTEN >/dev/null 2>&1; then
    echo "[UPGRADE] Candidate still owns port 5000 after termination; rollback cannot start safely" >&2
    exit 1
fi
cp -p "$ROLLBACK_BINARY" "$CURRENT_BINARY"
nohup "$CURRENT_BINARY" > "$REPO_DIR/daemon.log" 2>&1 &
ROLLBACK_PID=$!
if wait_for_health; then
    echo "[UPGRADE] Rollback node restored and passed authenticated health validation." >&2
    exit 1
fi

stop_owned_pid "$ROLLBACK_PID"
echo "[UPGRADE] Rollback binary also failed health validation; no node is being represented as healthy." >&2
exit 1
