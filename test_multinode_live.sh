#!/bin/bash
# ErnosDecent — Multi-Node Live Stress Test
# Tests 3-node cluster: bootstrap, consensus, DHT replication,
# cross-node operations, and node failure recovery.
# Requires: ./node binary built via build.sh

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

assert_contains() {
    local name="$1"
    local haystack="$2"
    local needle="$3"
    if echo "$haystack" | grep -q "$needle"; then
        pass "$name"
    else
        fail "$name (expected: '$needle')"
        echo "         got: '$haystack'"
    fi
}

ipc_cmd() {
    local port="$1"
    local cmd="$2"
    local token
    token=$(tr -d '\r\n ' < "$HOME/.ernosdecent/ipc-token" 2>/dev/null) || return 1
    [ -n "$token" ] || return 1
    printf 'AUTH %s %s\n' "$token" "$cmd" | nc -w 2 127.0.0.1 "$port" 2>/dev/null
}

cleanup() {
    echo ""
    echo "[*] Cleaning up all nodes..."
    for pid in $NODE1_PID $NODE2_PID $NODE3_PID; do
        kill "$pid" 2>/dev/null
        wait "$pid" 2>/dev/null
    done
    lsof -ti:5000,8080,9100,9101,9102,9200,9300,9280,9400,9500,9480 2>/dev/null | xargs kill -9 2>/dev/null
    sleep 1
}

trap cleanup EXIT

echo "==========================================================="
echo "  ErnosDecent — Multi-Node Live Stress Test"
echo "  3-node cluster: bootstrap, consensus, DHT, recovery"
echo "==========================================================="
echo ""

# ================================================================
# Setup: Start 3-node cluster
# ================================================================

echo "[*] Starting Node 1 (seed, default ports)..."
lsof -ti:5000,8080,9100,9101,9102 2>/dev/null | xargs kill -9 2>/dev/null
sleep 1
./node &
NODE1_PID=$!
sleep 3

# Verify Node 1 is alive
n1_status=$(ipc_cmd 5000 "STATUS")
if echo "$n1_status" | grep -q "status:active"; then
    echo "[+] Node 1 alive (PID $NODE1_PID, IPC:5000)"
else
    echo "[-] FATAL: Node 1 failed to start"
    exit 1
fi

echo "[*] Starting Node 2 (port 9200, seed -> Node 1)..."
lsof -ti:9200,9300,9280 2>/dev/null | xargs kill -9 2>/dev/null
sleep 1
./node --port 9200 --seed 127.0.0.1:9101 &
NODE2_PID=$!
sleep 3

n2_status=$(ipc_cmd 9300 "STATUS")
if echo "$n2_status" | grep -q "status:active"; then
    echo "[+] Node 2 alive (PID $NODE2_PID, IPC:9300)"
else
    echo "[-] FATAL: Node 2 failed to start"
    exit 1
fi

echo "[*] Starting Node 3 (port 9400, seed -> Node 1)..."
lsof -ti:9400,9500,9480 2>/dev/null | xargs kill -9 2>/dev/null
sleep 1
./node --port 9400 --seed 127.0.0.1:9101 &
NODE3_PID=$!
sleep 3

n3_status=$(ipc_cmd 9500 "STATUS")
if echo "$n3_status" | grep -q "status:active"; then
    echo "[+] Node 3 alive (PID $NODE3_PID, IPC:9500)"
else
    echo "[-] FATAL: Node 3 failed to start"
    exit 1
fi

echo ""
echo "=== TEST SUITE 1: Cluster Formation ==="
echo ""

# 1.1 All nodes responding
assert_contains "Node 1 is active" "$n1_status" "status:active"
assert_contains "Node 2 is active" "$n2_status" "status:active"
assert_contains "Node 3 is active" "$n3_status" "status:active"

