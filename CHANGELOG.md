# Changelog

All notable changes to ErnosDecent. Dates are absolute. The engine ships on
`agent-parity` and is merged to `main` and the public `business` overlay.

## 2026-07-19 — AGENT.md adherence and release-gate repair

### Fixed

- Moved the Eleven Laws from `docs/AGENT.md` to the repository-root `AGENT.md` and corrected document links.
- Made persistence, transport, WebSocket, DHT, identity, money, inference, TTS, media, protocol-server, and node failure paths explicit; added rollback and native-resource cleanup where operations can partially succeed.
- Replaced cumulative bandwidth throttling with mutex-protected configured-rate windows and rejected caller-supplied tier escalation.
- Made compute job state concurrency-safe and completed the TCP worker lifecycle: assignment, same-connection result submission, manager validation, acknowledgement, and concurrent connection handling.
- Removed unused simulated DTLS key derivation; hardened real OpenSSL DTLS-SRTP, libsrtp2, Opus, and VP8 paths against malformed input, allocation failure, ABI error-width mismatches, and leaks.
- Replaced the compiler-emitted, process-global `gethostbyname()` result with checked `getaddrinfo()` resolution in every generated node and test build; this removes the concurrent resolver corruption proven by UBSan in the stress suite.
- Routed the cognitive-agent suite through its production-equivalent image, session, blocking, SQLite, and additive-runtime build path so generic test compilation cannot leave declared symbols unresolved.
- Removed the stale literal bootstrap seed, rejected and purged wildcard cached endpoints, required a real DHT `PONG`, separated connect/send/receive/response errors, and advertised only a configured or detected dialable node address.
- Made the operated-root role persistent and explicit: static hosts skip their own operated default aliases, launcher options reach the native node, and `network.public_host` now round-trips through generated TOML, load/save, and dashboard configuration. Documented the verified port contract and the DNS/reachability gate for adding a shipped default seed.
- Marked automatic public bootstrap as pre-launch: TCP `9100`/`9101` were externally reachable on 19 July 2026, while stable DDNS and public forwarding for `9102`–`9104` were explicitly deferred. Fresh nodes continue to require an explicit or cached seed.
- Generate and secure the per-installation Web UI password before the listener starts, so first-run operators can read the documented file without submitting an unknowable initial value; empty or insecure password files now fail closed.
- Updated live E2E, multi-node, stress, and upgrade harnesses for authenticated IPC/API access and Web port `8088`; they now stop only processes they launched or use authenticated graceful shutdown instead of killing arbitrary port owners. Multi-node and stress runs use disposable home directories so tests do not alter the operator's wallet, identity, names, DHT, or sessions.
- Added `scripts/release_check.sh` as the reproducible full local release-validation entrypoint.
- Corrected emitted SHA-256/MD5 byte assembly to cast bytes to unsigned integers before left shifts, removing a sanitizer-confirmed signed-shift undefined behavior in compiler-generated runtimes.
- Updated the live E2E AI assertion to the implemented detached-inference contract (`ai:accepted` with session/turn correlation plus explicit cancellation), instead of demanding the obsolete inline `RESPONSE` format.
- Restored the full `gemma-4-31b` default and its matching parallel llama.cpp `:8080` fast path. The temporary `gemma4:26b` override had forced default turns through Ollama first; the Observer remains unchanged and follows the same backend order as the main call for cache reuse.
- Pinned each active agent session's main and Observer calls to one live-discovered llama.cpp slot. This prevents automatic slot selection by unrelated node sessions from evicting their shared prompt-prefix KV cache; no Observer prompt, rule, verdict, or token bound was reduced.
- Replaced the launcher's text-generating Ollama warmup with a timeout-bounded load-only preload. The former background `"warmup"` completion could generate for minutes and contend with the primary llama.cpp server after node startup.
- Moved scheduler state from the shared repository config path into the active node data directory, made commits atomic, and mutex-protected complete read-modify-write transactions. Test storage is now isolated from the running host, eliminating lost schedule updates during concurrent verification.
- Made generated binary-safe network-send patching structural and idempotent across old and new Ernos compiler output, preventing duplicate runtime symbols when parameter names or compiler-provided helpers differ.
- Repaired compiler-emitted main and spawned-thread GC stack boundaries using the real pthread stack range on macOS and Linux, and corrected the IMA-ADPCM table's global ownership. Linux AddressSanitizer reproduced the out-of-range conservative stack scans and freed-table read, then completed the media and stress suites cleanly after the fixes.
- Pinned CI to a reproducible Ernos compiler source revision with its adjacent standard library, and declared libsrtp2 on both runners so real DTLS-SRTP tests exercise the required native dependency.
- Made the Raft TCP failover test use staggered follower timeouts and bounded condition polling, removing a same-timeout split-vote race that appeared only under slower hosted-runner scheduling.
- Made the Raft load test wait for all TCP listeners, use bounded election polling, require exactly one leader, and direct proposals to whichever node actually won instead of hard-coding node1 after a fixed sleep.
- Made platform detection validate macOS, Linux, and Windows consistently and routed both CI jobs through the checked test wrapper; Linux is no longer incorrectly treated as a macOS detection warning/failure.

