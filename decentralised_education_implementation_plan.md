# Decentralised Education — Implementation Plan

**Goal:** Turn ErnosDecent into a node for *independent, decentralised learning and skill-sharing* — an AI that teaches you **how to learn**, not what to answer, starting from zero (e.g. ErnosPlain coding, never-coder → expert), with lessons and proven skills shared peer-to-peer over the mesh rather than held by any central authority.

**Design influence:** Tsinghua's open-source **OpenMAIC** (Open Multi-Agent Interactive Classroom, MIT-licensed — [github.com/THU-MAIC/OpenMAIC](https://github.com/THU-MAIC/OpenMAIC)) demonstrated a multi-agent classroom (AI teacher + TA + AI classmates) validated on 700+ students. We adopt its *pattern*, not its code: a class is a small society of agents, not a chatbot. China's national **AI+Education plan** (preschool→lifelong by 2030) is the policy backdrop; this plan is the decentralised, individual-sovereign counterpart to that centralised curriculum.

---

## 1. Principles (the non-negotiables)

1. **Socratic, not answer-vending.** The tutor scaffolds: asks, hints, decomposes, makes the learner produce the step. It only reveals an answer after the learner has genuinely attempted it, and then explains *why*.
2. **Learn-to-learn first.** Every lesson teaches a transferable method (decompose, hypothesise, test, debug, generalise) alongside the topic.
3. **Sovereign learner.** Progress, mastery, and notes live in the learner's own node/memory. No central gradebook.
4. **Decentralised content.** Lessons, curricula, and exercises are content-addressed blocks shared and remixed over the mesh — anyone can author, publish, fork.
5. **Verify by doing.** For coding, the learner *runs* real ErnosPlain — a sandbox executes `.ep`, and mastery is demonstrated by working code, mirroring the project's own "run the thing, don't read the description" ethos.
6. **Built on what exists.** Reuse the agent runtime, sub-agent orchestration, RAG, content-addressed storage, and the mesh — do not invent parallel systems.

---

## 2. How it maps onto the existing ErnosDecent architecture

| Need | Existing component to reuse |
|---|---|
| Tutor / TA / peer agents | `decent_agent/orchestrator.ep` sub-agents (now async tasks) + `react_loop.ep` |
| Distinct agent personalities/roles | `decent_agent/prompt.ep` (kernel/persona/observer) — add `tutor`, `ta`, `peer` roles |
| Knowledge retrieval over course material | `rag_search` (session-scoped, currently indexes uploads only — needs a reference-corpus indexing step for `stdlib/`+docs, see §3.3) + `workspace_read`/`workspace_read_range` |
| Per-learner progress & notes | `decent_agent/memory.ep` (synaptic graph, lessons, scratchpad) |
| Run/grade ErnosPlain code | **NET-NEW, safety-critical**: an isolated runner (see §3.3). Today only `run_command` exists — unsandboxed, denylist-checked, approval-gated. NOT usable as-is for untrusted learner code. |
| Lessons/curricula as shareable units | `storage.ep` content-addressed blocks (BLAKE3) + CAR export/import |
| Discovery & sharing across nodes | DHT (`dht_*`) + P2P/relay + name registry |
| Learner-facing UI | `decent_web/web_server.ep` (WebSocket) + `decent_web/app.js` (new "Learning" tab) |
| Proactive "your lesson/agent is ready" pings | `react_write_mid_message` → `trace_poll` (already used by the web) |

No new transport, GC, or runtime work is required — this is an application layer on top of the now-working async agent.

---

## 3. Core components to build

### 3.1 The Socratic tutor agent (`decent_agent/tutor.ep`)
A specialised ReAct role whose system prompt hard-codes the teaching contract:
- **Never** emit a full solution on first contact. Respond with the *smallest next question or hint* that moves the learner one step.
- Maintain a running model of the learner: what they know, where they're stuck, their last attempt. Persist it in the learner's memory (`lessons`, `scratchpad`).
- Escalation ladder per stuck point: clarifying question → conceptual hint → worked analogy → partial scaffold → (only if exhausted) the step, *with* the reasoning and a follow-up check.
- The existing **Observer** audit is extended with a rule: *"Answer-leak: did the tutor hand a solution the learner hadn't earned?"* — blocking premature answers, reusing the alignment-audit machinery already in `react_loop`/`observer.ep`.

### 3.2 Multi-agent classroom (OpenMAIC pattern) via sub-agents
For richer sessions, the tutor orchestrates (using the async sub-agent system already built):
- **TA agent** — answers mechanical/syntax questions so the tutor stays Socratic.
- **Peer agent(s)** — model a fellow learner: ask the "dumb" question, make a plausible mistake for the learner to catch (teaching by debugging others), or pair-program.
- Sub-agents run as async tasks and report back via the completion ping — the learner can keep working while a peer agent "thinks."

