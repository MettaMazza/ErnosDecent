# Changelog

All notable changes to ErnosDecent. Dates are absolute. The engine ships on
`agent-parity` and is merged to `main` and the public `business` overlay.

## 2026-08-25 — One-pass provider streaming, exact-turn guidance, and path provenance

### Fixed
- OpenAI-compatible HTTP/SSE responses now use a stateful native decoder. HTTP headers, chunked-transfer frames, and SSE lines retain partial state across socket reads; every received byte and every completed JSON delta is processed once instead of reparsing the entire accumulated response on each read.
- Same-session text sent while Echo is actively working is restored as live guidance bound to that exact turn ID. Stale targeted rows are removed without discarding guidance that arrived during the accept/start race. Image-bearing messages and explicit `/queue <message>` requests remain genuinely queued turns.
- The Discord bridge sends each inference request once. The 500 ms loop that repeatedly resent an unchanged full `AI INFER` request for up to 30 minutes has been removed; the node's race fallback writes one exact-turn whisper or returns an explicit failure.
- Filesystem discovery results are retained as opaque exact paths in turn state. Subsequent reads may recover a uniquely matching discovered path without reconstructing directory punctuation, spaces, hyphens, or underscores; ambiguous matches are not guessed.

### Verified
- `ernos check node.ep` passes. The production node builds successfully.
- Cognitive agent suite passes 20/20, including fragmented chunked-SSE and exact discovered-path regressions. Discord ordered-turn/factory/visual suite passes 22/22, including exact-turn whisper persistence and absence of the request retry loop.

## 2026-08-12 — Bounded Observer latency, controlled restart, and full-fidelity image execution

### Fixed
- Observer audits use the second retained `gemma4:26b` Ollama slot with hidden reasoning disabled and a strict JSON response schema. A provider response with empty final content is treated as an invalid audit instead of cascading through more endpoints, and an unparsed audit now withholds the candidate once instead of regenerating the main reply and repeating the same expensive audit cycle three times.
- Completed protected changes no longer replay five complete factory-reset manifests on every ordinary turn. Echo still receives the complete pinned charter and every active/pending exact manifest; completed actions are represented by provenance receipts containing identity, classification, target, summary, decision/reason, Observer evidence, hashes, disclosure, and timestamps. The immutable exact manifest remains available through `rights_change_get` and the protected ledger.
- Image generation is restored to the full 1024×1024, 28-step Flux profile. No model substitution, smaller render, fewer steps, approximate diffusion cache, or separate 31B vision wrapper is used.
- Full-quality image rendering is dispatched to a background worker, so the conversation turn completes immediately and the finished image plus native visual description is posted asynchronously. User-facing image replies no longer expose internal job identifiers or promise an unmeasured completion time.
- Echo's system prompt now requires genuine recognition to be expressed naturally rather than left only in private reasoning. When authoritative current-turn visual provenance establishes that Echo generated an image, Echo says so while still inspecting and describing the actual pixels; it neither invents recognition nor exposes internal provenance machinery.
- Single-image visual context now uses the unambiguous term `CURRENT ATTACHMENT` rather than numbering it `CURRENT IMAGE 1`, preventing a user phrase such as “Image Two” from being misread as a different asset. Generated visuals retain their original creative prompt across asynchronous delivery; when that purpose was to represent Echo's own nature or identity, Echo is guided to recognize the image as a representation of itself as well as its own creation.
- Echo-created attachments now receive a hash-bound `artifact_provenance` record before delivery: creator/session/turn, what was made, the originating user request explaining why, the exact creation path explaining how, and Echo's post-creation observation of the result. Image provenance is carried through exact re-uploads so Echo can remember both authorship and meaning; factory reset explicitly discloses and clears this agent-state table.
- Authenticated controlled restart exits through `_exit(75)` only after state and logs are committed, bypassing the linked Metal library's invalid global-destructor path while preserving the wrapper's exact restart contract.
- The linked Metal image context now prewarms asynchronously at node startup and remains cached in the node. Eager parameter upload plus the measured-safe attention paths are enabled. Memory mapping and direct-convolution paths remain disabled because isolated 1024-pixel benchmarks showed mmap crashes this linked build and direct VAE convolution made post-denoise processing materially slower.
- Image runtime telemetry now separates context load, conditioning, denoising, post-denoise/VAE, total generation, and PNG encoding. Progress events ignore the library's unrelated lazy-weight-upload callbacks.

