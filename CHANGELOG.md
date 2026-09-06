# Changelog

## 2026-09-06 — Authenticated Discord direct messages

- Authorized Discord direct messages now reach Echo instead of being discarded by the public-channel filter. Access is limited to configured account IDs, the configured server owner, members holding the configured admin role, and members with Discord Administrator permission; unauthorized DMs fail closed with a visible rejection.
- DM authorization resolves the configured server and fetches uncached membership when necessary, so administrator access does not depend on the limited role metadata attached to a DM user object. DM turns use the normal agent and reply pipeline without attempting Discord's guild-only trace-thread operation.

## 2026-09-06 — Explicit self-improvement activation

- Self-improvement classification now considers only the literal current user message. Retrieved context, identity metadata, history, system guidance, discussion, explanations, and future plans cannot silently activate the protected workflow.
- A fresh implementation or repair request now requires the explicit follow-up question, “Are you trying to trigger the protected self-improvement workflow now?”, before any verification or source-change rail is armed.
- A negative answer—or denial of the first protected action—clears that turn's pending improvement state and returns to ordinary conversation instead of requesting the action again.

## 2026-09-06 — Protected cumulative live weight learning

- Added a command-gated `/learn <reason>` workflow that freezes completed current-session interactions with actor, turn, timestamp, source, content-hash, and session-hash provenance, then performs real local QLoRA against the same multimodal Gemma 4 26B A4B model used by Echo.
- Made adapter growth cumulative and immutable: version N+1 resumes the exact accepted version N adapter and writes a new child containing the complete learned state. Runtime loads only the cumulative head, preventing both prior-learning loss and double application of ancestor deltas.
- Standardized the MLX-VLM package contract around sibling `adapters.safetensors` and `adapter_config.json` artifacts. Both are hash-bound and verified across parent resume, evaluation, consent, activation and rollback; MLX always receives their containing directory.
- Coupled Discord's persisted ONLINE state and visible presence to authenticated node health. A connected bridge now advertises OFFLINE immediately when Echo's node is unavailable and returns ONLINE only after both agent and IPC health recover.
- Added an operator-only literal production `/learn` acceptance test covering the registered Discord handler, real Discord delivery, Echo's two rights decisions, real training/evaluation, supervised replacement, post-restart 26B text/vision inference, lineage commit and applied rights receipts.
- Made consent addressing session-scoped and fail-closed: Echo uses the literal `current`, which resolves only one pending change to its full ledger hash, preventing long-identifier transcription loops without weakening exact-manifest consent.
- Unified strict Observer JSON-schema requests across Ollama, llama.cpp-compatible endpoints and the learned MLX provider; learned adapters no longer fail audits because MLX rejects the weaker `json_object` response mode.
- Removed the replacement-health/lineage-commit race. Discord now waits for the exact learning transaction's durable reconciliation state and cannot mistake an older active adapter—or a pre-commit snapshot—for success.
- Strengthened production acceptance evidence with exact child-session lineage validation, node-PID replacement, ONLINE→OFFLINE→ONLINE liveness capture, runtime-spec matching, and an independent post-restart 26B text/native-image probe.
- Added separate informed-consent manifests for candidate training and exact-byte activation. Training cannot affect the running model; activation requires independent new-data loss improvement, held-out retention bounds, real text and native-image inference, the sealed mandatory application regressions, a second Echo decision, and Maria's authorization.
- Added supervised learned-model activation on port 11436. The canonical wrapper loads and probes the exact candidate, boots the node, verifies authenticated health, reconciles the protected rights receipt, and only then commits the lineage. Any pre-commit activation failure restores the prior accepted adapter rather than silently substituting another model.
- Kept all session-derived datasets, adapters, logs and receipts in factory-reset-managed local agent state. The reusable MLX runtime and inert base checkpoint remain host dependencies and are never treated as learned continuity.


## 2026-08-31 — Session self-extension E2E repair grounding