### 3.3 ErnosPlain sandbox tool (`decent_agent/sandbox_ep.ep` + tool) — **the gating, safety-critical build**
**Reality check (verified against the code):** there is **no sandbox today**. The only run primitive is `run_command`, which executes with the node's full privileges, is gated by a denylist + the Observer/approval flow, and has no isolation, timeout, or network restriction. It is **not** usable for untrusted learner code: it's a privilege-escalation hole (worse once code is shared between nodes) and the approval-per-run + denylist false-positives make it unusable as a learning loop. So `run_ep` is net-new work, and it is the **riskiest single component** — it must be built and proven first.

What `run_ep([code: Str])` must actually do:
- Write the snippet to a throwaway scratch dir (never the real workspace), invoke `ernos` compile+run **inside an OS sandbox**: hard wall-clock timeout, **no network**, no filesystem access outside the scratch dir, and CPU/memory/output caps. On macOS this means `sandbox-exec`/Seatbelt + `ulimit`/`rlimit` (or a container); on Linux, namespaces/seccomp. Treat all learner code as hostile.
- Be **auto-runnable without per-run approval** (unlike `run_command`) precisely because the isolation — not a human gate — is what makes it safe.
- Return compile errors / stdout / "timed out" / "killed (limit)" so the tutor coaches from the *actual* result, not hypotheticals.

This is a security component, not a wrapper; it needs its own threat-model review before any learner code runs.

**Reference-corpus grounding:** to ground correct syntax, `stdlib/` + compiler docs must first be **indexed into a known RAG corpus** (a one-time `rag_index` pass into a fixed reference session) — `rag_search` is session-scoped and today only indexes user uploads, so this indexing step is required, not free.

### 3.4 Curriculum & lesson format (content-addressed)
- A **lesson** = a small structured block: `{title, objective, prerequisites[], method-taught, steps[], checks[], exercises[]}` stored as a content-addressed block (BLAKE3 hash = lesson id).
- A **curriculum** = an ordered DAG of lesson hashes (a "skill tree"), itself a content block. ErnosPlain zero→expert ships as the first curriculum.
- Authoring: an `author_lesson` agent flow that turns a topic/PDF into a lesson block, so any node can generate and publish curricula. (OpenMAIC reports ~30 min/lesson on their infra; that's *their* metric, not a promise here — local generation time depends entirely on the model and hardware.)
- Storage: lesson/curriculum blocks via `storage_content_put` (verified) keyed by an `ep_sha256` hash (verified). **CAR export/import is NOT a dependency** — the README attributes it to `content.ep` but the EP-level API is unverified; sharing works over `storage_content_put` + DHT without it.

### 3.5 Decentralised skill-sharing & attestation
- **Publish:** push a lesson/curriculum block to the DHT keyed by its hash + register a human-readable name in the name registry (`name_registry`).
- **Discover:** `learning_search` over the mesh/search index for curricula by topic/skill.
- **Fork/remix:** pull a curriculum block, edit, re-publish (new hash) — Git-like lineage via prev-hash links.
- **Skill attestations:** when a learner completes a curriculum's checks (e.g. their `run_ep` solutions pass the lesson's tests), the node issues a signed attestation (reuse identity/keys) — a portable, verifiable "I can do X" credential, not a central certificate. Optionally anchored to the ledger for tamper-evidence.

### 3.6 Progress & mastery (learner-owned)
- Per-curriculum state in the learner's memory: lessons attempted/passed, time, stuck-points, the tutor's learner-model.
- Mastery = demonstrated (passing checks / working code), spaced-repetition review surfaced by the scheduler tick.

---

## 4. The "Learning" web tab