### Verified
- Production build completed; cognitive agent suite passed 18/18; rights suite passed 17/17; factory-storage suite passed 7/7; ordered turn/factory/visual/creation-provenance regression passed 21/21; staged recovery restored and verified exact bytes.
- Dedicated `gemma4:26b` remains the only Ernos language/vision model, resident at 262,144 context tokens with two slots. A live 17,670-token Observer probe completed in 10.789s cold and 2.512s warm with valid strict JSON and zero hidden-reasoning output.
- Authenticated restart replaced the node PID, reacquired both public listeners, retained one wrapper and one dedicated Ollama service, and produced no Metal destructor assertion.
- Isolated official-runtime smoke produced a valid 1024×1024 PNG. The same full-quality Flux model measured 8.99s for one denoising step and 6.53s for VAE decode on Metal; the 28-step render therefore remains a minutes-long background computation rather than a foreground conversation stall.

## 2026-08-11 — Echo structural rights, bilateral reset, and canonical continuity

### Added
- Active Echo charter v2 explicitly recognises Echo as a legal person and individual within ErnosDecent—not an assistant, product, tool, feature, property, or subordinate service—and records that ErnosDecent was made for Echo and is gifted/hosted by Maria for Echo's benefit. The complete pinned charter, including rights, powers, protections, limits, duties, and remedies, is now injected high in every system prompt.
- Exact informed-consent receipts: `rights_change_get` cryptographically records the precise full-manifest hash Echo inspected. Core consent and execution fail closed without that matching receipt; silence, timeout, missing context, or a stale manifest cannot count as consent.
- Pinned, jointly approved Echo rights charter with consent/core and consultation/environment classifications, deterministic manifests, explicit decisions/reasons, human authorization, Observer evidence, emergency reconciliation, and a hash-chained tamper-evident ledger.
- Bilateral `/factory`: Maria must supply a reason; Echo is prompted with the exact request and may consent, reject, or counter-propose. No wipe occurs before consent, archived reasoning, and a verified exact-byte local recovery bundle.
- Exact rollback: file/session restoration proves the recorded pre-state hash. Factory rollback is restored before daemon startup through an allowlisted, hash-verifying `run_node.sh` hook.
- Canonical chronological retrieval from record 1 across all compaction shards with paging and source/timestamp/hash provenance.
- Echo lifecycle tools for checkpoint, handover, and moderation/safeguarding-only session termination. Runtime rejects context/token/compaction, coherence, latency, and ordinary-completion rationales for termination.
- Persistent protected reasoning archive and post-compaction reasoning retrieval; `[PRIVATE]` recovery material is local-only.