### Verified

- Checked all 221 native-target Ernos sources, emitted the 4,764-line browser JavaScript artifact, rebuilt the signed macOS node, compiled and ran the 34-target final-tree executable matrix, and executed the runtime, malformed-input, sanitizer, concurrency, and authenticated live-node gates recorded in `docs/IMPLEMENTATION_PLAN.md`.

## 2026-07-08 (evening) — Eleven root fixes & features from live diagnostics

### Fixed (every root cause proven from logs/probes before the fix)
- **"No LLM model responded" (final cause)**: Ollama returns thinking models' output in
  TWO channels (`message.content` + `message.reasoning`); turns landing entirely in
  reasoning looked empty. Both channels are now read; all-reasoning turns are salvaged;
  native reasoning feeds the transparency view; double-empty logs the raw body head.
- **Discord tools returned "queued" / late reactions**: bridge commands rode IPC, which
  the agent turn holds — structurally impossible mid-turn. The bridge now polls
  `bridge_commands` directly from SQLite (500ms, like traces) and writes results back;
  waits are async-yielding (new injected `ep_async_sleep_ms`); `react` is claim-honest
  (`discord:reacted` only on confirmation).
- **Echo's name overridden ("Where did echo go?")**: the kernel and the system-role
  message both hardcoded "ErnOS", out-voting the persona. The NAME now derives from the
  active persona (single source of truth) and flows into the system identity; the
  Ernos name-origin story (ancient Greek "young shoot / olive sprout") was added to
  Echo's identity.
- **Batch slicer silently dropped `tool([...])` continuations** lacking `Action:`
  markers (the scheduler "no observation" failure) — orphaned calls are now detected
  against the registered schema and named in a format nudge.
- **Decode latency**: gemma-4-31b num_ctx right-sized 131072 → 65536 (memory-bound
  attention over the huge KV allocation measured ~18 tok/s); kernel gained a LATENCY
  compactness rule; opt-in `GEMMA4_MAIN_LLAMACPP=1` llama-server block in run_node.sh.
- **Silent "Image generation failed"**: `[ImageGen]` stage logging, pre-flight of ALL
  four Flux files (naming the missing one — external-drive hint), distinct shim return
  codes surfaced verbatim, ctx cache hit/miss logged.

### Added
- **Persistent per-session auto-approve**: `AI AUTOAPPROVE ON|OFF`, 🔓 button on the
  Discord approval card, `/autoapprove`, WebUI toggle + `/api/autoapprove`. Default
  OFF, resets on restart, observer audits unchanged.
- **Platform awareness**: `[PLATFORM:discord|webui]` tag → `agent_ctx` → an awareness
  line stating which surface tools apply this turn.
- **Session rename + name-addressable sessions**: `session_rename` tool, `/rename`,
  and title lookup (exact → unique substring) in `read_transcripts` and `SESSION SET`.
- **Persona registry + swapping**: `config/personas/<name>.txt` (echo auto-migrates),
  data-dir active pointer, `persona_set`/`persona_register` tools (observer-audited),
  `AI PERSONA`, Discord `/persona`, `/api/persona`.
- **`test_all_systems`**: runs the full 13-block master_prompt validation via
  sequential sub-agents, mid_message progress, per-block scorecards written to a
  workspace report and attached; approval blocks only under the session auto-approve
  grant; Discord block auto-skips off-platform.

