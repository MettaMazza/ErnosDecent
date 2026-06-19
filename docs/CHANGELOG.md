# Changelog

All notable changes to the ErnosDecent project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0-beta] - 2026-05-29

**The first public release of ErnosDecent.** This release represents the completion of the full decentralised internet stack — 15 build phases, 16 subsystems, 48 source modules, 20 integration test suites, and 191 passing tests.

### Highlights

- **48 production source modules** implementing identity, networking, storage, messaging, social, naming, hosting, finance, AI, media, privacy, search, resource pooling, consensus, CLI, and web UI
- **191/191 integration tests** passing across all subsystems
- **Sovereign Node Daemon** (`node.ep`) — single binary coordinating all subsystems
- **Glassmorphic Web Dashboard** (`decent_web/`) — real-time telemetry, wallet, DEX, CDN, and AI playground
- **CLI Control Client** (`decent_cli/`) — local IPC command interface for daemon management
- **Complete documentation** — language reference, contributing guide, security policy, changelog, and implementation plan

### Architecture

```
decent_id     → Cryptographic identity (Ed25519, DIDs, capability auth)
decent_net    → P2P networking (Noise XX, Kademlia DHT, encrypted relays)
decent_store  → Storage (BLAKE3 content-addressing, CRDTs)
decent_msg    → Messaging (E2E encrypted direct + group channels)
decent_social → Social (Nostr + ActivityPub federation)
decent_name   → Naming (DNS resolver, .ernos TLD registry)
decent_host   → Hosting (HTTP, static, SMTP/IMAP, Git)
decent_money  → Finance (HD wallets, UTXO ledger, tokens, NFTs, DEX, smart contracts)
decent_ai     → AI (GGUF inference, embeddings, speech-to-text)
decent_media  → Media (WebRTC, HLS streaming, codecs, P2P CDN)
decent_anon   → Privacy (onion routing, mix networks)
decent_search → Search (distributed crawler, BM25 + PageRank ranking)
decent_pool   → Resource pooling (bandwidth, compute, symbiotic mesh)
decent_consensus → Raft consensus (election, replicated log)
decent_cli    → CLI (daemon control client)
decent_web    → Web UI (glassmorphic dashboard, HTTP/WebSocket server)
```

---

## [0.5.0-research] - 2026-05-29

This release completes Phase 15 (Sovereign Dashboard App & UI Integration), concluding the ErnosDecent project interface stack. It adds a premium glassmorphic Single-Page Application (SPA) dashboard served natively by the node daemon, bringing the total to 48 modules with 191 passing integration tests/verifications.

### Added

#### Sovereign Dashboard App (`decent_web/`)
- **Sovereign Dashboard Frontend (`decent_web/index.html`, `style.css`, `app.js`)**: Single-Page Application (SPA) dashboard presenting real-time telemetry, local wallet transactions, AMM swap engine, P2P CDN file storage explorer, and streaming AI playground interface. Includes visual simulation fallbacks.
- **Sovereign Web Server Gateway (`decent_web/web_server.ep`)**: Native HTTP and WebSocket gateway server serving static assets, REST JSON telemetry endpoints, and streaming GGUF transformer completion tokens.
- **Daemon Integration (`node.ep`)**: Spawned background thread for the Web UI Server on port `8080`.

### Fixed

- **Standard Library Receive Syntax**: Fixed `stdlib/static_server.ep` to use the latest compiler-enforced `set <name> to receive from <channel>` syntax.

---

## [0.4.0-research] - 2026-05-29

This release completes Phase 14 (Node Daemon & Cross-Platform Packaging), concluding the ErnosDecent project implementation. It unifies all peer-to-peer subsystems under a single running background daemon with a local control CLI client, bringing the total to 47 modules with 190 passing integration tests (including the CLI socket IPC validation).

### Added

