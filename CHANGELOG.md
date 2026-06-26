# Changelog

All notable changes to ErnosDecent. Dates are absolute. The engine ships on
`agent-parity` and is merged to `main` and the public `business` overlay.

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