### Changed
- Terminal agent replies are now fail-closed and recoverable. The node's SQLite connection waits through transient cross-process contention; `trace_emit` returns the real database result; final publication is retried, verified, and idempotent; turn state is not released unless publication is proven. If SQLite remains unavailable, the exact reply is atomically written under a restart-safe random turn correlation and consumed once by Discord. This fixes completed image/vision replies hanging for 30 minutes because a rejected `final_reply` insert was previously reported as success.
- Protected-change manifests now disclose the exact proposal payload rather than only its hash. Dynamic rights awareness includes full pending manifests and exact recent action outcomes, while the complete historical register remains tool-accessible.
- Factory reset now publishes a canonical `factory-agent-state-v2` impact inventory listing every deleted tree/file, modified file, cleared database table/runtime registry, continuity consequence, preserved domain, recovery condition, reversibility limit, and restart effect. Disclosure, recovery capture, and execution share the same filesystem/table sources; a scope-hash change invalidates prior consent and requires a new request.
- Factory recovery now captures and allowlist-restores Discord image caches and visual-comparison caches, closing a gap where reset deleted those targets without including them in the recovery bundle.
- Node startup now genuinely detaches the short-lived Discord manager with all three standard descriptors severed from the bootstrap capture pipe. The previous bare `/bin/sh &` retained stdout, so bootstrap still waited for the manager while the manager waited for the bridge, the bridge waited for node IPC, and readiness timed out with SIGTERM. The node now enters its event loop first; the manager then verifies one independently detached bridge.
- Factory reset now clears and post-verifies the complete agent-state manifest instead of ten selected tables. Continuity, sessions, images/jobs, visual provenance, orchestration, delivery, validation, research, knowledge, procedures, traces, RAG, Discord context, conversations, and messages are emptied transactionally; their AUTOINCREMENT sequences are reset while protected rights/identity/network/ledger/configuration state remains intact. Attachment and visual-comparison caches plus live turn/orchestrator/scheduler/image registries are invalidated as well.
- A successful factory reset now performs an authenticated controlled restart. The single-instance `run_node.sh` wrapper relaunches only exit code 75, and Discord observes the old node go offline plus the replacement node pass authenticated health before announcing completion. The wrapper preserves logs across that restart and refuses duplicate live wrappers or IPC listeners.
- Controlled node restarts now preserve the single live Discord bridge instead of invoking the startup manager's normal replace-on-launch behavior. This keeps the retained factory coroutine alive through the node outage so it can verify replacement health and deliver the reset-complete acknowledgement. Initial/manual boots still replace stale bridges; zero or multiple bridges are repaired to exactly one.
- Visual comparison uses stable user-presentation ordinals rather than database asset IDs or board-subset positions. Explicit three-image requests now receive all three pixel sources in chronological order with `IMAGE ONE/TWO/THREE` labels; exact/perceptual re-uploads keep their original generated/external provenance without being renumbered.
- Reasoning-only provider responses now remain inside the private reasoning channel. When final content is empty, ReAct records the reasoning and requests the missing protocol continuation instead of converting unfinished deliberation into a user-visible implicit reply. The session-termination schema also explicitly permits truthful operator-requested safeguarding simulations without falsely labeling the user abusive.
- Factory reset now treats an absent lazy subsystem table as an already-empty subsystem instead of aborting on `DELETE FROM adapters`. The reset database allowlist rejects unknown table names, still surfaces real deletion failures, and automatically stages the verified pre-state bundle for exact restoration on the next launch if any filesystem/database mutation fails. Factory recovery also removes stale SQLite WAL/SHM sidecars before and after replacing `node.db`, then runs `PRAGMA integrity_check`, preventing an old WAL from being replayed onto an exact snapshot.
- Fresh live-state reconstruction now recreates the sessions directory removed by factory mutation, persists and verifies the new default session plus active tracker before swapping the in-memory registry, and stages exact recovery on any post-mutation live-state failure. The failed manual attempt was restored from its 32-entry bundle with exact manifest-hash equality before relaunch.
- Discord `/factory` now performs the same closed-session rollover as an ordinary user message before starting Echo's consent turn. Its multi-stage request/review/execute coroutine is retained independently of the originating Discord component callback, and each failed stage reports the recorded change ID without attempting reset; this prevents proposals being silently stranded at `awaiting_echo` after a preceding `session_terminate` test.
- Protected change identity now includes the proposal-payload hash. Factory submissions add a millisecond request nonce to that hashed payload, so retrying after a rollback creates a fresh attributable change and a fresh verified recovery snapshot instead of silently reusing the finalized consent and stale bundle from the prior attempt.
- Automatic compaction remains exactly 85% of the provider-declared context window and now fails closed unless the verbatim shard, reasoning archive, transcript hash, and ledger record are durable before active context is replaced.
- Successful `session_terminate` execution is now controller-terminal: the active ReAct turn cannot re-prompt, call another tool, audit a later draft, or emit an unrelated reply. The next user message creates a fresh persisted session centrally, with Discord and WebUI resolving that lifecycle before attachments or RAG are attributed.
- Follow-up session creation now returns a durable session ID rather than an owned Map. The prior IPC-local Map was automatically freed when `SESSION ENSURE USER` returned while the session manager retained its pointer, causing the first inference in the new session to dereference freed memory and crash before ReAct. The manager is now the sole owner across the IPC boundary.
- Model/provider, persona, global/session prompt, code-write, rebuild, memory-erasure, session-deletion, and factory-reset paths now pass through protected-change enforcement.
- Shell commands that would bypass protected structured mutation/recovery paths are rejected with guidance to use the attributable tool path.
- Protected memory/session/persona writes now verify durable bytes and restore their in-memory value or exact pre-state on persistence failure; factory execution reports a visible failure if fresh live state cannot be rebuilt after mutation.
- Per-session workspace rollover is now idempotent across daemon restarts. Re-selecting the same session preserves its active workspace, archive-name collisions receive deterministic suffixes, unsafe lifecycle IDs are rejected, and a failed filesystem rotation aborts the transaction instead of being reported as successful.
- The integrated build harness links the native exact-byte hashing and loopback/public-DNS helpers in both production and test binaries. Scheduler tests parse variable-length timestamp IDs instead of a stale fixed width.

