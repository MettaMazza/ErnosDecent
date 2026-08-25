#!/bin/bash
# ErnosDecent — Live Daemon Stress Test
# Tests the running daemon under sustained load: IPC flood,
# HTTP flood, WebSocket reconnect storm, message/transfer storms.
# Requires: ./node binary running on default ports (5000, 8080)

set -o pipefail

PASS=0
FAIL=0
TOTAL=0

pass() {
    TOTAL=$((TOTAL + 1))
    PASS=$((PASS + 1))
    echo "  [PASS] $1"
}

fail() {
    TOTAL=$((TOTAL + 1))
    FAIL=$((FAIL + 1))
    echo "  [FAIL] $1"
}

ipc_cmd() {
    local port="$1"
    local timeout_seconds="$2"
    local cmd="$3"
    local token
    token=$(tr -d '\r\n ' < "$HOME/.ernosdecent/ipc-token" 2>/dev/null) || return 1
    [ -n "$token" ] || return 1
    printf 'AUTH %s %s\n' "$token" "$cmd" | nc -w "$timeout_seconds" 127.0.0.1 "$port" 2>/dev/null
}

cleanup() {
    echo "[*] Cleaning up..."
    lsof -ti:5000,8080,9100,9101,9102 2>/dev/null | xargs kill -9 2>/dev/null
}

trap cleanup EXIT

echo "==========================================================="
echo "  ErnosDecent — Live Daemon Stress Test"
echo "  IPC flood, HTTP flood, WS reconnect, message/transfer storms"
echo "==========================================================="
echo ""

# Start daemon if not already running
lsof -ti:5000,8080,9100,9101,9102 2>/dev/null | xargs kill -9 2>/dev/null
sleep 1
./node &
DAEMON_PID=$!
sleep 3

# Verify daemon alive
check=$(ipc_cmd 5000 2 "STATUS")
if ! echo "$check" | grep -q "status:active"; then
    echo "[-] FATAL: Daemon failed to start"
    exit 1
fi
echo "[+] Daemon alive (PID $DAEMON_PID)"
echo ""

# ================================================================
# TEST 1: IPC Flood (100 rapid STATUS commands)
# ================================================================
echo "=== TEST 1: IPC Flood (100 rapid STATUS) ==="
ipc_ok=0
ipc_fail=0
for i in $(seq 1 100); do
    r=$(ipc_cmd 5000 1 "STATUS")
    if echo "$r" | grep -q "status:active"; then
        ipc_ok=$((ipc_ok + 1))
    else
        ipc_fail=$((ipc_fail + 1))
    fi
done

if [ "$ipc_ok" -ge 95 ]; then
    pass "IPC flood: $ipc_ok/100 succeeded"
else
    fail "IPC flood: only $ipc_ok/100 succeeded ($ipc_fail failed)"
fi

# Verify daemon survived
post_ipc=$(ipc_cmd 5000 2 "STATUS")
if echo "$post_ipc" | grep -q "status:active"; then
    pass "Daemon alive after IPC flood"
else
    fail "Daemon crashed after IPC flood"
fi

echo ""

# ================================================================
# TEST 2: HTTP Flood (100 rapid /api/status requests)
# ================================================================
echo "=== TEST 2: HTTP Flood (100 rapid /api/status) ==="
http_ok=0
for i in $(seq 1 100); do
    code=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8080/api/status 2>/dev/null)
    if [ "$code" = "200" ]; then
        http_ok=$((http_ok + 1))
    fi
done

if [ "$http_ok" -ge 95 ]; then
    pass "HTTP flood: $http_ok/100 returned 200"
else
    fail "HTTP flood: only $http_ok/100 returned 200"
fi

# Verify daemon survived
post_http=$(ipc_cmd 5000 2 "STATUS")
if echo "$post_http" | grep -q "status:active"; then
    pass "Daemon alive after HTTP flood"
else
    fail "Daemon crashed after HTTP flood"
fi

echo ""

# ================================================================
# TEST 3: WebSocket Reconnect Storm (20 rapid connect/disconnect)
# ================================================================
echo "=== TEST 3: WebSocket Reconnect Storm (20 cycles) ==="
ws_key="dGhlIHNhbXBsZSBub25jZQ=="
ws_ok=0
for i in $(seq 1 20); do
    ws_resp=$(printf "GET /ws HTTP/1.1\r\nHost: 127.0.0.1:8080\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: ${ws_key}\r\nSec-WebSocket-Version: 13\r\n\r\n" | nc -w 1 127.0.0.1 8080 2>/dev/null | head -1)
    if echo "$ws_resp" | grep -q "101"; then
        ws_ok=$((ws_ok + 1))
    fi
done

if [ "$ws_ok" -ge 18 ]; then
    pass "WS reconnect storm: $ws_ok/20 upgrades succeeded"
else
    fail "WS reconnect storm: only $ws_ok/20 upgrades succeeded"
fi

# Verify daemon survived (this was the original crash trigger)
post_ws=$(ipc_cmd 5000 2 "STATUS")
if echo "$post_ws" | grep -q "status:active"; then
    pass "Daemon alive after WS reconnect storm"
else
    fail "Daemon CRASHED after WS reconnect storm (original bug)"
fi

echo ""

# ================================================================
# TEST 4: Message Storm (50 rapid MSG SEND)
# ================================================================
echo "=== TEST 4: Message Storm (50 rapid MSG SEND) ==="
msg_ok=0
for i in $(seq 1 50); do
    r=$(ipc_cmd 5000 1 "MSG SEND Stress message number $i")
    if echo "$r" | grep -q "msg:sent"; then
        msg_ok=$((msg_ok + 1))
    fi