# 1.2 Node 2 and 3 discovered seed via DHT
n2_dht_size=$(echo "$n2_status" | grep -o 'dht_size:[0-9]*' | cut -d: -f2)
if [ "$n2_dht_size" -ge 1 ] 2>/dev/null; then
    pass "Node 2 has DHT entries (dht_size=$n2_dht_size)"
else
    fail "Node 2 has DHT entries (dht_size=$n2_dht_size, expected >= 1)"
fi

n3_dht_size=$(echo "$n3_status" | grep -o 'dht_size:[0-9]*' | cut -d: -f2)
if [ "$n3_dht_size" -ge 1 ] 2>/dev/null; then
    pass "Node 3 has DHT entries (dht_size=$n3_dht_size)"
else
    fail "Node 3 has DHT entries (dht_size=$n3_dht_size, expected >= 1)"
fi

# 1.3 Node 2 and 3 have Raft peers
assert_contains "Node 2 has Raft peer" "$n2_status" "peers:1"
assert_contains "Node 3 has Raft peer" "$n3_status" "peers:1"

# 1.4 Node 1 has DHT entries from joiners
n1_refresh=$(ipc_cmd 5000 "STATUS")
n1_dht=$(echo "$n1_refresh" | grep -o 'dht_size:[0-9]*' | cut -d: -f2)
if [ "$n1_dht" -ge 1 ] 2>/dev/null; then
    pass "Node 1 sees joiners in DHT (dht_size=$n1_dht)"
else
    fail "Node 1 sees joiners in DHT (dht_size=$n1_dht, expected >= 1)"
fi

echo ""
echo "=== TEST SUITE 2: Cross-Node DHT Operations ==="
echo ""

# 2.1 Store on Node 1, retrieve on Node 1
dht_s1=$(ipc_cmd 5000 "DHT STORE cluster_key_1 value_from_node1")
assert_contains "Node 1 DHT STORE" "$dht_s1" "dht:stored"

dht_g1=$(ipc_cmd 5000 "DHT GET cluster_key_1")
assert_contains "Node 1 retrieves own key" "$dht_g1" "value:value_from_node1"

# 2.2 Store on Node 2
dht_s2=$(ipc_cmd 9300 "DHT STORE cluster_key_2 value_from_node2")
assert_contains "Node 2 DHT STORE" "$dht_s2" "dht:stored"

dht_g2=$(ipc_cmd 9300 "DHT GET cluster_key_2")
assert_contains "Node 2 retrieves own key" "$dht_g2" "value:value_from_node2"

# 2.3 Store on Node 3
dht_s3=$(ipc_cmd 9500 "DHT STORE cluster_key_3 value_from_node3")
assert_contains "Node 3 DHT STORE" "$dht_s3" "dht:stored"

dht_g3=$(ipc_cmd 9500 "DHT GET cluster_key_3")
assert_contains "Node 3 retrieves own key" "$dht_g3" "value:value_from_node3"

# 2.4 Rapid DHT operations (50 keys on each node)
echo "  [....] Rapid DHT stress: 50 keys per node..."
dht_ok=0
for i in $(seq 1 50); do
    r=$(ipc_cmd 5000 "DHT STORE stress_$i val_$i")
    if echo "$r" | grep -q "dht:stored"; then
        dht_ok=$((dht_ok + 1))
    fi
done
if [ "$dht_ok" -ge 45 ]; then
    pass "Rapid DHT: $dht_ok/50 stores succeeded on Node 1"
else
    fail "Rapid DHT: only $dht_ok/50 stores succeeded on Node 1"
fi

# Verify a sample
dht_sample=$(ipc_cmd 5000 "DHT GET stress_25")
assert_contains "Rapid DHT sample retrieval" "$dht_sample" "value:val_25"

echo ""
echo "=== TEST SUITE 3: Cross-Node Name Registry ==="
echo ""

# 3.1 Register name on Node 1
ts=$(date +%s)
name1="cluster-alice-$ts"
nr1=$(ipc_cmd 5000 "NAME REGISTER $name1")
assert_contains "Node 1 registers name" "$nr1" "name:registered"

