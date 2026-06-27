# ErnosDecent — Full Implementation Plan

## ErnosDecent: The Decentralised Internet, Written in Ernos

**The architecture's own product builds the exit from the architecture.**

---

## What We Are Building

A complete, 1:1 replacement for every layer of the captured internet. Written entirely in native Ernos (`.ep`). No bridges, no stubs, and no platform-intermediated dependencies. Built from cryptographic primitives upward, compiled to native binaries via Clang, running at native C speed.

One binary. One system. Every layer.

---

## The 1:1 Mapping

Every layer of the contemporary captured internet has an ErnosDecent replacement.

### Transport

| Captured Internet | ErnosDecent | Component |
|------------------|-------------|-----------|
| TCP/IP | UDP with P2P routing / simulated transport | `decent_net/` |
| TLS/SSL | Noise Protocol handshakes + libsodium crypto | `decent_net/noise.ep` |
| DNS root servers | DHT-backed decentralised naming | `decent_name/` |
| BGP routing | DHT + relay mesh | `decent_net/dht.ep`, `decent_net/relay.ep` |
| NAT traversal | UDP hole punching / encrypted relay fallback | `decent_net/relay.ep` |

### Data & Storage

| Captured Internet | ErnosDecent | Component |
|------------------|-------------|-----------|
| Cloud databases | Local SQLite + CRDT synchronization | `decent_store/crdt.ep` |
| Cloud storage | Content-addressed P2P storage (BLAKE3) | `decent_store/content.ep` |
| CDNs | P2P content delivery network | `decent_media/cdn.ep` |

### Identity & Access

| Captured Internet | ErnosDecent | Component |
|------------------|-------------|-----------|
| Email/password accounts | DID:key (keypair is your identity) | `decent_id/did.ep` |
| OAuth/Google Sign-In | Self-sovereign auth (challenge-response) | `decent_id/auth.ep` |
| Capability management | Cryptographically signed capability tokens | `decent_id/auth.ep` |

---

## Build Phases

### Phase 1: Cryptographic Foundation — COMPLETE
**Deliverables**: Key generation, signing, symmetric/asymmetric encryption, password hashing, and derivation.
- `decent_id/keys.ep` — Complete primitive layer using libsodium FFI.
- **Verification**: Verified via `decent_id/test_keys.ep` (16/16 tests passing).

### Phase 2: Identity + Networking Foundation — COMPLETE
**Deliverables**: W3C DID Core, capability authorization, and Noise protocol handshakes.
- `decent_id/did.ep` — Base58btc codec, DID resolution (`did:key`, `did:peer`), and challenge-response authentication.
- `decent_id/auth.ep` — Signed session tokens and capability-based delegation with action checks.
- `decent_net/noise.ep` — Full Noise_XX handshake (X25519 DH + ChaChaPoly + HMAC-SHA256) over UDP.
- **Verification**: Verified via `decent_id/test_did.ep` (14/14 tests) and `decent_id/test_auth.ep` (11/11 tests).

### Phase 3: Peer Discovery — COMPLETE
**Deliverables**: Kademlia DHT routing table and encrypted relay circuits.
- `decent_net/dht.ep` — XOR distance metrics, k-bucket routing table, FIND_NODE/FIND_VALUE/STORE/PING RPCs.
- `decent_net/relay.ep` — Encrypted relay registration, circuit creation, and data forwarding fallback loops.
- **Verification**: Verified via `decent_net/test_dht.ep` (17/17 tests) and `decent_net/test_relay.ep` (15/15 tests).

### Phase 4: Storage — COMPLETE
**Deliverables**: Content-addressed chunk store and eventually-consistent synchronization.
- `decent_store/content.ep` — BLAKE3 chunk store, deduplication, SQLite index, CAR file archiver, Merkle trees.
- `decent_store/crdt.ep` — PN-Counters, LWW-Registers, Observed-Remove Sets, Multi-Value Registers.
- **Verification**: Verified via `decent_store/test_content.ep` (13/13 tests) and `decent_store/test_crdt.ep` (15/15 tests).

### Phase 5: Messaging — COMPLETE
**Deliverables**: E2E encrypted direct messages and multi-party secure channels.
- `decent_msg/message.ep` — Encrypted conversational message store, history query pagination.
- `decent_msg/channel.ep` — Group channels with member addition/removal and encrypted key distribution.
- **Verification**: Verified via `decent_msg/test_message.ep` (13/13 tests) and `decent_msg/test_channel.ep` (10/10 tests).

