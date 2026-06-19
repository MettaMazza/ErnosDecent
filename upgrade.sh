#!/bin/bash
# ErnosDecent — Hot-Swap Upgrade Script
# Swaps the running node binary with the newly compiled one,
# monitors health, and auto-rolls back if it fails to start.

echo "[UPGRADE] Starting upgrade sequence..."
cp ./node ./node_rollback
cp ./node_next ./node

# Kill the old node daemon (running on port 5000)
OLD_PID=$(lsof -ti :5000 2>/dev/null)
if [ -n "$OLD_PID" ]; then
    echo "[UPGRADE] Killing old node process: $OLD_PID"
    kill -9 $OLD_PID 2>/dev/null
fi

# Wait for port 5000 to free
sleep 2

# Start the new node daemon in the background
echo "[UPGRADE] Launching new node daemon..."
nohup ./node > daemon.log 2>&1 &
NEW_PID=$!

# Watchdog health checks
HEALTHY=false
for i in $(seq 1 15); do
    sleep 1
    # Try sending STATUS command via netcat to port 5000
    res=$(echo "STATUS" | nc -w 1 127.0.0.1 5000 2>/dev/null)
    if echo "$res" | grep -q "status:active"; then
        HEALTHY=true
        echo "[UPGRADE] ✅ New daemon is active and healthy!"
        break
    fi
    echo "[UPGRADE] Waiting for health status... ($i/15)"
done

if [ "$HEALTHY" = false ]; then
    echo "[UPGRADE] ❌ New daemon failed health check. Rolling back..."
    kill -9 $NEW_PID 2>/dev/null
    cp ./node_rollback ./node
    nohup ./node > daemon.log 2>&1 &
    echo "[UPGRADE] 🔄 Rollback completed. Restored old node version."
    exit 1
fi

echo "[UPGRADE] Upgrade successful!"
exit 0
