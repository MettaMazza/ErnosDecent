# The ErnosDecent System Bible
*A plain-language reference. Every entry uses the same six-part shape so you can read one or read them all. Status lines are taken from the verified ground-truth in `book/notes/status.md` (compiled from the live code on 2026-06-21). Where something is partial, it says so.*

---

## What ErnosDecent actually is

ErnosDecent is **one program you run on your own machine that replaces the services you currently rent from big companies** — your identity (login), your messages, your file storage, your money, your website hosting, your AI assistant, your video calls — with no company sitting in the middle. Instead of trusting a corporation to hold your account, your data, and your money on their servers, your computer does those jobs directly and talks peer-to-peer with other people's computers. There is no head office to hack, censor, bill you, or switch you off. The whole thing is written in **ErnosPlain**, a programming language whose code reads like plain English sentences, which is part of the point: a system meant to free people from hidden control should itself be readable by ordinary people, not locked behind jargon.

The project is large but real: **17 subsystems**, about **103 source modules**, roughly **30,000 lines of source code** plus another ~12,700 lines of tests across **94 test files**. It builds with `bash build.sh` and boots as a single daemon (`./node`) that opens a local control port and a web dashboard. The sections below cover every subsystem, the core daemon, the AI agent's inner parts, the GitDec code-hosting engine, and the Business edition.

A note on honesty, which the whole project insists on: "working" below means verified end-to-end. "Partial" means the core mechanism is proven but the full original vision isn't reached yet. The book should never paper over that gap.

---

### decent_id — Who you are, without an account

- **The human need:** Today you "are" your email address or your phone number, and a company can lock you out of your own life by suspending the account. People need an identity that is genuinely theirs and can't be taken away.
- **The plain idea:** Your identity is just a pair of secret/public cryptographic keys generated on your own machine. The public key *is* your name on the network; the secret key proves you're you. No registration, no server, no password reset desk.
- **An everyday analogy:** It's a wax seal and signet ring. Anyone can recognise your seal (your public key), but only you hold the ring (your secret key) that stamps it. Nobody issues you the ring — you make it yourself, and nobody can confiscate it.
- **How ErnosDecent does it:** It generates an **Ed25519** signing keypair (for proving and signing) and an **X25519** encryption keypair (for private messages), then packs the public signing key into a **DID** — a "Decentralized Identifier," a self-describing name string like `did:key:z6Mk...` that anyone can verify offline without phoning a central database. The secret keys live in an encrypted keystore on disk, locked by a passphrase stretched through 10,000 rounds of PBKDF2 so it's hard to brute-force.
- **How it serves freedom:** This is the root of the whole mission. If no company, university, bank, government, or church grants you your identity, then none of them can revoke it. You speak for yourself by cryptographic fact, not by permission.
- **Where it stands:** Working. `did:key` and `did:peer`, Ed25519/X25519, capability auth, and the encrypted keystore are implemented and tested (6 modules, ~2,434 lines).

---

### decent_money — Money without a bank

- **The human need:** Sending value normally means a bank or payment processor takes a cut, can freeze your account, and sees every transaction. People need to hold and move money without asking a middleman's permission.
- **The plain idea:** A shared ledger that everyone helps keep, recording who owns what. You can hold coins, send them, create your own tokens, mint collectibles, and swap one token for another — all settled by the network itself, not a company.
- **An everyday analogy:** Imagine a village notebook of who owns which coins that thousands of people each keep an identical copy of. To spend, you sign your entry; everyone updates their notebook together. No single notebook-keeper can quietly edit your balance.
- **How ErnosDecent does it:** It uses a **UTXO ledger** (the same "unspent coins" bookkeeping style as Bitcoin) secured by **Proof-of-Stake** (validators lock up coins to earn the right to add blocks, chosen by a stake-weighted lottery). On top sits a built-in exchange (**DEX**) combining an automatic **constant-product market maker** (the `x·y=k` pricing pools used by Uniswap) with an escrow-backed limit orderbook, plus **HD wallets** (BIP-39 seed phrases), ERC-20-style **tokens**, ERC-721-style **NFTs**, and a small gas-metered **smart-contract VM** so programs can hold and move funds safely.
- **How it serves freedom:** Financial control is one of the sharpest tools of coercion — frozen accounts, denied service, surveilled spending. A ledger nobody owns removes that lever entirely.
- **Where it stands:** Working in test suites. Ledger, PoS election, AMM+orderbook DEX, tokens, NFTs, and the contract VM are implemented and exercised by tests (6 modules, ~3,377 lines).

---

### decent_net — How the machines find and trust each other

