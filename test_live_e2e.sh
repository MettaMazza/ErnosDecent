#!/bin/bash
# ErnosDecent — Live System E2E Test Harness (Shell)
# Tests every user-facing feature through the real running daemon
# No compilation needed. Uses nc/curl directly.

set -o pipefail

# Netcat wrapper to automatically inject loopback IPC AUTH tokens
nc() {
    if [ "$1" = "-z" ]; then
        command nc "$@"
        return $?
    fi
    local input
    input=$(cat)
    # If the input is an HTTP request or already has AUTH, pass it raw
    if [[ "$input" == "AUTH "* ]] || [[ "$input" == "GET "* ]] || [[ "$input" == "POST "* ]] || [[ "$input" == *"\r\n\r\n"* ]]; then
        printf '%s' "$input" | command nc "$@"
    else
        local token
        token=$(tr -d '\r\n ' < "$HOME/.ernosdecent/ipc-token" 2>/dev/null) || return 1
        [ -n "$token" ] || return 1
        printf 'AUTH %s %s\n' "$token" "$input" | command nc "$@"
    fi
}

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
    if [[ "$haystack" == *"$needle"* ]]; then
        pass "$name"
    else
        fail "$name (expected: '$needle')"
        echo "         got: '$haystack'"
    fi
}

assert_not_empty() {
    local name="$1"
    local val="$2"
    if [ -n "$val" ]; then
        pass "$name"
    else
        fail "$name (empty response)"
    fi
}

echo "==========================================================="
echo "  ErnosDecent — Live System E2E Test Harness (Shell)"
echo "  Tests every user-facing feature through the real daemon"
echo "==========================================================="
echo ""

# Wait for daemon
echo "[*] Waiting for daemon IPC port 5000..."
for i in $(seq 1 20); do
    if nc -z 127.0.0.1 5000 2>/dev/null; then
        echo "[+] Daemon is ready."
        break
    fi
    if [ $i -eq 20 ]; then
        echo "[FATAL] Daemon not running. Start ./node first."
        exit 1
    fi
    sleep 0.5
done

echo ""
echo "=== TEST SUITE 1: IPC Commands ==="
echo ""

# 1.1 STATUS
resp=$(echo "STATUS" | nc -w 2 127.0.0.1 5000 2>/dev/null)
assert_contains "IPC STATUS returns status:active" "$resp" "status:active"
assert_contains "IPC STATUS returns role:" "$resp" "role:"
assert_contains "IPC STATUS returns did:" "$resp" "did:"
assert_contains "IPC STATUS returns term:" "$resp" "term:"
assert_contains "IPC STATUS returns peers:" "$resp" "peers:"
assert_contains "IPC STATUS returns dht_size:" "$resp" "dht_size:"

# 1.2 IDENTITY
resp=$(echo "IDENTITY" | nc -w 2 127.0.0.1 5000 2>/dev/null)
assert_contains "IPC IDENTITY returns did:" "$resp" "did:"
assert_contains "IPC IDENTITY returns signing_key:" "$resp" "signing_key:"
assert_contains "IPC IDENTITY returns encryption_key:" "$resp" "encryption_key:"

# 1.3 WALLET BALANCE
resp=$(echo "WALLET BALANCE" | nc -w 2 127.0.0.1 5000 2>/dev/null)
assert_contains "IPC WALLET BALANCE returns wallet_balance:" "$resp" "wallet_balance:"

# 1.4 STORAGE STATUS
resp=$(echo "STORAGE STATUS" | nc -w 2 127.0.0.1 5000 2>/dev/null)
assert_contains "IPC STORAGE returns type:storage" "$resp" '"type":"storage"'
assert_contains "IPC STORAGE returns chunk_count" "$resp" '"chunk_count"'

# 1.5 POOL STATUS
resp=$(echo "POOL STATUS" | nc -w 2 127.0.0.1 5000 2>/dev/null)
assert_contains "IPC POOL returns pool:active" "$resp" "pool:active"
assert_contains "IPC POOL returns compute_jobs:" "$resp" "compute_jobs:"
assert_contains "IPC POOL returns relay_registrations:" "$resp" "relay_registrations:"