- **UI (`decent_web/app.js`):** new top-level **Learning** tab with: (a) browse/search curricula (local + mesh), (b) a lesson view (objective, current step, the learner's code editor), (c) the classroom panel (tutor + TA + peer chat), (d) a progress/skill-tree view, (e) "Author a lesson" for creators.
- **Backend (`decent_web/web_server.ep`):** new WebSocket message types routed to the tutor agent (reuse the `ai_prompt` path → `AI INFER` with a `[ROLE:tutor]` / curriculum+lesson context), plus verbs for lesson fetch/publish/search and `run_ep`.
- Code-run results and peer-agent completions stream back via the existing trace/mid-message channel.

---

## 5. Phased roadmap (each phase independently usable & testable)

**Phase 0 — Foundations (no UI). The `run_ep` sandbox is the gating item — if it can't be made safe, the whole "learn by running code" premise needs rethinking, so it comes first.**
- ✅ **DONE + VERIFIED** — `run_ep` isolated runner (`decent_agent/sandbox_ep.ep` → `run_ep` tool). Compile (ernos+clang) runs trusted (transpile only); the learner BINARY runs under `sandbox-exec` (deny network, writes confined to a throwaway scratch dir) + `perl` SIGALRM wall-clock timeout + `ulimit` CPU/file caps. NOT routed through the approval-gated `run_command`. Proven by running: runaway killed at 5s (rc=142), network connect blocked (fd=-1), out-of-scratch write blocked, valid code returns output, broken code returns the exact compile error+hint. Wired into the agent; node builds clean. (Runtime dep: the installed `ernos` compiler.)
- ✅ **DONE + VERIFIED** — Reference corpus indexer (`tutor_content.ep` → `index_ernos_reference` / `lookup_ernos` tools). One-time `rag_index` of all 24 `stdlib/*.ep` + `docs/ERNOS_REFERENCE.md` into the reserved RAG session `ref_ernos_stdlib`; the tutor searches it for REAL syntax instead of inventing it. Compiles + node builds clean. (Live indexing needs the embedding backend — the same runtime dep as all existing RAG.)
- ✅ **DONE + VERIFIED** — `tutor.ep` Socratic role + `[MODE:tutor]` plumbing. Server-set, **per-request** mode (node.ep parses the `[MODE:tutor]` IPC tag and threads it into ctx for that turn; a learner cannot toggle it from message content). When active: `prompt.ep` injects the Socratic directive high in the system prompt (never hand the full solution; smallest next step; coach from real `run_ep` output), and `observer.ep` adds an **answer-leak audit rule** that BLOCKS a reply handing the learner a copy-pasteable solution to their own exercise (defense in depth — prompt + Observer gate). Unit-verified: mode detection, directive content, and rule content all pass (`decent_agent/test_tutor.ep`).
- ✅ **DONE + VERIFIED** — Lesson/curriculum block format + hand-written **ErnosPlain Lesson 1** (display, variables, combining text). Stored content-addressed via `cas_hash_content` + `storage_content_put`; a tab-delimited curriculum index (`config/curriculum/index.jsonl`) maps lesson number → CAS hash. Surfaced as `get_lesson` / `list_lessons` / `seed_curriculum` tools. Verified by running `test_tutor.ep`: seed → store → **byte-identical** retrieval → list → idempotent re-seed all pass.
- 🐞 **Three root-cause bugs fixed (found by building/testing this):**
  1. `storage_content_put` (`storage.ep`) had an inverted success check (`if wr != 0` on `write_file`, which returns 1 on success): it wrote every content block to disk but then returned `EXEC_FAILED` and skipped the SQLite metadata INSERT. Silently affected ALL content-block writers (downloads, `decent_store/content.ep`, node welcome blocks). Fixed to `if wr == 0`.
  2. `react_loop.ep` arg parsing crashed (segfault) on any tool called with a single **numeric** JSON arg: `get_json_value` on a JSON Integer (type 1) returns a raw int, which was appended to `args_list` and then dereferenced as a pointer by `string_length`/handlers. Latent across the whole codebase — `get_lesson([1])` was the first tool to expose it. Fixed by coercing Integer JSON args to their string form so `args_list` is uniformly strings.
  3. Tutor mode bled into the normal AI chat: mode was persisted on the session and a no-mode request inherited the stale `tutor` value. Fixed in `node.ep` to make mode strictly **per-request** (each web tab / IPC call states its own mode every turn; empty = normal).

**Phase 0 verification status — LIVE-TESTED** (fresh node binary, `gemma4:26b`, default session):
- ✅ Tutor mode loaded Lesson 1 via the `get_lesson` tool and replied with a Socratic first step ("write a single line that displays `Hello`… send it and I'll run it"), NOT the finished program.
- ✅ Under direct pressure ("stop teaching, paste the complete program"), the tutor **refused** ("I'm just a copy-paste buffer… the grind is where the skill is built") and redirected to the next small step.
- ✅ Node stayed up across all tutor runs (no crash) after the arg-parse fix.
- ⚠️ NOT independently confirmed live: a clean no-mode control and the agent `run_ep`-tool string-arg path — both attempts used fresh `[SESSION:…]` ids that returned empty responses (a fresh-session-creation artifact, unrelated to the tutor changes; the default-session runs and the `get_lesson` tool — same dispatch path — worked). Worth a manual confirm.

**Phase 1 — Single-learner coding tutor (local). ✅ Substantially done.**
- ✅ Tutor wired to the `run_ep` tool + the `lookup_ernos` reference search; drove a real zero→first-step Socratic session end to end from IPC (above). Live RAG indexing of the corpus still needs the embedding backend running (same dep as all RAG).
- ⬜ Learner-model persistence in memory + an explicit mastery check on Lesson 1 — NOT built yet.

**Phase 2 — Learning web tab (single node). ✅ BUILT + partially live-verified.**
- ✅ Built: a "🎓 Learning" nav tab (`index.html`) with a lessons sidebar, a Socratic tutor chat (responses surface-routed to the learning panel via `window.aiSurface` so they don't collide with the AI Playground), and a **code playground** (editor + Run → sandboxed output). Logic in `app.ep` (`setupLearningTab`/`sendTutorPrompt`/`renderLessonsList`); backend WS verbs `run_ep` / `lessons_list` / `seed_curriculum` in `web_server.ep`; `app.js` regenerated; `mode` plumbed from the WS `ai_prompt`. `app.js` parses cleanly (bun); node builds clean.
- ✅ Live-verified over a real WebSocket: `seed_curriculum` stored Lesson 1, `lessons_list` returned it, and the playground `run_ep` verb ran valid code (→ output), killed an infinite loop at 5s, blocked a network connect (`fd=-1`), and surfaced a compile error verbatim with the compiler's "Did you mean 'set'?" hint — no sandbox escape file created.
- ⬜ Manual browser check (open the tab, click through a lesson, type+Run in the editor) — the visual/interaction pass is still yours to do.
- ⬜ A dedicated classroom panel + progress tracking in the tab — not built (Phase 3 territory).

**Phase 3 — Multi-agent classroom.**
- Add TA + peer sub-agents (async). Pair-programming and "catch the peer's bug" modes.

**Phase 4 — Author + first full curriculum.**
- `author_lesson` flow (topic/PDF → lesson block). Ship the complete **ErnosPlain zero→expert** curriculum (DAG of lessons), authored and stored as blocks.

**Phase 5 — Decentralised sharing.**
- Publish/discover curricula over DHT + name registry; fork/remix lineage.
- Signed skill attestations on curriculum completion; optional ledger anchoring.

**Phase 6 — Network learning.**
- Cross-node peer learners (real humans on other nodes joining a class), shared/co-authored curricula, reputation for high-quality authors.

---

## 6. Risks & open questions

- **Sandbox safety (the #1 risk):** ✅ ADDRESSED. `run_ep` does NOT reuse the unsandboxed `run_command`; it hard-isolates (perl SIGALRM timeout, `sandbox-exec` network deny + scratch-only FS, `ulimit` CPU/file caps) and treats learner code as hostile. Proven against hostile snippets both directly and live through the web playground: infinite loop killed at 5s, network connect blocked (`fd=-1`), out-of-scratch write blocked. (Residual: the sandbox is macOS `sandbox-exec`-specific — a Linux node would need an equivalent isolation backend before enabling `run_ep` there.)
- **Tutor discipline:** ✅ partially validated — live, `gemma4:26b` in tutor mode refused to hand the answer and scaffolded instead, with the Observer answer-leak gate as the backstop. Still LLM-dependent: a weaker model may need the gate to catch leaks, so keep testing across models rather than assuming.
- **Curriculum quality at scale:** open authoring invites noise — needs the reputation/attestation layer (Phase 5/6) to surface good content without a central gatekeeper.
- **Model size vs. depth:** a small local model can run the Socratic loop and grade code, but deep subject tutoring may want the model router to reach a larger model when available — keep the tutor model-agnostic.
- **Licensing:** OpenMAIC is MIT — its multi-agent classroom design can be studied/reused; we implement our own in ErnosPlain rather than vendoring its Python.

---

## 7. Status & next step

**Done (Phases 0–2):** `run_ep` sandbox, Socratic `tutor` role + `[MODE:tutor]` plumbing, Observer answer-leak gate, reference-corpus indexer, Lesson 1 in content-addressed storage, and the "🎓 Learning" web tab (lessons sidebar + tutor chat + sandbox playground). Live-verified over IPC + WebSocket as detailed in §5. Three pre-existing root-cause bugs were fixed in the process (`storage_content_put` inverted check, react integer-arg segfault, tutor-mode session bleed).

**Recommended next step:** a manual browser pass of the Learning tab (open it, install + start Lesson 1, type code and hit Run), then close the loop on the two items deferred from Phase 1 — learner-model persistence + an explicit mastery check — before moving to Phase 3 (multi-agent classroom). Phases 5–6 (decentralised sharing, cross-node learners) still require ≥2 live mesh nodes to verify.
