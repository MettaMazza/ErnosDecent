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
CURRENT_NODE_PID=""
LEARNING_PROVIDER_PID=""
LEARNING_PROVIDER_ADAPTER_HASH=""

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
  if [ -n "$CURRENT_NODE_PID" ] && kill -0 "$CURRENT_NODE_PID" 2>/dev/null; then
    kill -TERM "$CURRENT_NODE_PID" 2>/dev/null || true
  fi
  if [ -n "$LEARNING_PROVIDER_PID" ] && kill -0 "$LEARNING_PROVIDER_PID" 2>/dev/null; then
    kill -TERM "$LEARNING_PROVIDER_PID" 2>/dev/null || true
  fi
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
# run_node.sh owns all process replacement. A staged self-upgrade is activated only
# after the old node exits 75, then committed only after authenticated replacement
# health and in-node rights-ledger reconciliation. Any failed gate restores the exact
# pre-upgrade executable before the old process is relaunched.
ipc_cmd() {
  local timeout_seconds="$1"
  local command="$2"
  local token
  token=$(tr -d '\r\n ' < "${HOME}/.ernosdecent/ipc-token" 2>/dev/null) || return 1
  [ -n "$token" ] || return 1
  printf 'AUTH %s %s\n' "$token" "$command" | nc -w "$timeout_seconds" 127.0.0.1 5000 2>/dev/null
}

runtime_hash_file() {
  local path="$1"
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$path" | awk '{print $1}'
  elif command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$path" | awk '{print $1}'
  else
    return 1
  fi
}

