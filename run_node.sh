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

# Keep the previous session's log so a crash + relaunch doesn't erase it.
[ -f "$LOG" ] && mv -f "$LOG" "$LOG.prev" 2>/dev/null

echo "[run_node] $(date '+%Y-%m-%d %H:%M:%S') starting node — logging to $LOG"
# Combine stdout+stderr and tee to the logfile (live in terminal AND persisted).
./node 2>&1 | tee "$LOG"
