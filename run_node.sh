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

# Pin the LLM model resident so Ollama does not idle-unload it between messages. A cold
# reload of gemma4's 262144-token context takes ~15s, during which calls return
# "No LLM model responded" — the intermittent "agent not responding" Maria saw. Two parts:
#  1. Set the server default (applies to every future model load, survives reloads/crashes).
#     The GUI Ollama picks this up on its next start.
#  2. Pin the currently-loaded model NOW via the NATIVE /api/chat endpoint — the OpenAI
#     /v1 endpoint the node uses IGNORES keep_alive, so we pin it here directly.
launchctl setenv OLLAMA_KEEP_ALIVE -1 2>/dev/null || true
curl -s http://127.0.0.1:11434/api/chat \
  -d '{"model":"gemma4:26b","messages":[{"role":"user","content":"warmup"}],"keep_alive":-1,"stream":false}' \
  >/dev/null 2>&1 &

# Vision: gemma-4-31b's Ollama tag ships WITHOUT its vision projector (Capabilities: completion
# only), so the agent couldn't SEE the images it generates. Serve the SAME gemma-4-31b weights
# WITH their mmproj here on :8091 so generate_image's describe step works — same model, its own
# projector, no extra model and no 18GB Ollama re-copy. query_vision routes to :8091.
GEMMA4_BLOB=$(ollama show gemma-4-31b --modelfile 2>/dev/null | awk '/^FROM/{print $2; exit}')
GEMMA4_MMPROJ="${HOME}/.ernosdecent/lib/gemma4vision/mmproj-gemma4-31b-BF16.gguf"
LLS="/opt/homebrew/bin/llama-server"; [ -x "$LLS" ] || LLS="$(command -v llama-server)"
if [ -n "$GEMMA4_BLOB" ] && [ -f "$GEMMA4_BLOB" ] && [ -f "$GEMMA4_MMPROJ" ] && [ -x "$LLS" ]; then
  if ! curl -s -m 2 http://127.0.0.1:8091/health 2>/dev/null | grep -q '"status":"ok"'; then
    echo "[run_node] starting gemma-4-31b vision server on :8091 (mmproj)"
    "$LLS" --model "$GEMMA4_BLOB" --mmproj "$GEMMA4_MMPROJ" --host 127.0.0.1 --port 8091 \
      --alias gemma-4-31b-vision -c 8192 -ngl 999 -fa on \
      > "${HOME}/.ernosdecent/gemma4vision.log" 2>&1 &
  fi
fi

# OPT-IN (P5 latency proposal — adopt only after [LLM TTFT] confirms it wins): serve
# gemma-4-31b's MAIN inference via llama-server instead of Ollama — exact prefill/decode
# timings in every [LLM TTFT] line, faster prefill (-b/-ub 2048), and slot-cache control.
# Off by default; enable with: GEMMA4_MAIN_LLAMACPP=1 ./run_node.sh
# No node config change needed — the discovery cascade tries llama.cpp :8080 before Ollama.
if [ "${GEMMA4_MAIN_LLAMACPP:-0}" = "1" ]; then
  GEMMA4_MAIN_BLOB=$(ollama show gemma-4-31b --modelfile 2>/dev/null | awk '/^FROM/{print $2; exit}')
  if [ -n "$GEMMA4_MAIN_BLOB" ] && [ -f "$GEMMA4_MAIN_BLOB" ] && [ -x "$LLS" ]; then
    if ! curl -s -m 2 http://127.0.0.1:8080/health 2>/dev/null | grep -q '"status":"ok"'; then
      echo "[run_node] starting gemma-4-31b MAIN server on :8080 (llama.cpp, -b/-ub 2048, fa on)"
      "$LLS" --model "$GEMMA4_MAIN_BLOB" --host 127.0.0.1 --port 8080 \
        --alias gemma-4-31b -c 65536 -b 2048 -ub 2048 -ngl 999 -fa on -np 1 \
        > "${HOME}/.ernosdecent/gemma4main.log" 2>&1 &
    fi
  fi
fi

# Keep the previous session's log so a crash + relaunch doesn't erase it.
[ -f "$LOG" ] && mv -f "$LOG" "$LOG.prev" 2>/dev/null

echo "[run_node] $(date '+%Y-%m-%d %H:%M:%S') starting node — logging to $LOG"
# Combine stdout+stderr and tee to the logfile (live in terminal AND persisted).
./node 2>&1 | tee "$LOG"