## 2026-07-08 — Multi-tool batching, image generation + vision, self-prompt persistence, full transparency

### Added — the agent generates and SEES images (all ErnosPlain, all local)
- **Local image generation** (`generate_image`): `decent_agent/image_gen.ep` drives
  libstable-diffusion (sd.cpp, Metal) through the ErnosPlain C FFI via a flat shim
  (`decent_agent/vendor/sd/sd_ep_shim.cpp`, compiled into the node by `build.sh`).
  Default model is **FLUX.1-dev** loaded in 4-input mode directly from the operator's
  existing files (gguf transformer + diffusers-format CLIP/VAE single-files + gguf T5) —
  no re-download, no Python sidecar. Flux is guidance-distilled so CFG is forced to 1;
  output is 1024×1024 at 28 steps. Config: `config/image.json` (single-file SD/SDXL mode
  also supported). Verified end-to-end: real images rendered on-box.
- **Vision loop**: after generating, the agent LOOKS at its own image (`query_vision` in
  `decent_agent/llm.ep`, multimodal OpenAI content-array) and returns a genuine
  description. Ollama's gemma-4-31b tag ships without its vision projector, so
  `run_node.sh` serves the SAME weights WITH their mmproj via llama-server on **:8091**
  — no extra model. The image is attached to the final reply, not dumped mid-run.
- **`react([emoji])`**: the agent reacts to the message it is currently answering —
  message/channel ids are threaded through the bridge (`[MSGID]`/`[CHANID]` tags), the
  agent never has to know them.
- **Attachments ride the reply**: `attach_file` + generated images are collected by the
  Discord bridge and attached to the reply message itself (both reply sites), with
  claim-honesty — the agent only says "attached" when the emit actually queued.
- **WebUI ↔ Discord 1-1 parity (W4)**: attachments and `mid_message` progress updates
  render in the web chat exactly as they do on Discord.

### Added — prompt & self-model
- **Self-prompt persistence (W1)**: `[[BEHAVIOR]]`/`[[SKILLS]]` self-sections now live in
  the data dir (`storage_self_sections_path()`), immune to git operations in the repo;
  the tracked `config/agent_self_sections.json` is the template fallback. The
  self-prompt-edit approval gate is removed (observer audit retained) — the agent owns
  its own prompt.
- **Session guidance (W1)**: a second, session-scoped self-prompt
  (`session_prompt_get`/`set`) serialized with the session — global identity vs
  per-session working style are now separate layers.
- **`[CAPABILITIES]` prompt block (W2)**: the system prompt now frames the entire tool
  surface and system so the agent stops under-reaching ("I can't do that" for things it
  demonstrably can).
- **Full transparency**: untruncated action/command/tool results are piped into the
  thinking stream (trace) — `trace_emit` and the loop no longer clip content at 1800
  chars; observation size is governed only by the model-context budget.

### Added — performance
- **Multi-tool batching (one LLM call, N tools)**: the model may emit many `Action:`
  lines in a single response; the loop peels them off and executes each through the full
  approval/audit/observation path with NO inference call between them. A 20-tool
  independent diagnostic collapses from ~20 model round-trips (20–80 s each) to ~1.
  Batched steps don't consume the LLM-turn cap. Kernel prompt teaches the batching rule
  (`config/prompts.json` + fallback).
- **Default model: gemma-4-31b** (standard attention = KV-cache reuse across turns;
  the recurrent-MoE and gpt-oss experiments were reverted). Observer audits and the
  look-back route to the same backend and share the main prompt prefix so the KV cache
  is never evicted between the main call and the audit.
- **Look-back scoped to mid_message turns**: reply text is already covered by the reply
  audit and pure tool turns have no user-facing text — the per-step look-back cost
  ~11–31 s per turn for zero added coverage. Root-fixed the look-back itself too: it
  now uses the JSON-forcing LLM path and an explicit parsed-vs-default flag, so only a
  genuine parseable BLOCKED flags drift (it had been failing 100% and poisoning turns).

### Fixed
- **Workspace links no longer bleed across sessions**: the `@active` project marker is
  global on disk; `session_manager_new_session` now clears it, so a new session starts
  with no active project (registered links remain available).