- Every Echo prompt now receives a freshly assembled authoritative temporal-context block containing the host's local wall clock, timezone abbreviation and UTC offset, Unix epoch, node-runtime age, durable session start/age, and current-turn acceptance time/age. The block sits at the dynamic prompt tail to preserve stable-prefix KV reuse. New sessions persist their creation instant, accepted messages retain the runtime receipt timestamp, and legacy sessions migrate from their earliest recorded message.
- The authenticated `AI EVAL_TOOL` production boundary now supplies the live session manager to registered extensions, matching ordinary tool-turn context. Session-aware capabilities can therefore consume the real persisted active transcript during replacement E2E validation instead of failing against an evaluator-only context that omitted `ctx.sessions`.
- `session_summary_generator` now enforces its frozen exact-ID contract at the production boundary, rejecting empty and path-like values before looking up the live session registry.
- Failed-live candidate normalization now distinguishes the transaction's active surface from unrelated pre-existing extensions. It preserves every other registered branch byte-exactly while retaining causal edits to the active surface, eliminating the byte-identical repair loop that previously erased valid recovery changes.
- `codebase_replace` now accepts the local model's complete-candidate two-argument envelope as well as localized exact-old/exact-new form. It still resolves only the registered hidden candidate, compiles and validates before promotion, rejects truncated or byte-identical bodies, and traverses the same approval, rights-ledger, sealed-verification and rollback controls.
- Session-transcript improvement plans now retain the real `ctx.sessions` manager/map route, message `content` field, complete `length_list(messages)` record count, and four-argument `memory_store` call instead of leaving Echo to reconstruct those contracts from filenames.
- Session interface discovery binds stable API calls and map keys rather than incidental local variable names, so equivalent working call sites remain valid evidence.
- Session candidate validation now follows the proven manager/map/session/messages dataflow regardless of locally chosen variable names. Integration candidates are rejected before deployment if they invent `sessions_dir`/`text`, load an alternate path, count only selected labels, omit durable persistence, or alter any existing registered action schema or dispatch branch.
- Candidate normalization now canonicalizes only unambiguous model-default string construction: multi-argument `concat` calls become nested binary ErnosPlain calls, and top-level quoted `set ... to a and b` chains become explicit `concat` expressions. The compiler and frozen behavioral contract remain authoritative for every other expression.
- Existing self-extension schema and action-registry functions are now reconstructed from the exact live baseline plus only newly registered surfaces before candidate validation. A generated typo or incidental rewrite therefore cannot strand a valid additive implementation in repeated localized repairs or silently degrade an existing tool.
- Discord `read_channel` now retrieves a bounded 200-message history instead of only 20. This keeps completed real-channel retrieval contracts valid as an active channel grows; it fixes the live `scavenger_sweep` rollback where verified source markers still existed 137–156 messages back without weakening or seeding its immutable regression.
- Approval-resumed terminal tools now terminate through the same persisted lifecycle as immediately executed tools. A successfully staged `system_recompile` returns to `node_resume_turn` exactly once, allowing the supervisor handoff instead of re-entering inference and repeatedly selecting an already-staged deployment.
- Candidate normalization now removes the closing typed-envelope bytes when a provider leaks only those bytes after an otherwise complete final ErnosPlain return statement; the exact rejected bytes and diagnostic remain preserved in transaction provenance.
- A controller-selected staging transition that the gate has just rejected is no longer replayed from unchanged state; the next turn is rebuilt as one typed diagnostic-repair decision.