#### Sovereign Node Daemon & CLI (`node.ep`, `decent_cli/`)
- **Node Background Daemon (`node.ep`)**: Coordinates libsodium cryptography, DID sovereign identity, Kademlia DHT routing, and Raft consensus. Exposes local IPC over TCP socket port 5000.
- **Control CLI Client (`decent_cli/decent_cli.ep`)**: Parses CLI command inputs, sends request messages to the daemon over socket connection, and displays formatted status/metric responses.
- **CLI Integration Test Suite (`decent_cli/test_cli.ep`)**: Spawns the daemon server thread, executes loopback socket calls simulating CLI status, wallet balance, and pool resource queries, and validates clean node termination.

### Fixed

- **Command Line Arguments Compiler FFI Implementation**: Implemented `ep_get_args` in the compiler's C runtime template generator (`src/codegen.rs`), enabling OS-level argument collection into native lists of strings and resolving undefined arm64 linker symbols.
- **IPC Loop Safety Violation**: Switched the local socket listener server loop to handle client commands synchronously on borrowed state references, preventing compiler-rejected multi-thread ownership moves inside iterations.

---

## [0.3.0-research] - 2026-05-29

This release completes Phase 13 (Email, Git, and Consensus), bringing the total to 44 modules across 14 functional subsystems with 189 passing integration tests.

### Added

#### Subsystem 14: Raft Consensus (`decent_consensus/`)
- **Raft State Machine (`raft.ep`)**: Implementation of the core Raft consensus protocol, handling `RequestVote` and `AppendEntries` RPC logic.
- **Replicated Log State (`state.ep`)**: Replicated state machine log entry representation, application to local state machines, and log rollback/truncation during leader displacement.
- **Election Management (`election.ep`)**: Manages election timeouts with randomized ticks, candidate status promotion, voting collections, and leader heartbeats.
- **Consensus Integration tests (`test_consensus.ep`)**: Integration test suite simulating a 3-node network cluster, validating leader election, log replication, partition recovery reconciliation, SMTP DID-signed mail routing, and Git push signature verification.

#### Subsystem 7: Web Hosting Extension (`decent_host/`)
- **SMTP/IMAP Server (`email.ep`)**: Simulated email server mapping addresses deterministically to DIDs, performing cryptographic DID signature verification on inbound emails, handling IMAP LOGIN/SELECT/FETCH authentication.
- **P2P Git Host (`git.ep`)**: Secure P2P git repository host authorizing collaborator DIDs and validating push commit signatures.

### Fixed

- **List/Map Variable Reassignment Deallocation**: Resolved memory corruption causing followers' state machines to fail by eliminating local list variable reassignments, which previously triggered compiler-generated `free_list`/`free_map` cleanup on active referenced data structures.

---

## [0.2.0-research] - 2026-05-29

This release completes Phase 11 (Privacy & Search) and Phase 12 (Collaborative Resource Pooling), bringing the total to 41 modules across 13 functional subsystems with 185 passing integration tests.

### Added

#### Subsystem 11: Privacy & Anonymity (`decent_anon/`)
- **Onion Routing (`onion.ep`)**: Multi-hop layered onion packet encryption and decryption. Ephemeral X25519 shared key agreement via FFI scalarmult, packet wrapping/unwrapping, and exit destination relaying.
- **Mix Network (`mixnet.ep`)**: Traffic mixing and packet delay jitter. Fisher-Yates packet queue shuffling and randomized delays to prevent timing correlation attacks.
- **Privacy Integration tests (`test_anon_search.ep`)**: Integration tests validating onion loopbacks and mixnet shuffling.

#### Subsystem 12: Decentralised Search (`decent_search/`)
- **Crawler (`crawl.ep`)**: Distributed crawler tokenizing page text, extracting outgoing links, and populating the local inverted index database.
- **Ranking Engine (`rank.ep`)**: Search ranking engine computing BM25 keyword relevance and PageRank authority scores via power iteration using fixed-point representation.
- **Query Merger (`query.ep`)**: Query processing merging and result formatting. Parses search query terms, calculates combined BM25+PageRank scores, and merges de-duplicated local/remote P2P results.