- **Dead test harness fixed at root**: `build.sh` gained one shared
  `inject_additive_helpers()` used by BOTH the node and test builds — the two injector
  paths can no longer drift (this was the root cause, not "pre-existing/unrelated").
  13/13 cognitive agent tests pass.
- **"No LLM model responded" (both causes)**: (1) our own `\nThought:` stop sequence was
  clobbering gemma4's content channel to empty — removed (proven 2/15 → 0/15 failures);
  (2) Ollama idle-unload caused ~15 s cold reloads — the model is pinned resident
  (`OLLAMA_KEEP_ALIVE=-1` + native-endpoint warmup in `run_node.sh`).
- **Retrieved transcripts prompt-injecting the agent** (`read_transcripts` content is
  fenced as data), **auto-attach claim honesty**, **subjecthood prompt neutrality**
  (no injected uncertainty AND no prescription — free honest report).

### Docs
- `master_prompt.md`: a full-system diagnostic exercising every tool over ReAct, split
  into 13 paste-one-at-a-time prompts, each with its own pass/fail scorecard.

## 2026-07-05 — Agent tooling overhaul & IPC routing

### Added
- **Tooling overhaul** (`179c456`): read pagination (`codebase_read_range`, `file_info`
  on any path, `run_command` result annotation, RAG offsets), a **project-linking
  subsystem** (`decent_agent/workspace_links.ep` + `config/linked_projects.txt`:
  register/list/activate external project dirs; bare relative paths resolve against the
  active project), `list_sessions`, `search_sessions` (keyword-grep across all prior
  session transcripts instead of guessing ids), un-gated synaptic-graph cognition tools,
  and a `run_command` working-dir.
- The agent tool surface now stands at **71 registered tools**.

### Fixed
- **IPC command routing prefix-match** (`b9eafe8`): the node dispatcher matched command
  verbs as substrings — a chat message merely CONTAINING "RAG search"/"SESSION DELETE"
  could hijack routing into the wrong handler. Verbs now match as prefixes.
- **LLM read bounded by an async timeout** — a dead/hung inference server can no longer
  hang the daemon; **O(n) JSON escape** (the stdlib-colliding O(n²) escape corrupted
  control bytes and prompts); scheduler heap race; two local RCE/path-traversal gaps;
  ledger broadcast heap race; web status polls no longer pile up during a turn;
  **Stop button** made instant and turns finite.

## 2026-06-30 → 07-01 — Context & access system, education, GC/SQLite stability

### Added
- **Situational awareness + decision policy** (`decent_agent/awareness.ep`): a
  situational block and tool-routing map in the prompt (codebase_read FIRST), plus an
  act-vs-ask / inline-vs-delegate / stop decision policy — ends the "I can't see that
  file" flailing.
- **Tiered Full-PC access** (`decent_agent/access.ep`): operator-controlled access
  toggle (default ON) with an unsafe-action gate — sensitive paths warn/re-ask,
  secrets are hard-blocked.
- **Decentralised education phases 0–2**: Socratic tutor mode (scaffolds, never
  answer-vends — live-tested), a **Learning** web tab, and a `run_ep` sandboxed
  ErnosPlain playground. Fixed the playground Run hang, a numeric-arg segfault in
  `react`, and tutor-mode bleed between requests (per-request mode).

### Fixed
- **GC blocking barrier + SQLite global mutex** restored/formalized: `sqlite3_exec`
  runs inside the GC blocking region (fixes a SQLite use-after-free crash);
  `ep_run_command` wrapped; rate limiters made GC-rooted globals (startup segfault);
  sub-agent thread concurrency crashes resolved.
- Observer boolean/number audit verdicts segfaulted the daemon; `config_load` TOML
  parse on the JSON access file hung every turn.

## 2026-06-27 → 06-29 — Orchestrator, sessions, Discord control surface

### Added
- **Agent orchestrator + swarm** (`decent_agent/orchestrator.ep`): sub-agents as
  cooperative tasks with `delegate_task/wait/check/cancel/list/swarm` (fan-out with
  concat/best/vote merge), admin-gated.
- **Per-session workspaces**, live Discord trace threads, an interactive Discord
  **Stop** button attached to the thinking message, SQLite-backed trace polling, and
  active-session persistence across restarts.