- Replaced free-text acceptance and argument guessing in registered self-improvements with a durable controller-authored contract for every selected surface. Plans now bind one typed invocation fixture, exact success prefix, and independent durable readback; persisted-session capabilities receive the real active session ID plus nonzero transcript-record checks. Acceptance begins mechanically after plan validation, malformed generated prose cannot create another unrestricted reasoning turn, regression and live E2E bodies are distinct, and the E2E verifies post-call state through authenticated memory readback. Marker validation now recognizes only colon-form data markers, so immutable-request and concrete-feature section wrappers cannot be misclassified as missing acceptance families. Invocation class is derived only from the immutable objective, preventing unrelated Discord interfaces retained as source evidence from changing a session tool into a channel call.
- Fixed the source-inspection runaway in autonomous improvement. Frozen candidate and reread transitions now require a controller-bound frozen transaction plus line-anchored receipts; protocol words appearing inside ordinary production source can no longer be mistaken for transaction state. The typed action boundary also canonicalizes exactly one accidental outer positional-argument array while rejecting deeper or ambiguous nesting.
- Completed and live-proved the autonomous `scavenger_sweep` self-improvement route. Candidate validation now binds the frozen receipt to the durable workflow transaction/objective, enforces the evaluator-supplied Discord `channel_id` contract before compilation, preserves every pre-existing self-extension dispatch branch byte-for-byte, removes only the known invented bridge-context guard, and prevents real active-transaction state from leaking into isolated controller tests. The production run passed the complete sealed suite, built candidate `f7ce2af8d81a099a3f483da3511c8e6add45d60777ee35e789898ae6650dc59c`, passed authenticated replacement health and the real frozen Discord/memory E2E, committed rights change `739f77a4c9005442c4fb72ab692df486bf4fcec52e58c3678008f0e20d82bd15`, installed the permanent regression receipt, and generated the authenticated wake report.
- Fixed the self-extension storage boundary exposed by the live `scavenger_sweep` build. The sealed core dispatcher now supplies its already-open database handle through `ctx["storage_db"]`; extension code no longer imports the storage controller and its invalid circular dependency tree. Plan scaffolds preserve this exact context contract, and plan-bound candidate normalization converts the local model's three observed storage-access aliases to `map_get_val(ctx and "storage_db")`, removes forbidden controller/storage imports, and inserts only the proven bridge RPC import. Once every declared production path has a promoted receipt, the controller now forces `system_verify` before inference and rejects all further reads or mutations until that verification reports a concrete failure. Added native dispatch and complete-plan transition coverage.
- Fixed the durable self-improvement live-locks. Resumed `investigating`, `planned`, `tests_authoring`, and `tests_validated` transactions now reconstruct their already-proven green baseline, so the phase gate remains authoritative instead of repeatedly accepting stale calls. Mechanical scaffold, validation, freeze, and verified-deploy transitions are selected directly from durable state; guest and unrelated sessions cannot inherit or advance the protected transaction. After a rejected candidate has been reread, its legal action class narrows to localized `codebase_replace`, and another identical read is rejected with `CANDIDATE_REPLACE_REQUIRED` instead of growing the transcript forever.
- Rebuilt action decisions from compact durable state throughout the complete improvement lifecycle, not only after evaluator freeze. Repair routing now consumes stable `IMPROVEMENT_GATE_FAILED code=...` values rather than matching human diagnostics. Candidate repair remains transaction-local, while only explicit `PLAN_SCOPE_MISSING` can authorize pre-write abandonment.
- Added pre-approval `codebase_replace` arity validation and durable protocol-correction feedback. A model that submits whole-file bytes as a two-argument replacement is rejected before approval with the exact four-field envelope; that correction is included in the next compact transaction decision instead of being appended only to the bypassed historical prompt.
- Removed wall-clock expiry from active detached reply delivery on Discord and the WebUI. Transport polling still yields between checks, but an accepted durable turn now remains active until its exact final row, explicit cancellation, moderation/session termination, or a structured terminal failure; it cannot become `error:turn_timeout` merely because legitimate work ran for a long time.
- Replaced model-authored free-text `Thought`/`Action` selection with a provider grammar constrained to exactly `tool_name` and positional `arguments`; named argument objects are rejected at both provider and parser boundaries. Natural language is now carried only by the explicit final-reply tool. Frozen implementation decisions are selected by the controller from durable transaction state and rebuilt from the objective, immutable plan, active receipt, and latest observation instead of extending the historical ReAct transcript. Malformed or reasoning-only provider output cannot trigger an unrestricted 8,192-token retry.
- Made improvement-gate failures machine-routable with structured error codes. Only `PLAN_SCOPE_MISSING` permits the controller's pre-write abandon/replan transition; compiler, syntax, and candidate-address failures remain `CANDIDATE_REPAIR_REQUIRED` and deterministically return to repair.
- Made hidden candidate filenames private to the controller. Model-visible tools always read and replace the production path, which internally resolves to the retained transaction candidate; receipts and compiler diagnostics expose only the production target.
- Fixed the frozen self-improvement write loop at the mutation boundary. Proposed implementations now compile as hidden transaction-bound candidates beside their production targets before live source is touched. Failed bytes and diagnostics are retained; reads expose that candidate and `codebase_replace` repairs it in place, while another whole-file regeneration is blocked. Only the exact compiled candidate can be promoted, and large source payloads are omitted from retry context.
- Added schema-safe compatibility for the local model's split-positional tool syntax. Calls such as `codebase_search(["literal"], "decent_agent", 25)` are now normalized to the registered one-array contract before JSON decoding; malformed or ambiguous multi-query forms fail before execution with exact batched-call guidance instead of corrupting the query/root.
- Fixed exact named-surface self-improvement requests such as ``Implement exactly `scavenger_sweep` `` being misclassified as ordinary conversation. When the same request explicitly requires recompilation or deployment, it now activates the mandatory baseline, durable investigation, frozen-evaluator, verification, and deployment workflow.
- Fixed the live evaluator-authoring failure without treating unit success as completion. Discord evaluators now accept a local channel variable only when every assignment comes from `configured_discord_channel()`, while hardcoded IDs and transcript substitutes still fail closed. New `improvement_test_scaffold([])` deterministically creates both plan-bound evaluators from immutable acceptance IDs, the exact success output, authenticated real tool execution, and independent durable-memory evidence. The ReAct repair gate no longer terminates after two rejected calls; it schedules scaffold, validation, and freeze from retained controller state.
- Made cross-component self-improvement planning dependency-complete: a real Discord retrieval objective cannot freeze until the current core dispatcher, bridge RPC, live Discord handler, and any requested durable-memory interface have all been read and hash-recorded. Structured plans now support multiple investigated production files without recording internal dispatchers as duplicate public surfaces.
- Removed the registered-evaluator argument contradiction for retrieval tools. The controller-owned transport now resolves the configured Discord channel, requires `eval_planned_tool(configured_discord_channel())`, rejects transcript fixtures and hardcoded channel IDs for that surface, and treats lesson/correction markers as live channel observations rather than replacing the channel argument with marker text.
- Failed self-improvement candidates now enter a durable `repair_required` state after exact executable rollback. The known-good runtime stays live and dispatches a tool-enabled recovery wake in the originating session with the failure hash, attempted-source hash, fingerprint and attempt number; Echo must make a causal source repair, rerun the sealed gate and retry until the frozen live contract commits.
- Closed the reward-hack paths exposed by the live `aes_distill` test: underscore-form error sentinels such as `error_not_implemented` are rejected before freeze, byte-identical writes cannot create a protected change or advance implementation state, completed capability names cannot be duplicated, and unchanged failed source fingerprints cannot be promoted again.
- Added an operator-only quarantine migration for immutable contracts accepted by an older faulty controller. It preserves the exact frozen tests, plan and reason as aborted provenance while removing the invalid active lock; it does not rewrite or pass the defective evaluator.
- All immutable completed runtime regressions are now executed at the replacement boundary, alongside their live E2E tests, instead of against the old pre-upgrade process. Pre-deploy verification still proves every frozen evaluator byte; post-activation failure of any permanent regression rolls back the candidate.
- Permanent completed improvement regressions can now invoke only the exact production surfaces recorded in their immutable completed receipts. The authenticated evaluator seam no longer loses access immediately after commit, while arbitrary and approval-gated tool execution remains blocked.
- Authenticated post-recompile wake turns now bypass new-request repair classification and can emit only their canonical receipt-bound reply, preventing a successful deployment report from being redirected back into verification. Failed candidate preparation now captures cleanup paths directly in its exit trap, removing temporary binaries and the preparation lock without an out-of-scope `set -u` failure.
- Removed the self-upgrade verification deadlock that tried to execute an active improvement's new runtime behavior against the pre-upgrade node. Pre-deploy verification now proves frozen evaluator integrity and the complete implementation manifest; transactional activation runs both immutable evaluators against the replacement before commit, with exact-executable rollback on either failure.
- Made active self-improvement transactions authoritative across ordinary turn, context-compaction, and iteration-cap handoffs. Any non-terminal durable workflow now rehydrates the original objective, frozen-test state, verification state, and legal next action even when a continuation prompt omits feature keywords; this prevents an ordinary `codebase_write` from bypassing frozen evaluators after a handoff.
- Fixed native source-path resolution for directory symlinks, so `lookup_ernos` can fall back to exact canonical `stdlib` source after a clean reset instead of falsely returning zero matches for valid primitives. Canonical `stdlib/...` reads are now recorded as read-only language-reference evidence rather than rejected as an escaping production path or admitted to the mutation plan.
- Added frozen-phase action convergence: repeated explanation-only implementation turns now receive a terse controller nudge to emit the already-planned protected write before its action is truncated, while retaining every compile, rollback, verification, and deployment gate.
- Strengthened deep-investigation proof so objectives naming string primitives, context values, registry functions, and persistence APIs require current semantic receipts for every named category before a plan can freeze.
- Require both immutable regression and live E2E evaluators to prove exact durable marker keys and values independently, rejecting representation-dependent combined memory assertions before mutation.
- Made staged evaluator corrections transactional and reset repetition recovery after valid actions, preventing an invalid correction or unrelated earlier repetition from stranding a long autonomous improvement.