### Phase 6: Social Publishing — COMPLETE
**Deliverables**: Nostr event engine, ActivityPub inbox delivery, and unified chronological feeds.
- `decent_social/nostr.ep` — Nostr event signing, filters, and subscription queries.
- `decent_social/activitypub.ep` — Actor Person profile generation, activity wrapping (Create, Follow, Accept, Like).
- `decent_social/feed.ep` — Unified aggregator normalising events.
- `decent_social/publish.ep` — Multi-protocol broadcasting.
- **Verification**: Verified via `decent_social/test_social.ep` (8/8 tests).

### Phase 7: Naming & Hosting — COMPLETE
**Deliverables**: DNS caching resolver, `.ernos` domain registrar, and native HTTP hosting.
- `decent_name/resolver.ep` — Caching DNS resolver with record TTL invalidation.
- `decent_name/registry.ep` — Decentralised registrar mapping names to owner DIDs.
- `decent_host/http.ep` — Socket listener parsing HTTP requests and serving responses.
- `decent_host/static.ep` — Static route mapper.
- **Verification**: Verified via `decent_host/test_host.ep` (21/21 assertions).

### Phase 8: Financial Systems — COMPLETE
**Deliverables**: HD wallets, PoS distributed ledger, fungible/NFT assets, constant-product AMM DEX, and smart contract engine.
- `decent_money/wallet.ep` — BIP39 mnemonics, BIP44 HD derivation.
- `decent_money/ledger.ep` — UTXO verification, block mining, PoS election.
- `decent_money/token.ep` — ERC-20 equivalent token standard.
- `decent_money/nft.ep` — ERC-721 equivalent NFT standard with royalties.
- `decent_money/exchange.ep` — Hybrid constant-product AMM and limit order priority orderbook.
- `decent_money/contracts.ep` — Smart contract persistent state, evaluations, rolling back on REVERT.
- **Verification**: Verified via `decent_money/test_money.ep` (6/6 tests).

### Phase 9: Local AI — COMPLETE
**Deliverables**: Local GGUF transformer inference, vector embeddings, and speech-to-text.
- `decent_ai/models.ep` — Model registry with integrity checks.
- `decent_ai/inference.ep` — GGUF v3 parsing, fixed-point attention/generation.
- `decent_ai/embeddings.ep` — Average token representations, cosine similarity.
- `decent_ai/speech.ep` — Feature pooling, vocabulary projections, CTC decoding.
- **Verification**: Verified via `decent_ai/test_ai.ep` (6/6 tests).

### Phase 10: Media & Communication — COMPLETE
**Deliverables**: SDP negotiation, STUN mapping, DTLS/SRTP cryptography, adaptive segmenting, Opus/VP8, and P2P CDN CDN.
- `decent_media/webrtc.ep` — SDP Offer/Answer, STUN Binding, SRTP encryption/decryption.
- `decent_media/stream.ep` — Media segmentation, adaptive bitrate HLS manifests, LRU cache.
- `decent_media/codec.ep` — FFI wrappers and IMA-ADPCM/RLE fallbacks.
- `decent_media/cdn.ep` — Segment swarm distribution over Kademlia DHT.
- **Verification**: Verified via `decent_media/test_media.ep` (7/7 tests).

### Phase 11: Privacy & Search — COMPLETE
**Deliverables**: Anonymity overlays and decentralized crawler and rank engines.
- `decent_anon/onion.ep` — Multi-hop layered onion routing.
- `decent_anon/mixnet.ep` — Traffic mixing and packet timing delays to resist analysis.
- `decent_search/crawl.ep` — Distributed network web crawler.
- `decent_search/rank.ep` — BM25 text relevance and PageRank authority ranking.
- `decent_search/query.ep` — Decentralised query processing and merging.
- **Verification**: Verified via `decent_anon/test_anon_search.ep` (3/3 tests passing).

### Phase 12: Collaborative Resource Pooling (Bandwidth & Compute) — COMPLETE
**Deliverables**: Shared P2P bandwidth proxying, distributed AI inference execution, and secure mesh resource pooling.
- `decent_pool/bandwidth.ep` — Bandwidth rate limits and contribution tracking.
- `decent_pool/compute.ep` — Compute job delegation, worker scheduling, contribution tracking, execution consensus.
- `decent_pool/mesh.ep` — Symbiotic resource mesh integration.
- **Verification**: Verified via `decent_pool/test_pool.ep` (3/3 tests passing).