# 1.6 NET STATUS
resp=$(echo "NET STATUS" | nc -w 2 127.0.0.1 5000 2>/dev/null)
assert_contains "IPC NET returns net:active" "$resp" "net:active"
assert_contains "IPC NET returns dht_size:" "$resp" "dht_size:"
assert_contains "IPC NET returns nat_mode:" "$resp" "nat_mode:"
assert_contains "IPC NET returns active_circuits:" "$resp" "active_circuits:"

# 1.7 MSG SEND
resp=$(echo "MSG SEND live_test_message" | nc -w 2 127.0.0.1 5000 2>/dev/null)
assert_contains "IPC MSG SEND returns msg:sent" "$resp" "msg:sent"
assert_contains "IPC MSG SEND returns id:" "$resp" "id:"
assert_contains "IPC MSG SEND echoes text:" "$resp" "text:live_test_message"

# 1.8 MONEY TRANSFER
resp=$(echo "MONEY TRANSFER 10 did:key:test_recipient" | nc -w 2 127.0.0.1 5000 2>/dev/null)
assert_contains "IPC MONEY TRANSFER returns transfer:" "$resp" "transfer:"

# 1.9 MONEY SWAP
resp=$(echo "MONEY SWAP ERN USD 5" | nc -w 2 127.0.0.1 5000 2>/dev/null)
assert_contains "IPC MONEY SWAP returns swap:" "$resp" "swap:"

# 1.10 HEALTH
resp=$(echo "HEALTH" | nc -w 2 127.0.0.1 5000 2>/dev/null)
assert_not_empty "IPC HEALTH returns non-empty" "$resp"
assert_contains "IPC HEALTH returns health:" "$resp" "health:"

# 1.11 Unknown command
resp=$(echo "BOGUS_COMMAND" | nc -w 2 127.0.0.1 5000 2>/dev/null)
assert_contains "IPC unknown returns error:unknown_command" "$resp" "error:unknown_command"

# 1.12 AI INFER (last — blocks the single-threaded IPC server while the LLM processes)
resp=$(echo "AI INFER hello world" | nc -w 120 127.0.0.1 5000 2>/dev/null)
assert_contains "IPC AI INFER returns ai:" "$resp" "ai:"
assert_contains "IPC AI INFER returns RESPONSE" "$resp" "RESPONSE"

echo ""
echo "=== TEST SUITE 2: HTTP Static Serving ==="
echo ""

# 2.1 GET /
code=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8088/)
assert_contains "HTTP GET / returns 200" "$code" "200"

body=$(curl -s http://127.0.0.1:8088/)
assert_contains "HTTP GET / returns HTML" "$body" "<!DOCTYPE html>"

# 2.2 GET /app.js
code=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8088/app.js)
assert_contains "HTTP GET /app.js returns 200" "$code" "200"

body=$(curl -s http://127.0.0.1:8088/app.js)
assert_contains "HTTP GET /app.js has connectDaemon" "$body" "connectDaemon"

# 2.3 GET /style.css
code=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8088/style.css)
assert_contains "HTTP GET /style.css returns 200" "$code" "200"

# 2.4 GET /nonexistent
code=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8088/does_not_exist.xyz)
assert_contains "HTTP GET /nonexistent returns 404" "$code" "404"

echo ""
echo "=== TEST SUITE 3: HTTP API Endpoints ==="
echo ""