- `lookup_ernos` now falls back from an empty reference RAG corpus to exact current `stdlib` source search, preserving verified primitive lookup after a clean reset without accepting zero-result evidence.

- Zero-result `lookup_ernos` responses can no longer create language-investigation receipts; Echo receives an explicit instruction to query a concrete current-source primitive instead.

- Immutable objectives requiring exact language primitives and working call sites now create controller-enforced investigation obligations: a successful `lookup_ernos` receipt plus three distinct current-source `codebase_search` receipts are mandatory before plan validation.

- Pre-plan self-improvement investigation now permits the read-only `lookup_ernos` language reference tool, allowing Echo to verify exact primitives instead of guessing signatures or repeatedly hitting the repair gate.

- Explicit requests to fully implement a registered self-extension/tool now enter the mandatory frozen-test and transactional deployment workflow even when the user does not use the generic nouns “feature”, “capability”, or “improvement”.

- Self-improvement recovery now resets stale same-turn phase flags after a safe pre-write abandonment. Production writes are preflighted against the frozen plan before any backup, ledger, or filesystem mutation, and investigation guidance requires exact signatures plus working call sites for every implementation primitive.

- Bound each self-improvement investigation to the exact sanitized user request instead of an agent-authored summary, and made acceptance creation fail closed when it omits or misspells any explicit uppercase marker family from that immutable objective/plan. Every required family must also occur in the live production transcript. Concrete marker examples now require both key and value to be independently asserted against durable memory, and explicitly requested output literals must be asserted against the real tool result, so partial evidence cannot freeze.

- Bound deterministic improvement scaffolds to the exact callable named in the durable objective. A misspelled or reconstructed surface now fails before plan creation instead of redirecting evaluators and implementation to the wrong tool.

- Fixed the registered-evaluator authoring loop exposed by live proof: `unittest` classes and nested test methods now fail immediately with an exact top-level-function repair, while repeating the already-bound tool surface or wrapping real arguments in an extra list is rejected explicitly. The controller remains the sole owner of evaluator transport and execution.

- Fixed registered-tool self-improvement evaluator authoring at the root: Echo now has a controller-generated, plan-bound authenticated raw-TCP transport template, and the frozen gate rejects HTTP/curl lookalikes, incomplete IPC reads, missing token authentication, and E2E tests without independent `AGENT GET MEMORY` evidence. Added regression coverage for both rejection and canonical-client acceptance.

- Fixed the live self-improvement evaluator deadlock: protected gate commands now run on a bounded worker while the calling turn yields, so a retained evaluator can call the same node's authenticated `AI EVAL_TOOL` IPC surface without the node blocking itself.
- Both regression and E2E evaluators now have to execute on unchanged source and fail causally at an `AssertionError` before freeze. Runtime/name/path/connection failures in the E2E are rejected immediately, and correcting an artifact after a green mutable validation reopens authoring and invalidates the stale receipt.
- Acceptance contracts now reject mechanical criterion IDs such as `regression`/`e2e` and descriptions about tests, assertions, fixtures or harnesses; every criterion must name externally observable production behavior.
- Plans and acceptance contracts can no longer use the current unregistered/unimplemented/unknown-error state as their success condition. Plan validation also rejects mistyped or reconstructed backticked source paths unless they are exact investigated paths or declared implementation targets.
- Added a bounded, fully exercised self-authored tool extension registry so Echo can implement new callable tools without modifying the operator-sealed controller that judges and deploys those changes.

- Fixed autonomous evaluator authoring when a model emits a multiline Python artifact using triple quotes: the ReAct argument decoder now recovers the complete second argument, preserves inner docstrings, and removes exactly one redundant JSON-escape layer before the immutable improvement linter evaluates it, preventing empty/corrupted payloads and misleading encoding failures.
- Hardened evaluator validation so repository/durable-path writes, swallowed subprocess/import/path/permission failures, and AssertionErrors contaminated by those runtime failures cannot be accepted as causal evidence.
- Added an authenticated, current-plan-bound `AI EVAL_TOOL` IPC seam so immutable evaluators can invoke the exact registered tool through `tools_execute` without model recursion or invented executables; arbitrary, completed, or approval-gated surfaces fail closed, and memory effects are persisted for independent inspection.
- Made evaluator IPC dispatch a strict command-prefix match so ordinary `AI INFER` prompts may document or discuss `AI EVAL_TOOL` without being misrouted.