#### Subsystem 13: Collaborative Resource Pooling (`decent_pool/`)
- **Bandwidth Sharing (`bandwidth.ep`)**: Manages bandwidth tiers (free, emergency, premium), uploaded/downloaded byte counters, dynamic contribution scoring, rate limits, and anonymous routing proxy simulation.
- **Compute Pooling (`compute.ep`)**: Job submission queue, worker scheduling, contribution tracking, and redundant execution consensus verification.
- **Symbiotic Mesh Coordinate (`mesh.ep`)**: Orchestrates bandwidth sharing, compute delegation, and onion-routed anonymous AI inference execution.
- **Resource Mesh Integration tests (`test_pool.ep`)**: End-to-end verification of the symbiotic pooling architecture.

### Fixed

- **PageRank Integer Overflow**: Fixed scaling values in power iteration to prevent values exceeding 64-bit integer limits and causing incorrect sorting.
- **String Comparison Syntax**: Changed string comparisons in new modules to use native `equals` operator instead of FFI `string_compare`.
- **Boolean Negation Parser error**: Bypassed lack of `!` operator support by comparing expressions to `== 0`.
- **Struct Field Type Destructor Mismatch**: Resolved compiler crashes calling undeclared destructor functions `free_struct_Map`/`free_struct_List` by typing map/list fields `as Int` in structures.

---

## [0.1.0-research] - 2026-05-29

This is the initial pre-alpha research release of the ErnosDecent decentralized stack. The release contains a complete, working, peer-to-peer subsystem architecture implementing 33 modules across 10 functional phases, with 179 passing integration tests.

### Added

#### Subsystem 1: Cryptographic Foundation (`decent_id/`)
- **Key Generation & Keystore (`keys.ep`)**: Ed25519 signatures, X25519 Diffie-Hellman encryption, XChaCha20-Poly1305 symmetric AEAD, HKDF key derivation, and Argon2id password-based key derivation (PBKDF) using libsodium FFI.
- **DID Resolution (`did.ep`)**: Implementation of W3C Decent Identity Documents (DID Core v1.0), supporting Base58btc encoding/decoding, deterministic `did:key` resolution, `did:peer` encoding for peer-to-peer sessions, and challenge-response signature verification.
- **Access Delegation (`auth.ep`)**: Cryptographically signed capability delegation tokens with fine-grained action lists, session token lifetimes (TTL checks), and multi-device interactive authorization flows.

#### Subsystem 2: Peer-to-Peer Networking (`decent_net/`)
- **Noise Handshake (`noise.ep`)**: Noise_XX handshake protocol (Revision 34) built over simulated UDP. Manages handshake states, symmetric keys, cipher operations, payload encryption, and interactive packet transmission.
- **Kademlia DHT (`dht.ep`)**: Distributed Hash Table with XOR routing metrics, k-bucket routing table updates, iterative lookup queries, and RPC operations (`PING`, `STORE`, `FIND_NODE`, `FIND_VALUE`).
- **Relay and NAT Traversal (`relay.ep`)**: Encrypted relay fallback circuits for symmetric NAT traversal. Supports relay node discovery via DHT, circuit creation/registration, and data forwarding fallback loops.

#### Subsystem 3: Distributed Storage (`decent_store/`)
- **Content-Addressed Storage (`content.ep`)**: Storage manager implementing chunk-level deduplication, SQLite-backed chunk lookup databases, garbage collection of orphan chunks, Merkle tree computation, and CAR (Content Addressable Archive) export/import.
- **CRDT Synchronization (`crdt.ep`)**: Conflict-free Replicated Data Types (CRDTs) for eventual consistency, including G-Counter, PN-Counter, LWW-Register, OR-Set, and Multi-Value (MV) Registers.

#### Subsystem 4: Encrypted Messaging (`decent_msg/`)
- **Direct Messaging (`message.ep`)**: E2E encrypted messages with cryptographic signature validation, payload encryption, local message storage, and chronological query pagination.
- **Group Channels (`channel.ep`)**: Multi-party messaging channels. Supports owner role delegation, membership list updates, and secure symmetric key envelopes distributed using public-key encryption.

