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

*ErnosDecent is a local-first peer-to-peer application stack covering identity, networking, storage, messaging, social publishing, hosting, finance, AI, and media.*

*Implemented behavior and interoperability boundaries are recorded in [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md).*

<br/>

</div>

---

## What This Is

ErnosDecent is a ground-up reimplementation of the services people depend on every day — identity, messaging, social media, hosting, payments, AI inference, and live media — as a unified peer-to-peer system. Every module is written in [Ernos](https://github.com/MettaMazza/Ernos-Programming-Language), a compiled programming language with plain English syntax that transpiles to C and compiles to native binaries via Clang.

The node is written in Ernos and links established native libraries for cryptography, persistence, Nostr signatures, and optional media/AI backends. The dependency list is explicit below.

### The problem it solves

ErnosDecent provides locally controlled keys and storage. Some configured features use peers or remote model providers; the node does not claim that every connection or computation is local.

### Current state

**v1.0.0-beta.** The repository contains **17 subsystem directories**, **117 non-test Ernos modules**, and **105 Ernos test files**. Verification is evidence-based and changes with the code; see the checked results and release gate in [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md). The node provides a local authenticated CLI and Web dashboard.

> **Public bootstrap is pre-launch (last verified 19 July 2026).** The operated node
> is live and TCP `9100`/`9101` are externally reachable, but stable DDNS and public
> forwarding for `9102`–`9104` are deferred. No automatic public default seed is
> shipped yet, so a fresh installation does not auto-join the public mesh. Until the
> launch gate is completed, operators must provide an explicit `--seed host:9101` or
> use a previously verified cached peer. This beta does not claim public-mesh availability.

---

## Feature Highlights

| You get... | Instead of... |
|-----------|--------------|
| 🔑 **Self-owned identity** — Ed25519 keys, W3C DIDs, capability tokens | Google/Apple sign-in, OAuth |
| 🌐 **Encrypted P2P networking** — Noise XX handshake, Kademlia DHT | AWS, Cloudflare, centralised DNS |
| 💾 **Content-addressed storage** — SHA-256 hashing, SQLite persistence, CRDT structures | Local application storage |
| 💬 **End-to-end encrypted messaging** — direct and group channels | iMessage, WhatsApp, Telegram |
| 📢 **Social publishing primitives** — NIP-01 events, ActivityPub-shaped activities, unified feeds | Local and peer social data |
| 🏠 **Self-hosted services** — HTTP, email, Git, DNS | GitHub, Gmail, GoDaddy |
| 💰 **Native financial system** — HD wallets, UTXO ledger, DEX, smart contracts | Ethereum, Coinbase, PayPal |
| 🤖 **Local AI** — GGUF transformer, embeddings, speech-to-text, **Kokoro text-to-speech** (🔊 local neural voice), **FLUX image generation + vision** (the agent generates an image locally, looks at it, and describes it) | OpenAI, Anthropic, Google Cloud AI, Midjourney |
| 🧠 **Sovereign agent** — ReAct loop with **multi-tool batching** (many tools per model call) and long-horizon chaining, a **71-tool surface**, a captured per-turn reasoning channel with **full untruncated transparency**, tiered/Hebbian memory + per-session RAG, sessions with per-session guidance, workspace project linking, a fail-closed **and self-auditing** observer (steelmans, won't straw-man or lie), clarifying-question + stop-mid-run controls, a self-owned editable prompt, sub-agent delegation/swarms, and grounded psychological/argumentation/architectural frameworks | Cloud agent platforms |
| 🗂️ **GitDec** — decentralised in-repo issue/PR tracker over Nostr | GitHub Issues/PRs |
| 📡 **P2P media primitives** — SDP/STUN/SRTP structures, adaptive HLS, codecs, CDN | Application media transport |
| 🕵️ **Anonymity layer** — onion routing, mix networks | Tor (external), VPNs |
| 🔍 **Decentralised search** — crawler, BM25 + PageRank ranking | Google Search |
| 🤝 **Resource pooling** — bandwidth sharing, compute delegation | AWS Lambda, Cloudflare Workers |
| 🗳️ **Consensus** — Raft leader election, replicated log | Centralised databases |
| 🖥️ **Dashboard UI** — glassmorphic SPA with real-time telemetry | Cloud consoles |

Local features run under the node operator's control. Optional remote providers and peer connections are reported as such.

---

## Quick Start

### Prerequisites

- [Ernos compiler](https://github.com/MettaMazza/Ernos-Programming-Language) (Rust — `cargo build --release`)
- Clang (C compiler backend)
- libsodium (`brew install libsodium` on macOS, `apt install libsodium-dev` on Linux)
- libsrtp2 (`brew install libsrtp` on macOS, `apt install libsrtp2-dev` on Linux)
- OpenSSL and SQLite development libraries
- libsecp256k1 (`brew install secp256k1` on macOS, `apt install libsecp256k1-dev` on Linux)
- stable-diffusion.cpp shared library for the required image runtime; `build.sh` validates its presence

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

# Read the per-installation password generated before the Web listener starts
tr -d '\r\n' < ~/.ernosdecent/web-password; printf '\n'

# Control the running node from another terminal:
#   ./decent_cli/decent_cli status
#   ./decent_cli/decent_cli pool status
```

> **Local AI (optional):** the agent uses your local LLM if one is running —
> llama.cpp on **8080/8081**, Ollama on 11434, or LM Studio on 1234 (auto-discovered;
> default model **gemma-4-31b** via the parallel llama.cpp server on **:8080**, with
> Ollama and LM Studio as fallbacks). `run_node.sh` additionally serves the same
> gemma-4-31b weights WITH their vision projector on **:8091** (Ollama's tag ships
> without it) so the agent can see the images it generates. Speech-to-text uses a
> **whisper.cpp** server (default port **8090**, set via the `[ai]` section of
> `~/.ernosdecent/config.toml`). Image generation loads FLUX/SD weights configured in
> `config/image.json` through libstable-diffusion (`~/.ernosdecent/lib/`). The Web UI
> defaults to **8088** so port 8080 is free for llama.cpp. Prefer `./run_node.sh` over
> `./node` — it persists logs to `~/.ernosdecent/node.log` and starts the vision server.

### Multi-Node Cluster

**Pre-launch notice:** automatic public bootstrap is not active yet. ErnosDecent does
not ship an unverifiable external seed. The operated bootstrap node
must have `network.is_static_host = 1`, a stable `network.public_host` DNS name, and a
verified public endpoint before that name is added to the shipped default-seed list.
Until then, every additional node must receive an explicit seed or have a previously
verified peer in `~/.ernosdecent/peers.txt`. A static host never dials the operated
default aliases that represent itself, but may still join an explicit or cached peer.

Expose TCP `9101` for DHT bootstrap. Full participation also requires TCP `9100`
(encrypted P2P), `9102` (relay registration), `9103` (Raft), and `9104` (compute).
Keep IPC `5000` and Web `8088` loopback-only unless a separate authenticated reverse
proxy and access policy are deliberately configured.

```bash
# Start the operated seed node (default ports; --host applies to this launch)
./run_node.sh --host

# Start a second node, bootstrapped to the seed
./node --port 9200 --seed 127.0.0.1:9101 &

# Start a third node
./node --port 9400 --seed 127.0.0.1:9101 &

# Verify cluster formation
{ printf 'AUTH '; tr -d '\r\n' < ~/.ernosdecent/ipc-token; printf ' STATUS'; } | nc -w2 127.0.0.1 5000
{ printf 'AUTH '; tr -d '\r\n' < ~/.ernosdecent/ipc-token; printf ' STATUS'; } | nc -w2 127.0.0.1 9300
{ printf 'AUTH '; tr -d '\r\n' < ~/.ernosdecent/ipc-token; printf ' STATUS'; } | nc -w2 127.0.0.1 9500
```

**Port layout:** `--port BASE` sets P2P=BASE, DHT=BASE+1, Relay=BASE+2, Raft=BASE+3, IPC=BASE+100, Web=BASE+80.

### Run All Tests

```bash
# Rebuild, check every native-target .ep file, compile and run the checked
# subsystem/integration matrix, run the cognitive-agent suite, exercise both
# additive C runtimes, validate shell syntax, and reject whitespace errors.
bash scripts/release_check.sh

# Live E2E tests (requires a running default-port daemon and uses its 0600 IPC token)
bash test_live_e2e.sh

# Multi-node and stress harnesses use disposable state, start only their own
# nodes, refuse occupied ports, and clean up the processes they own.
bash test_multinode_live.sh
bash test_stress_live.sh
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
├── decent_agent/      Cognitive Agent — ReAct loop (multi-tool batching + long-horizon chaining + reasoning channel), 71-tool surface, sessions, workspace linking, tiered/Hebbian memory + RAG, image gen + vision, Turing grid, self-auditing observer, access/awareness gates, education tutor, self-owned prompt, model router, platform bridges
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
| `content.ep` | SHA-256 content-addressed storage, deduplication, SQLite-backed chunk storage, chunking, and Merkle tree generation. |
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
| `nostr.ep` | NIP-01 canonical event hashing, BIP-340 secp256k1 signing/verification, WebSocket relay messages, and subscription filters. Plain `ws` is implemented; `wss` is not. |
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
| `email.ep` | Documented SMTP/IMAP command subsets, DID-backed address routing, and signature verification. It is not a complete SMTP/IMAP implementation. |
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

Speech-to-text and Kokoro text-to-speech both ship; TTS was verified end-to-end (Web UI 🔊 confirmed). Image generation + vision live in `decent_agent/` (`image_gen.ep` + `llm.ep query_vision`) — see the agent section below.

---

### `decent_agent/` — Cognitive Agent Architecture

| Module | What it does |
|--------|-------------|
| `react_loop.ep` | ReAct coordinator: **multi-tool batching** (many `Action:` calls executed per model call), long-horizon chaining (50-turn LLM cap, per-request tunable), approval gate, observer audits, mid-turn whispers, cooperative cancel, clarification pause/resume, full untruncated trace transparency. |
| `prompt.ep` | Prompt assembler: kernel (ReAct grammar + batching rule), persona/identity, `[CAPABILITIES]` framing, self-sections (`[[BEHAVIOR]]`/`[[SKILLS]]`), `[[SESSION GUIDANCE]]`, awareness block, memory tiers. |
| `tools.ep` | Schema registry and guarded execution dispatcher for the **71-tool surface**: wallet/DHT/name, codebase + workspace files (paginated reads), project linking, sessions/transcripts/search, memory/cognition (scratchpad, lessons, timeline, KG, procedures, synaptic graph), RAG, web search/visit/download, `run_command`/`run_ep` sandbox, image generation, Discord (channels, read, react), delegation, scheduler, self-prompt, and more. |
| `session.ep` | Persistent sessions: transcripts, per-session guidance prompt, compression, active-session tracking; a new session clears the active workspace link. |
| `workspace.ep` / `workspace_links.ep` | Per-session workspace files + a project-link registry: register external project dirs, set one active per session, resolve bare relative paths against it. |
| `memory.ep` / `sleep.ep` / `synaptic_tool.ep` | Tiered cognitive memory: scratchpad, lessons (semantic recall), timeline, Hebbian knowledge graph, consolidation/"sleep" sweep. |
| `llm.ep` | Model client + router: auto-discovers llama.cpp (8080/8081), Ollama (11434), LM Studio (1234); default gemma-4-31b uses the matching parallel llama.cpp server on :8080 first; async-timeout-bounded reads; `query_vision` multimodal path (:8091). |
| `image_gen.ep` + `vendor/sd/sd_ep_shim.cpp` | Local image generation via libstable-diffusion FFI: FLUX 4-input mode (gguf transformer + diffusers CLIP/VAE + gguf T5) or single-file SD/SDXL; `config/image.json`; 1024×1024; the agent then vision-describes its own output. |
| `observer.ep` / `observer_rules.ep` / `observer_parser.ep` | Safety supervisor: fail-closed LLM audit gate for dangerous tools (human approval overrides to advisory), fail-open reply audit + mid_message look-back, deterministic moderation classifier, explicit parsed-vs-default verdicts. |
| `access.ep` / `awareness.ep` | Tiered Full-PC access with an unsafe-action gate (sensitive = warn/re-ask, secrets = hard-block) + situational awareness / tool-routing / act-vs-ask decision policy. |
| `orchestrator.ep` | Sub-agent delegation: spawn/wait/check/cancel/list + swarm fan-out with concat/best/vote merge, as cooperative async tasks. |
| `tutor.ep` / `tutor_content.ep` / `sandbox_ep.ep` | Decentralised education: Socratic tutor mode (scaffolds, never answer-vends), curriculum lessons, `run_ep` sandboxed ErnosPlain playground (Learning web tab). |
| `scheduler.ep` / `learning.ep` / `changelog.ep` / `trace.ep` | Scheduled jobs + autonomy, learning buffers (golden/preference/rejection), change logging, and the SQLite trace-event stream that feeds the live thinking view. |
| `turing_grid.ep` | 3D Turing Grid machine tape workspace. Tracks active HEAD position across (X, Y, Z) space and reads/writes cell states. |
| providers / model registry & router | Provider specs (OpenAI-compatible + Hugging Face) and pure, deterministic model selection. |
| `adapters.ep` + `decent_net/discord_bridge.py` | Platform bridges. The Discord bridge (Python, discord.py) polls trace events into a live thinking thread, attaches files/images to the reply message, threads message/channel ids for `react`, and renders Stop/approval/clarification buttons; Telegram/WhatsApp registry. |

Agent-parity Phases 1–6 are done and gated. Since then: sessions + guidance, workspace linking, context/access system, education, tooling overhaul (71 tools), image gen + vision, self-prompt persistence, multi-tool batching. The recursive self-improvement loop (SAE/steering/LoRA promotion) remains **partial** — planned, not built.

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
| `bandwidth.ep` | Bandwidth sharing with mutex-protected 60-second tier limits, byte counters, contribution scoring, tier-spoof rejection, and a checked TCP routing proxy. |
| `compute.ep` | Mutex-protected compute manager with concurrent TCP worker assignment, result acknowledgement, contribution tracking, and distinct-worker redundancy checks. |
| `mesh.ep` | Symbiotic mesh coordinate layer. Orchestrates bandwidth accounting and compute-job coordination; its current collaborative-AI path runs redundant local inference and verifies matching results. It does not onion-route inference. |

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
| Source modules | ~113 |
| Source lines (non-test) | ~45,800 |
| Test files | 105 |
| Test lines | ~18,300 |
| Agent tools | 71 |
| Test coverage | each subsystem ships its own suite; node builds and boots, core paths verified |
| External dependencies | Clang, SQLite, libsodium, OpenSSL, libsecp256k1, stable-diffusion.cpp; optional configured backends include espeak-ng, ONNX Runtime, Opus, VPX, SRTP, and whisper.cpp |
| Target platforms | macOS (ARM64, x86_64) · Linux (x86_64, aarch64) · Windows via WSL2 (runs the Linux build) |

---

## Roadmap

This checklist names implemented areas and explicit interoperability boundaries. An unchecked item is not represented as complete elsewhere in this README.

- [x] **Node Daemon** — unified coordinator for all subsystems
- [x] **Web Dashboard** — glassmorphic SPA with real-time telemetry
- [x] **CLI Control Client** — local IPC command interface
- [x] **Raft Consensus** — cluster coordination with leader election
- [x] **Onion Routing** — multi-hop anonymity with mix networks
- [x] **Distributed Search** — crawl, rank, and query the decentralised web
- [x] **Resource Pooling** — bandwidth sharing, compute delegation, symbiotic mesh
- [x] **Email & Git Hosting Primitives** — documented SMTP/IMAP subsets and Git helpers
- [x] **Multi-Node Bootstrap** — CLI `--seed`/`--port`, DHT discovery, Raft peer sync
- [x] **Real UTXO Transfers** — Ed25519-signed transactions, overdraft protection
- [x] **DHT Key-Value Store** — store/get via IPC and Web UI
- [x] **Decentralised Name Registry** — register/resolve via IPC and Web UI
- [x] **Cross-Platform Build** — `build.sh` auto-detects macOS/Linux, Homebrew/system paths
- [x] **Live E2E Test Suite** — native integration coverage recorded in the verification record
- [x] **Multi-Node Stress Tests** — 3-node cluster formation, failure recovery, concurrent ops
- [ ] **QUIC Transport** — multiplexed low-latency transport alongside the current TCP/UDP transports
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
- [System Guide Synthesis](docs/system_guide_synthesis.md) — The technical subsystem documentation covering architecture, schemas, and APIs.
- [GitDec Simple User Guide](docs/gitdec_user_guide.md) — A friendly, clear guide on how to host and collaborate on repositories using GitDec.
- Subsystem guides: [Network & DHT](docs/network_dht_guide.md) · [Storage & CRDTs](docs/storage_crdt_guide.md) · [Identity Registry](docs/identity_registry_guide.md) · [Ledger & DEX](docs/ledger_dex_guide.md) · [Messaging & Social](docs/messaging_social_guide.md) · [Resource Pooling](docs/resource_pooling_guide.md) · [Turing Grid & Hebbian Memory](docs/turing_hebbian_guide.md) · [Settings](docs/settings_guide.md)
- [AGENT.md](AGENT.md) — The engineering laws every change to this codebase is held to.
- [master_prompt.md](master_prompt.md) — A 13-block full-system diagnostic that exercises every agent tool with pass/fail scorecards.
- [CHANGELOG.md](CHANGELOG.md) — Dated record of all notable changes.
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