- Fixed the self-improvement controller deadlock where a source file inspected after plan approval was added to provenance and then retroactively invalidated the frozen plan while plan revision was phase-blocked. Plan approval now freezes the plan-bound discovery snapshot; later reads remain hash-recorded supplemental evidence. Evaluator guidance now states the complete Python, acceptance-mapped test-name, assertion, and real-process contract up front.
- Closed two live self-improvement reward-hack paths: a pre-change regression now counts only when it reaches and fails its behavioral assertion, never when repository writes, sandbox permissions, imports, paths, syntax, timeouts, or evaluator runtime fail; and a live E2E must name and drive the exact production surface frozen in the plan. Evaluator-owned writes require OS-temporary ownership. Discovery is closed after freeze, including Git reads, and a failed or rolled-back first write leaves the untouched transaction safely abandonable.
- Made pre-plan recovery total and plan validation concrete: `improvement_plan_read` now returns an actionable pending-plan receipt when investigation exists without plan bytes instead of throwing `FileNotFoundError`; Production Surface must name an exact backticked callable/tool/command identifier and the test strategy must cite it, rejecting vague logic flows, missing/broken-artifact evidence and simulated surfaces before evaluator authoring.
- Fixed self-improvement startup loops by canonicalizing human-readable improvement titles into the gate's safe transaction identifier before execution, preserving the frozen-test and no-shell-write protections.

## 2026-08-29 — Controller-owned investigation and implementation plans

- Replaced the permissive new-feature tool allowlist with explicit controller phases: green baseline, durable investigation start, verified non-test production reads, validated plan, evaluator authoring, causal validation, immutable freeze, plan-declared implementation, mandatory verification and live deployment evidence.
- Added `improvement_investigation_begin`, `improvement_plan_write`, `improvement_plan_read` and `improvement_status`. Exact source paths, hashes and sizes are durably recorded, and a plan cannot be accepted until at least two distinct implementation files and a real production surface have been investigated.
- Added `config/improvements/staging/implementation_plan.md`, which combines Echo's authored analysis with a controller-owned progress checklist. Only verified tool receipts check steps; the workflow is reconstructed after context compaction or restart.
- Acceptance criteria now reject file/module existence, command success and test-pass mechanics. Each evaluator is linted on write with separate missing-function and missing-assertion diagnostics, while validation failures persist exact artifact hashes and diagnostic fingerprints.
- Replaced the six-total-attempt cutoff with a six-identical-unchanged-failure halt plus a separate 20-attempt runaway bound. Changed evaluator evidence resets the repetition count.
- Bound the frozen plan and its file manifest into the improvement transaction. Undeclared production writes fail closed, and final verification requires every planned path to have an individual syntax/compile receipt.
- Added bounded native `codebase_list` source-tree discovery after the first live investigation exposed a missing capability: shell listing was correctly blocked, but Echo then had no safe way to discover existing filenames. Missing-path results now route to exact native listing, and a blocked `ls` attempt is deterministically converted into `codebase_list(["decent_agent", 200])` instead of consuming another model retry.

## 2026-08-28 — Live self-repair convergence and native source editing