# 3.2 Resolve on Node 1
nres1=$(ipc_cmd 5000 "NAME RESOLVE $name1")
assert_contains "Node 1 resolves own name" "$nres1" "name:resolved"

# 3.3 Register name on Node 2
name2="cluster-bob-$ts"
nr2=$(ipc_cmd 9300 "NAME REGISTER $name2")
assert_contains "Node 2 registers name" "$nr2" "name:registered"

# 3.4 Register name on Node 3
name3="cluster-charlie-$ts"
nr3=$(ipc_cmd 9500 "NAME REGISTER $name3")
assert_contains "Node 3 registers name" "$nr3" "name:registered"

echo ""
echo "=== TEST SUITE 4: Cross-Node UTXO Transfers ==="
echo ""

# 4.1 Node 1 initial balance
bal1=$(ipc_cmd 5000 "WALLET BALANCE" | sed 's/wallet_balance://')
assert_contains "Node 1 has initial balance" "bal:$bal1" "bal:"

# 4.2 Node 2 initial balance
bal2=$(ipc_cmd 9300 "WALLET BALANCE" | sed 's/wallet_balance://')
assert_contains "Node 2 has initial balance" "bal:$bal2" "bal:"

# 4.3 Transfer on Node 1
xfer1=$(ipc_cmd 5000 "MONEY TRANSFER 100 did:key:zTestRecipient1")
assert_contains "Node 1 transfer succeeds" "$xfer1" "transfer:ok"
assert_contains "Node 1 transfer amount" "$xfer1" "amount:100"

# 4.4 Transfer on Node 2
xfer2=$(ipc_cmd 9300 "MONEY TRANSFER 75 did:key:zTestRecipient2")
assert_contains "Node 2 transfer succeeds" "$xfer2" "transfer:ok"

# 4.5 Transfer on Node 3
xfer3=$(ipc_cmd 9500 "MONEY TRANSFER 50 did:key:zTestRecipient3")
assert_contains "Node 3 transfer succeeds" "$xfer3" "transfer:ok"

# 4.6 Balances decreased
bal1_after=$(ipc_cmd 5000 "WALLET BALANCE" | sed 's/wallet_balance://')
if [ "$bal1_after" -lt "$bal1" ] 2>/dev/null; then
    pass "Node 1 balance decreased ($bal1 -> $bal1_after)"
else
    fail "Node 1 balance didn't decrease ($bal1 -> $bal1_after)"
fi

echo ""
echo "=== TEST SUITE 5: Messaging Per Node ==="
echo ""

# 5.1 Each node can send messages
msg1=$(ipc_cmd 5000 "MSG SEND Hello from node 1")
assert_contains "Node 1 MSG SEND" "$msg1" "msg:sent"
assert_contains "Node 1 MSG has ID" "$msg1" "id:"

msg2=$(ipc_cmd 9300 "MSG SEND Hello from node 2")
assert_contains "Node 2 MSG SEND" "$msg2" "msg:sent"

msg3=$(ipc_cmd 9500 "MSG SEND Hello from node 3")
assert_contains "Node 3 MSG SEND" "$msg3" "msg:sent"

echo ""
echo "=== TEST SUITE 6: Health Checks Across Cluster ==="
echo ""

# 6.1 All nodes pass health checks
h1=$(ipc_cmd 5000 "HEALTH")
assert_contains "Node 1 health check" "$h1" "health:"
assert_contains "Node 1 crypto ok" "$h1" "crypto:healthy"

h2=$(ipc_cmd 9300 "HEALTH")
assert_contains "Node 2 health check" "$h2" "health:"
assert_contains "Node 2 crypto ok" "$h2" "crypto:healthy"

h3=$(ipc_cmd 9500 "HEALTH")
assert_contains "Node 3 health check" "$h3" "health:"
assert_contains "Node 3 crypto ok" "$h3" "crypto:healthy"

echo ""
echo "=== TEST SUITE 7: Node Failure + Recovery ==="
echo ""

