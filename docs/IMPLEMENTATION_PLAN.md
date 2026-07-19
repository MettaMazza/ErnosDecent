# ErnosDecent — Implementation and Verification Record

This file records implemented behavior and verification evidence. It does not describe ErnosDecent as a replacement for TCP/IP, BGP, the public DNS root, cloud infrastructure, or the entire public internet. Those claims are not supported by the code.

## Build and runtime

Ernos source is compiled to C and linked into native binaries. The node currently depends on Clang, SQLite, libsodium, OpenSSL, libsecp256k1, pthreads, and stable-diffusion.cpp. The web application is emitted from `decent_web/app.ep` to JavaScript. These are explicit platform dependencies.

The supported CI targets are the macOS and Linux runners declared in `.github/workflows/ci.yml`. A platform is not considered verified until that workflow completes on that platform.

## Implemented components

| Area | Implemented behavior | Boundary |
|---|---|---|
| Identity | Ed25519 signing, X25519 encryption, DID:key/DID:peer helpers, signed capabilities, authenticated IPC | This is not an OAuth provider or a replacement for every account system. |
| Networking | Framed TCP transport, UDP-backed subsystem transports, Noise sessions, DHT routing, relay forwarding, host election, checked WebSocket framing | This does not replace TCP/IP or BGP. |
| Storage | SQLite persistence, SHA-256 content addressing, CRDT data structures, RAG and knowledge stores | Content addressing uses SHA-256, not BLAKE3. |
| Messaging | Signed/encrypted messages, conversations, channels, persistence, network delivery | Direct-message keys are static; the code explicitly provides no forward-secret ratchet. |
| Social | NIP-01 canonical event hashing and BIP-340 secp256k1 signing, filters, feed aggregation, ActivityPub-shaped data structures | The Nostr client supports plain WebSocket transport; it does not provide `wss` TLS. ActivityPub federation interoperability is not established. |
| Naming | Persistent name registry, cache, signed DHT publication and remote resolution | This is an ErnosDecent naming system, not an authoritative public-DNS implementation. |
| Money | UTXO validation, PoS selection, tokens, NFTs, contracts, AMM/order-book structures, persistent blocks | No claim of production financial safety is made without an independent security audit. |
| AI | Local/remote model routing, deterministic inference references, whisper.cpp HTTP transcription, Kokoro/ONNX TTS, stable-diffusion.cpp image generation | Reference inference and speech functions are not represented as trained production models. Backends report unavailability rather than fabricate output. |
| Media | SDP/STUN/SRTP-related structures, codecs, streaming and CDN primitives | The current DTLS/media path is not a complete browser-interoperable WebRTC stack. |
| Resource pooling | Mutex-protected bandwidth windows, configured kbps enforcement, redundant compute jobs, and TCP worker assignment/result acknowledgement | The mesh convenience call executes its two inference passes on the coordinator; the TCP worker protocol is available separately and is not represented as automatic cross-node inference. |
| Search/privacy | Local crawl/index/ranking, authenticated federation, multi-hop onion search when verified relays are available | The UI reports when it falls back to direct federation. Reader-page fetching is direct and sandboxed; it is not labeled anonymous. |
| Hosting | Static HTTP hosting plus documented SMTP/IMAP command subsets and Git hosting helpers | The email server implements a command subset, not complete SMTP/IMAP standards. |
| Agent | ReAct loop, prompt/persona management, memory, tools, scheduling, workspaces, tracing, local and remote provider routing | Test-only deterministic inference is explicitly gated by test state. |
| Dashboard | Password login, signed expiring sessions, CSRF/origin checks, authenticated HTTP/WebSocket APIs, sandboxed reader and attachment delivery | Authentication is local-node authentication, not a public multi-tenant identity service. |

## Verification evidence

The following native suites were compiled and run during the July 2026 adherence repair. A count is recorded only when the executable produced that result and did not report a failure marker.

- Identity: keys 17, DID 14, auth 11.
- Networking: DHT 18, Noise 8, relay 15, transport 6, Noise transport 2, DHT transport 8, relay transport 5, host election 2.
- Consensus: consensus 4 and Raft TCP 3.
- Messaging/storage: message 13, channel 10, content 13, CRDT 20, persistence 11.
- Money/media/social/AI: money 6, media 7, social 8, AI 6.
- Privacy/pooling/hosting: circuit 15, pool 4, host 4.
- Integration: E2E 10, multi-node 4, networking 10, security 6, CLI 10, stress 5, plus the platform executable.
- Runtime-specific: WebSocket framing 8 and BIP-340 runtime 4.

These counts are historical evidence from that run, not a permanent assertion. CI and local release checks must execute the binaries again after code changes.

The checked release matrix contains 32 subsystem, integration, persistence, security,
stress, platform, Raft, and CLI binaries. All 32 were freshly compiled and exited
successfully without failure markers on 19 July 2026. The separately linked cognitive
agent suite passed 13 of 13 sections, and the WebSocket and BIP-340 runtime binaries
passed 8 and 4 checks respectively. The production node was rebuilt after the Web
password startup repair and authenticated login was then verified against the live
`/api/login` endpoint.

The live harnesses additionally passed 47 of 47 multi-node checks and 16 of 16
isolated stress checks. The isolated live E2E harness passed 108 of 108 checks. Its
`AI INFER` assertions follow the asynchronous contract: IPC returns correlated
session/turn acceptance, and completion is delivered through trace/session state
rather than an inline `RESPONSE` payload. A freshly linked AddressSanitizer and
UndefinedBehaviorSanitizer node also completed clean startup after the emitted-runtime
unsigned-shift repair without a sanitizer finding.

Bootstrap does not ship a literal external seed. It accepts an explicit operator seed or previously verified cached peers, rejects wildcard/non-dialable endpoints, requires a framed DHT `PONG`, and reports connection, send, receive, invalid-response, close, registration, and invalid-endpoint failures distinctly. Without a reachable candidate, the node is truthfully reported as a mesh root. A configured static host skips operated default aliases while retaining explicit and cached peer eligibility. `network.public_host` is now preserved across default generation, load/save, and dashboard editing. Adding an operated default remains gated on a stable DNS record and independent external DHT verification.

Public bootstrap remains explicitly **pre-launch** as of 19 July 2026. External TCP
reachability was verified for `9100` and `9101`; DDNS and external reachability for
`9102`–`9104` were deferred by the operator. Fresh nodes therefore require an explicit
or cached seed, and no documentation or startup output represents a public mesh as live.

The July 19 adherence run validated all 221 native-target `.ep` sources in the working tree with `ernos check`. The browser-target `decent_web/app.ep` emitted a 4,764-line JavaScript artifact successfully. Its browser globals are validated by the JavaScript emitter, not by the native-target checker. `scripts/release_check.sh` is the reproducible local entrypoint for these source, build, native-matrix, cognitive-agent, runtime, shell, and whitespace checks.

## Release gate

A release is accepted only when all of the following are true:

1. Every native-target `.ep` source passes `ernos check`; the browser-target `decent_web/app.ep` emits JavaScript successfully with `ernos emit ... --js`.
2. Every parameter and return value has an explicit Ernos type.
3. The forbidden source markers in `AGENT.md` are absent from production code.
4. `bash build.sh` succeeds from freshly generated C and produces a signed macOS binary when run on macOS.
5. The subsystem, integration, security, persistence, malformed-input, transport, and runtime-specific suites exit successfully without printed failure markers.
6. The live node starts from the new binary, binds only its configured interfaces, and passes authenticated API and WebSocket checks.
7. Documentation states implementation boundaries exactly; unimplemented interoperability is never labeled complete.
