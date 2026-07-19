#!/bin/bash
# Launch the ErnosDecent node with PERSISTENT logging.
#
# Running `./node` directly sends its stdout/stderr only to the terminal's scrollback,
# so when a transient failure happens (e.g. an intermittent "No LLM model responded")
# there is no saved [LLM DEBUG] trace to diagnose it after the fact. This wrapper tees
# the node's combined output to a logfile while still showing it live in the terminal.
#
# Usage: ./run_node.sh [node options]   (instead of ./node)
# Log:   ~/.ernosdecent/node.log   (previous session kept at node.log.prev)

set -uo pipefail

cd "$(dirname "$0")" || exit 1
LOG="${HOME}/.ernosdecent/node.log"
if ! mkdir -p "$(dirname "$LOG")"; then
  echo "[run_node] failed to create runtime directory for $LOG" >&2
  exit 1
fi

# Pin the full default LLM resident so Ollama remains a warm fallback when llama.cpp is
# unavailable. A cold reload of gemma4's context takes ~15s, during which calls return
# "No LLM model responded" — the intermittent "agent not responding" Maria saw. Two parts:
#  1. Set the server default (applies to every future model load, survives reloads/crashes).
#     The GUI Ollama picks this up on its next start.
#  2. Pin the currently-loaded model NOW via Ollama's native load-only /api/generate
#     request. Supplying no prompt preloads without starting an unbounded generation;
#     the OpenAI /v1 endpoint the node uses ignores keep_alive.
if ! launchctl setenv OLLAMA_KEEP_ALIVE -1 2>/dev/null; then
  echo "[run_node] warning: could not set OLLAMA_KEEP_ALIVE through launchctl" >&2
fi
# DO NOT SET OLLAMA_NUM_PARALLEL. It was set to 4 here for parallelism; Ollama 0.30.x
# ignored it for memory sizing (five weeks, 1963 loads, zero evictions), but the 0.31.2
# update (2026-07-13 18:03) multiplies EVERY model's KV arena by it — gemma4:26b's
# predicted load went 29 GiB -> 174.6 GiB, exceeding free RAM, and the scheduler began
# evicting/reloading models on nearly every call (+25s per reply). Removed via
# launchctl unsetenv; never re-add without checking the sched log for 'evicting'.
if ! launchctl unsetenv OLLAMA_NUM_PARALLEL 2>/dev/null; then
  echo "[run_node] warning: could not clear OLLAMA_NUM_PARALLEL through launchctl" >&2
fi
(
  if ! curl -fsS --max-time 180 http://127.0.0.1:11434/api/generate \
    -d '{"model":"gemma-4-31b","keep_alive":-1,"stream":false}' \
    >/dev/null 2>"${HOME}/.ernosdecent/ollama-warmup.err"; then
    echo "[run_node] warning: Ollama warmup request failed; see ~/.ernosdecent/ollama-warmup.err" >&2
  fi
) &

# Vision: gemma-4-31b's Ollama tag ships WITHOUT its vision projector (Capabilities: completion
# only), so the agent couldn't SEE the images it generates. Serve the SAME gemma-4-31b weights
# WITH their mmproj here on :8091 so generate_image's describe step works — same model, its own
# projector, no extra model and no 18GB Ollama re-copy. query_vision routes to :8091.
GEMMA4_BLOB=$(ollama show gemma-4-31b --modelfile 2>"${HOME}/.ernosdecent/ollama-show-vision.err" | awk '/^FROM/{print $2; exit}')
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
# PARALLEL MAIN MODEL (default ON — Maria's M3 Ultra 512GB has ample headroom):
# serve gemma-4-31b via llama-server on :8080 with -np 4 PARALLEL SLOTS + continuous
# batching, so the main agent's reply, sub-agents, and background coordinators run
# CONCURRENTLY on one model instead of queueing serially (the real "async replies" fix —
# the EP loop was already non-blocking; the model server was the bottleneck). -c 131072
# across 4 slots = 32k tokens/slot, comfortably above the agent's ~15k prompts. The
# node's discovery cascade tries :8080 before Ollama, and falls back to Ollama :11434 if
# this server isn't up yet — so a slow load or OOM degrades to serial, never to broken.
# Opt out with GEMMA4_MAIN_LLAMACPP=0 ./run_node.sh (uses Ollama, serial unless
# OLLAMA_NUM_PARALLEL took effect).
if [ "${GEMMA4_MAIN_LLAMACPP:-1}" = "1" ]; then
  GEMMA4_MAIN_BLOB=$(ollama show gemma-4-31b --modelfile 2>"${HOME}/.ernosdecent/ollama-show-main.err" | awk '/^FROM/{print $2; exit}')
  if [ -n "$GEMMA4_MAIN_BLOB" ] && [ -f "$GEMMA4_MAIN_BLOB" ] && [ -x "$LLS" ]; then
    if ! curl -s -m 2 http://127.0.0.1:8080/health 2>/dev/null | grep -q '"status":"ok"'; then
      echo "[run_node] starting gemma-4-31b MAIN server on :8080 (llama.cpp, -np 4 PARALLEL, -b/-ub 2048, fa on)"
      "$LLS" --model "$GEMMA4_MAIN_BLOB" --host 127.0.0.1 --port 8080 \
        --alias gemma-4-31b -c 131072 -np 4 --slots -b 2048 -ub 2048 -ngl 999 -fa on \
        > "${HOME}/.ernosdecent/gemma4main.log" 2>&1 &
      echo "[run_node] (gemma :8080 loading in background; agent uses Ollama until it is ready)"
    fi
  else
    echo "[run_node] gemma-4-31b llama.cpp blob or llama-server not found — falling back to Ollama (set OLLAMA_NUM_PARALLEL for concurrency)."
  fi
fi

# Keep the previous session's log so a crash + relaunch doesn't erase it.
if [ -f "$LOG" ] && ! mv -f "$LOG" "$LOG.prev"; then
  echo "[run_node] failed to rotate $LOG" >&2
  exit 1
fi

echo "[run_node] $(date '+%Y-%m-%d %H:%M:%S') starting node — logging to $LOG"
# Combine stdout+stderr and tee to the logfile (live in terminal AND persisted).
./node "$@" 2>&1 | tee "$LOG"