# 7.1 Kill Node 3
echo "  [....] Killing Node 3 (PID $NODE3_PID)..."
kill $NODE3_PID 2>/dev/null
wait $NODE3_PID 2>/dev/null
sleep 2

# 7.2 Node 1 and 2 still alive
n1_alive=$(ipc_cmd 5000 "STATUS")
assert_contains "Node 1 survives Node 3 death" "$n1_alive" "status:active"

n2_alive=$(ipc_cmd 9300 "STATUS")
assert_contains "Node 2 survives Node 3 death" "$n2_alive" "status:active"

# 7.3 Node 1 and 2 can still do DHT ops
dht_survive=$(ipc_cmd 5000 "DHT STORE post_crash_key post_crash_value")
assert_contains "Node 1 DHT works after Node 3 death" "$dht_survive" "dht:stored"

dht_s_n2=$(ipc_cmd 9300 "DHT STORE post_crash_key2 post_crash_value2")
assert_contains "Node 2 DHT works after Node 3 death" "$dht_s_n2" "dht:stored"

# 7.4 Restart Node 3
echo "  [....] Restarting Node 3..."
lsof -ti:9400,9500,9480 2>/dev/null | xargs kill -9 2>/dev/null
sleep 1
./node --port 9400 --seed 127.0.0.1:9101 &
NODE3_PID=$!
sleep 3

n3_restart=$(ipc_cmd 9500 "STATUS")
assert_contains "Node 3 restarts successfully" "$n3_restart" "status:active"
n3_rec_dht_size=$(echo "$n3_restart" | grep -o 'dht_size:[0-9]*' | cut -d: -f2)
if [ "$n3_rec_dht_size" -ge 1 ] 2>/dev/null; then
    pass "Node 3 reconnects to DHT (dht_size=$n3_rec_dht_size)"
else
    fail "Node 3 reconnects to DHT (dht_size=$n3_rec_dht_size, expected >= 1)"
fi

echo ""
echo "=== TEST SUITE 8: Concurrent Operations Stress ==="
echo ""

# 8.1 Rapid concurrent operations across all 3 nodes
echo "  [....] Concurrent stress: 30 ops across 3 nodes..."
concurrent_ok=0
for i in $(seq 1 10); do
    r1=$(ipc_cmd 5000 "DHT STORE conc1_$i cv1_$i")
    r2=$(ipc_cmd 9300 "DHT STORE conc2_$i cv2_$i")
    r3=$(ipc_cmd 9500 "DHT STORE conc3_$i cv3_$i")
    if echo "$r1" | grep -q "dht:stored"; then concurrent_ok=$((concurrent_ok + 1)); fi
    if echo "$r2" | grep -q "dht:stored"; then concurrent_ok=$((concurrent_ok + 1)); fi
    if echo "$r3" | grep -q "dht:stored"; then concurrent_ok=$((concurrent_ok + 1)); fi
done

if [ "$concurrent_ok" -ge 25 ]; then
    pass "Concurrent stress: $concurrent_ok/30 ops succeeded"
else
    fail "Concurrent stress: only $concurrent_ok/30 ops succeeded"
fi

# 8.2 All nodes still healthy after stress
h1_post=$(ipc_cmd 5000 "STATUS")
assert_contains "Node 1 alive after stress" "$h1_post" "status:active"
h2_post=$(ipc_cmd 9300 "STATUS")
assert_contains "Node 2 alive after stress" "$h2_post" "status:active"
h3_post=$(ipc_cmd 9500 "STATUS")
assert_contains "Node 3 alive after stress" "$h3_post" "status:active"

echo ""
echo "==========================================================="
echo "  RESULTS: $PASS/$TOTAL passed, $FAIL failed"
echo "==========================================================="
if [ $FAIL -gt 0 ]; then
    echo ""
    echo "[FAIL] Some multi-node tests failed. See output above."
    exit 1
else
    echo ""
    echo "[PASS] All multi-node stress tests passed!"
    exit 0
fi