- **The human need:** For a network with no central servers to work at all, your computer has to find other people's computers and talk to them securely — without a phone-book company in the middle.
- **The plain idea:** Every node keeps a slice of a shared, distributed address book and learns its neighbours. When two nodes connect, they first do a secret handshake so the conversation is encrypted from the very first byte.
- **An everyday analogy:** A neighbourhood where everybody keeps a few pages of the same phone book. To find someone, you ask the neighbour whose pages are "closest" to that name, who points you closer, and so on — a few hops and you've found anyone, with no central directory.
- **How ErnosDecent does it:** Discovery and lookup run on a **Kademlia DHT** (a Distributed Hash Table — a key/value address book spread across everyone's machines, where you find any record in about log-N hops using an XOR "distance" between IDs). Connections are wrapped in a **Noise XX handshake**, a modern protocol that establishes an encrypted, mutually-authenticated tunnel. It also includes **relay circuits** (so firewalled nodes can still be reached) and **host election** (deciding which nodes act as helpers).
- **How it serves freedom:** The network has no chokepoint to seize. There is no DNS root, no central registry, no ISP-level gatekeeper whose cooperation can be compelled to cut someone off.
- **Where it stands:** Working core, with a known caveat. Noise + Kademlia DHT + relay are the biggest subsystem (15 modules, ~6,472 lines) and proven. Production-grade QUIC and real STUN/TURN NAT traversal are post-1.0, and the transport is known to degrade under repeated short-lived connections (onion lookups can work once then fall back).

---

### decent_msg — Private messages nobody else can read

- **The human need:** Chat apps route your messages through company servers that can read them, log them, hand them over, or lose them. People need conversations that only the two of them can open.
- **The plain idea:** Direct messages are encrypted end-to-end so only sender and recipient hold the keys. Group channels let people gossip on shared topics, every message signed so you know who really sent it. Your history lives on your own disk, not a company's.
- **An everyday analogy:** Sealed letters versus postcards. A normal chat app is a postcard the postal company can read; this is a letter in a box only the recipient's key can open — and you keep your own copy of every letter in your own drawer.
- **How ErnosDecent does it:** DMs derive a shared secret with an **X25519 Diffie-Hellman** key agreement, then encrypt each message with a symmetric cipher (ChaCha20-Poly1305 / AES-GCM family). Group channels (like `#general-mesh`) broadcast **Ed25519-signed** messages over the gossip layer. All history is stored locally in the node's database.
- **How it serves freedom:** Surveillance of communication is how dissent is tracked and chilled. End-to-end encryption with no server copy means no one can quietly read or seize the conversation.
- **Where it stands:** Working in test suites. E2E DMs, signed group channels, and local history are implemented (2 modules, ~1,107 lines).

---

### decent_social — A social feed with no platform owner

- **The human need:** Social platforms decide what you see, sell your attention, and can delete your account and your audience overnight. People need to publish and follow without a platform owning the megaphone.
- **The plain idea:** Your posts are signed by your own key and pushed to open relays that anyone can run. You can also exchange posts with the wider "Fediverse" (Mastodon and friends). One feed pulls it all together in time order.
- **An everyday analogy:** A community noticeboard system where the boards (relays) are run by lots of different people. If one board takes your flyer down, the others still carry it, because the flyer is signed by you and not owned by any board.
- **How ErnosDecent does it:** It speaks **Nostr** (signed JSON events broadcast to many independent relays over WebSockets — censorship-resistant because no relay owns your identity) and **ActivityPub** (the W3C standard behind Mastodon, using actor inbox/outbox delivery). A unified feed normalises both into one chronological stream on your dashboard.
- **How it serves freedom:** No single company can deplatform you, shape your feed with a secret algorithm, or monetise your attention. The audience follows your key, not a corporate account.
- **Where it stands:** Working in test suites. Nostr publishing, ActivityPub federation, and the unified feed are implemented (4 modules, ~747 lines).

---

### decent_anon — Hiding who is talking to whom

- **The human need:** Even encrypted messages reveal *who* is talking to *whom* and *when* — the "metadata" that can be just as dangerous as the content. People in hostile environments need to hide the pattern of their communication.
- **The plain idea:** Wrap each message in several layers of encryption and bounce it through a chain of relays, each of which only knows the next hop — so no single relay sees both the sender and the destination. Add timing tricks so traffic patterns can't be read.
- **An everyday analogy:** A letter inside three nested envelopes, handed person to person. The first courier knows who gave it to them and who's next, but nothing else; by the time it arrives, no courier in the chain knows both ends.
- **How ErnosDecent does it:** **Onion routing** — multi-hop layered packet encryption where each relay peels one layer (the same idea as Tor) — combined with a **mix network** that batches packets, shuffles their order (Fisher-Yates), and adds randomized timing jitter to defeat traffic-correlation analysis.
- **How it serves freedom:** Political and religious persecution often relies on the *map* of who talks to whom. Breaking that map protects sources, organisers, and ordinary people from being targeted for their associations.
- **Where it stands:** Working core, with the same transport caveat. Onion routing and the mix network are implemented (3 modules, ~520 lines); under repeated short-lived connections the underlying transport can degrade, so onion lookups may work once then fall back.

---

### decent_store — Your files, addressed by what they are

- **The human need:** Cloud storage means handing your files to a company that can read them, lose them, raise the price, or delete them. People need durable storage they control, that can sync across devices without conflicts.
- **The plain idea:** Files are split into chunks and named by a fingerprint of their contents, so identical data is stored once and any tampering is instantly detectable. Shared documents merge changes automatically even when edited offline in two places at once.
- **An everyday analogy:** A library where every book is shelved by a fingerprint of its exact text instead of by an arbitrary call number. Ask for that fingerprint and you always get *exactly* that book; change one word and it's a different book with a different fingerprint.
- **How ErnosDecent does it:** **Content-addressed storage (CAS)** chunks data and indexes it by **SHA-256** hashes, verifiable with **Merkle trees**. For live collaborative data it uses **CRDTs** (Conflict-free Replicated Data Types — counters, sets, and registers with mathematical merge rules like "newest timestamp wins" or "add beats concurrent remove") so two offline copies always reconcile to the same result with no central referee.
- **How it serves freedom:** Owning your storage means no provider can hold your data hostage, scan it, or vanish it. Conflict-free sync means you can collaborate without a coordinating company.
- **Where it stands:** Working in test suites. CAS, the 5 CRDT types, and Merkle trees are implemented (5 modules, ~2,445 lines).

---

### decent_name — Human-friendly names instead of long key strings

- **The human need:** Nobody can remember `did:key:z6MkjajSim1uQ5WF...`. People need short, memorable names — but the normal naming system (DNS) is centrally controlled and can be censored or seized.
- **The plain idea:** A decentralized phone book that maps a friendly handle like `alice.decent` to a full cryptographic identity, stored across the network so no registrar owns it. Look-ups check fast local caches first, then the wider network.
- **An everyday analogy:** Saving a contact's name over their long phone number — except the contact list is shared across the whole community and the number is signed, so only Alice can change where `alice.decent` points.
- **How ErnosDecent does it:** A name registry for the `.decent` (people/handles) and `.ernos` (system) TLDs. Registration writes the mapping locally and broadcasts it to the **Kademlia DHT**. Resolution is a 4-tier cascade: in-memory cache (300-second TTL) → local SQLite → DHT lookup (`name:alice.decent`) → direct query to a known peer. Only the DID that registered a name can update it.
- **How it serves freedom:** Names are a classic censorship lever — seize the domain and you erase the site. A registry nobody owns means a handle can't be confiscated or redirected by an authority.
- **Where it stands:** Working, modest in size. The registry and 4-tier resolver are implemented (2 modules, ~105 lines) — small because they lean on decent_net's DHT.

---

### decent_search — Finding things without a search giant

- **The human need:** Search is dominated by a couple of companies that rank results by their own interests and track every query. People need to find content across the network without a gatekeeper deciding what's findable.
- **The plain idea:** Your node can crawl and index content, build a word index, and rank results by relevance and link-popularity — the same maths a search engine uses, running on your own machine with no one watching your searches.
- **An everyday analogy:** Keeping your own card-catalogue of everything you've come across, scored so the most relevant and most-cited cards float to the top — instead of phoning one giant librarian who logs every question you ask.
- **How ErnosDecent does it:** A crawler builds an **inverted index** (word → documents). Ranking combines **BM25** (a standard relevance score balancing how often a word appears against how common it is) with **PageRank** (scoring pages by how many others link to them, computed by power iteration). Because ErnosPlain favours integer maths, even the natural-log inside BM25 is done in fixed-point. Results from multiple sources are merged.
- **How it serves freedom:** Whoever controls search controls what is effectively visible. Distributing it removes a powerful, quiet form of editorial and political control — and stops your curiosity being surveilled.
- **Where it stands:** Working in test suites. Crawler, BM25 + PageRank, and query merge are implemented (3 modules, ~578 lines).

---

### decent_host — Running websites, email, and Git yourself

- **The human need:** Putting something online normally means renting a web host, an email provider, and a code host — each a company that can shut you down or read your mail. People need to serve their own content.
- **The plain idea:** Your node *is* the server. It can answer web requests, send and receive email, and host Git repositories straight from your own machine.
- **An everyday analogy:** Instead of renting a stall in someone else's market (and following their rules), you open the shop front of your own house. The goods, the hours, and the door are yours.
- **How ErnosDecent does it:** A built-in **HTTP server** (request parsing, response building, static file serving), an **SMTP/IMAP** mail server that verifies senders by **DID signatures** (so spoofing is cryptographically blocked), and **peer-to-peer Git** hosting (which GitDec builds on).
- **How it serves freedom:** Self-hosting removes the host as a point of control. Nobody can take your site down, snoop your mail, or delete your repository because the server lives under your own roof.
- **Where it stands:** Working in test suites. HTTP, SMTP/IMAP with signature verification, and P2P Git are implemented (4 modules, ~633 lines).

---

### decent_media — Calls, streaming, and a shared CDN

- **The human need:** Video calls and streaming run through corporate infrastructure that can listen in, throttle, charge, or block. People need real-time audio/video and content delivery without those middlemen.
- **The plain idea:** Two nodes set up a direct, encrypted audio/video link and compress the media with real codecs. Popular content is served cooperatively by everyone who has a copy, so no single server bears the load.
- **An everyday analogy:** A direct phone line you string between two houses for calls, plus a neighbourhood where, when a popular video is wanted, whoever already has it shares a piece — like everyone seeding a download instead of one shop selling every copy.
- **How ErnosDecent does it:** **WebRTC** for peer media (SDP signalling, STUN, DTLS, and real **SRTP** encryption via libsrtp2 FFI), genuine **Opus** (audio) and **VP8** (video) codecs through C-library bindings (with ADPCM/Delta-RLE fallbacks), **HLS** streaming, and a **P2P CDN** that locates and pulls content chunks from peers via the DHT and content store.
- **How it serves freedom:** Real-time communication and media distribution are expensive to self-host alone; pooling it across the mesh keeps live, rich media free of the gatekeepers who otherwise meter and monitor it.
- **Where it stands:** Working core. WebRTC, real Opus+VP8 codecs (delivered via careful struct-level FFI), HLS, and the P2P CDN are implemented (4 modules, ~1,861 lines). Real STUN/TURN NAT traversal at production scale is post-1.0 (see decent_net).

---

### decent_pool — Sharing spare bandwidth and compute

- **The human need:** A serverless network only works if people contribute resources. There has to be a fair way to pool spare bandwidth and CPU — and to reward those who give more.
- **The plain idea:** Your node lends out spare upload bandwidth and processing slots to help carry traffic and run jobs for others. The more you contribute, the better your own priority and speed.
- **An everyday analogy:** A barn-raising or a tool-lending co-op. Everyone chips in spare hands and tools; the neighbours who show up most get the quickest help when it's their turn.
- **How ErnosDecent does it:** **Bandwidth tiers** track relayed upload/download bytes, promote qualifying Free peers to Premium, and enforce configured rates over a locked sixty-second window. A mutex-protected **compute job queue** assigns jobs to remote TCP workers and accepts results only from assigned identities; two distinct matching submissions complete a job and mismatches are disputed. Contribution records are coordinator-local, not a global multiplier or reputation score. The mesh convenience path still performs its redundant inference locally rather than automatically dispatching it.
- **How it serves freedom:** This is the economic engine that lets the network exist without renting cloud capacity from corporations. Cooperation, not a corporate balance sheet, keeps the lights on — and the pooled savings are what make a corporate-free stack practical.
- **Where it stands:** Working in test suites. Bandwidth tiers, compute job queue, and the contribution scoring are implemented (3 modules, ~452 lines).

---

### decent_ai — A local AI brain (and voice)

- **The human need:** AI assistants today send your every prompt to a company's servers, which read it, log it, and can change or revoke the service. People need an assistant that runs on their own machine and answers only to them.
- **The plain idea:** The node can load and run a language model locally to answer prompts, turn speech into text, and turn text back into spoken audio — all without sending your words to anyone.
- **An everyday analogy:** A knowledgeable assistant who lives in your house and never phones a head office to ask permission or report what you said. What you tell them stays in the room.
- **How ErnosDecent does it:** Local **GGUF** model inference (a fixed-point transformer plus a GGUF file parser), **embeddings** for semantic search/recall, **speech-to-text** delegated to a real whisper.cpp backend (with a small fixed-point reference path), and **text-to-speech** via **Kokoro** — driving the real ONNX voice model through FFI: text → IPA phonemes (libespeak-ng) → vocab tokens → onnxruntime → 24 kHz audio → a WAV file. Float audio is kept on raw byte buffers because ErnosPlain's lists mangle floats.
- **How it serves freedom:** Cognitive tools are becoming central to how people think and work. An AI that runs locally can't be censored, surveilled, paywalled, or aligned to someone else's politics behind your back.
- **Where it stands:** Working, including TTS. Inference, embeddings, STT (via whisper.cpp), and Kokoro TTS are implemented; TTS was verified end-to-end this session — synthesised audio served byte-exact and triggered from the Web UI 🔊 button (6 modules, ~2,264 lines). (A stale header comment in `tts.ep` still says "Stage A / FFI lands next stage" although the FFI and WAV output are present.)

---

### decent_agent — The thinking, acting assistant

- **The human need:** A raw language model just predicts text. To be genuinely useful — and trustworthy — an assistant needs memory, the ability to *do* things safely, and a way to choose which model to use. People need that whole loop running under their own control.
- **The plain idea:** An agent that reasons step by step, remembers what it learns, uses tools to act in the world, checks dangerous actions before doing them, can speak to you, and reaches multiple AI providers — all on your machine.
- **An everyday analogy:** A capable personal assistant with a notebook, a filing cabinet, a phone, and a sensible supervisor who double-checks anything risky before it's done.
- **How ErnosDecent does it:** A **ReAct loop** (Reason → Act → Observe, repeating) drives the agent: it assembles context, calls a model, parses any requested action, runs it through a safety audit, executes the tool, records the result, and loops. It carries a **9-tool** surface, tiered memory, a guarded tool executor, a model router, and platform bridges (its sub-parts follow below).
- **How it serves freedom:** A sovereign agent means the most powerful new kind of software — an autonomous helper — answers to *you*, not to a vendor who can throttle, surveil, or steer it.
- **Where it stands:** Working core; self-improvement partial. The agent is the second-largest subsystem (24 modules, ~6,376 lines); agent-parity Phases 1–6 are done and gated. The full recursive self-improvement loop (SAE interpretability, steering vectors, LoRA training-and-promotion) is partial versus the original ErnosAgent — Phase 6 proved fixed-point training is real, but parity isn't reached.

---

### decent_agent · 7-tier memory — Remembering across time

- **The human need:** An assistant that forgets everything between turns is useless. People need it to hold the current task in mind, recall lessons, and keep a history — without uploading their life to a server.
- **The plain idea:** Memory is split into layers by how long things last and how they're recalled: fast scratch notes, learned lessons, a timeline of events, and a web of related concepts — all saved to a local file.
- **An everyday analogy:** A desk (sticky notes you'll toss today), a filing cabinet (lessons worth keeping), a diary (what happened, in order), and a mind-map on the wall (how ideas connect).
- **How ErnosDecent does it:** Tiers include a **scratchpad** (transient key/value, cleared when a goal finishes), **lessons** (long-term, recalled by **cosine-similarity embeddings** over a 0.5 threshold), a **timeline** (chronological event log), a reasoning trace, and the synaptic graph (its own entries below), all persisted to JSON and reloaded on start. A consolidation/"sleep" sweep synthesises and prunes.
- **How it serves freedom:** Persistent memory is what makes an assistant truly *yours* — and keeping it on local disk means your accumulated context is never a corporate asset to mine or sell.
- **Where it stands:** Working. The tiers, semantic recall, save/load, and consolidation are implemented in `memory.ep` and gated under agent-parity.

---

### decent_agent · knowledge graph — Concepts that learn to connect

- **The human need:** Real understanding isn't a list of facts; it's knowing how ideas relate, and having the strong connections stick while weak ones fade. An assistant needs that to reason instead of just recite.
- **The plain idea:** Concepts are dots; connections between them are lines that get stronger each time two ideas come up together and slowly weaken if they don't. Connections that prove themselves become permanent.
- **An everyday analogy:** A path worn across a field. Walk it often and it becomes a clear trail (permanent); stop using it and the grass grows back (decay and pruning).
- **How ErnosDecent does it:** A **Hebbian synaptic graph** — "neurons that fire together wire together." Edge weights are fixed-point integers (scale 1,000,000). Co-activation strengthens an edge toward 1.0 (`new = old + 0.1·(1 − old)`); at ≥0.99 it becomes a **permanent edge** immune to decay. A consolidation sweep decays non-permanent edges 5% and prunes anything below 0.01.
- **How it serves freedom:** A reasoning structure that grows from *your* use, on *your* machine, makes the assistant's intelligence personal and uncapturable rather than a model rented from a vendor.
- **Where it stands:** Working. The Hebbian graph, strengthen/decay/prune, and permanent promotion are implemented and tested.

---

### decent_agent · procedural memory — Learning how to do things

- **The human need:** Beyond facts, a good assistant should get better at *skills* — remembering which approach worked and improving the recipe over time, under your control rather than a vendor silently updating a model.
- **The plain idea:** Track the "how-to" the agent has learned — trained adapters and the payoff of past actions — and keep bookkeeping on which version is live, so improvements can be promoted or rolled back.
- **An everyday analogy:** A craftsperson's record of techniques, with version notes: "method v3 works best — keep it; v4 was worse — roll back."
- **How ErnosDecent does it:** An **adapter version manifest** (SQLite-backed) records each trained adapter's path, status, health, and notes, with promote/rollback bookkeeping; the **learning** module computes a fixed-point payoff so good outcomes reinforce. Producing the actual adapter weights is the training path (`decent_ai/train.ep` proves the math); this tracks which version is in charge.
- **How it serves freedom:** Self-improvement that you can inspect, promote, and roll back keeps the agent's growth transparent and reversible — the opposite of an opaque model that changes underneath you.
- **Where it stands:** Partial. The management/bookkeeping half and a proven fixed-point training step exist; the full recursive self-improvement loop is not yet at parity with the original ErnosAgent.

---

### decent_agent · Turing grid workspace — A scratch-space for plans

- **The human need:** Multi-step work needs somewhere to lay out steps, stash intermediate results, and stage commands — a working surface the agent can move around in.
- **The plain idea:** A 3-D grid of cells the agent's "head" moves through, writing notes or commands into cells and reading or running them later. It's an unbounded notepad with coordinates.
- **An everyday analogy:** A giant 3-D spreadsheet, or a Rubik's-cube of pigeonholes, where the assistant walks a marker from box to box, dropping off and picking up instructions.
- **How ErnosDecent does it:** A **3-D Turing-grid tape**: the head sits at an `(x,y,z)` coordinate key; `LEFT/RIGHT` move x, `IN/OUT` move y, `DOWN/UP` move z. Each cell can hold a string or a shell instruction; the agent can write, read, and execute a cell's contents, with the active cells visualised live in the dashboard.
- **How it serves freedom:** A transparent, inspectable reasoning workspace keeps the agent's "thinking" legible to its owner rather than hidden inside a black box.
- **Where it stands:** Working. Grid create/move/write/read/execute and the visualisation are implemented.

---

### decent_agent · observer gate — The safety supervisor

- **The human need:** An assistant that can run commands and write files could do real damage. There has to be a check that stops harmful actions *before* they happen — and fails safe if it's unsure.
- **The plain idea:** Before any dangerous action runs, a separate "observer" judges it against a written rule set and either allows or blocks it. If the judge is unavailable or gives a garbled answer, the action is **denied**, not waved through.
- **An everyday analogy:** A second pair of eyes who must sign off before anything risky goes ahead — and whose default answer, when they can't be reached, is "no."
- **How ErnosDecent does it:** `observer_audit` makes every audit decision via LLM inference (no hardcoded heuristics) and **fails closed** — the default verdict is BLOCKED; only an explicit ALLOWED verdict lets a dangerous tool (`run_command`, `codebase_write`) proceed. The rule set lives as inspectable data in `observer_rules.ep`, parsing is split into `observer_parser.ep`, and a separate deterministic moderation classifier backs the moderation tool.
- **How it serves freedom:** A sovereign agent must be *safe* to be trusted with real power on your machine. A fail-closed, inspectable guard keeps autonomy from becoming a liability — and keeps the rules in the owner's sight, not a vendor's.
- **Where it stands:** Working. The observer split (rules / parser / audit) and moderation are implemented and gated under agent-parity.

---

### decent_agent · providers & model router — Choosing which brain to use

- **The human need:** Different jobs suit different AI models, and you shouldn't be locked to one vendor. The agent needs to pick the right model and reach it wherever it lives — local or remote.
- **The plain idea:** A registry describes available models (where they live, how to talk to them, how big, whether they need a key), and a router picks the best fit for the task. The connection details are data, not hard-coded.
- **An everyday analogy:** A switchboard with a labelled directory of specialists. The router reads the job, checks the directory, and patches you through to the right one.
- **How ErnosDecent does it:** A **model registry/router** holds provider specs (name, base URL, port, API style `"openai"`/`"hf"`, size class, key requirement) and selection logic that's pure and deterministic. `llm.ep` consults it for endpoints and routing while preserving the proven live cascade; provider adapters cover **OpenAI-compatible** and **Hugging Face** APIs plus a streaming parser.
- **How it serves freedom:** No vendor lock-in. The owner decides which model answers — including fully local ones — so the assistant can never be quietly captured by a single provider's terms or politics.
- **Where it stands:** Working. The registry/router and OpenAI-compatible + Hugging Face providers are implemented and gated under agent-parity.

---

### decent_agent · platform bridge — Reaching the apps people already use

- **The human need:** Most people's contacts are on Discord, Telegram, or WhatsApp. A sovereign agent is more useful if it can meet them there without abandoning its own principles.
- **The plain idea:** Gateways relay messages between your node and mainstream chat platforms, so the local agent can read and reply in those apps. The node and the bridge talk over a simple internal command channel.
- **An everyday analogy:** A translator standing at the border who carries messages between your sovereign town and the big neighbouring cities, faithfully relaying both ways.
- **How ErnosDecent does it:** Platform **adapters** (configured in Settings) cover **Discord**, **Telegram**, and **WhatsApp**. A node↔bridge **RPC** channel (`bridge_poll` / `bridge_submit_result` in `node.ep`) lets the bridge fetch pending agent commands and return their results; the Discord 🔊 TTS button rides this path.
- **How it serves freedom:** Meeting people on existing platforms lowers the cost of leaving them — a migration bridge out of walled gardens, not a deeper lock-in.
- **Where it stands:** Partial. Discord bridge code plus Telegram/WhatsApp adapter registry exist (the Discord 🔊 path is wired but not bot-connected live); this is not the full breadth of the original 16 connectors.

---

### decent_agent · TTS voice — Giving the assistant a voice

- **The human need:** Reading every answer is tiring and excludes people who can't or prefer not to read on screen. People want their assistant to *speak*, without sending their text to a cloud voice service.
- **The plain idea:** Turn the agent's written reply into natural-sounding speech entirely on your own machine, and play it from the dashboard or a chat app.
- **An everyday analogy:** A narrator who lives in your house and reads your messages aloud — never phoning a studio, never recording what was said.
- **How ErnosDecent does it:** The **Kokoro** TTS engine (in decent_ai) drives a real ONNX voice model via FFI: text is chunked, phonemized to IPA (libespeak-ng), tokenized, synthesised by onnxruntime into 24 kHz audio, and written to a PCM16 WAV. The Web UI sends a `tts_request` over WebSocket; the node exposes a `TTS SPEAK` command; a 🔊 button appears on AI messages in both the Web UI and Discord.
- **How it serves freedom:** A local voice keeps even *how your assistant sounds to you* off corporate servers — accessibility and presence without surveillance.
- **Where it stands:** Working, verified end-to-end this session (Web UI 🔊 confirmed; Discord button wired but not bot-connected live).

---

### decent_consensus — Agreeing on the truth, even when nodes fail or lie

- **The human need:** When many machines share a ledger or a name registry, they must agree on one history — even if some crash, and even if some try to cheat. People need that agreement without a trusted central referee.
- **The plain idea:** The network elects a leader to coordinate the shared log; if nodes disagree, they can safely rewind to the agreed state. A stronger mode tolerates not just crashes but outright dishonest nodes.
- **An everyday analogy:** A committee with a rotating chair who keeps the official minutes. If the chair vanishes, the committee picks a new one; if someone tries to forge two contradictory minutes, the signatures expose them and they're penalised.
- **How ErnosDecent does it:** **Raft** elects a leader and replicates a log, committing only with a majority quorum (`⌊N/2⌋+1`), and an undo-stack lets followers **roll back** mismatched entries. A separate **PBFT-style BFT** mode adds Byzantine safety: a 3-phase agreement (PRE-PREPARE → PREPARE → COMMIT) over a 3f+1 validator set with 2f+1 quorums, every vote **Ed25519-signed**, and **slashing evidence** generated against any validator that signs two conflicting messages.
- **How it serves freedom:** Trustless agreement is what lets money, names, and shared state exist with no central authority — the cheat-proof referee is replaced by mathematics everyone can check.
- **Where it stands:** Working in test suites. Raft (election, replication, rollback) and BFT (signed 3-phase consensus with slashing) are implemented (5 modules, ~1,628 lines).

---

### decent_web — The dashboard you actually click

- **The human need:** All this power is useless if it's command-line only. People need a friendly window to see their node, send money, chat, and talk to the AI.
- **The plain idea:** A local web dashboard in your browser shows your node's status and lets you drive every subsystem. It doesn't hold any data itself — it just translates your clicks into commands to the daemon.
- **An everyday analogy:** The dashboard of a car. It doesn't *make* the engine run; it shows you what's happening and gives you the controls — wheel, pedals, gauges.
- **How ErnosDecent does it:** A **web server** serves the dashboard (`index.html`, `style.css`, `app.js`) and exposes REST endpoints (`/api/status`, `/api/wallet`, `/api/storage`, `/api/pool`) plus a **WebSocket gateway** (RFC 6455 framing) that turns events like `get_status`, `transfer`, `swap`, `ai_prompt`, and `tts_request` into IPC commands to the daemon on the control port. It owns no database — everything is proxied. (The UI is authored in `app.ep` and built into `app.js` by `build.sh`; `app.js` is never hand-edited.)
- **How it serves freedom:** A clear, local control panel keeps the whole sovereign stack usable by ordinary people, not just engineers — freedom you can't use isn't freedom.
- **Where it stands:** Working, now with TTS routes. The web UI server, dashboard, WS gateway, and TTS routes are implemented (2 modules, ~4,728 lines).

---

### Core node / daemon — The one program that runs it all

- **The human need:** Seventeen subsystems are no use as scattered parts. People need a single thing they can start that wires everything together, keeps your data, and stays up.
- **The plain idea:** One background program (`./node`) boots every subsystem, holds your identity and data, listens for commands on a local port, opens the network ports, checks its own health, and shuts down cleanly.
- **An everyday analogy:** The mains panel and plumbing of a house. You flip one main switch and the lights, water, and heating all come alive together, drawing from one supply.
- **How ErnosDecent does it:** `node.ep` (~2,109 lines) wires all subsystems and the structured IPC command surface; `protocol_server.ep` (~619 lines) accepts incoming P2P connections, runs the **Noise handshake**, and dispatches authenticated messages to the DHT/relay/consensus/messaging handlers; `storage.ep` (~842 lines) is the persistence layer (**SQLite** for structured data, the filesystem for content blobs). Supporting core files cover config, health checks, logging, and platform glue (~4,300 lines of core in total). It builds with `bash build.sh` and boots with the IPC control port and the web UI live.
- **How it serves freedom:** A single self-contained daemon on your own hardware is the physical embodiment of sovereignty: the entire stack lives under your roof, beholden to no one.
- **Where it stands:** Working — builds and boots, verified live this session. Caveat: the build can ship a stale binary if `node.ep` fails its whole-program type-check, so new symbols must be confirmed present in the fresh binary before trusting a build.

---

### GitDec — A code host nobody can take down

- **The human need:** Code hosting (GitHub and the like) is owned by single corporations that can delete repos, ban accounts, scrape your code, or be compelled to censor projects. Developers need to host and collaborate without that risk.
- **The plain idea:** A Git host built into your node that syncs repositories, issues, and pull requests over a decentralized network instead of a company's servers. Your code stays under your keys.
- **An everyday analogy:** Like GitHub, but the "company" is replaced by a network of peers, and the keys to every repo are held by the contributors themselves — so no landlord can evict the project.
- **How ErnosDecent does it:** Repositories live on local disk (`config/gitdec/repos/<id>/` with `gitdec.json`, `objects/`, `issues.json`, `pull_requests.json`). Real-time sync of manifests, pushes, issues, and PRs rides **Nostr** relays via dedicated event kinds (20020 manifest, 20021 push, 20022 issue, 20023 PR). Access is enforced by **Ed25519 signatures** checked against each repo's authorized-collaborator DIDs (owner/writer/reader), and clones discover the owner via the DHT.
- **How it serves freedom:** Source code is speech and infrastructure both. A host nobody owns means no project — however unpopular with some authority — can be erased or de-platformed.
- **Where it stands:** Working. Create/clone/comment/close, collaborator roles, and Nostr sync are implemented, including escaping and id-collision fixes.

---

### Business edition — The same engine, dressed for organisations

- **The human need:** Companies want a product that looks and reads like *theirs* — but the moment a "business version" forks the code, the free and paid editions drift apart and fixes stop flowing. Organisations need the polish without a captured, divergent codebase.
- **The plain idea:** The Business edition is a thin cosmetic layer — different prompts, persona, and branding — over the *identical* engine. With no special config it behaves byte-for-byte like the standard node; every fix made to the engine flows straight into it.
- **An everyday analogy:** The same car with a different badge and paint. The engine, safety, and wiring are unchanged — so a recall fix on the base model fixes the badged one too.
- **How ErnosDecent does it:** An **edition resolver** (`decent_agent/edition.ep`) picks which prompt/persona/branding assets load. With no `config/edition.json`, or `edition="default"`, every returned path is byte-identical to the original — main behaviour is unchanged. Crucially, the edition is **cosmetic only**: there is deliberately no field that can disable P2P/DHT/relay, so a business node is always a full mesh node. It lives on the public `business` branch (`README-Business.md`, `ANTI_CAPTURE.md`, `config/business/`); engine→business merges propagate features.
- **How it serves freedom:** This is the anti-capture design: because a business node *must* be a full mesh participant, commercial use strengthens the network instead of privatising it, and the AGPL plus mesh-derived savings keep the value flowing to the commons rather than to an owner.
- **Where it stands:** Working as designed. The overlay exists and is default byte-identical; it is a cosmetic edition, not a feature-gated fork.

---

*End of the System Bible. Status reflects `book/notes/status.md` as of 2026-06-21 on the `agent-parity` branch. "Working" = verified end-to-end or by test suite; "partial" = core proven, full original vision not yet reached. Numbers (17 subsystems, ~103 modules, ~30k source lines, 94 test files) supersede older "48 modules / 191 tests" claims.*
