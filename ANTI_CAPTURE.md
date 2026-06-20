# ErnosDecent Business Edition — Anti-Capture Design

## Why this document exists

The Business edition is meant to be *adopted*: a company runs its own ErnosDecent node to
escape cloud bills, and in doing so its node strengthens the public mesh. That adoption creates a
predictable risk — the **capture-vector**. The moment the edition saves a company enough money to
matter, the corporate instinct is to *enclose* it: fork it, strip the mesh, and wrap the
efficiency in a proprietary, centralised silo.

This document records the architectural reason that enclosure is **self-defeating**, so the
benefit cannot be carried off the mesh.

## The thesis: the utility exists *because of* decentralisation

The savings are not features you can extract. They are **emergent properties of mesh
participation**:

| Cost-saving | Where the saving actually comes from | What enclosure costs you |
|---|---|---|
| Free/cheap AI inference | The model router can federate to mesh peers' compute (`decent_agent/model_registry.ep`); a node draws on the shared pool | A private silo must buy its own GPUs or pay a cloud API — the bill returns |
| Free/cheap storage | Content-addressed + deduplicated + replicated across the mesh (`decent_store/`, BLAKE3 + CRDT) | A centralised fork must pay for its own object storage + replication |
| Free/cheap bandwidth & reach | P2P transport + relays carry traffic (`decent_net/`) | A silo must pay for egress, CDN, and load balancers |
| Resilience / availability | Redundancy is the mesh's, not any one deployment's | A single private node is a single point of failure again |
| Identity & messaging | DID + P2P + relay — the network *is* the directory (`decent_id/`, `decent_msg/`) | A centralised identity service is another system to run and secure |

Strip the decentralised core and you have an empty local box with none of the shared resources —
i.e. you have rebuilt the centralised cost structure you were trying to escape. **The savings
only exist while you are on the mesh.**

## Reinforcing layers

1. **Licence — AGPLv3 (already in `LICENSE`).** It closes the SaaS loophole: running a *modified*
   version as a network service obliges you to publish the modifications. An enclosed fork either
   stays open and interoperable (contributing back), or it is in licence violation. Reciprocity is
   legally baked in.

2. **Thin overlay, not a code fork.** The Business edition differs from the standard node only in
   `config/business/prompts.json`, `config/business/agent_persona.txt`, and branding — selected by
   `config/edition.json` via `decent_agent/edition.ep`. There is **no separate "lite/centralised"
   code path** to capture, and **no configuration flag that disables P2P/DHT/relay**. The edition
   is cosmetic; a Business node is a full mesh node. (Enforced by `decent_agent/test_edition.ep`:
   the resolver only ever returns prompt/persona asset paths.)

3. **Passive contribution by default.** Simply running the node relays traffic, stores DHT/content
   shards, and participates in BFT validation. Adoption-for-savings inadvertently grows the
   commons.

## The honest caveat

Licence + economics **deter and disincentivise** enclosure; they do not make it physically
impossible. A determined actor can always run a private, non-compliant fork. The durable defence
is not a lock — it is that **enclosure destroys the very savings that motivated it**, and that
**AGPL makes any networked modification reciprocal**. We claim deterrence and self-defeat, not
"cannot." If a future feature delivers a saving that survives enclosure (i.e. a saving *not*
derived from the mesh), that is a real capture-vector and should be redesigned so the saving is
mesh-coupled — or documented plainly as an exception.