# 3.1 GET /api/status
resp=$(curl -s http://127.0.0.1:8088/api/status)
assert_contains "API /api/status returns type:status" "$resp" '"type":"status"'
assert_contains "API /api/status returns did" "$resp" '"did":"'
assert_contains "API /api/status returns role" "$resp" '"role":"'

# 3.2 GET /api/wallet
resp=$(curl -s http://127.0.0.1:8088/api/wallet)
assert_contains "API /api/wallet returns type:wallet" "$resp" '"type":"wallet"'
assert_contains "API /api/wallet returns balance" "$resp" '"balance":"'

# 3.3 GET /api/storage
resp=$(curl -s http://127.0.0.1:8088/api/storage)
assert_contains "API /api/storage returns type:storage" "$resp" '"type":"storage"'
assert_contains "API /api/storage returns chunk_count" "$resp" '"chunk_count":'

# 3.4 GET /api/pool
resp=$(curl -s http://127.0.0.1:8088/api/pool)
assert_contains "API /api/pool returns type:pool" "$resp" '"type":"pool"'
assert_contains "API /api/pool returns bandwidth" "$resp" '"bandwidth_up":'

echo ""
echo "=== TEST SUITE 4: WebSocket Upgrade ==="
echo ""

# 4.1 WebSocket Upgrade (verify 101 response)
resp=$(curl -s --include \
  --header "Upgrade: websocket" \
  --header "Connection: Upgrade" \
  --header "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==" \
  --header "Sec-WebSocket-Version: 13" \
  --max-time 2 \
  http://127.0.0.1:8088/ws 2>/dev/null || true)
assert_contains "WS upgrade returns 101" "$resp" "101 Switching Protocols"
assert_contains "WS upgrade returns Sec-WebSocket-Accept" "$resp" "Sec-WebSocket-Accept:"

echo ""
echo "=== TEST SUITE 5: Data Integrity ==="
echo ""

# 5.1 DID format is valid
resp=$(echo "STATUS" | nc -w 2 127.0.0.1 5000 2>/dev/null)
# resp format: status:active,role:follower,did:did:key:z6Mk...,term:0,...
# Extract after "did:" prefix — the DID value itself starts with "did:key:"
did=$(echo "$resp" | grep -o 'did:did:key:[^,]*' | sed 's/^did://')
assert_contains "DID starts with did:key:" "$did" "did:key:z6Mk"

# 5.2 Signing key is hex
resp=$(echo "IDENTITY" | nc -w 2 127.0.0.1 5000 2>/dev/null)
signing_key=$(echo "$resp" | sed 's/.*signing_key:\([^,]*\).*/\1/')
if echo "$signing_key" | grep -qE '^[0-9a-f]{64}$'; then
    pass "Signing key is 32-byte hex"
else
    fail "Signing key is 32-byte hex (got: $signing_key)"
fi

# 5.3 Encryption key is hex
enc_key=$(echo "$resp" | sed 's/.*encryption_key:\([^,]*\).*/\1/')
if echo "$enc_key" | grep -qE '^[0-9a-f]{64}$'; then
    pass "Encryption key is 32-byte hex"
else
    fail "Encryption key is 32-byte hex (got: $enc_key)"
fi

# 5.4 Message ID is SHA256 hash
resp=$(echo "MSG SEND integrity_check" | nc -w 2 127.0.0.1 5000 2>/dev/null)
msg_id=$(echo "$resp" | sed 's/.*id:\([^,]*\).*/\1/')
if echo "$msg_id" | grep -qE '^[0-9a-f]{64}$'; then
    pass "Message ID is SHA256 hash"
else
    fail "Message ID is SHA256 hash (got: $msg_id)"
fi

# 5.5 Health check returns structured data
resp=$(echo "HEALTH" | nc -w 2 127.0.0.1 5000 2>/dev/null)
assert_contains "Health includes crypto check" "$resp" "crypto:"
assert_contains "Health includes consensus check" "$resp" "consensus:"
assert_contains "Health includes network check" "$resp" "network:"

# 5.6 Consecutive STATUS calls return consistent DID
resp1=$(echo "STATUS" | nc -w 2 127.0.0.1 5000 2>/dev/null)
resp2=$(echo "STATUS" | nc -w 2 127.0.0.1 5000 2>/dev/null)
did1=$(echo "$resp1" | sed 's/.*did:\([^,]*\).*/\1/')
did2=$(echo "$resp2" | sed 's/.*did:\([^,]*\).*/\1/')
if [ "$did1" = "$did2" ]; then
    pass "DID is consistent across STATUS calls"
else
    fail "DID is consistent (got: $did1 vs $did2)"
fi

echo ""
echo "=== TEST SUITE 6: Real UTXO Transfers ==="
echo ""

# 6.1 Get initial balance
bal_resp=$(echo "WALLET BALANCE" | nc -w 2 127.0.0.1 5000 2>/dev/null)
initial_bal=$(echo "$bal_resp" | sed 's/wallet_balance://')
assert_not_empty "Initial balance is non-empty" "$initial_bal"

# 6.2 Transfer 50 coins
xfer_resp=$(echo "MONEY TRANSFER 50 did:key:zE2ETestRecipient" | nc -w 2 127.0.0.1 5000 2>/dev/null)
assert_contains "Transfer returns transfer:ok" "$xfer_resp" "transfer:ok"
assert_contains "Transfer returns tx_id:" "$xfer_resp" "tx_id:"
assert_contains "Transfer returns amount:50" "$xfer_resp" "amount:50"
assert_contains "Transfer returns to:" "$xfer_resp" "to:did:key:zE2ETestRecipient"

# 6.3 Verify balance decreased
bal_after=$(echo "WALLET BALANCE" | nc -w 2 127.0.0.1 5000 2>/dev/null | sed 's/wallet_balance://')
expected_bal=$((initial_bal - 50))
if [ "$bal_after" = "$expected_bal" ]; then
    pass "Balance decreased by transfer amount ($initial_bal -> $bal_after)"
else
    fail "Balance decreased by transfer amount (expected $expected_bal, got $bal_after)"
fi

# 6.4 Second transfer (chain UTXO spending)
xfer2_resp=$(echo "MONEY TRANSFER 25 did:key:zE2ETestRecipient2" | nc -w 2 127.0.0.1 5000 2>/dev/null)
assert_contains "Second transfer succeeds" "$xfer2_resp" "transfer:ok"
bal_after2=$(echo "WALLET BALANCE" | nc -w 2 127.0.0.1 5000 2>/dev/null | sed 's/wallet_balance://')
expected_bal2=$((expected_bal - 25))
if [ "$bal_after2" = "$expected_bal2" ]; then
    pass "Balance correct after chained transfer ($expected_bal -> $bal_after2)"
else
    fail "Balance correct after chained transfer (expected $expected_bal2, got $bal_after2)"
fi

# 6.5 Overdraft protection
over_resp=$(echo "MONEY TRANSFER 999999999999 did:key:zOverdraftTest" | nc -w 2 127.0.0.1 5000 2>/dev/null)
assert_contains "Overdraft rejected" "$over_resp" "transfer:error"
assert_contains "Overdraft reason: insufficient_balance" "$over_resp" "insufficient_balance"

# 6.6 Balance unchanged after failed transfer
bal_unchanged=$(echo "WALLET BALANCE" | nc -w 2 127.0.0.1 5000 2>/dev/null | sed 's/wallet_balance://')
if [ "$bal_unchanged" = "$bal_after2" ]; then
    pass "Balance unchanged after failed overdraft ($bal_unchanged)"
else
    fail "Balance unchanged after failed overdraft (expected $bal_after2, got $bal_unchanged)"
fi

echo ""
echo "=== TEST SUITE 7: DHT Store / Get ==="
echo ""

# 7.1 Store a value
dht_store=$(echo "DHT STORE testkey1 hello_world_123" | nc -w 2 127.0.0.1 5000 2>/dev/null)
assert_contains "DHT STORE returns dht:stored" "$dht_store" "dht:stored"
assert_contains "DHT STORE returns key" "$dht_store" "key:testkey1"

# 7.2 Get the stored value
dht_get=$(echo "DHT GET testkey1" | nc -w 2 127.0.0.1 5000 2>/dev/null)
assert_contains "DHT GET returns dht:found" "$dht_get" "dht:found"
assert_contains "DHT GET returns correct value" "$dht_get" "value:hello_world_123"

# 7.3 Get a non-existent key
dht_miss=$(echo "DHT GET nonexistent_key_xyz" | nc -w 2 127.0.0.1 5000 2>/dev/null)
assert_contains "DHT GET missing returns not_found" "$dht_miss" "dht:not_found"

# 7.4 Overwrite an existing key
dht_over=$(echo "DHT STORE testkey1 updated_value" | nc -w 2 127.0.0.1 5000 2>/dev/null)
assert_contains "DHT STORE overwrite succeeds" "$dht_over" "dht:stored"
dht_get2=$(echo "DHT GET testkey1" | nc -w 2 127.0.0.1 5000 2>/dev/null)
assert_contains "DHT GET returns updated value" "$dht_get2" "value:updated_value"

echo ""
echo "=== TEST SUITE 8: Name Register / Resolve ==="
echo ""

# 8.1 Register a name (use timestamp for uniqueness)
test_name="e2e-name-$(date +%s)"
name_reg=$(echo "NAME REGISTER $test_name" | nc -w 2 127.0.0.1 5000 2>/dev/null)
assert_contains "NAME REGISTER returns name:registered" "$name_reg" "name:registered"
assert_contains "NAME REGISTER returns name" "$name_reg" "name:$test_name"
assert_contains "NAME REGISTER returns did" "$name_reg" "did:did:key:"

# 8.2 Resolve the registered name
name_res=$(echo "NAME RESOLVE $test_name" | nc -w 2 127.0.0.1 5000 2>/dev/null)
assert_contains "NAME RESOLVE returns name:resolved" "$name_res" "name:resolved"
assert_contains "NAME RESOLVE returns correct DID" "$name_res" "did:did:key:"

# 8.3 Resolve a non-existent name
name_miss=$(echo "NAME RESOLVE nonexistent_name_xyz" | nc -w 2 127.0.0.1 5000 2>/dev/null)
assert_contains "NAME RESOLVE missing returns not_found" "$name_miss" "name:not_found"

# 8.4 Register a second name for same DID
test_name2="e2e-name2-$(date +%s)"
name_reg2=$(echo "NAME REGISTER $test_name2" | nc -w 2 127.0.0.1 5000 2>/dev/null)
assert_contains "Second NAME REGISTER succeeds" "$name_reg2" "name:registered"

echo ""
echo "=== TEST SUITE 9: Multi-Node Bootstrap ==="
echo ""

# Start a second node with --port and --seed
lsof -ti:9200,9201,9202,9203,9280,9300 2>/dev/null | xargs kill -9 2>/dev/null
sleep 1
./node --port 9200 --seed 127.0.0.1:9101 &
NODE2_PID=$!

# Wait for Node 2 IPC to become ready (up to 15 seconds)
for i in $(seq 1 15); do
    n2_check=$(echo "STATUS" | nc -w 1 127.0.0.1 9300 2>/dev/null)
    if echo "$n2_check" | grep -q "status:active"; then
        break
    fi
    sleep 1
done

# 9.1 Node 2 is alive on IPC port 9300
n2_status=$(echo "STATUS" | nc -w 2 127.0.0.1 9300 2>/dev/null)
assert_contains "Node 2 STATUS responds" "$n2_status" "status:active"

# 9.2 Node 2 has peer(s)
assert_contains "Node 2 has peers" "$n2_status" "peers:1"

# 9.3 Node 2 has DHT entries (discovered seed via ping)
n2_dht_size=$(echo "$n2_status" | grep -o 'dht_size:[0-9]*' | cut -d: -f2)
if [ "$n2_dht_size" -ge 1 ] 2>/dev/null; then
    pass "Node 2 has DHT entries (dht_size=$n2_dht_size)"
else
    fail "Node 2 has DHT entries (dht_size=$n2_dht_size, expected >= 1)"
fi

# 9.4 Node 1 also sees the new peer (dht_size >= 1)
n1_dht_size=$(echo "STATUS" | nc -w 2 127.0.0.1 5000 2>/dev/null | grep -o 'dht_size:[0-9]*' | cut -d: -f2)
if [ "$n1_dht_size" -ge 1 ] 2>/dev/null; then
    pass "Node 1 has DHT entries (dht_size=$n1_dht_size)"
else
    fail "Node 1 has DHT entries (dht_size=$n1_dht_size, expected >= 1)"
fi

# 9.5 Node 2 can store and retrieve from its own DHT
n2_dht=$(echo "DHT STORE node2key node2value" | nc -w 2 127.0.0.1 9300 2>/dev/null)
assert_contains "Node 2 DHT STORE works" "$n2_dht" "dht:stored"
n2_get=$(echo "DHT GET node2key" | nc -w 2 127.0.0.1 9300 2>/dev/null)
assert_contains "Node 2 DHT GET works" "$n2_get" "dht:found"

# Cleanup node 2
kill $NODE2_PID 2>/dev/null
wait $NODE2_PID 2>/dev/null

echo ""
echo "=== TEST SUITE 10: HTTP API DHT & Name ==="
echo ""

# 10.1 API /api/status has DID
api_status=$(curl -s http://127.0.0.1:8088/api/status 2>/dev/null)
assert_contains "API status has DID" "$api_status" "did"
assert_contains "API status has role" "$api_status" "role"
assert_contains "API status has dht_size" "$api_status" "dht_size"

# 10.2 API /api/wallet has balance
api_wallet=$(curl -s http://127.0.0.1:8088/api/wallet 2>/dev/null)
assert_contains "API wallet has balance" "$api_wallet" "balance"

# 10.3 API /api/storage has chunk_count
api_store=$(curl -s http://127.0.0.1:8088/api/storage 2>/dev/null)
assert_contains "API storage has chunk_count" "$api_store" "chunk_count"

echo ""
echo "=== TEST SUITE 11: Persistence (Daemon Restart) ==="
echo ""

# Store unique values before restart
persist_key="persist_test_$(date +%s)"
persist_val="persist_value_$(date +%s)"
ipc_cmd_result=$(echo "DHT STORE $persist_key $persist_val" | nc -w 2 127.0.0.1 5000 2>/dev/null)
assert_contains "Pre-restart DHT store" "$ipc_cmd_result" "dht:stored"

# Register a name before restart
persist_name="persist-name-$(date +%s)"
name_pre=$(echo "NAME REGISTER $persist_name" | nc -w 2 127.0.0.1 5000 2>/dev/null)
assert_contains "Pre-restart name register" "$name_pre" "name:registered"

# Get DID before restart
did_pre=$(echo "IDENTITY" | nc -w 2 127.0.0.1 5000 2>/dev/null)
did_val_pre=$(echo "$did_pre" | grep -o 'did:[^,]*' | head -1)

# Kill and restart daemon
echo "  [....] Restarting daemon..."
lsof -ti:5000,8088,9100,9101,9102 2>/dev/null | xargs kill -9 2>/dev/null
sleep 2
nohup ./node > node_restart_2.log 2>&1 &
sleep 3

# Wait for daemon
for i in $(seq 1 10); do
    check=$(echo "STATUS" | nc -w 1 127.0.0.1 5000 2>/dev/null)
    if echo "$check" | grep -q "status:active"; then
        break
    fi
    sleep 1
done

# 11.1 Daemon is alive after restart
post_status=$(echo "STATUS" | nc -w 2 127.0.0.1 5000 2>/dev/null)
assert_contains "Daemon alive after restart" "$post_status" "status:active"

# 11.2 DID persists (same key material)
did_post=$(echo "IDENTITY" | nc -w 2 127.0.0.1 5000 2>/dev/null)
did_val_post=$(echo "$did_post" | grep -o 'did:[^,]*' | head -1)
if [ "$did_val_pre" = "$did_val_post" ]; then
    pass "DID persists across restart ($did_val_post)"
else
    fail "DID changed after restart (was $did_val_pre, now $did_val_post)"
fi

# 11.3 Name resolves after restart
name_post=$(echo "NAME RESOLVE $persist_name" | nc -w 2 127.0.0.1 5000 2>/dev/null)
assert_contains "Name persists after restart" "$name_post" "name:resolved"

# 11.4 Wallet still works after restart
bal_post=$(echo "WALLET BALANCE" | nc -w 2 127.0.0.1 5000 2>/dev/null)
assert_contains "Wallet works after restart" "$bal_post" "wallet_balance:"

echo ""
echo "=== TEST SUITE 12: WebSocket Protocol ==="
echo ""

# 12.1 WS upgrade with correct key produces valid accept header
ws_key="dGhlIHNhbXBsZSBub25jZQ=="
ws_resp=$(printf "GET /ws HTTP/1.1\r\nHost: 127.0.0.1:8088\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: ${ws_key}\r\nSec-WebSocket-Version: 13\r\n\r\n" | command nc -w 2 127.0.0.1 8088 2>/dev/null | head -5)
assert_contains "WS upgrade HTTP 101" "$ws_resp" "101"
assert_contains "WS upgrade has Accept" "$ws_resp" "Sec-WebSocket-Accept"

# 12.2 WS with bad version rejected or accepted gracefully
ws_bad=$(printf "GET /ws HTTP/1.1\r\nHost: 127.0.0.1:8088\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: ${ws_key}\r\nSec-WebSocket-Version: 8\r\n\r\n" | command nc -w 2 127.0.0.1 8088 2>/dev/null | head -3)
# Just verify it doesn't crash the server
post_ws=$(echo "STATUS" | nc -w 2 127.0.0.1 5000 2>/dev/null)
assert_contains "Server survives bad WS version" "$post_ws" "status:active"

echo ""
echo "=== TEST SUITE 13: HTTP API Auth & Proxy ==="
echo ""

# 13.1 POST /api/login with correct passphrase returns success
WEB_PASS=$(cat "$HOME/.ernosdecent/web-password" 2>/dev/null | tr -d '\r\n ')
login_correct=$(curl -s -X POST -H "Content-Type: application/json" -d "{\"passphrase\":\"${WEB_PASS}\"}" http://127.0.0.1:8088/api/login 2>/dev/null)
assert_contains "Login correct returns success:true" "$login_correct" '"success":true'
assert_contains "Login correct returns token" "$login_correct" '"token":'

# Extract token and session parameters for authentication
token=$(echo "$login_correct" | grep -o '"token":"[^"]*' | cut -d'"' -f4)
did=$(echo "$login_correct" | grep -o '"did":"[^"]*' | cut -d'"' -f4)
issued_at=$(echo "$login_correct" | grep -o '"issued_at":[0-9]*' | cut -d':' -f2)
expires_at=$(echo "$login_correct" | grep -o '"expires_at":[0-9]*' | cut -d':' -f2)
nonce=$(echo "$login_correct" | grep -o '"nonce":"[^"]*' | cut -d'"' -f4)

# 13.2 POST /api/login with incorrect passphrase returns 401
login_wrong=$(curl -s -w "%{http_code}" -o /dev/null -X POST -H "Content-Type: application/json" -d '{"passphrase":"wrong_password"}' http://127.0.0.1:8088/api/login 2>/dev/null)
if [ "$login_wrong" = "401" ]; then
    pass "Login wrong returns 401 Unauthorized"
else
    fail "Login wrong returns $login_wrong (expected 401)"
fi

# 13.3 GET /api/meili without headers returns 401
meili_no_auth=$(curl -s -w "%{http_code}" -o /dev/null http://127.0.0.1:8088/api/meili 2>/dev/null)
if [ "$meili_no_auth" = "401" ]; then
    pass "MeiliSearch without token returns 401 Unauthorized"
else
    fail "MeiliSearch without token returns $meili_no_auth (expected 401)"
fi

# 13.4 GET /api/meili with valid headers passes auth check
meili_auth=$(curl -s -w "%{http_code}" -o /dev/null \
  -H "X-Session-Token: ${token}" \
  -H "X-Session-Did: ${did}" \
  -H "X-Session-Issued: ${issued_at}" \
  -H "X-Session-Expires: ${expires_at}" \
  -H "X-Session-Nonce: ${nonce}" \
  http://127.0.0.1:8088/api/meili 2>/dev/null)
if [ "$meili_auth" != "401" ]; then
    pass "MeiliSearch with token passes auth check (status: $meili_auth)"
else
    fail "MeiliSearch with token rejected with 401 Unauthorized"
fi

# 13.5 GET /api/ollama without headers returns 401
ollama_no_auth=$(curl -s -w "%{http_code}" -o /dev/null http://127.0.0.1:8088/api/ollama 2>/dev/null)
if [ "$ollama_no_auth" = "401" ]; then
    pass "Ollama without token returns 401 Unauthorized"
else
    fail "Ollama without token returns $ollama_no_auth (expected 401)"
fi

# 13.6 GET /api/ollama with valid headers passes auth check
ollama_auth=$(curl -s -w "%{http_code}" -o /dev/null \
  -H "X-Session-Token: ${token}" \
  -H "X-Session-Did: ${did}" \
  -H "X-Session-Issued: ${issued_at}" \
  -H "X-Session-Expires: ${expires_at}" \
  -H "X-Session-Nonce: ${nonce}" \
  http://127.0.0.1:8088/api/ollama 2>/dev/null)
if [ "$ollama_auth" != "401" ]; then
    pass "Ollama with token passes auth check (status: $ollama_auth)"
else
    fail "Ollama with token rejected with 401 Unauthorized"
fi

echo "==========================================================="
echo "  RESULTS: $PASS/$TOTAL passed, $FAIL failed"
echo "==========================================================="
if [ $FAIL -gt 0 ]; then
    echo ""
    echo "[FAIL] Some tests failed. See output above."
    exit 1
else
    echo ""
    echo "[PASS] All live system E2E tests passed!"
    exit 0
fi