done

if [ "$msg_ok" -ge 45 ]; then
    pass "Message storm: $msg_ok/50 messages sent"
else
    fail "Message storm: only $msg_ok/50 messages sent"
fi

post_msg=$(ipc_cmd 5000 2 "STATUS")
if echo "$post_msg" | grep -q "status:active"; then
    pass "Daemon alive after message storm"
else
    fail "Daemon crashed after message storm"
fi

echo ""

# ================================================================
# TEST 5: Transfer Storm (50 rapid MONEY TRANSFER)
# ================================================================
echo "=== TEST 5: Transfer Storm (50 rapid MONEY TRANSFER) ==="

# Get initial balance
bal_before=$(ipc_cmd 5000 2 "WALLET BALANCE" | sed 's/wallet_balance://')
xfer_ok=0
for i in $(seq 1 50); do
    r=$(ipc_cmd 5000 1 "MONEY TRANSFER 1 did:key:zStressRecipient$i")
    if echo "$r" | grep -q "transfer:ok"; then
        xfer_ok=$((xfer_ok + 1))
    fi
done

if [ "$xfer_ok" -ge 45 ]; then
    pass "Transfer storm: $xfer_ok/50 transfers succeeded"
else
    fail "Transfer storm: only $xfer_ok/50 transfers succeeded"
fi

# Verify balance changed correctly
bal_after=$(ipc_cmd 5000 2 "WALLET BALANCE" | sed 's/wallet_balance://')
expected_decrease=$xfer_ok
actual_decrease=$((bal_before - bal_after))
if [ "$actual_decrease" -eq "$expected_decrease" ] 2>/dev/null; then
    pass "Balance accounting correct after storm ($bal_before -> $bal_after, -$actual_decrease)"
else
    fail "Balance accounting wrong ($bal_before -> $bal_after, expected -$expected_decrease, got -$actual_decrease)"
fi

post_xfer=$(ipc_cmd 5000 2 "STATUS")
if echo "$post_xfer" | grep -q "status:active"; then
    pass "Daemon alive after transfer storm"
else
    fail "Daemon crashed after transfer storm"
fi

echo ""

# ================================================================
# TEST 6: DHT Rapid Write/Read (100 key-value pairs)
# ================================================================
echo "=== TEST 6: DHT Rapid Write/Read (100 KV pairs) ==="
dht_write_ok=0
for i in $(seq 1 100); do
    r=$(ipc_cmd 5000 1 "DHT STORE stress_key_$i stress_val_$i")
    if echo "$r" | grep -q "dht:stored"; then
        dht_write_ok=$((dht_write_ok + 1))
    fi
done

if [ "$dht_write_ok" -ge 95 ]; then
    pass "DHT write storm: $dht_write_ok/100 stores succeeded"
else
    fail "DHT write storm: only $dht_write_ok/100 stores succeeded"
fi

# Read back a random sample
dht_read_ok=0
for i in 10 25 50 75 99; do
    r=$(ipc_cmd 5000 1 "DHT GET stress_key_$i")
    if echo "$r" | grep -q "value:stress_val_$i"; then
        dht_read_ok=$((dht_read_ok + 1))
    fi
done

if [ "$dht_read_ok" -ge 4 ]; then
    pass "DHT read-back: $dht_read_ok/5 samples match"
else
    fail "DHT read-back: only $dht_read_ok/5 samples match"
fi

echo ""

# ================================================================
# TEST 7: Mixed Workload (parallel different operations)
# ================================================================
echo "=== TEST 7: Mixed Workload (interleaved ops) ==="
mixed_ok=0
for i in $(seq 1 20); do
    r1=$(ipc_cmd 5000 1 "STATUS")
    r2=$(ipc_cmd 5000 1 "MSG SEND Mixed test $i")
    r3=$(ipc_cmd 5000 1 "DHT STORE mix_$i mixv_$i")
    r4=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8080/api/status 2>/dev/null)
    if echo "$r1" | grep -q "status:active" && echo "$r2" | grep -q "msg:sent" && echo "$r3" | grep -q "dht:stored" && [ "$r4" = "200" ]; then
        mixed_ok=$((mixed_ok + 1))
    fi
done

if [ "$mixed_ok" -ge 18 ]; then
    pass "Mixed workload: $mixed_ok/20 rounds fully succeeded"
else
    fail "Mixed workload: only $mixed_ok/20 rounds fully succeeded"
fi

echo ""

# ================================================================
# TEST 8: Final Health Check
# ================================================================
echo "=== TEST 8: Final Health Check ==="
final_status=$(ipc_cmd 5000 2 "STATUS")
if echo "$final_status" | grep -q "status:active"; then
    pass "Daemon alive after all stress tests"
else
    fail "Daemon died during stress tests"
fi

final_health=$(ipc_cmd 5000 2 "HEALTH")
if echo "$final_health" | grep -q "health:"; then
    pass "Health check: responsive after all stress ($(echo "$final_health" | grep -o 'health:[a-z]*'))"
else
    fail "Health check failed after stress"
fi

echo ""
echo "==========================================================="
echo "  RESULTS: $PASS/$TOTAL passed, $FAIL failed"
echo "==========================================================="
if [ $FAIL -gt 0 ]; then
    echo ""
    echo "[FAIL] Some stress tests failed. See output above."
    exit 1
else
    echo ""
    echo "[PASS] All live daemon stress tests passed!"
    exit 0
fi