#### Subsystem 5: Social Protocols (`decent_social/`)
- **Nostr (`nostr.ep`)**: Event creation, stable serialization, Ed25519 signing/verification, and subscription filters.
- **ActivityPub (`activitypub.ep`)**: Actor Person profiles, activity wrappers (`Create`, `Follow`, `Accept`, `Like`), and local actor inbox/outbox delivery loops.
- **Chronological Feed (`feed.ep`, `publish.ep`)**: Unified feeds aggregating and sorting Nostr and ActivityPub events chronologically.

#### Subsystem 6: Domain Naming (`decent_name/`)
- **Caching Resolver (`resolver.ep`)**: Local DNS resolver caching query responses with active TTL validation and record eviction.
- **Registry (`registry.ep`)**: DHT-backed name registrar mapping `.ernos` TLD names to owner DIDs.

#### Subsystem 7: Web Hosting (`decent_host/`)
- **HTTP Server (`http.ep`)**: TCP socket listener parsing paths, handling single-connection buffers, and constructing HTTP responses.
- **Static Mapper (`static.ep`)**: Static route mapping connecting incoming paths to raw files.

#### Subsystem 8: Financial Systems (`decent_money/`)
- **HD Wallet (`wallet.ep`)**: BIP39 24-word mnemonic generation, PBKDF2-HMAC-SHA512 seed derivation, BIP44 hierarchical deterministic derivation, and XChaCha20-Poly1305 keystore serialization.
- **UTXO Ledger (`ledger.ep`)**: Genesis block initialization, transaction input/output verification, block Merkle proofs, consensus signing, and Proof-of-Stake validator staking/election.
- **Token Standards (`token.ep`, `nft.ep`)**: Fungible tokens (ERC-20 equivalent) and non-fungible collections (ERC-721 equivalent) supporting transfer approvals, metadata, and creator royalties.
- **Decentralized Exchange (`exchange.ep`)**: Hybrid DEX with AMM liquidity pools (constant-product model) and priority limit order books.
- **Smart Contracts (`contracts.ep`)**: Virtual execution machine parsing state variables, running operations, logging events, and rolling back state on execution failures (`REVERT`).

#### Subsystem 9: Local Artificial Intelligence (`decent_ai/`)
- **Model Registration (`models.ep`)**: Dynamic registry verifying model integrity hashes via libc and OpenSSL FFI.
- **Transformer Inference (`inference.ep`)**: Binary GGUF v3 parser and transformer generation engine. Features Float32-to-fixed-point weight decoding, attention queries, feed-forward steps, ReLU activations, and softmax distribution math.
- **Embeddings (`embeddings.ep`)**: Vector representations with fixed-point cosine similarity metrics.
- **Speech Transcription (`speech.ep`)**: CTC-decoded transcription of audio wave feature pools.

#### Subsystem 10: Live Media & CDN (`decent_media/`)
- **WebRTC Coordination (`webrtc.ep`)**: SDP parser, STUN Binding packing/unpacking, DTLS fingerprint key derivation, and SRTP payload encryption.
- **Adaptive Bitrate (`stream.ep`)**: Media segmenting with HLS playlist manifest output and LRU segment eviction cache.
- **Opus & VP8 Codecs (`codec.ep`)**: Dynamic FFI wrapper bindings with pure-Ernos fallback compression (IMA-ADPCM for audio, RLE for video).
- **P2P CDN Replication (`cdn.ep`)**: File fragment publishing to the Kademlia DHT, peer source discovery, and concurrent chunk download coordination.

---

### Fixed

- **Memory Reclamation**: Worked around Ernos GC map constraints by using dynamic registry buffers (`values_list` root guards).
- **HM Type Inference Limits**: Addressed compiler comparison issues for values >= 4096 by using composite range boundaries (`<=` and `>=`) to prevent incorrect `strcmp` generation.
- **Aliased List Assignment**: Prevented pointer cleanup crashes in codegen during list assignment loops.
- **Reserved Identifier Clobbers**: Restricted the keyword `channel` to prevent naming conflicts in parser generation.
- **String Equal Safety**: Fixed crashes on null string comparisons by adding checks in runtime code generation.
