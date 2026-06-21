# Turing Grid & Hebbian Memory User Guide

This guide details the operations of the 3D Turing Grid computational tape and the architecture of the 4-tier Hebbian Memory Subsystem.

---

## 1. 3D Turing Grid Computational Tape

The Turing Grid is a 3-dimensional infinite execution tape utilized by the agent to structure multi-step reasoning, schedule sequential tasks, and execute local commands.

### A. Coordinate Head Position
The head coordinates are tracked as a `(X, Y, Z)` position key (e.g. `0_0_0`). The active cell is defined at the head's current coordinates.

### B. Manual operations
You can interact with the Turing Grid using the manual operations form:
- **Move**: Translates the head position by 1 unit along any axis. Supported directions are:
  - `LEFT` ($X - 1$) and `RIGHT` ($X + 1$)
  - `IN` ($Y - 1$) and `OUT` ($Y + 1$)
  - `DOWN` ($Z - 1$) and `UP` ($Z + 1$)
- **Write**: Records a string value or shell script instruction inside the cell at the active head coordinates.
- **Read**: Retrieves the string value stored at the active head coordinates.
- **Execute**: Reads the string value stored at the active head coordinates and runs it as a local system shell command, printing the execution logs below.

### C. Visualization
The Turing Grid panel features a live visualization grid mapping active cells. Non-empty cells are displayed with their coordinates and stored instruction contents.

---

## 2. Hebbian Cognitive Memory Subsystem

The cognitive core leverages a 4-tier memory hierarchy to manage short-term context, chronological logs, derived lessons, and relational concept associations.

### A. The 4 Tiers of Memory
- **Tier 1: Scratchpad Memory**: Fast, transient key-value storage used to hold temporary variables, task parameters, and active loop counters. It is cleared when a major goal finishes.
- **Tier 2: Lessons Memory**: Concept-oriented, long-term learning details and instructions. These are synthesized during sleep cycles or registered from explicit user corrections, and are semantic-recalled using cosine similarity embeddings.
- **Tier 3: Timeline Memory**: A chronological list of past actions, inputs, and events. It serves as a linear historical log for reasoning convergence checks.
- **Tier 4: Hebbian Synaptic Memory Graph**: A relational graph of concepts (nodes) and connections (edges). Concept nodes co-activated during the agent's ReAct turns strengthen their synapses.

### B. Mathematical Rules of Hebbian Learning
The synaptic graph implements Hebbian reinforcement learning and weight decay using fixed-point integer math:

1. **Fixed-Point Scaling**:
   - Connection weights are represented as integers with a scale factor of $1,000,000$.
   - A weight of $1.0$ is represented as $1,000,000$.
   - The initial co-activation weight of a new synapse starts at $100,000$ (representing $0.1$).

2. **Synaptic Reinforcement**:
   - When two concepts are co-activated, the connection edge weight is reinforced asymptotically using the formula:
     $$\text{increment} = \frac{100,000 \times (1,000,000 - \text{old\_weight})}{1,000,000}$$
     $$\text{new\_weight} = \text{old\_weight} + \text{increment}$$
   - This ensures the weight approaches the theoretical limit of $1.0$ ($1,000,000$) but never overflows.

3. **Permanent Promotion**:
   - If a synapse's weight reaches or exceeds $990,000$ (representing $0.99$), it is promoted to a permanent edge. Permanent edges represent core knowledge and are immune to decay.

4. **Synaptic Decay & Pruning**:
   - Tapping the **Consolidate & Decay Synapses** button triggers a sweep of the graph.
   - Non-permanent edges decay by $5\%$ during each consolidation sweep:
     $$\text{decayed\_weight} = \frac{\text{old\_weight} \times 950,000}{1,000,000}$$
   - If an edge's weight drops below $10,000$ (representing $0.01$), the connection is considered weak and is pruned (deleted) from the graph.

---

## 3. Related agent subsystems (agent-parity)

This guide covers the Turing Grid and the Hebbian memory tiers. The agent also ships, on the gated `agent-parity` branch:

- **Procedural memory** — an adapter version manifest (promote/rollback bookkeeping) plus a fixed-point learning payoff. The full recursive self-improvement loop (SAE interpretability, steering vectors, LoRA training-and-promotion) is **partial**.
- **Observer gate** — split into `observer_rules.ep` / `observer_parser.ep` / `observer_audit.ep`: a fail-closed LLM audit (default verdict BLOCKED) for dangerous tools (`run_command`, `codebase_write`), plus a deterministic moderation classifier.
- **Providers + model registry/router** — provider specs and pure, deterministic model selection across OpenAI-compatible and Hugging Face adapters.
- **Platform bridge** — Discord adapter plus a Telegram/WhatsApp registry, over a node↔bridge RPC channel (`bridge_poll` / `bridge_submit_result`).
- **Tooling** — a 9-tool surface dispatched through a guarded executor.

For the full picture, see `book/notes/system-bible.md` and the `decent_agent/` section of `docs/system_guide_synthesis.md`.
