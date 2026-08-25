#!/bin/bash
# Launch the ErnosDecent node with PERSISTENT logging.
#
# Running `./node` directly sends its stdout/stderr only to the terminal's scrollback,
# so when a transient failure happens (e.g. an intermittent "No LLM model responded")
# there is no saved [LLM DEBUG] trace to diagnose it after the fact. This wrapper tees
# the node's combined output to a logfile while still showing it live in the terminal.
#
# Usage: ./run_node.sh   (instead of ./node)
# Log:   ~/.ernosdecent/node.log   (previous session kept at node.log.prev)

cd "$(dirname "$0")" || exit 1
LOG="${HOME}/.ernosdecent/node.log"
mkdir -p "$(dirname "$LOG")"
LOCK_DIR="${HOME}/.ernosdecent/node-runtime.lock"
LOCK_PID="${LOCK_DIR}/pid"

# Atomic single-instance guard. The lock belongs to this wrapper, which owns the node
# pipeline for its whole lifetime. A stale lock is removed only after its recorded PID
# is proven absent; a live IPC listener is an independent second guard.
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  EXISTING_PID="$(sed -n '1p' "$LOCK_PID" 2>/dev/null)"
  if [ -n "$EXISTING_PID" ] && kill -0 "$EXISTING_PID" 2>/dev/null; then
    echo "[run_node] node wrapper already running as PID $EXISTING_PID — refusing duplicate." >&2
    exit 1
  fi
  rm -f "$LOCK_PID"
  if ! rmdir "$LOCK_DIR" 2>/dev/null || ! mkdir "$LOCK_DIR" 2>/dev/null; then
    echo "[run_node] could not safely recover stale runtime lock." >&2
    exit 1
  fi
fi
echo "$$" > "$LOCK_PID"
cleanup_runtime_lock() {
  rm -f "$LOCK_PID"
  rmdir "$LOCK_DIR" 2>/dev/null || true
}
trap cleanup_runtime_lock EXIT INT TERM

if lsof -nP -iTCP:5000 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "[run_node] IPC port 5000 already has a listener — refusing duplicate node." >&2
  exit 1
fi

# A factory rollback is executed only while the daemon is stopped. The hook validates
# the pinned bundle path, every payload hash, every destination allowlist entry, and
# the exact pre-state manifest before replacing agent state or node.db. Any mismatch
# aborts startup; the node must never boot into a partially restored false continuity.
if [ -f "config/rights/pending_factory_restore.txt" ]; then
  if ! ./scripts/rights_restore_pending.sh "$PWD"; then
    echo "[run_node] RIGHTS RESTORE FAILED — refusing to start the node." >&2
    exit 1
  fi
fi

# Keep shared-Ollama fallbacks resident, but never increase its parallel-slot count:
# recent Ollama versions multiply the model's KV arena by OLLAMA_NUM_PARALLEL.
launchctl setenv OLLAMA_KEEP_ALIVE -1 2>/dev/null || true
# DO NOT SET OLLAMA_NUM_PARALLEL. It was set to 4 here for parallelism; Ollama 0.30.x
# ignored it for memory sizing (five weeks, 1963 loads, zero evictions), but the 0.31.2
# update (2026-07-13 18:03) multiplies EVERY model's KV arena by it — gemma4:26b's
# predicted load went 29 GiB -> 174.6 GiB, exceeding free RAM, and the scheduler began
# evicting/reloading models on nearly every call (+25s per reply). Removed via
# launchctl unsetenv; never re-add without checking the sched log for 'evicting'.
launchctl unsetenv OLLAMA_NUM_PARALLEL 2>/dev/null || true

# The configured gemma4:26b artifact is natively multimodal in Ollama. Do not start
# a second 31B visual model or bind the obsolete visual sidecar.
LLS="/opt/homebrew/bin/llama-server"; [ -x "$LLS" ] || LLS="$(command -v llama-server)"