### Phase 13: Email, Git, and Consensus — COMPLETE
**Deliverables**: SMTP/IMAP protocol hosting, decentralized Git server, and Raft consensus.
- `decent_host/email.ep` — Native SMTP/IMAP server mapping email identities to DIDs.
- `decent_host/git.ep` — Secure P2P git repository host.
- `decent_consensus/raft.ep` — Raft consensus state machine.
- `decent_consensus/state.ep` — Replicated log state replication.
- `decent_consensus/election.ep` — Leader election loops.
- **Verification**: Verified via `decent_consensus/test_consensus.ep` (4/4 integration tests passing).

### Phase 14: Node Daemon & Cross-Platform Packaging — COMPLETE
**Deliverables**: Unified main node daemon executable and target platform configurations.
- `node.ep` — Core daemon coordinating all completed subsystems and network interfaces.
- `decent_cli/decent_cli.ep` — Command line control interface CLI tools.
- `decent_cli/test_cli.ep` — CLI integration test suite.
- **Verification**: Verified via `decent_cli/test_cli.ep` (1/1 test suite passing).

### Phase 15: Sovereign Dashboard App (UI Integration) — COMPLETE
**Deliverables**: Premium glassmorphic Web UI client and daemon HTTP/WebSocket integration server.
- `decent_web/index.html`, `style.css`, `app.js` — Single-Page Application (SPA) dashboard presenting real-time telemetry, local wallet transactions, AMM swap engine, P2P CDN file storage explorer, and streaming AI playground interface.
- `decent_web/web_server.ep` — Native HTTP and WebSocket gateway server serving static assets, REST JSON telemetry endpoints, and streaming GGUF transformer completion tokens.
- **Verification**: Verified via automated HTTP/JSON API requests (1/1 verification suite passing).

### Phase 16: Cognitive Agent Brain (ErnOS Agent) — COMPLETE
**Deliverables**: ReAct decision-making loop, Hebbian memory systems, secure observer execution audits, and cognitive routing.
- `decent_agent/react_loop.ep` — Core agentic ReAct loop managing prompt assembly, tool call parsing (with unescaped quote truncation fallback), and turn orchestration.
- `decent_agent/tools.ep` — Extensible tool executor with 18+ registered tools (filesystem, git, network, and node IPC).
- `decent_agent/memory.ep` — Tiered memory management utilizing a Hebbian association graph for dynamic beliefs and knowledge consolidation.
- `decent_agent/observer.ep` — Independent, fail-closed LLM observer audit pipeline checking for harmful output, prompt injections, and dangerous terminal commands.
- `decent_agent/llm.ep`, `provider_*.ep` — Standardized LLM client abstractions for OpenAI-compatible local APIs and Hugging Face local models.

### Phase 17: Workspace, Changelog, and Discord Transparency — COMPLETE
**Deliverables**: Per-session workspace rotation, SHA-256 code change logging, and real-time Discord transparency streaming.
- `decent_agent/workspace.ep` — Session-isolated workspaces under `config/workspaces/active/` with automatic tar-gzip archival of older workspaces (14-day policy) and cross-session retrieval.
- `decent_agent/changelog.ep` — Automated codebase write logging using SHA-256 file hashing on changes, combined with boot-time git diff auditing.
- `decent_agent/trace.ep` — SQLite-backed tracing of agent execution events across 12 ReAct stages.
- `decent_net/discord_bridge.py` — Bidirectional Discord connector that spawns real-time reasoning trace threads per prompt, schedules self-deletions after 2 minutes, and cleans up expired threads crash-resiliently via SQLite.
- **Verification**: Verified via integration compilation and unit/lint checks (`ernos check` on all 7 affected `.ep` modules and python compiling).

---

## Verification Plan

### Per-Component Testing
- Companion integration tests (`test_*.ep`) must accompany all code.
- Coverage criteria: happy paths, malformed parameters, bounds boundaries, concurrency, and error handling.
- Executed using `ernos test` or compiling/running test binaries natively.

### Cross-Platform Verification
- Compiles via Clang:
  - macOS ARM64 (Apple Silicon)
  - Linux x86_64
  - Linux ARM64
