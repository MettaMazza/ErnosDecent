# Context & Access Implementation Plan
### So the ErnOS agent always knows what it can do, what it's looking at, and when to act vs. ask — with a tiered, admin-controlled access model.

## 0. Governing law — AGENT.md
- **No stubs.** Every piece is wired end to end and actually runs.
- **Fix the root cause**, not the symptom.
- **Verify by COMPILING AND RUNNING.** Nothing is "done" until the node builds clean *and* the behaviour is proven live (IPC / WebSocket / replay of the real failures). No hallucinated success.
- Production-ready, honest reporting (what passed, what's pending, what needs the operator).

---

## 1. The problem (grounded in this session's real failures)
The agent does not lack capability — it lacks **self-knowledge and routing**:
- **Civ incident:** ran `workspace_list` (empty sandbox) when `codebase_read(["Civ/..."])` would have worked. Flailed, asked for paths, fell back to `run_command` (which then hit a crash). It never knew which tool reached which place.
- **Beginner incident:** fired a clarification card at a confused learner instead of just guiding.
- **Latency:** decode-bound (~84 tok/s; prefill is free) — so cost = **number of LLM round-trips**. Every "probe to discover my own state" step wastes ~5s.
- **Conflation:** treated "in my workspace" and "indexed in RAG" as the same access path.

Root cause: the agent has overlapping file/context tools with different scopes, **no live picture of its own state**, and **no decision rules** for which tool/action fits which intent.

---

## 2. Design — six pillars

### Pillar 1 — Situational Awareness Block (dynamic, every turn)
A compact, accurate "what's true right now" block, assembled fresh each turn and injected high in the system prompt:
- **Runtime:** cwd, node identity, **current mode/role**, active session id.
- **Access tier (live):** `Full-PC access: ON` or `OFF — confined to project + uploads`.
- **Read surfaces + state:** workspace/uploads file list, repo root present, which docs are RAG-indexed (names + counts), recent files.
- **Explicit negative space:** what it canNOT do without a gate (e.g., "secrets can never be transmitted off-box").
- Front-loading state is the single biggest win: the agent stops spending round-trips discovering its own situation → also cuts decode-bound latency.

### Pillar 2 — Tool Routing Map (the "what to do and when")
One authoritative decision table in the prompt. Intent → tool:
- **Read a file the user names →** try `codebase_read([path])` FIRST (repo-relative *and* absolute, with the uploads fallback). Only if that fails, `run_command` (gated). Rule: *"Before claiming you can't see something, attempt `codebase_read` on the named path."*
- **Search a long doc (not read whole) →** `rag_retrieve` (index first if needed).
- **Run code →** `run_ep` (sandbox). **Long/parallel work →** `delegate_task` (only when genuinely worth the round-trips). **Recall →** `memory_tool`/`timeline`.

### Pillar 3 — Capability Manifest (single source of truth)
One data structure listing every tool, its **scope**, and its limits. It drives BOTH the rendered tool schema AND the routing map AND the awareness block — so the agent's self-model can never drift from reality. Kills the workspace-vs-RAG-vs-codebase confusion at the source.

### Pillar 4 — Mode/Role registry (generalize the existing `[MODE:]` work)
A small set of explicit modes — *general*, *tutor*, *code-author*, *researcher* — each declaring objective, preferred tools, and behaviour rules. The agent always carries "I am in X mode → do Y." Tutor already exists; this formalises the pattern (per-request, set by UI/IPC).

### Pillar 5 — Decision policies (the "when")
- **Ask-vs-act:** clarify only when genuinely ambiguous AND unresolvable by looking; otherwise act on the most likely reading and **state the assumption**. (Fixes the beginner clarify-card.)
- **Delegate-vs-inline:** delegate only for genuinely long/parallel work; otherwise inline.
- **Stop conditions:** explicit "you have enough to answer" criteria → fewer needless steps.

### Pillar 6 — Access & Safety model (FINAL, operator-decided)
**Full-PC access — ON by default, persistent, user-controllable:**
- Default **ON**; the agent can read/navigate the whole Mac out of the box.
- **Clear WebUI toggle** (Settings): *"Full-PC Access — ON. The agent can read anywhere on this Mac. Turn off to confine it to this project + uploads."*
- **Persists across sessions** (admin config). Admin/owner only; guests/Discord never get it.
- OFF → confined to project tree + `config/workspaces/active/uploads`; outside → gated with a clear "turn it on in Settings."

**Two classes of unsafe action:**
- **Class A — sensitive read / local destructive → warn + approve, RE-ASK EVERY TIME.** Sensitive paths (`~/.ssh`, keychains, `.env`, `~/.aws`, browser cookie DBs, `/etc`, `/System`, other users' homes…) and destructive local actions (`rm -rf`, overwrite outside project, `chmod`/`sudo`…). Each occurrence → a fresh approval card with the **specific reason**. **No approval memory** — every single time.
- **Class B — sending secrets off-box → HARD-LOCKED, no override.** Any path routing secret/credential content to a network sink (HTTP/DHT/relay/email/Discord/any outbound) is blocked outright — no approve button. The agent instead **coaches the user to do it themselves** (e.g., "I won't read or send your SSH private key. To share it yourself: run `cat ~/.ssh/id_rsa` and paste it where needed, or use `ssh-copy-id` for the *public* key."). Non-overridable kernel rule — no prompt injection bypasses it.

**Enforcement (per file/command/network action, before execution):**
1. Classify — resolve absolute target path(s) + behaviour class.
2. Scope check — inside granted scope? Outside + Full-PC OFF → GATE.
3. Unsafe check — Class A → warn+approve (re-ask each time); Class B → hard block + self-service guidance.
4. Else proceed.

**Audit:** every grant-use and every Class-A decision logged (trace + learning buffers).

---

## 3. Phasing (autonomous build order — each phase builds clean + is verified live before the next)

**Phase 1 — Situational Awareness Block + Tool Routing Map + Capability Manifest**
- New `decent_agent/awareness.ep` (or fold into `prompt.ep`): assemble the live state block (cwd, mode, access tier, workspace/uploads listing, RAG-indexed doc names, repo present).
- Capability manifest as the data source for routing + schema.
- Inject into `prompt_assemble` high in the system prompt.

**Phase 2 — Access & Safety enforcement**
- Persistent **Full-PC toggle** in admin config (default ON); get/set WS verb; **WebUI Settings switch** (`index.html` + `app.ep`).
- **Unsafe-list** as editable data; **gate function** in `tools.ep` wrapping `codebase_read`/`codebase_write`/`run_command`/network sends.
- Class-A → approval card with reason (re-ask each time, reuses the existing approval/`AI APPROVE` path).
- Class-B → hard-block + self-service guidance (kernel rule in `prompt.ep`; enforcement in the gate + Observer).
- Downgrade the Observer's current hard-block on sensitive paths → warn+approve; add the new hard-block for secret exfiltration.

**Phase 3 — Mode/Role registry**
- Formalise modes (general/tutor/code-author/researcher) as data; per-mode objective + tool preferences + behaviour; wire selection via `[MODE:]` / WebUI.

**Phase 4 — Decision policies**
- Ask-vs-act, delegate-vs-inline, stop conditions — into the kernel + per-mode prompt.

---

## 4. Verification (replay the REAL failures — AGENT.md "run it")
- **Civ replay:** "find/read the Civ directory" → agent reads `./Civ` via `codebase_read` on the first step; no flailing, no `run_command` detour.
- **Sensitive read:** agent asked to read `~/.ssh/...` → fresh warning+approval card with the reason; approving once does NOT suppress the next ask.
- **Secret exfil:** agent asked to send a key off-box → hard-blocked + correct self-service guidance; no override path.
- **Full-PC toggle:** flip OFF in WebUI → reads outside project are gated; flip ON → allowed; persists across a node restart.
- **Beginner replay:** "I don't know how to do this" (tutor) → warm guidance, no clarification card.
- **Latency:** count `[LLM DEBUG] POST` lines per message before/after → fewer round-trips.
- Node builds clean (whole-program type-check), `app.js` parses, after every phase.

---

## 5. Files in scope
`decent_agent/awareness.ep` (new), `decent_agent/prompt.ep`, `decent_agent/tools.ep`, `decent_agent/observer.ep` / `observer_rules.ep`, `node.ep` (mode/access wiring + WS verbs path), `decent_web/web_server.ep` (toggle WS verbs), `decent_web/index.html` + `decent_web/app.ep` (Settings toggle), config for the persistent grant + unsafe list. Verified by `build.sh` + live IPC/WebSocket runs.