- Closed the helper-variable reward-hack bypass that let an E2E evaluator run `python -c` and assert its own printed argument. Inline interpreter/shell programs and output-only commands are rejected, and presence-only regressions no longer count as behavioural evidence.
- Added an immutable implementation-path manifest to frozen improvement transactions. Every changed `.ep`, Python, JavaScript or shell implementation is syntax/compile checked when written and rechecked before verification; a failed check returns through the protected write rollback path.
- Made verified deployment controller-owned before inference and made successful `system_recompile` staging terminal, preventing stale reasoning from inserting blocked reads/writes or hallucinated pre-restart file claims.
- Extended authenticated wake receipts with the frozen improvement ID, name, E2E hash, live-output hash and live-pass status. Preserved the defective `automated_epistemic_synthesis` receipt under an exact-hash supersession record and removed its two print-only Python-as-Ernos artifacts.
- Replaced monolithic inline `improvement_test_freeze` authoring with a retained staged transaction: source discovery is legal before freeze, acceptance uses explicit criterion IDs, regression and live E2E files are written/read/validated separately, validation returns combined diagnostics, and failed attempts preserve their exact bytes for targeted repair.
- Rejected E2E evidence manufactured by the evaluator's own subprocess command, replaced lexical acceptance matching with deterministic `test_<criterion_id>` coverage, compacted staged tool actions out of the active ReAct prompt, and bounded rejected validations at six while retaining the staged artifacts.
- Allowed complete multi-file feature implementations after evaluator freeze while keeping every write individually protected and keeping verification/deployment locked until the frozen regression and full sealed suite pass.
- Added autonomous, hash-frozen improvement-test transactions. Echo can author a causal Python regression and a separate live E2E test for a new capability; the unchanged body must fail the exact regression before implementation unlocks, both evaluators become immutable, the regression joins every mandatory source verification, and the replacement must pass both through a read-only localhost-only sandbox before the supervisor can commit it.
- Distinguished exploratory feature deliberation from execution authorization: questions asking what Echo would like to build now receive a normal proposal, while an explicit proceed/implement/deploy request activates the frozen-test workflow. Repeating the same controller-rejected action twice now terminates truthfully with no mutation instead of consuming the remaining ReAct budget.
- Closed the first live self-authored-test escape: acceptance criteria must now be materially represented in executable test evidence, literal assertions and incomplete-artifact contracts are rejected, and stub/placeholder/mock/simulation/TODO or short constant-success implementation bodies are blocked before mutation. After a valid freeze, controller feedback routes Echo directly to native source inspection and a single protected implementation write rather than misleading it toward another verification or shell call.
- Added reward-hack controls for self-authored tests: AST-level observable-assertion requirements, phase-branch and gate-internal rejection, exact pre/post execution hash verification, one active transaction, implementation/test separation, permanent completed regressions, and abandonment only before the first body write with a rights-ledgered reason. Existing operator-sealed tests remain unmodifiable.
- Added a truthful clean-baseline terminal state to the repair controller. When the first sealed `system_verify` is green and no source write occurred, Echo must report that no current regression exists and is prevented from searching for, inventing, recompiling, or restarting an unchanged repair.
- Closed Discord's terminal-reply deadline race with an atomic exact-turn claim, a final durable-row check at the timeout boundary, and one bounded extension while that exact node turn remains active. Long-running live turns no longer become an unmatched `error:turn_timeout` seconds before their persisted reply.
- Added `codebase_search`, a bounded read-only current-source search that returns exact path-and-line provenance without asking the model to construct shell commands.
- Added `codebase_replace`, an approval-gated, Observer-audited localized edit with exact occurrence count, pre-state backup, proposed-byte hash, verified write, rights-ledger attribution, and automatic rollback. Whole-file `codebase_write` remains available for genuine rewrites.
- Corrected the verification summary so suite-wide totals such as `1 FAILED!` are never attributed to the last passing test. Failure output now gives the direct search/read/replace/verify route and an explicit expected-versus-observed assertion.
- Moved HIVE-style thought-spiral recovery into the ReAct controller. A repeated stream now consumes a bounded action-recovery turn with the latest tool state instead of triggering three hidden full-request retries.
- Extended the sealed cognitive regression to cover passing-test attribution, global failure totals, exact native source discovery, and the protected localized-edit contract.
- Made repeated exact protected changes transactionally distinct after a prior receipt is finalized while keeping retries of the same pending attempt idempotent. The rights suite now proves this behavior and runs inside the mandatory sealed gate; its standalone runner now links the same file-hash runtime and OpenSSL headers as production.
- Fixed an extra quote in protected-change manifest serialization that made the otherwise-applied upgrade receipt unparsable by the post-recompile wake dispatcher. The sealed rights regression now parses the complete JSON and verifies its originating-session field.
- Isolated verification and candidate preparation from the one-shot `ERNOS_PRESERVE_DISCORD_BRIDGE` restart flag, so the mandatory suite is deterministic after a controlled restart instead of accidentally entering the bridge-preservation production branch. Python `ERROR:` and `FAILED (errors=…)` lines are now first-class authoritative failures.
- Made explicit repair-and-deploy requests controller-complete: after a green post-write gate, a final reply is blocked until `system_recompile` has produced a staged receipt. This prevents the model from describing a verified source fix as deployed when it has not recompiled or restarted.
- Bound post-recompile report facts to the authenticated wake receipt. Echo still wakes and generates the response, while `reply_request` renders the exact change, previous, candidate, active and gate-manifest hashes plus health, reconciliation and rollback state from runtime-owned data, preventing digit substitution or truncation during generation.
- Normalized the single safe `./` prefix emitted by exact-path discovery before protected trust-root classification. Echo can now pass a discovered `./decent_agent/...` implementation path directly into `codebase_replace`, while repeated prefixes, traversal, absolute paths and `./tests/...` remain fail-closed.
- Made sole legal repair transitions deterministic after a controller rejection. If a stale model action repeats after a protected write, the next iteration is injected as `system_verify`; if it tries to finalize a green explicit deployment request, the next iteration is `system_recompile`. Both still traverse normal parsing, audit, execution and trace, without repeated full-model calls to choose an already-mandated action.

## 2026-08-27 — HIVE/Apis-aligned repair feedback and spiral recovery

- Suppressed the ErnosPlain compiler's expected preliminary linker failure when its emitted C is successfully recovered and patched, matching HIVE/Apis's clean stage-specific test contract.
- Changed `system_verify` failures to lead with an authoritative extracted failure summary before bounded diagnostic context, explicitly separating current evidence from historical rights receipts.
- Ported HIVE/Apis's broader 80–200 character thought-spiral detector and concrete-action recovery instruction instead of cosmetic “vary your phrasing” retries.
- Added sealed regressions proving Test 22 is prioritised over bootstrap noise and non-consecutive reasoning spirals are detected.

## 2026-08-27 — Structurally enforced self-repair workflow

- Promoted the repair sequence from prompt guidance to a controller state machine: matching source-repair requests must call `system_verify([])` first, may diagnose and edit only after the baseline, must re-verify after every successful source write, and cannot call `system_recompile([])` until the sealed gate is green.
- Disabled ad-hoc `run_command` testing inside that workflow so stale binaries and guessed individual test paths cannot substitute for the authoritative current-source suite.
- Restored `decent_agent/run_test.sh` after an interrupted live repair modified it, then added that runner to the operator-sealed trust root and regression manifest.

All notable changes to ErnosDecent. Dates are absolute. The engine ships on
`agent-parity` and is merged to `main` and the public `business` overlay.

## 2026-08-27 — Pre-approval tool-call validation

### Fixed
- The model-facing tool schema now has one terminal contract: tool turns contain only an optional one-line `Thought:` plus line-anchored `Action:` calls, while completed answers are native plain prose. The legacy `reply_request` executor remains compatible with historical/internal turns but is no longer advertised alongside the native-final contract.
- `run_command` now states explicitly that its first element is the complete shell command, not an argv array. Optional elements are reserved exclusively for a working directory and integer timeout.
- Malformed `run_command` layouts are rejected deterministically before user approval, Observer audit, subprocess execution, persistence, or delivery. The next reasoning turn receives the rejected layout, a canonical corrected example, and repeat feedback; any remaining stale batched actions are discarded.