verify_operator_regression_gate() {
  local seal="${HOME}/.ernosdecent/mandatory-regressions.seal"
  local manifest="config/upgrades/mandatory-regressions.sha256"
  local expected actual
  [ -f "$seal" ] && [ ! -L "$seal" ] || return 1
  [ -f "$manifest" ] && [ ! -L "$manifest" ] || return 1
  expected=$(tr -d '\r\n ' < "$seal") || return 1
  actual=$(runtime_hash_file "$manifest") || return 1
  [ ${#expected} -eq 64 ] && [ "$actual" = "$expected" ] || return 1
  bash scripts/run_mandatory_regressions.sh --verify-only
}

launch_node_process() {
  if [ "$PRESERVE_DISCORD_BRIDGE" -eq 1 ]; then
    ERNOS_PRESERVE_DISCORD_BRIDGE=1 ./node > >(tee -a "$LOG") 2>&1 &
  else
    ./node > >(tee -a "$LOG") 2>&1 &
  fi
  CURRENT_NODE_PID=$!
}

wait_for_node_health() {
  local attempt response
  for attempt in $(seq 1 60); do
    if ! kill -0 "$CURRENT_NODE_PID" 2>/dev/null; then
      return 1
    fi
    response=$(ipc_cmd 1 "STATUS" || true)
    if echo "$response" | grep -q "status:active"; then
      return 0
    fi
    sleep 1
  done
  return 1
}

stop_current_node() {
  local attempt
  if [ -z "$CURRENT_NODE_PID" ] || ! kill -0 "$CURRENT_NODE_PID" 2>/dev/null; then
    wait "$CURRENT_NODE_PID" 2>/dev/null || true
    CURRENT_NODE_PID=""
    return 0
  fi
  kill -TERM "$CURRENT_NODE_PID" 2>/dev/null || true
  for attempt in $(seq 1 25); do
    if ! kill -0 "$CURRENT_NODE_PID" 2>/dev/null; then
      wait "$CURRENT_NODE_PID" 2>/dev/null || true
      CURRENT_NODE_PID=""
      return 0
    fi
    sleep 0.2
  done
  kill -KILL "$CURRENT_NODE_PID" 2>/dev/null || true
  wait "$CURRENT_NODE_PID" 2>/dev/null || true
  CURRENT_NODE_PID=""
}

stop_learning_provider() {
  local attempt
  if [ -z "$LEARNING_PROVIDER_PID" ] || ! kill -0 "$LEARNING_PROVIDER_PID" 2>/dev/null; then
    LEARNING_PROVIDER_PID=""
    LEARNING_PROVIDER_ADAPTER_HASH=""
    return 0
  fi
  kill -TERM "$LEARNING_PROVIDER_PID" 2>/dev/null || true
  for attempt in $(seq 1 50); do
    if ! kill -0 "$LEARNING_PROVIDER_PID" 2>/dev/null; then
      wait "$LEARNING_PROVIDER_PID" 2>/dev/null || true
      LEARNING_PROVIDER_PID=""
      LEARNING_PROVIDER_ADAPTER_HASH=""
      return 0
    fi
    sleep 0.2
  done
  kill -KILL "$LEARNING_PROVIDER_PID" 2>/dev/null || true
  wait "$LEARNING_PROVIDER_PID" 2>/dev/null || true
  LEARNING_PROVIDER_PID=""
  LEARNING_PROVIDER_ADAPTER_HASH=""
}

learning_runtime_spec() {
  python3 scripts/live_learning.py runtime-spec 2>/dev/null
}

start_learning_provider() {
  local spec status model adapter adapter_load adapter_hash port runtime_python
  if [ ! -f "config/learning/live/runtime_active.json" ]; then
    stop_learning_provider
    return 0
  fi
  spec=$(learning_runtime_spec) || return 1
  status=$(printf '%s' "$spec" | jq -r '.status // empty') || return 1
  model=$(printf '%s' "$spec" | jq -r '.model_path // empty') || return 1
  adapter=$(printf '%s' "$spec" | jq -r '.adapter_path // empty') || return 1
  adapter_load=$(printf '%s' "$spec" | jq -r '.adapter_load_path // empty') || return 1
  adapter_hash=$(printf '%s' "$spec" | jq -r '.adapter_hash // empty') || return 1
  port=$(printf '%s' "$spec" | jq -r '.provider_port // empty') || return 1
  runtime_python="${HOME}/.ernosdecent/live-learning/runtime/bin/python"
  [ "$status" = "active" ] || [ "$status" = "candidate" ] || return 1
  [ -x "$runtime_python" ] && [ -d "$model" ] && [ -f "$adapter" ] && [ -d "$adapter_load" ] || return 1
  if [ -n "$LEARNING_PROVIDER_PID" ] && kill -0 "$LEARNING_PROVIDER_PID" 2>/dev/null && [ "$LEARNING_PROVIDER_ADAPTER_HASH" = "$adapter_hash" ]; then
    return 0
  fi
  stop_learning_provider
  if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "[run_node] learned-model port :$port is occupied by an unowned process; refusing ambiguous activation." >&2
    return 1
  fi
  echo "[run_node] loading cumulative Gemma 4 adapter ${adapter_hash:0:12} on :$port"
  "$runtime_python" -m mlx_vlm.server \
    --host 127.0.0.1 --port "$port" --model "$model" --adapter-path "$adapter_load" \
    --max-kv-size 262144 --max-tokens 8192 \
    > "${HOME}/.ernosdecent/mlx-vlm-learned.log" 2>&1 &
  LEARNING_PROVIDER_PID=$!
  LEARNING_PROVIDER_ADAPTER_HASH="$adapter_hash"
  # Startup has no artificial transaction deadline: a large local model may take
  # as long as the host requires. Process exit is a definitive failure; successful
  # HTTP inference is the definitive readiness condition.
  while kill -0 "$LEARNING_PROVIDER_PID" 2>/dev/null; do
    if curl -fsS -m 2 "http://127.0.0.1:${port}/docs" >/dev/null 2>&1; then
      if "$runtime_python" scripts/live_learning_probe.py \
        --model "$model" --adapter "$adapter" --port "$port" --existing-server \
        --output "config/learning/live/runtime-probe.json" \
        --server-log "${HOME}/.ernosdecent/mlx-vlm-learned.log" \
        > "${HOME}/.ernosdecent/mlx-vlm-runtime-probe.log" 2>&1; then
        echo "[run_node] cumulative learned-model provider passed live text and native-image inference readiness."
        return 0
      fi
    fi
    sleep 1
  done
  wait "$LEARNING_PROVIDER_PID" 2>/dev/null || true
  LEARNING_PROVIDER_PID=""
  LEARNING_PROVIDER_ADAPTER_HASH=""
  return 1
}

upgrade_outcome_status() {
  sed -n 's/^status=//p' config/upgrades/outcome.env 2>/dev/null | head -n 1
}

PRESERVE_DISCORD_BRIDGE=0
while true; do
  LEARNING_PENDING=0
  if [ -f "config/learning/live/pending_activation.json" ]; then
    LEARNING_PENDING=1
    if ! python3 scripts/live_learning.py prepare-runtime >/dev/null; then
      echo "[run_node] pending learned adapter failed receipt verification; refusing activation." >&2
      exit 1
    fi
  fi
  if ! start_learning_provider; then
    if [ "$LEARNING_PENDING" -eq 1 ]; then
      echo "[run_node] candidate learned adapter failed live provider validation; restoring prior accepted runtime." >&2
      python3 scripts/live_learning.py write-outcome --status failed --reason learned_provider_live_validation_failed >/dev/null || exit 1
      python3 scripts/live_learning.py abort-pending --reason learned_provider_live_validation_failed >/dev/null || exit 1
      start_learning_provider || exit 1
    else
      echo "[run_node] accepted learned-model provider failed to start; refusing silent model substitution." >&2
      exit 1
    fi
  fi
  UPGRADE_PENDING=0
  if [ -f "config/upgrades/pending.env" ]; then
    UPGRADE_PENDING=1
    if ! verify_operator_regression_gate; then
      echo "[run_node] staged upgrade trust root changed after validation; keeping the previous executable live and leaving the transaction for inspection." >&2
      UPGRADE_PENDING=0
    elif [ ! -f "config/upgrades/outcome.env" ]; then
      if ! bash upgrade.sh activate; then
        echo "[run_node] staged upgrade activation failed before launch; refusing an unverified runtime." >&2
        exit 1
      fi
    fi
  fi

  launch_node_process

  if [ "$LEARNING_PENDING" -eq 1 ]; then
    if ! wait_for_node_health; then
      stop_current_node
      stop_learning_provider
      python3 scripts/live_learning.py write-outcome --status failed --reason candidate_node_failed_authenticated_health >/dev/null || exit 1
      python3 scripts/live_learning.py abort-pending --reason candidate_node_failed_authenticated_health >/dev/null || exit 1
      start_learning_provider || exit 1
      PRESERVE_DISCORD_BRIDGE=1
      launch_node_process
      wait_for_node_health || exit 1
      RECONCILE_RESPONSE=$(ipc_cmd 5 "AI LEARNING RECONCILE" || true)
      if ! echo "$RECONCILE_RESPONSE" | grep -q '^learning:rolled_back,'; then
        echo "[run_node] learned-adapter failure could not be reconciled: ${RECONCILE_RESPONSE:-no response}" >&2
        stop_current_node
        exit 1
      fi
      rm -f "config/learning/live/activation_outcome.json"
      LEARNING_PENDING=0
    else
      python3 scripts/live_learning.py write-outcome --status applied --reason exact_candidate_provider_and_node_health_passed >/dev/null || exit 1
      RECONCILE_RESPONSE=$(ipc_cmd 5 "AI LEARNING RECONCILE" || true)
      if ! echo "$RECONCILE_RESPONSE" | grep -q '^learning:committed,'; then
        echo "[run_node] learned-adapter rights reconciliation failed: ${RECONCILE_RESPONSE:-no response}" >&2
        stop_current_node
        exit 1
      fi
      python3 scripts/live_learning.py commit-pending >/dev/null || {
        echo "[run_node] learned-adapter lineage commit failed after rights reconciliation; transaction retained for exact recovery." >&2
        stop_current_node
        exit 1
      }
      rm -f "config/learning/live/activation_outcome.json"
      echo "[run_node] cumulative learned adapter activation committed."
      LEARNING_PENDING=0
    fi
  fi

  if [ "$UPGRADE_PENDING" -eq 1 ]; then
    if ! wait_for_node_health; then
      OUTCOME_STATUS=$(upgrade_outcome_status)
      stop_current_node
      if [ "$OUTCOME_STATUS" = "failed" ]; then
        echo "[run_node] rollback executable failed authenticated health; transaction remains for inspection." >&2
        exit 1
      fi
      echo "[run_node] candidate failed authenticated health; restoring exact pre-upgrade executable." >&2
      if ! python3 scripts/improvement_test_gate.py record-failure --detail replacement_failed_authenticated_health; then
        echo "[run_node] could not persist the active improvement health failure; rollback still takes priority." >&2
      fi
      if ! bash upgrade.sh rollback || ! bash upgrade.sh failure replacement_failed_authenticated_health; then
        echo "[run_node] automatic executable rollback failed; refusing further launch." >&2
        exit 1
      fi
      PRESERVE_DISCORD_BRIDGE=1
      continue
    fi

    # Generic health is necessary but not sufficient for a self-authored feature.
    # Run every frozen live E2E test against the replacement before recording success.
    # The test bytes were frozen before implementation and execute read-only with
    # localhost-only networking, so the implementation cannot rewrite its evaluator.
    OUTCOME_STATUS=$(upgrade_outcome_status)
    if [ "$OUTCOME_STATUS" != "failed" ]; then
      if ! python3 scripts/improvement_test_gate.py live; then
        echo "[run_node] candidate failed a frozen live E2E contract; restoring exact pre-upgrade executable." >&2
        stop_current_node
        if ! python3 scripts/improvement_test_gate.py record-failure --detail frozen_improvement_live_e2e_failed; then
          echo "[run_node] could not persist a complete frozen live-E2E failure receipt; rollback still takes priority." >&2
        fi
        if ! bash upgrade.sh rollback || ! bash upgrade.sh failure frozen_improvement_live_e2e_failed; then
          echo "[run_node] rollback after frozen live E2E failure failed." >&2
          exit 1
        fi
        PRESERVE_DISCORD_BRIDGE=1
        continue
      fi
    fi

    if [ ! -f "config/upgrades/outcome.env" ]; then
      if ! bash upgrade.sh success; then
        echo "[run_node] healthy candidate could not produce an outcome receipt; rolling back." >&2
        stop_current_node
        if ! python3 scripts/improvement_test_gate.py record-failure --detail outcome_receipt_failed; then
          echo "[run_node] could not persist the active improvement outcome-receipt failure; rollback still takes priority." >&2
        fi
        if ! bash upgrade.sh rollback || ! bash upgrade.sh failure outcome_receipt_failed; then
          echo "[run_node] rollback after outcome failure failed; refusing further launch." >&2
          exit 1
        fi
        PRESERVE_DISCORD_BRIDGE=1
        continue
      fi
    fi

    RECONCILE_RESPONSE=$(ipc_cmd 5 "UPGRADE RECONCILE" || true)
    if echo "$RECONCILE_RESPONSE" | grep -qE '^upgrade:(committed|rolled_back),'; then
      echo "[run_node] $RECONCILE_RESPONSE"
      if echo "$RECONCILE_RESPONSE" | grep -q '^upgrade:committed,' && [ -f "config/improvements/active.json" ]; then
        if ! python3 scripts/improvement_test_gate.py complete; then
          echo "[run_node] upgrade committed but its frozen improvement receipt could not be finalized." >&2
          stop_current_node
          exit 1
        fi
      fi
      if ! bash upgrade.sh cleanup; then
        echo "[run_node] upgrade committed but transaction cleanup failed; refusing ambiguous continuation." >&2
        stop_current_node
        exit 1
      fi
      UPGRADE_PENDING=0
    else
      OUTCOME_STATUS=$(upgrade_outcome_status)
      echo "[run_node] rights reconciliation failed: ${RECONCILE_RESPONSE:-no response}" >&2
      stop_current_node
      if [ "$OUTCOME_STATUS" = "applied" ]; then
        if ! python3 scripts/improvement_test_gate.py record-failure --detail rights_reconciliation_failed; then
          echo "[run_node] could not persist the active improvement reconciliation failure; rollback still takes priority." >&2
        fi
        if ! bash upgrade.sh rollback || ! bash upgrade.sh failure rights_reconciliation_failed; then
          echo "[run_node] rollback after rights reconciliation failure failed." >&2
          exit 1
        fi
        PRESERVE_DISCORD_BRIDGE=1
        continue
      fi
      echo "[run_node] rolled-back executable could not reconcile its failure receipt; transaction remains for inspection." >&2
      exit 1
    fi
  fi

  wait "$CURRENT_NODE_PID"
  NODE_RC=$?
  CURRENT_NODE_PID=""
  if [ "$NODE_RC" -ne 75 ]; then
    exit "$NODE_RC"
  fi
  echo "[run_node] authenticated restart requested; supervisor is evaluating pending state."
  PRESERVE_DISCORD_BRIDGE=1
done