# The optional 31B text server is started only when it is actually the configured model.
# The current gemma4:26b default must never be redirected to these different weights.
DEFAULT_TEXT_MODEL=$(sed -n '1{s/[[:space:]]*$//;p;}' config/default_model.txt 2>/dev/null)
if [ "$DEFAULT_TEXT_MODEL" = "gemma-4-31b" ] && [ "${GEMMA4_MAIN_LLAMACPP:-1}" = "1" ]; then
  GEMMA4_MAIN_BLOB=$(ollama show gemma-4-31b --modelfile 2>/dev/null | awk '/^FROM/{print $2; exit}')
  if [ -n "$GEMMA4_MAIN_BLOB" ] && [ -f "$GEMMA4_MAIN_BLOB" ] && [ -x "$LLS" ]; then
    if ! curl -s -m 2 http://127.0.0.1:8080/health 2>/dev/null | grep -q '"status":"ok"'; then
      echo "[run_node] starting gemma-4-31b MAIN server on :8080 (llama.cpp, -np 4 PARALLEL, -b/-ub 2048, fa on)"
      "$LLS" --model "$GEMMA4_MAIN_BLOB" --host 127.0.0.1 --port 8080 \
        --alias gemma-4-31b -c 131072 -np 4 --slots -b 2048 -ub 2048 -ngl 999 -fa on \
        > "${HOME}/.ernosdecent/gemma4main.log" 2>&1 &
      echo "[run_node] (gemma :8080 loading in background; agent uses Ollama until it is ready)"
    fi
  else
    echo "[run_node] gemma-4-31b llama.cpp blob or llama-server not found — falling back to Ollama."
  fi
fi

# The 26B artifact requires Ollama's Gemma4 renderer/parser. Hold it in a dedicated,
# single-model Ollama process so unrelated local model requests cannot evict its runner.
# Two slots retain independent Main and Observer KV histories instead of making their
# alternating prompt shapes evict each other and re-prefill the entire context.
if ! curl -fsS -m 2 http://127.0.0.1:11435/api/version >/dev/null 2>&1; then
  if command -v ollama >/dev/null 2>&1 && ollama show gemma4:26b >/dev/null 2>&1; then
    echo "[run_node] starting dedicated gemma4:26b Ollama service on :11435"
    OLLAMA_HOST=127.0.0.1:11435 \
    OLLAMA_KEEP_ALIVE=-1 \
    OLLAMA_MAX_LOADED_MODELS=1 \
    OLLAMA_NUM_PARALLEL=2 \
    OLLAMA_MODELS="${HOME}/.ollama/models" \
      ollama serve > "${HOME}/.ernosdecent/ollama-26b-dedicated.log" 2>&1 &
  else
    echo "[run_node] gemma4:26b or ollama executable not found — shared Ollama remains the fallback."
  fi
fi

OLLAMA26_READY=0
for _attempt in $(seq 1 60); do
  if curl -fsS -m 2 http://127.0.0.1:11435/api/version >/dev/null 2>&1; then
    OLLAMA26_READY=1
    break
  fi
  sleep 1
done
if [ "$OLLAMA26_READY" = "1" ]; then
  if curl -fsS --max-time 300 http://127.0.0.1:11435/api/generate \
    -H 'Content-Type: application/json' \
    -d '{"model":"gemma4:26b","prompt":"","stream":false,"keep_alive":-1}' \
    > "${HOME}/.ernosdecent/ollama-26b-preload.json" && \
    grep -q '"done_reason":"load"' "${HOME}/.ernosdecent/ollama-26b-preload.json"; then
    echo "[run_node] dedicated gemma4:26b loaded and held resident on :11435"
  else
    echo "[run_node] dedicated gemma4:26b preload failed — shared Ollama remains the fallback."
  fi
else
  echo "[run_node] dedicated gemma4:26b service did not become ready — shared Ollama remains the fallback."
fi

# Keep the previous session's log so a crash + relaunch doesn't erase it.
[ -f "$LOG" ] && mv -f "$LOG" "$LOG.prev" 2>/dev/null

echo "[run_node] $(date '+%Y-%m-%d %H:%M:%S') starting node — logging to $LOG"
# Combine stdout+stderr and tee to the logfile (live in terminal AND persisted).
set -o pipefail
PRESERVE_DISCORD_BRIDGE=0
while true; do
  if [ "$PRESERVE_DISCORD_BRIDGE" -eq 1 ]; then
    ERNOS_PRESERVE_DISCORD_BRIDGE=1 ./node 2>&1 | tee -a "$LOG"
  else
    ./node 2>&1 | tee -a "$LOG"
  fi
  NODE_RC=${PIPESTATUS[0]}
  if [ "$NODE_RC" -ne 75 ]; then
    exit "$NODE_RC"
  fi
  echo "[run_node] authenticated restart requested; relaunching clean node."
  PRESERVE_DISCORD_BRIDGE=1
  sleep 1
done