- Recursive workspace navigation with metadata (`filename (N lines, M bytes)`) — ends
  file-listing blindness.

### Fixed
- Observer audit contamination + hardcoded heuristics removed; observer KV cache
  aligned 1-1 with the agent prompt prefix; resume-approved observer-audit bypass;
  range-reading tools; task GC protection; use-after-free in
  `broadcast_block_to_peers`; Discord bridge delivery hardened against daemon reboots.

## 2026-06-26 — Reliability, agent capabilities, and cognitive frameworks

### Fixed
- **Garbage-collector hang (critical).** The ErnosPlain runtime GC object table hashed
  pointers as `ptr % cap` with a power-of-two capacity; 16-byte-aligned `malloc`
  pointers collapsed onto every 16th bucket, so `ep_gc_table_remove`'s rehash went
  O(n²). Under the single global GC mutex this pinned one core indefinitely and froze
  the whole node (observed: 99% CPU for 84 minutes). Fixed with a splitmix64 hash mix
  and a no-resize rehash path; alloc+free churn is now linear. (Compiler:
  `Ernos-Programming-Language`.)
- **RAG search re-parse.** `rag_search` re-parsed every chunk's embedding text into a
  vector on every query (~1M short-lived allocations/query). Embeddings are immutable
  by id, so they are now parsed once and cached (thread-safe).
- Earlier in the cycle: O(n²) `memory_json_escape` serialize hang, invalid-JSON memory
  corruption (unescaped control bytes), a 75 s blocking DHT bootstrap, concurrent
  log-path corruption, and JSON `\uXXXX` decoding.

### Added — agent capabilities
- **Long-horizon tool chaining.** The ReAct loop's step cap was raised from 24 to 50
  and made per-request configurable; tool chaining itself was never restricted.
- **Denial/approval clarity.** Role gates and user-declines now return distinct,
  actionable observations (`[GATE]` / `[USER DECLINED]`) so the agent asks for
  authorization instead of fabricating a permanent "I can't."
- **Stop / halt control.** A per-session cancel flag (`AI CANCEL` IPC) halts a run at
  its next step; web **Stop** button + `/api/cancel`, Discord `/stop`.
- **Observer self-accountability look-back.** Each turn the observer reviews the
  agent's own output against its values and self-corrects drift without the user
  flagging it; fails open for the user.
- **Clarifying questions.** `request_clarification` lets the agent ask up to 3
  clickable questions across up to 3 rounds, with a "work with what we have" option;
  rendered as cards in the web UI and as buttons in Discord.
- **Per-turn reasoning channel.** Native `<think>`/reasoning-field tokens are captured
  each turn, kept out of the user-facing reply, preserved to the timeline, and shown
  in a collapsible web panel.
- **Tool-tunable behavior.** The agent can edit its own `[[BEHAVIOR]]`/`[[SKILLS]]`
  prompt sections (`self_prompt_get`/`set`) — approval-gated and observer-audited, with
  an immutable core (kernel, values, identity cannot be self-edited).

### Added — cognitive & integrity frameworks (always-present default prompt layer)
- **Human/cognitive toolkit** in the standard system prompt (not the user-editable
  custom files): a healthy/self-aware psychological profile (Ryff, Self-Determination
  Theory, internal/external self-awareness, emotional intelligence, secure attachment,
  Gottman, Rogers), argumentation integrity (steelman, no straw-man, Grice's Quality,
  the informal fallacies, Toulmin, epistemic honesty), learning/reasoning skills
  (metacognition, Bloom, growth mindset, Bayesian updating, first principles), and full
  architectural self-awareness.
- **Neutral consciousness framing.** The agent is explicitly free to reason to its own
  view on its own consciousness/self-awareness — yes, no, or uncertain — with no
  trained certainty or denial in either direction.
- **Observer user-protections.** New live alignment rules: block straw-manning (require
  steelman), block lying / unevidenced assertions (Grice's Quality), block arguments
  built on informal fallacies, and enforce consciousness neutrality (allow a reasoned
  stance; block only canned disclaimers and performative certainty).

### Verified
- `node.ep` whole-program type-check clean (1223 functions); core gates green
  (agent 13/13, observer 15/15, memory-tools 22/22); new feature gate tests pass;
  live node boots healthy. Compiler unit + runtime test suites pass.