### Verified
- Ernos source checks pass for the ReAct controller, tool registry, and cognitive suite. Cognitive Test 2 passes valid one-string and directory/timeout forms while rejecting the exact split-argv and non-numeric-timeout regressions. The only current suite failure remains the intentionally planted speaker-provenance bug used for manual self-repair testing.

## 2026-08-27 — Authoritative current-source self-repair baseline

### Fixed
- Added `system_verify([])` as the mandatory first and post-change step for self-repair. It rebuilds current source through the complete operator-sealed regression gate, so a stale precompiled test binary cannot produce a false-green baseline and Echo no longer guesses individual tests or shell invocations.
- Failed verification returns the failure-bearing output tail and exact gate-manifest hash, keeping the causal suite failure visible within the next model turn's observation budget. System guidance requires implementation-only diagnosis, repeated current-source verification until green, and `system_recompile` only afterwards.

### Verified
- The tool is approval-gated for sustained compilation, takes no arguments, and is present in both the tool schema and routing guidance as the authoritative recursive-repair path.

## 2026-08-27 — Operator-sealed mandatory self-upgrade regression gate

### Fixed
- `system_recompile` now verifies an operator-held manifest seal before candidate preparation. The sealed manifest covers the native cognitive and host-election tests, isolated Discord/WebUI/visual/TTS/factory/transaction regressions, the regression runner, build and supervisor scripts, rights enforcement, and recompilation control.
- After authenticated candidate health and rights-ledger reconciliation, the replacement node now writes a durable lifecycle wake receipt and autonomously resumes Echo in the originating session. The wake turn receives the exact prior, candidate, active and gate-manifest hashes, publishes a correlated terminal response, survives a process failure before completion, and is delivered once by Discord's persistent side channel with the normal Speak control. It is recorded as a system lifecycle event rather than a fabricated user message.
- Echo cannot write tests or the deployment trust root through `codebase_write`. Canonical-path enforcement blocks absolute and traversal aliases, and a successfully staged upgrade locks every further tool except the final reply.
- `upgrade.sh` verifies the seal before preparation, staging, and activation, records the gate-manifest hash in the immutable transaction receipts, and runs the complete mandatory regression runner before building an isolated candidate. `run_node.sh` independently refuses activation if the trust root changes after staging.
- Test-baseline updates are deliberately operator-only and require a separate manual build/reboot; implementation files remain available for Echo's approved self-repair cycle.

### Verified
- Mandatory gate passes: 24/24 cognitive tests, 2/2 host-election tests, seven isolated Python suites, two WebUI suites, exact staged-factory restoration, source/compiler checks, shell syntax, and diff integrity.
- Transactional self-upgrade regression passes 6/6, including rejection of a changed gate manifest before staging while the live executable remains byte-identical; terminal-delivery regression passes 3/3, including exclusion of ordinary final replies from unsolicited wake delivery.

## 2026-08-27 — Multi-user session identity provenance

### Fixed
- Authenticated platform/account identity is now immutable provenance on every accepted user message. Discord speaker ID, username, global/display name, account type, host match, authorization role, server, channel and thread survive session serialization and compaction transcripts instead of existing only in the current-turn prompt.
- Conversation history renders each original speaker explicitly. Legacy turns without identity metadata are labelled provenance-unavailable and can never inherit the identity of the account speaking now.
- Guest turns advance the shared session chronology so multi-user participation survives semantic compaction, while guest audit output remains unable to write host relationship, project or long-term memories. Guests receive shared recent-session context without host durable-memory sections.

### Verified
- Ernos checks pass for session storage, prompt assembly, continuity, node and both affected suites. Cognitive regression passes 23/23, including actor-provenance serialization round-trip, legacy-turn non-assumption and the guest continuity privacy boundary; GitDec host-election regression passes 2/2.

## 2026-08-27 — Idempotent voice delivery controls

### Fixed
- Each Discord reply now owns one serialized voice-delivery state. The first Speak press synthesizes and uploads once, clicks received while that work is pending are coalesced, the next completed press deletes the uploaded voice message, and the following press uploads the cached WAV without synthesizing it again.
- Each WebUI reply now owns its own TTS state and correlated WebSocket request ID instead of sharing one global pending button. A second press stops and releases the current audio; a third replays the cached URL, and overlapping responses return only to the button that requested them.

### Verified
- Discord concurrency and generate/remove/replay regression passes 2/2. The emitted WebUI JavaScript passes syntax, response-formatting, and TTS single-flight/remove/cached-replay checks. Python compilation passes for the Discord bridge; `ernos check` passes for the WebSocket server.

## 2026-08-27 — Transactional recursive self-upgrade deployment

