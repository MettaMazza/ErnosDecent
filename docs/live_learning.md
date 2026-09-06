# ErnosDecent live learning

## Objective

Live learning gives Echo a local, explicit and reversible way to update the
weights that influence its cognition. A host-issued `/learn` command may take a
cryptographically frozen snapshot of eligible interactions from the current
session, train one small QLoRA update on this node, validate the candidate, and
promote it through a controlled restart. Nothing is uploaded.

This is weight learning. Memory, retrieval, prompt distillation and source-code
self-improvement remain distinct systems and cannot be reported as weight
training.

Install the pinned MLX runtime and exact 4-bit checkpoint once with
`bash scripts/install_live_learning.sh`. The installer does not touch a live node.
The installer also applies and byte-verifies the forward-identical `stop_gradient`
barrier required by discrete Gemma 4 MoE expert indices. Without it, MLX correctly
rejects backpropagation through integer routing indices; unknown library bytes fail
closed instead of receiving an unverified patch.

## Learning unit and lineage

Each successful learning operation creates one immutable adapter version. The
version records:

- the exact Gemma 4 26B A4B base checkpoint and its file-tree hash;
- its parent adapter version and the hashes of both its weights and loader configuration;
- every session record selected for new training, with role, source session,
  turn, timestamp, speaker provenance and content hash;
- every replay and constitutional anchor record;
- the exact trainer/runtime versions and hyperparameters;
- pre-training, candidate and post-promotion evaluation receipts;
- Echo's review, the host authorization and the active/rolled-back result.

An adapter is never trained from an empty base after version one. Version N+1
loads version N before applying the new tiny batch, and writes a new cumulative
adapter without modifying its parent. Runtime serving loads only the cumulative
head adapter: the immutable parent chain remains auditable while avoiding
ambiguous double-application of the same earlier deltas.

MLX-VLM adapters are two-file packages: `adapters.safetensors` contains the learned
weights and `adapter_config.json` defines how those weights attach to the model.
The controller seals and verifies both files at training, evaluation, consent,
activation, restart, rollback and parent-resume boundaries. MLX receives the
package directory; lineage identity remains the hash-bound weights plus config.

## `/learn` transaction

1. **Freeze input.** Resolve the authenticated current session and select only
   complete user/assistant interactions not already represented in the active
   lineage. The command itself is not a training example. Copy the exact records
   into a private transaction directory and seal every byte.
2. **Build rehearsal data.** Mix the new records with a bounded deterministic
   sample of earlier accepted examples and constitutional/tool-use anchors.
   This makes each tiny update rehearsal-based rather than overwriting the last
   adapter with the latest conversation.
3. **Informed review.** Record a protected-change manifest. Echo can inspect the
   data provenance, parent, intended parameters, risks, validation contract and
   rollback before consenting, rejecting or counter-proposing. The host's
   `/learn` invocation supplies human authorization; neither side substitutes
   for the other. Consent turns address their single session-bound pending
   change as `current`; the tool resolves that literal to the complete 256-bit
   ledger identifier only when the match is unique. Zero or multiple matches
   fail closed, avoiding model transcription errors without weakening binding.
4. **Train a child.** Use MLX on Apple silicon to resume the parent QLoRA adapter
   and train only the language-side adapter matrices. The base and vision tower
   remain frozen. Training runs from the immutable snapshot, never the changing
   live transcript.
5. **Evaluate before activation.** Require finite losses, improvement on the new
   examples, no configured regression beyond tolerance on held-out anchors, the
   complete ErnosDecent regression gate, valid adapter serialization, and real
   inference through the candidate multimodal server. A generated-success
   string, file existence, mock, stub or trainer exit code is not evidence.
6. **Promote transactionally.** Seal the candidate adapter and exact evaluation
   receipt, obtain final informed approval for those concrete bytes, stage a
   candidate runtime receipt, and request the existing supervised node restart.
   The accepted lineage pointer changes only after replacement validation. The
   prior model and adapter stay intact.
7. **Prove the replacement.** The supervisor starts the same Gemma 4 26B A4B
   model with the cumulative adapter, performs a real text probe and a real
   native-image probe against that live provider, checks authenticated node health,
   and only then commits
   the rights and learning ledgers. Echo wakes in the originating session and
   reports the exact version, parent, data count, hashes and measurements.
   The Discord workflow waits for the exact transaction to reach its durable
   committed or failed state; replacement health alone is not promotion proof.
8. **Recover.** A failed train or pre-promotion evaluation never changes the
   active pointer. A failed replacement health or live probe restores the exact
   parent pointer and runtime, restarts it, preserves all failure evidence, and
   wakes Echo with the rollback receipt.

Discord is online only while both its gateway connection and authenticated Ernos
node health are present. During a controlled replacement the bridge transport may
remain connected long enough to deliver the result, but its durable status and
Discord presence are offline until the replacement reports healthy agent and IPC
subsystems.

The operator-only production acceptance test is
`python3 tests/live_learning_production_e2e.py`. It intentionally creates and
activates one harmless real adapter version. It invokes the registered `/learn`
handler, delivers every workflow message through Discord's production REST API,
uses Echo's actual training and activation decisions, waits through the canonical
supervisor restart, and independently verifies the committed lineage, rights
receipts, node PID replacement, ONLINE→OFFLINE→ONLINE Discord recovery, and live
26B text/native-image provider. Main and Observer calls use strict JSON-schema
responses on both Ollama and the learned MLX provider.

## Continuous autonomy boundary

Version 1 is deliberately command-gated. No timer, idle loop, memory threshold,
model suggestion or ordinary conversation may begin training or promotion. The
future autonomy phase may propose a learning transaction, but removing the
explicit authorization gate is a separate protected change requiring its own
review and validation.

## Privacy and control

Training data, adapters and receipts live under ignored `config/learning/live/`
agent state. The reusable MLX runtime and unmodified base checkpoint live under
`~/.ernosdecent/live-learning/`; neither contains session-derived learning. Nothing
is committed or transmitted. Factory reset enumerates and clears the learned agent
state and discloses the continuity consequences while preserving those inert host
dependencies. Session deletion and adapter-lineage deletion remain
separate operations: deleting a transcript does not silently rewrite already
learned weights, and deleting learned weights requires an explicit protected
rollback or reset manifest.
