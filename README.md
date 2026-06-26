<div align="center">

<br/>

# ⬡ ErnosDecent

### The Decentralised Internet — Written in Ernos

<br/>

**A decentralized, peer-to-peer application stack — from cryptographic identity to media streaming — compiled to native binaries via a self-hosting programming language.**

<br/>

[![Version](https://img.shields.io/badge/version-v1.0.0--beta-8B5CF6?style=for-the-badge)](https://github.com/MettaMazza/ErnosDecent/releases)
[![Language](https://img.shields.io/badge/language-Ernos%20(.ep)-A855F7?style=for-the-badge)](https://github.com/MettaMazza/Ernos-Programming-Language)
[![Backend](https://img.shields.io/badge/backend-Clang%20Native-EF4444?style=for-the-badge)]()
[![Subsystems](https://img.shields.io/badge/subsystems-17-10B981?style=for-the-badge)]()
[![License](https://img.shields.io/badge/license-AGPL--3.0-3B82F6?style=for-the-badge)](LICENSE)

---

*ErnosDecent replaces the centralised internet stack — identity, networking, storage, messaging, social publishing, hosting, finance, AI, and media — with a single, auditable, natively compiled codebase.*

*No cloud. No platform. No intermediary.*

<br/>

</div>

---

## What This Is

ErnosDecent is a ground-up reimplementation of the services people depend on every day — identity, messaging, social media, hosting, payments, AI inference, and live media — as a unified peer-to-peer system. Every module is written in [Ernos](https://github.com/MettaMazza/Ernos-Programming-Language), a compiled programming language with plain English syntax that transpiles to C and compiles to native binaries via Clang.

This is not a framework. This is not a wrapper around existing libraries. This is the stack itself, built from cryptographic primitives upward.

### The problem it solves

Every service on the current internet requires you to trust a third party with your data, your identity, and your relationships. ErnosDecent eliminates that requirement. Your keys are yours. Your data stays on your machine. Your connections are direct. Your compute is local.

### Current state

**v1.0.0-beta.** The core architecture is implemented and verified. **17 subsystems** comprise roughly **103 source modules** (~30,300 source code-lines plus ~12,700 test lines). Each subsystem ships its own test suite (**94 test files** in total); the node builds with `bash build.sh` and boots, and the core paths are verified. It is served with a local control CLI client and a premium glassmorphic Web UI dashboard.

---

## Feature Highlights

| You get... | Instead of... |
|-----------|--------------|
| 🔑 **Self-owned identity** — Ed25519 keys, W3C DIDs, capability tokens | Google/Apple sign-in, OAuth |
| 🌐 **Encrypted P2P networking** — Noise XX handshake, Kademlia DHT | AWS, Cloudflare, centralised DNS |
| 💾 **Content-addressed storage** — BLAKE3 hashing, CRDT sync | Google Drive, iCloud, Dropbox |
| 💬 **End-to-end encrypted messaging** — direct and group channels | iMessage, WhatsApp, Telegram |
| 📢 **Federated social publishing** — Nostr + ActivityPub | Twitter/X, Instagram, Facebook |
| 🏠 **Self-hosted services** — HTTP, email, Git, DNS | GitHub, Gmail, GoDaddy |
| 💰 **Native financial system** — HD wallets, UTXO ledger, DEX, smart contracts | Ethereum, Coinbase, PayPal |
| 🤖 **Local AI** — GGUF transformer, embeddings, speech-to-text, **Kokoro text-to-speech** (🔊 local neural voice) | OpenAI, Anthropic, Google Cloud AI |
| 🧠 **Sovereign agent** — ReAct loop with long-horizon tool chaining, a captured per-turn reasoning channel, tiered/Hebbian memory, a fail-closed **and self-auditing** observer (steelmans, won't straw-man or lie), clarifying-question + stop-mid-run controls, tool-tunable behavior, and grounded psychological/argumentation/architectural frameworks | Cloud agent platforms |
| 🗂️ **GitDec** — decentralised in-repo issue/PR tracker over Nostr | GitHub Issues/PRs |
| 📡 **P2P media streaming** — WebRTC, adaptive HLS, codec layer, CDN | YouTube, Twitch, Zoom |
| 🕵️ **Anonymity layer** — onion routing, mix networks | Tor (external), VPNs |
| 🔍 **Decentralised search** — crawler, BM25 + PageRank ranking | Google Search |
| 🤝 **Resource pooling** — bandwidth sharing, compute delegation | AWS Lambda, Cloudflare Workers |
| 🗳️ **Consensus** — Raft leader election, replicated log | Centralised databases |
| 🖥️ **Dashboard UI** — glassmorphic SPA with real-time telemetry | Cloud consoles |

**Every feature runs on your hardware, under your keys, with direct connections to the people you choose.**

---

## Quick Start

### Prerequisites

- [Ernos compiler](https://github.com/MettaMazza/Ernos-Programming-Language) (Rust — `cargo build --release`)
- Clang (C compiler backend)
- libsodium (`brew install libsodium` on macOS, `apt install libsodium-dev` on Linux)

### Build & Run

```bash
# Clone
git clone https://github.com/MettaMazza/ErnosDecent.git
cd ErnosDecent

# Symlink the standard library
ln -s /path/to/Ernos-Programming-Language/stdlib ./stdlib

# Build the node daemon (cross-platform)
bash build.sh

# Launch — starts IPC on port 5000, Web UI on port 8088
# (set ERNOSDECENT_PASSPHRASE to encrypt the node identity at rest)
ERNOSDECENT_PASSPHRASE="choose-a-strong-passphrase" ./node

# Open the dashboard
open http://localhost:8088

# Control the running node from another terminal:
#   ./decent_cli/decent_cli status
#   ./decent_cli/decent_cli pool status
```

> **Local AI (optional):** the agent uses your local LLM if one is running —
> llama.cpp on **8080/8081**, Ollama on 11434, or LM Studio on 1234 (auto-discovered).
> Speech-to-text uses a **whisper.cpp** server (default port **8090**, set via the
> `[ai]` section of `~/.ernosdecent/config.toml`). The Web UI now defaults to **8088**
> so port 8080 is free for llama.cpp.

### Multi-Node Cluster

```bash
# Start the seed node (default ports)
./node &

# Start a second node, bootstrapped to the seed
./node --port 9200 --seed 127.0.0.1:9101 &

# Start a third node
./node --port 9400 --seed 127.0.0.1:9101 &

# Verify cluster formation
echo "STATUS" | nc -w2 127.0.0.1 5000   # Node 1: dht_size >= 1
echo "STATUS" | nc -w2 127.0.0.1 9300   # Node 2: peers:1, dht_size:1
echo "STATUS" | nc -w2 127.0.0.1 9500   # Node 3: peers:1, dht_size:1
```

**Port layout:** `--port BASE` sets P2P=BASE, DHT=BASE+1, Relay=BASE+2, Raft=BASE+3, IPC=BASE+100, Web=BASE+80.

### Run All Tests

```bash
# Unit + integration tests (per-subsystem)
for test in decent_*/test_*.ep; do
    ernos "$test" && "./${test%.ep}" || echo "FAIL: $test"
done

# Live E2E tests (requires running daemon)
bash test_live_e2e.sh

# Multi-node stress tests (starts 3-node cluster)
bash test_multinode_live.sh
```

---

## Architecture
 
ErnosDecent is organised into 17 subsystems, each in its own directory. Every `.ep` file is a self-contained module compiled to a native binary.
 
```
ErnosDecent/
├── decent_id/         Cryptographic identity — keys, DIDs, authentication
├── decent_net/        Peer-to-peer networking — Noise protocol, Kademlia DHT, relays
├── decent_store/      Storage — content-addressed store, CRDTs
├── decent_msg/        Messaging — E2E encrypted direct and group channels
├── decent_social/     Social publishing — Nostr, ActivityPub, unified feeds
├── decent_name/       Naming — decentralised DNS, .ernos TLD registry
├── decent_host/       Hosting — HTTP server, static content, SMTP, Git
├── decent_money/      Finance — HD wallets, UTXO ledger, tokens, NFTs, DEX, smart contracts
├── decent_ai/         AI — GGUF inference, embeddings, speech-to-text, Kokoro text-to-speech
├── decent_agent/      Cognitive Agent — ReAct loop (long-horizon chaining + reasoning channel), broad tool surface, tiered/Hebbian memory, Turing grid, self-auditing observer, clarification/stop controls, tool-tunable behavior, model router, platform bridges
├── decent_media/      Media — WebRTC, adaptive streaming, codecs, P2P CDN
├── decent_anon/       Privacy — onion routing, mixnet traffic analysis resistance
├── decent_search/     Search — distributed crawler, BM25 & PageRank ranking engine, query merge
├── decent_pool/       Resource pooling — bandwidth tiers, compute job queue, symbiotic mesh
├── decent_consensus/  Raft consensus — election loops, replicated log state
├── decent_cli/        Daemon CLI — node control CLI client & integration tests
├── decent_web/        Web UI — glassmorphic dashboard & HTTP/WebSocket server
└── node.ep            Node Daemon — central coordinator
```
 
### Dependency Flow
 
```
┌─────────────────────────────────────────────────────────────┐
│                      decent_web / decent_cli                │
│               Dashboard & CLI Control              │
├─────────────────────────────────────────────────────────────┤
│                        decent_agent                         │
│            Cognitive ReAct Agent & Hebbian Memory           │
├─────────────────────────────────────────────────────────────┤
│                         decent_pool                         │
│             Symbiotic Bandwidth & Compute Pooling           │
├──────────────────────────┬──────────────────────────────────┤
│       decent_anon        │          decent_search           │
│   Onion Routing · Mixnet │      Crawler · Rank · Query      │
├──────────────────────────┴──────────────────────────────────┤
│                       decent_media                          │
│                  WebRTC · HLS · Codecs · CDN                │
├──────────────────────────┬──────────────────────────────────┤
│      decent_ai           │         decent_money             │
│  Inference · Embeddings  │  Wallet · Ledger · DEX · Contracts│
├──────────────────────────┼──────────────────────────────────┤
│      decent_social       │         decent_host              │
│  Nostr · ActivityPub     │    HTTP · Email · Git · DNS      │
├──────────────────────────┤         decent_name              │
│      decent_msg          │    DNS Resolver · Registry       │
│  E2E Messages · Channels │                                  │
├──────────────────────────┴──────────────────────────────────┤
│                    decent_consensus                         │
│             Raft Election · Replicated Log State             │
├─────────────────────────────────────────────────────────────┤
│                       decent_store                          │
│           Content-Addressed Storage · CRDTs                 │
├─────────────────────────────────────────────────────────────┤
│                       decent_net                            │
│          Noise XX Handshake · Kademlia DHT · Relays         │
├─────────────────────────────────────────────────────────────┤
│                       decent_id                             │
│        Libsodium Crypto · DID:key · DID:peer · Auth         │
└─────────────────────────────────────────────────────────────┘
```

---

## Subsystem Detail

### `decent_id/` — Cryptographic Identity

| Module | What it does |
|--------|-------------|
| `keys.ep` | Ed25519 signing, X25519 encryption, XChaCha20-Poly1305 symmetric encryption, HKDF key derivation, Argon2id password-protected keystores. All via libsodium FFI. |
| `did.ep` | W3C DID Core v1.0. Base58btc codec, `did:key` creation/resolution, `did:peer` for private connections, challenge-response authentication. |
| `auth.ep` | Signed TTL-bound session tokens, capability-based delegation with fine-grained action checks, cross-device authorisation flows. |
| `mem.ep` | Raw C heap memory allocator wrappers (`calloc`/`free`/`memset`) for libsodium FFI. |
| `sodium_ffi.ep` | Low-level libsodium FFI function pointer bridge logic. |

**Tests:** ships its own test suite (`test_*.ep`); see "Run All Tests".

---

### `decent_net/` — Peer-to-Peer Networking

| Module | What it does |
|--------|-------------|
| `noise.ep` | Full Noise_XX handshake (Revision 34) over UDP. X25519 DH, ChaChaPoly1305 AEAD, HMAC-SHA256, Noise-spec HKDF, complete state machine. |
| `dht.ep` | Kademlia DHT. XOR distance metrics, k-bucket routing, FIND_NODE, FIND_VALUE, STORE, PING RPCs, iterative closest-node lookup. |
| `relay.ep` | Encrypted relay circuits. Relay registration/discovery via DHT, circuit creation for anonymous routing, data forwarding for symmetric NAT traversal. |
| `transport.ep` | Generic raw TCP/UDP socket creation and socket write/read abstractions. |
| `dht_transport.ep` | DHT socket loop listening for FIND_NODE/STORE/PING query packets. |
| `noise_transport.ep` | Noise XX packet framing, transmission, and decryption loop. |
| `relay_transport.ep` | Encrypted relay data framing and multi-hop transport circuits. |
| `security.ep` | Core security gate enforcing IP rate limits, ban timers, and query argument validators. |

**Tests:** ships its own test suite (`test_*.ep`); see "Run All Tests".

---

### `decent_store/` — Storage

| Module | What it does |
|--------|-------------|
| `content.ep` | Content-addressed storage engine. BLAKE3 hashing, deduplication, SQLite-backed chunk storage, garbage collection, CAR archive export/import, Merkle tree generation. |
| `crdt.ep` | Conflict-free Replicated Data Types. G-Counter, PN-Counter, LWW-Register, OR-Set, MV-Register — deterministic merging for eventual consistency. |

**Tests:** ships its own test suite (`test_*.ep`); see "Run All Tests".

---

### `decent_msg/` — Messaging

| Module | What it does |
|--------|-------------|
| `message.ep` | E2E encrypted direct messaging. Message signing/verification, body encryption/decryption, conversation histories with unread tracking and pagination. |
| `channel.ep` | Group messaging with secure membership. Channel creation, member management, group symmetric encryption, key distribution envelopes. |

**Tests:** ships its own test suite (`test_*.ep`); see "Run All Tests".

---

### `decent_social/` — Social Publishing

| Module | What it does |
|--------|-------------|
| `nostr.ep` | Nostr event creation, stable serialisation, Ed25519 signing/verification, subscription filters. |
| `activitypub.ep` | ActivityPub actor profiles, activity wrappers (Create, Follow, Accept, Like), inbox/outbox delivery. |
| `feed.ep` | Unified feed aggregation normalising Nostr events and ActivityPub activities into chronological order. |
| `publish.ep` | Multi-protocol broadcasting to target feeds with publisher follow flows. |

**Tests:** ships its own test suite (`test_*.ep`); see "Run All Tests".

---

### `decent_name/` — Naming

| Module | What it does |
|--------|-------------|
| `resolver.ep` | Local DNS caching resolver with TTL validation and record eviction. |
| `registry.ep` | Decentralised `.ernos` TLD name registrar mapping human-readable names to owner DIDs. |

---

### `decent_host/` — Hosting

| Module | What it does |
|--------|-------------|
| `http.ep` | Native HTTP server. Request path parsing, response building, single-connection socket handling. |
| `static.ep` | Static route mapper for serving content by path. |
| `email.ep` | SMTP/IMAP protocol hosting. Maps email addresses to DIDs and cryptographically verifies signatures. |
| `git.ep` | Secure P2P git repository hosting. Authorizes collaborator roles and verifies commit signatures. |

**Tests:** ships its own test suite (`test_*.ep`); see "Run All Tests".

---

### `decent_money/` — Financial Systems

| Module | What it does |
|--------|-------------|
| `wallet.ep` | BIP39/BIP44 HD wallet. 24-word mnemonic generation, PBKDF2-HMAC-SHA512 seed derivation, HD keypair derivation, encrypted keystore. |
| `ledger.ep` | UTXO-based distributed ledger. Genesis blocks, transaction validation, Merkle trees, block consensus signing, Proof-of-Stake validator election. |
| `token.ep` | Fungible token standard (ERC-20 equivalent). Metadata, minting, balances, approvals, allowance transfers. |
| `nft.ep` | Non-fungible token standard (ERC-721 equivalent). Collections, minting, ownership, transfers, royalty distribution. |
| `exchange.ep` | Hybrid DEX. Constant-product AMM liquidity pools and price-time priority orderbook matching. |
| `contracts.ep` | Smart contract execution engine. Persistent state, variable evaluation, event logging, instruction execution, state rollback on REVERT. |

**Tests:** ships its own test suite (`test_*.ep`); see "Run All Tests".

---

### `decent_ai/` — Local AI

| Module | What it does |
|--------|-------------|
| `models.ep` | Model registry with SHA-256 hash verification via libc/OpenSSL FFI. |
| `inference.ep` | GGUF v3 binary parser and fixed-point transformer executor. Token-by-token text generation with attention, feedforward networks, ReLU, and softmax. |
| `embeddings.ep` | Vector embedding generator with fixed-point cosine similarity. |
| `speech.ep` | Speech-to-text transcription (whisper.cpp backend, with a fixed-point reference path). |
| `tts.ep` | Kokoro text-to-speech via FFI: text → IPA phonemes (libespeak-ng) → vocab tokens → onnxruntime → 24 kHz audio → PCM16 WAV. Delivered to the Web UI 🔊 button and Discord. |

Speech-to-text and Kokoro text-to-speech both ship; TTS was verified end-to-end (Web UI 🔊 confirmed).

---

### `decent_agent/` — Cognitive Agent Architecture

| Module | What it does |
|--------|-------------|
| `prompt.ep` | Assembles prompt context, combining core identity instructions, task details, and relevant memory tiers. |
| `react_loop.ep` | ReAct reasoning coordinator. Manages reasoning steps, model dispatch, and observation feedback. |
| `memory.ep` | Tiered cognitive memory: scratchpad, lessons (semantic recall), timeline, knowledge graph, with a consolidation/"sleep" sweep. |
| `tools.ep` | Schema registry and guarded execution dispatcher for the 9-tool surface (DHT, Name, Wallet, Turing Grid, Command, Files, etc.). |
| `turing_grid.ep` | 3D Turing Grid machine tape workspace. Tracks active HEAD position across (X, Y, Z) space and reads/writes cell states. |
| `observer_rules.ep` / `observer_parser.ep` / `observer_audit.ep` | Safety supervisor, split into rule data, parser, and a fail-closed LLM audit gate (default verdict BLOCKED) for dangerous tools; a deterministic moderation classifier backs the moderation tool. |
| providers / model registry & router | Provider specs (OpenAI-compatible + Hugging Face) and pure, deterministic model selection. |
| platform bridge | Adapters for Discord, Telegram, WhatsApp; node↔bridge RPC (`bridge_poll` / `bridge_submit_result`). |

Agent-parity Phases 1–6 are done and gated; the full recursive self-improvement loop (SAE/steering/LoRA promotion) is **partial**.

---

### `decent_media/` — Media & Communication

| Module | What it does |
|--------|-------------|
| `webrtc.ep` | SDP parsing/serialisation, STUN binding request/response, DTLS fingerprint derivation, SRTP encryption/decryption. |
| `stream.ep` | Adaptive bitrate segmenter with HLS manifest generation and LRU segment cache. |
| `codec.ep` | Opus/VP8 FFI wrappers with native IMA-ADPCM audio and RLE video fallbacks. |
| `cdn.ep` | P2P content delivery. DHT-based piece announcement, peer discovery, concurrent chunk download with hash verification. |

**Tests:** ships its own test suite (`test_*.ep`); see "Run All Tests".

---

### `decent_anon/` — Privacy & Anonymity

| Module | What it does |
|--------|-------------|
| `onion.ep` | Multi-hop layered onion routing. Ephemeral X25519 shared key agreement, packet wrapping/unwrapping, and exit destination relaying. |
| `mixnet.ep` | Traffic mixing and packet delay jitter. Fisher-Yates packet queue shuffling and randomized delays to prevent timing correlation attacks. |

**Tests:** ships its own test suite (`test_*.ep`); see "Run All Tests".

---

### `decent_search/` — Decentralised Search

| Module | What it does |
|--------|-------------|
| `crawl.ep` | Distributed network crawler. Tokenizes page HTML/text, extracts outgoing links, and populates the local inverted index database. |
| `rank.ep` | Search ranking engine. Computes BM25 keyword relevance and PageRank authority scores via power iteration using fixed-point math. |
| `query.ep` | Query merging and result formatting. Parses search query terms, calculates combined BM25+PageRank scores, and merges de-duplicated local/remote P2P results. |

**Tests:** ships its own test suite (`test_*.ep`); see "Run All Tests".

---

### `decent_pool/` — Collaborative Resource Pooling

| Module | What it does |
|--------|-------------|
| `bandwidth.ep` | Bandwidth sharing. Manages bandwidth tiers (free, emergency, premium), uploaded/downloaded byte counters, dynamic contribution scoring, rate limits, and anonymous routing proxy simulation. |
| `compute.ep` | Compute pooling manager. Job submission queue, worker scheduling, contribution tracking, and redundant execution consensus verification. |
| `mesh.ep` | Symbiotic mesh coordinate layer. Orchestrates bandwidth sharing, compute delegation, and onion-routed anonymous AI inference execution. |

**Tests:** ships its own test suite (`test_*.ep`); see "Run All Tests".

---

### `decent_consensus/` — Raft Consensus

| Module | What it does |
|--------|-------------|
| `raft.ep` | Raft state machine handling RequestVote and AppendEntries RPCs. |
| `state.ep` | Replicated log state. Features log entry serialization, state machine execution, and log rollbacks on leadership change. |
| `election.ep` | Election loops with randomized timeouts, heartbeats, and candidate transitions. |
| `raft_transport.ep` | TCP socket handling, connection pooling, and log updates delivery for Raft cluster peers. |

**Tests:** ships its own test suite (`test_*.ep`); see "Run All Tests".

---

### `decent_cli/`, `decent_web/` & `node.ep` — Node Daemon, Web UI & CLI Control

| Module | What it does |
|--------|-------------|
| `node.ep` | Node Daemon coordinating all subsystems, exposing port 5000 IPC and port 8088 Web Server. |
| `decent_cli/decent_cli.ep` | Command-line control client querying the daemon via local socket IPC. |
| `decent_cli/test_cli.ep` | Integration test spawning the daemon and running command queries. |
| `decent_web/index.html` | Premium glassmorphic Single-Page Application (SPA) dashboard layout. |
| `decent_web/style.css` | Obsidian and neon-accented responsive stylesheet. |
| `decent_web/app.js` | WebSocket client logic connecting all UI panels to live daemon data. |
| `decent_web/web_server.ep` | Native HTTP & WebSocket gateway serving Web UI assets, REST JSON APIs, and WS handlers for DHT/Name/Wallet/AI/Messaging. |

**Tests:** ships its own test suite (`test_*.ep`); see "Run All Tests".

---

### Root-Level Coordination Modules

These root-level `.ep` libraries provide base infrastructure shared by all components:

| Module | What it does |
|--------|-------------|
| `config.ep` | Configuration parser loading seeds, ports, and node options from `config.toml`. |
| `health.ep` | Automated sanity checking routing queries through the DHT and Raft consensus engines to test node health. |
| `logging.ep` | Thread-safe logging engine that writes formatted console logs to `ernosdecent.log`. |
| `platform.ep` | Cross-platform utilities for local folder creation and path mapping. |
| `protocol_server.ep` | Daemon-spawning protocol socket listener orchestrating DHT and Relay servers. |
| `storage.ep` | SQLite client opening `node.db` and validating consensus, transaction, and name registry schemas. |

---

## The Language

ErnosDecent is written in [Ernos](https://github.com/MettaMazza/Ernos-Programming-Language) — a compiled, statically-typed programming language with plain English syntax. Ernos is self-hosting: the compiler is written in Ernos.

```ernos
define greet with name as Str returning Int:
    display f"Hello, {name}!"
    return 0

define main:
    greet("world")
    return 0
```

**Compilation pipeline:** `.ep` source → Ernos compiler → C → Clang → native binary.

Key features:
- **Hindley-Milner type inference** with optional explicit annotations
- **Ownership and move semantics** for memory safety
- **Built-in concurrency** via channels and `spawn`
- **FFI interop** via `ep_dlopen`/`ep_dlsym` for C library access
- **23 standard library modules** and **29 FFI bridge libraries**

See [ERNOS_REFERENCE.md](docs/ERNOS_REFERENCE.md) for the full language specification.

---

## Project Statistics

| Metric | Value |
|--------|-------|
| Subsystems | 17 |
| Source modules | ~103 |
| Source lines (non-test) | ~30,300 |
| Test files | 94 |
| Test lines | ~12,700 |
| Test coverage | each subsystem ships its own suite; node builds and boots, core paths verified |
| External dependencies | libsodium (plus optional FFI: libespeak-ng, onnxruntime, libopus, libvpx, libsrtp2, whisper.cpp) |
| Target platforms | macOS (ARM64, x86_64) · Linux (x86_64, aarch64) · Windows via WSL2 (runs the Linux build) |

---

## Roadmap

v1.0.0-beta is the first public release. The architecture is proven and verified. What comes next:

- [x] **Node Daemon** — unified coordinator for all subsystems
- [x] **Web Dashboard** — glassmorphic SPA with real-time telemetry
- [x] **CLI Control Client** — local IPC command interface
- [x] **Raft Consensus** — cluster coordination with leader election
- [x] **Onion Routing** — multi-hop anonymity with mix networks
- [x] **Distributed Search** — crawl, rank, and query the decentralised web
- [x] **Resource Pooling** — bandwidth sharing, compute delegation, symbiotic mesh
- [x] **Email & Git Hosting** — SMTP/IMAP and Git over the P2P layer
- [x] **Multi-Node Bootstrap** — CLI `--seed`/`--port`, DHT discovery, Raft peer sync
- [x] **Real UTXO Transfers** — Ed25519-signed transactions, overdraft protection
- [x] **DHT Key-Value Store** — store/get via IPC and Web UI
- [x] **Decentralised Name Registry** — register/resolve via IPC and Web UI
- [x] **Cross-Platform Build** — `build.sh` auto-detects macOS/Linux, Homebrew/system paths
- [x] **Live E2E Test Suite** — 100+ assertions covering all user-facing features
- [x] **Multi-Node Stress Tests** — 3-node cluster formation, failure recovery, concurrent ops
- [ ] **QUIC Transport** — production UDP transport replacing simulated connections
- [ ] **NAT Traversal** — STUN/TURN integration for direct peer connections
- [ ] **Double Ratchet** — Signal-protocol-grade forward secrecy for messaging
- [x] **Windows (via WSL2)** — runs the Linux build unchanged inside WSL2 Ubuntu
- [ ] **Native Windows** — the C runtime has `_WIN32` guards (threads/sockets/dlopen/dirent) and
  libsodium `.dll` loading; remaining work (home-dir via `%USERPROFILE%`, Windows CSPRNG, Winsock
  startup) lives in the ErnosPlain compiler's emitted runtime and needs a Windows box/CI to verify
- [ ] **Mobile Clients** — iOS and Android companion apps
- [ ] **Plugin System** — third-party module loading

---

## Philosophy

ErnosDecent is not built to compete with existing platforms. It is built to make them unnecessary.

The current internet requires you to rent your identity from a corporation, store your data on someone else's computer, route your messages through someone else's server, and pay someone else for the privilege of being surveilled. This is not a technical limitation. It is an architectural choice made by the people who built the platforms.

ErnosDecent makes a different architectural choice: **everything runs on your hardware, under your keys, with direct connections to the people you choose.** No server you don't control. No key you don't hold. No intermediary you didn't invite.

The language it's written in — Ernos — exists because the tools should be auditable by the people who use them. Plain English syntax is not a gimmick. It is a design decision: the code should be readable by anyone who cares enough to look.

---

## Documentation

For guides on how to use and understand the ErnosDecent system, refer to:
- [GitDec Simple User Guide](docs/gitdec_user_guide.md) — A friendly, clear guide on how to host and collaborate on repositories using GitDec.
- [System Guide Synthesis](docs/system_guide_synthesis.md) — The technical subsystem documentation covering architecture, schemas, and APIs.
- [Ernos Reference Manual](docs/ERNOS_REFERENCE.md) — The official reference manual for the Ernos programming language syntax and standard library.

---

## Contributing

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for development guidelines, coding standards, and how to submit changes.

See [SECURITY.md](SECURITY.md) for reporting security vulnerabilities.

---

## License

ErnosDecent is licensed under the [GNU Affero General Public License v3.0](LICENSE). This means:

- You can use, modify, and distribute this software freely
- If you modify it and run it as a network service, you must release your modifications
- All derivative works must remain open source under the same license

---

## Author

**Maria Smith** — Scotland, 2026.

Built in operational symbiosis with AI. Named openly.

---

<div align="center">

<br/>

*The architecture's own product builds the exit from the architecture.*

<br/>

</div>