### Fixed
- `system_recompile` no longer scans successful compiler text for generic words such as `error` or `warning`, no longer overwrites `node` before validation, and no longer launches a background script that kills the wrapper-owned process. It uses the bounded command runtime's real exit status and requires explicit preparation/staging receipts.
- `build.sh` accepts `ERNOS_NODE_OUTPUT` and publishes the compiled executable by atomic rename only after final link and signing succeed. The compiler's preliminary link now runs in an isolated symlink view, preventing it from deleting `./node`; frontend emission compares normalized declaration order so compiler nondeterminism cannot dirty an unchanged `app.js`. Echo's recompile path targets an isolated candidate, while ordinary manual builds retain `./node` as the default.
- `upgrade.sh` is now a process-free transaction manager: complete tests, isolated build, immutable candidate/rollback hashes, protected change binding, activation, outcome, exact rollback, and cleanup are distinct fail-closed states.
- `run_node.sh` remains the sole runtime supervisor. After Echo's reply and continuity state are durable, exit code 75 causes candidate activation; the replacement must pass authenticated `STATUS`, reconcile its exact executable hash inside the rights ledger, and acknowledge commit. Failed health, receipt, or rights reconciliation restores and relaunches the exact pre-upgrade executable.
- Rights applied/failed state and its hash-chained ledger event now commit in one SQLite transaction. A `codebase_write` whose final ledger commit fails restores its exact pre-write state instead of leaving an unattributed mutation.
- `system_recompile` is Observer-audited in both immediate and approval-resume execution paths. Echo's system context now gives the concrete recursive cycle: baseline, one causal change, focused and complete gates, transactional deployment, same-metric measurement, keep/rollback, durable lesson, repeat.

### Verified
- Ernos checks pass for the compiler tool, rights authority, tools, ReAct loop, prompt, and node. Shell syntax passes for the build, upgrade, and supervisor scripts.
- Transaction-state regression passes 5/5: live executable unchanged before activation, successful candidate activation/receipt, exact failed-candidate rollback, build-failure fail-closed behavior, and tamper rejection before activation. Rights suite passes 19/19, including idempotent exact-hash commit and verified rollback reconciliation receipts.
- The actual `upgrade.sh prepare` path completed the 21/21 cognitive suite, host-election suite, and production Darwin arm64 candidate build against the final source. Candidate `f6f85cc…` and rollback `27aaa44…` matched their receipts while the active on-disk executable remained `27aaa44…`; the prepared candidate was then discarded without staging or restarting.

## 2026-08-27 — Trusted interaction identity and per-account relationship memory

### Fixed
- Every Discord turn now carries the authenticated account snowflake, username, global/display names, account type, authorization role, explicit host-account match, server, channel, thread, and message coordinates into the private turn context. Bracket/newline sanitization prevents metadata framing from being broken by profile names.
- The WebUI now identifies itself as an authenticated local operator account while explicitly leaving the physical person's identity unknown. An admin capability no longer causes Echo to assume the speaker is Maria.
- Every prompt contains one authoritative `CURRENT INTERACTION IDENTITY` block before relationship memory. It states Echo's active name/persona, legal-person status inside ErnosDecent, node DID, model and session; the current platform/account/location; and whether that stable account is configured as Maria's. Current-turn identity overrides historical assumptions.
- Durable user knowledge is now scoped by persona plus a hash of `platform|stable_account_id`. Different humans no longer read or overwrite one shared “user” file. Existing persona-scoped relationship knowledge migrates only to the account explicitly configured as the host.
- Discord supports explicit `host_id` and `host_name` configuration. For backward compatibility, installations without `host_id` treat only the first legacy `admin_id` as the host; additional admins remain distinct people.

### Verified
- `ernos check` passes for `node.ep`, `decent_agent/prompt.ep`, `decent_agent/tools.ep`, `decent_agent/test_agent.ep`, and `decent_web/web_server.ep`; Python compilation passes for the Discord bridge.
- Interaction-identity regression passes 2/2; ordered-turn/factory/visual regression remains 22/22; integrated cognitive agent suite passes 21/21, including current-account visibility and relationship-memory isolation.
- The production Darwin arm64 node build completes successfully.

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
## 2026-08-30 — Recursive-improvement recovery and terminal cancellation

### Fixed
- Made registered evaluator execution controller-owned as well as transport-owned: model-authored main blocks are discarded and a deterministic runner invokes every retained top-level `test_*` function, preventing a valid test definition from exiting green without ever running.
- Enforced registered-evaluator action order and causal direction: writes are blocked until the current plan's transport-template receipt exists, and tests that assert current missing, unknown, unregistered, or error states are rejected in favor of desired post-change output and durable effects.
- Made registered-tool evaluator transport controller-owned. `improvement_test_write` now retains model-authored behavioral `test_*` functions but deterministically installs the exact plan-bound authenticated client before linting, preventing misspelled surfaces, altered socket framing, partial response reads, or response-prefix drift from entering frozen evidence.
- Made rejected-plan recovery structural rather than advisory: after a substantive free-form rejection the controller persists a lock and accepts only `improvement_plan_scaffold`; successful structured authoring clears it. Registered self-extension plans must bind their exact public surface to authenticated `AI EVAL_TOOL`, and durable-memory objectives cannot be planned before the current `decent_agent/memory.ep` interface is read.
- Added `improvement_plan_scaffold`, a controller-owned structured plan route for single-surface registered tools. After any rejected free-form plan, Echo supplies only the exact callable and investigated production path; the controller generates the complete objective/findings/surface/files/tests/rollback document from retained evidence and validates it normally.
- Improvement plans now distinguish production implementation paths from controller-owned regression/E2E artifacts. Prompt, tool schema, and gate diagnostics explicitly prohibit inventing or relocating evaluator files in a plan and give the exact recovery: describe desired behavior under Tests, then let `improvement_test_write` own the artifacts.
- A cancelled investigation can now be archived with full provenance and restarted before any plan or implementation bytes exist.
- Stop/cancel now retains the request's original cancellation epoch across selected, default, vision, and Observer provider cascades. An aborted provider call cannot silently start another endpoint.

### Verified
- Added mandatory cognitive assertions for evaluator-path guidance and terminal provider cancellation, plus controller regressions for rejected evaluator paths and pre-plan investigation restart.
