# ErnosDecent — Verified Status & Ground Truth
*(Compiled from the live code + git history on branch `agent-parity`, 2026-06-21. This is the
authoritative source for the book's status sections AND the documentation truth-pass. Where a number
is not yet re-verified by running, it is marked ⚠️.)*

## Headline reality vs. what the docs currently say

| Claim in current README/docs | Verified reality |
|---|---|
| "48 source modules" | **103 source modules** (`.ep`, non-test, excluding hosted GitDec copies) |
| "~11.7k LOC" (old guide) / not stated in README | **~30,300 source code-lines** (non-blank, non-comment) + ~12,700 test lines |
| "16 subsystems" | **17 subsystems** (`decent_*`) + 7 core files |
| "191/191 tests, 20 integration suites" | **94 test files** now exist; the 191 number is stale ⚠️ (must re-run the harness to state a real pass count) |
| AI = "speech-to-text" only | **Speech-to-text AND text-to-speech**: Kokoro TTS ships end-to-end (Web UI 🔊 + Discord), live-verified this session |
| No agent memory tiers / providers / observer split | **Agent-parity Phases 1–6 done**: 9-tool surface, memory tiers (knowledge graph, procedural, consolidation), observer split (rules/parser/audit + moderation), providers + model registry/router, platform adapters (Telegram/WhatsApp registry), node↔bridge RPC, fixed-point learning payoff |
| No issue tracker mentioned | **GitDec** — a decentralized, in-repo issue/PR tracker — exists and works (create/comment/close, escaping + id-collision fixes) |
| No business edition | **Business edition** exists on the public `business` branch (README-Business.md, ANTI_CAPTURE.md, config/business/) — a cosmetic overlay, default byte-identical; engine→business merges propagate features |

## Verified subsystem inventory (source files / code-lines)

| Subsystem | files | code-lines | What it is (verified from headers/guides) |
|---|---|---|---|
| decent_net | 15 | 6,472 | P2P: Noise XX handshake, Kademlia DHT, relay circuits, transport, host election |
| decent_agent | 24 | 6,376 | Cognitive agent: ReAct loop, 7-tier memory, Turing grid, observer gate, tools, providers, platform bridge |
| decent_web | 2 | 4,728 | Web UI server (app.ep→app.js) + dashboard; WS gateway; now TTS routes |
| decent_money | 6 | 3,377 | HD wallets, UTXO ledger, PoS, tokens/NFTs, AMM+orderbook DEX, contract VM |
| decent_id | 6 | 2,434 | Ed25519/X25519, DIDs (did:key/did:peer), capability auth, keystore |
| decent_store | 5 | 2,445 | Content-addressed storage (SHA-256), 5 CRDT types, Merkle trees |
| decent_ai | 6 | 2,264 | GGUF inference, embeddings, speech-to-text, **TTS (Kokoro via FFI)** |
| decent_media | 4 | 1,861 | WebRTC (SDP/STUN/DTLS/SRTP), HLS, real Opus/VP8 codecs, P2P CDN |
| decent_consensus | 5 | 1,628 | Raft leader election, replicated log, state rollback |
| decent_msg | 2 | 1,107 | E2E encrypted DMs + group channels, history |
| decent_social | 4 | 747 | Nostr + ActivityPub federation, unified feeds |
| decent_host | 4 | 633 | HTTP server, SMTP/IMAP, P2P Git |
| decent_search | 3 | 578 | Crawler, BM25 + PageRank, query merge |
| decent_anon | 3 | 520 | Onion routing, mix networks, timing defenses |
| decent_pool | 3 | 452 | Bandwidth tiers, compute job queue, symbiotic mesh |
| decent_cli | 1 | 128 | Daemon control CLI client |
| decent_name | 2 | 105 | Decentralized DNS / `.decent` `.ernos` registry |
| **Core** | 7 | ~4,300 | node.ep (2,109), storage.ep (842), protocol_server.ep (619), config/health/logging/platform |

## What actually works end-to-end (high confidence)
- **Builds and runs**: `bash build.sh` → `./node` boots; IPC on 5000, Web UI on 8088 (verified live this session).
- **TTS**: WS `tts_request` → Kokoro synth → byte-exact `/tts/*.wav` serve; node `TTS SPEAK` IPC verb; Discord 🔊 button (bridge code; not bot-connected live).
- **Identity, networking, storage/CRDT, messaging, social, naming, hosting, money/DEX, AI inference, media codecs (real Opus+VP8), anonymity, search, pooling, consensus, web UI** — all have test suites and per-subsystem guides in `docs/`.

## Honest "what's left" (verify each before the book asserts it)
- **Test count**: re-run the suite (`bash build.sh` + per-subsystem `run_test.sh` + `test_live_e2e.sh`) to state a real, current pass number. Do NOT reprint "191/191."
- **Agent self-improvement**: SAE interpretability / steering vectors / LoRA adapter training-promotion are partial vs. the original ErnosAgent (Phase 6 proved fixed-point training is real, but the full self-improvement loop is not at parity).
- **Transport**: Noise+DHT proven; production QUIC + real STUN/TURN NAT traversal are post-1.0 (memory: transport degrades under repeated short-lived connects — onion search works once then falls back).
- **Platform connectors**: Discord bridge + Telegram/WhatsApp adapters exist; not the full breadth of the original 16 connectors.
- **Build hazard (known)**: node.ep can fail whole-program type-check; build.sh can ship a stale binary — always verify new symbols are in the fresh binary (memory: build-node-ships-stale).
- **Platforms**: macOS + Linux native; Windows via WSL2; mobile + plugin system not started.

## Notes for the documentation truth-pass (A0)
Files to correct (claims to fix listed above): `README.md` (badges + "Project Status" + AI feature row + subsystem count + test claims), `README-Business.md`/`ANTI_CAPTURE.md` (business branch — verify accurate), `docs/CHANGELOG.md` (add TTS, agent phases, GitDec, business), `docs/ERNOS_REFERENCE.md`, `docs/system_guide_synthesis.md`, the per-subsystem `docs/*_guide.md` (esp. AI guide → add TTS; turing_hebbian/agent → add memory tiers/observer/providers), `docs/IMPLEMENTATION_PLAN.md` + `implementation_plan*.md` (status), and stale code header comments (e.g. `decent_ai/tts.ep` header still says "STAGE A … FFI + WAV land in the next stage" although FFI+WAV are present).