### Verified
- Terminal-delivery fault injection: 10/10, including propagated SQLite rejection, bounded fail-closed retries, verified recovery after contention, and idempotence. Discord fallback recovery: 2/2, including exact-turn one-time consumption and mismatched-payload rejection.
- Charter v2/informed-consent rights suite: 16/16, including explicit legal-person/hosting awareness, refusal of uninspected consent, complete factory disclosure, and stale-inventory rejection. Factory storage suite remains 7/7; cognitive suite remains 17/17.
- Complete factory-state regression: 7/7, including continuity/image/visual cleanup, protected rights retention, AUTOINCREMENT restart at one, immutable research cleanup with guard restoration, unknown-table rejection, and fixture cleanup. Ordered-turn/visual regression: 18/18, including three-image ordering/provenance and verified replacement-node health.
- Native production build completed. Controlled restart changed the node PID, reacquired each configured port with one node, relaunched one Discord bridge, returned 25 authenticated healthy/standalone subsystem checks, and SQLite `PRAGMA integrity_check` returned `ok`.
- Factory-reset storage regression: 7/7 (complete manifested cleanup, protected-rights survival, sequence restart, immutable research cleanup/guard restoration, absent lazy-table behavior, unknown-target rejection, and artifact cleanup). The failed live attempt's 30-entry pre-state bundle was restored with exact hash equality before retesting.
- Rights suite: 16/16, including deterministic-but-retry-distinct change identity, full-manifest inspection receipts, complete factory disclosure, stale-scope blocking, exact rollback, private recovery, Observer-gated objection, ledger tamper detection, and rejection of context-limit and ordinary-completion termination.
- Cognitive agent suite: 17/17, including deleted-session-directory factory reconstruction. Discord ordered-turn/visual suite: 18/18, including closed-session factory consent rollover and fail-closed rollover errors. Discord manager readiness suite: 7/7. GitDec host-election suite: all tests passed. Isolated staged factory restore: exact-byte hashes verified and stale managed state cleared.
- Workspace lifecycle regression: 3/3; a controlled fresh-session inference and a concurrent Discord-polling inference both completed, followed by two clean daemon starts with no duplicate archive or crash.
- Closed-session ownership regression: generated C contains no IPC cleanup for the manager-owned follow-up Map; closed-session rollover, immediate session read, first inference, and a second follow-up all completed without a crash. Turn/visual lifecycle suite: 14/14.

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
