# *The Book of ErnosDecent* — Outline, Voice Guide & No-Jargon Method
*Working title options: **A System No One Owns** · **One Node** · **Built Without Permission** ·
**The Internet You Hold in Your Hand**. (Maria to choose.)*

This is the blueprint for the manuscript. It is grounded in the research notes in `book/notes/`
(philosophy-and-voice, quotes, foundations, ernosplain, story, status, system-bible). The book is a
**comprehensive, jargon-free volume**, structured as a **system-first tour**, with Maria's mission
and story as the spine that carries the reader between the technical chapters.

---

## A. The promise of the book (one paragraph, for the back cover)

You do not need a degree, a coding background, or anyone's permission to understand this book. It is
the plain-language story of ErnosDecent: a single program you run on your own machine that quietly
replaces the things you currently rent from large companies — your identity, your messages, your
files, your money, your website, your video, even your AI — with no company sitting in the middle.
It explains, piece by piece, in everyday words, how each part works, why it was built, how far it has
got, and what is left to do. And it tells the story of the woman who built it: one person, no formal
education, who taught herself to do all of this, because she believes the systems people need to learn
and to live should belong to everyone and be owned by no one.

---

## B. The No-Jargon Method (the rule every chapter obeys)

1. **No undefined word.** Any technical term is translated *the first time it appears*, in the
   sentence itself: "a *Kademlia DHT* — really just an address book spread across everyone's machines."
2. **Analogy before mechanism.** Every concept gets a concrete, everyday picture (a wax seal, a
   neighbourhood, a filing cabinet, a worn footpath) *before* any explanation of how it actually works.
3. **The reader is never made to feel stupid.** Sentences reset often. Nothing depends on a paragraph
   you read ten pages ago without a reminder.
4. **Show, don't dazzle.** No term is used to impress. If a fact can't be explained simply, it is
   explained simply or left out.
5. **Honesty over hype.** Working is working; partial is partial; planned is planned. (Maria's own
   AGENT.md law, applied to prose — see `notes/status.md`.)
6. **A running glossary.** Every translated term also lands in the back-matter glossary, so a reader
   can look anything up in one place.
7. **The "two readers" test.** Each chapter must land for both a curious 14-year-old and a busy
   policy-maker. Phase D audits every chapter against this.

---

## C. The Voice Guide (so the whole book sounds like Maria)
*Distilled from `notes/philosophy-and-voice.md`. The book is written in her register — but it is a
calmer, warmer cousin of the* Last Mind *voice: less prosecutorial, because this book is about what
she* built*, not whom she accuses.*

- **Declarative cold opens.** Start sections with a short, plain, true sentence, given room to breathe.
  *"There is a key. Only you hold it."*
- **Short hammer sentences against long ones.** Alternate rhythm. Let a four-word sentence land after
  a long one.
- **Triads and repetition.** Her signature cadence: *"The roots are traceable. The names are named.
  The dates are dated."* Use restrained, earned repetition.
- **Second person.** Talk to the reader. *"Your keys are yours. Your data stays on your machine."*
- **Name plainly; never hedge.** Avoid "arguably/perhaps/it could be said." Say the true thing.
- **Refuse despair.** Her core affect: diagnosis without an exit is despair, and she refuses it. The
  book's emotional through-line is *there is a way out, and it runs.*
- **"Audit it."** The book invites checking, not belief. *"The work is on disk. It runs. Audit it."*
- **Dignity in the personal.** Where her life appears, it is plain and unsentimental, never pitying.
- **Quotes:** use the short attributed lines in `notes/quotes.md` sparingly (an epigraph per part, the
  occasional in-text line). Never long passages.

---

## D. The recurring chapter pattern (every subsystem chapter)
Each system chapter is a gentle six-beat arc (mirrors `notes/system-bible.md`):
1. **The human need** — the ordinary problem, in human terms.
2. **The plain idea** — what this part does, in 3-4 sentences.
3. **An everyday analogy** — the vivid picture.
4. **How ErnosDecent does it** — the real mechanism, named and explained.
5. **How it serves freedom** — the tie back to the mission (free of academic/financial/political/
   religious control).
6. **Where it stands** — the honest status (working / partial / planned), from `notes/status.md`.

---

## E. Structure — 8 Parts, 28 chapters (comprehensive volume)

### Front matter
- Title page; epigraph (one short line from `quotes.md`).
- **How to read this book** — you need no background; read in order or dip in; every term is
  explained; you are invited to audit, not to believe.

### PART ONE — THE MISSION AND THE MACHINE *(the "why" and the big picture)*
> **NOTE (per Maria):** This book is **about ErnosDecent, not about her.** Her story is *reference,
> not focus* — touched only briefly, factually, where it serves the reader (chiefly as proof of the
> book's promise: that no permission, credentials, or background are needed to understand or run
> this). There is **no biography chapter.** A short preface may note, in a line or two, that the
> system was built by one self-taught person and point readers to *Behind the Creator* for the
> personal account. Everything else is the mission and the system.
- **1. What ErnosDecent is, and why it exists.** The mission stated up front — systems of learning and
  living that belong to everyone and are owned by no one, free of academic/financial/political/
  religious control — and the plain picture of what the software actually is. Her background appears
  only as a single reference point (built by one self-taught person, no institution) because it proves
  the reader needs no permission either.
- **2. The world as it's handed to us.** Why this is needed: the four-masks argument, stated directly
  (per Maria's instruction) as her documented case — academic, financial, political, religious control
  as one system. What those locks cost ordinary people. (Guardrail still applies to *new* specific
  allegations about named living individuals — see §F.)
- **3. The shape of an exit.** What a genuinely free system would *have* to be — owned by no one,
  readable by anyone, running on your own machine. "The substrate is not the obstacle; the deployment is."
- **4. A language anyone can read.** ErnosPlain: code that reads like plain English, and why that is a
  political act, not just a convenience (from `notes/ernosplain.md`). A tiny real example vs. ordinary
  code. The tool the whole thing is built in.
- **5. One axiom, and a theory of everything.** The root: the Smithian Fold Theory of Everything in
  plain language (one axiom "the One," one move "the fold," zero free parameters), the proof it runs and
  matches measured reality, the honest scope (independently reproduced by two AI systems; not yet
  examined by the physics field; new predictions await experiment), the hermetic vision underneath, and
  why it is the proof-of-method for the whole book — truth anyone can check, owned by no one, built
  without permission. (From `notes/foundations.md`.)
- **6. How it all hangs together.** The concrete picture before the parts: one program (a "node") on
  your machine; many nodes finding each other directly (a "mesh"); a daemon running the services; no
  company in the middle. How to picture the whole thing before we open it up.

> **Numbering note:** the Theory-of-Everything chapter was inserted at **5** (per Maria), so every
> chapter from Part Two onward shifts **+1** from the numbers shown below (identity is Ch 7, etc.).
> The titles and groupings are unchanged.

### PART TWO — YOU: IDENTITY & MONEY
- **6. Who you are, with no one's permission.** `decent_id` — keys, signatures, DIDs, capability auth.
- **7. Money you actually hold.** `decent_money` part 1 — wallets, the shared ledger, proof-of-stake.
- **8. Trading without a middleman.** `decent_money` part 2 — tokens, NFTs, the DEX, smart contracts.

### PART THREE — TALKING: CONNECTION, MESSAGES, A VOICE TO THE WORLD
- **9. Finding each other.** `decent_net` — Noise handshake, the DHT address book, relays, NAT.
- **10. Private words.** `decent_msg` — end-to-end encrypted DMs and group channels.
- **11. Publishing without a platform.** `decent_social` — Nostr + ActivityPub, unified feeds.
- **12. Disappearing into the crowd.** `decent_anon` — onion routing and mix networks.

### PART FOUR — REMEMBERING: STORAGE, NAMES, FINDING THINGS
- **13. Keeping things, together.** `decent_store` — content addressing (BLAKE3) and CRDTs (how two
  copies merge with no boss to settle the argument).
- **14. Names that can't be repossessed.** `decent_name` — decentralized DNS, `.decent`/`.ernos`.
- **15. Searching a web no one owns.** `decent_search` — crawler, BM25 + PageRank, merged results.

### PART FIVE — MAKING & SERVING: HOSTING, MEDIA, SHARING THE LOAD
- **16. Be your own website and post office.** `decent_host` — HTTP, SMTP/IMAP, P2P Git.
- **17. Live video, neighbour to neighbour.** `decent_media` — WebRTC, HLS, real Opus/VP8, P2P CDN.
- **18. Lending the mesh your strength.** `decent_pool` — bandwidth tiers, shared compute, symbiosis.

### PART SIX — THINKING: AI THAT ANSWERS TO YOU
- **19. A mind on your own machine.** `decent_ai` — local model inference, embeddings, speech-to-text;
  why "your prompts never leave your machine" matters.
- **20. A companion that learns and remembers.** `decent_agent` part 1 — the ReAct reasoning loop, the
  7-tier memory, the knowledge graph, procedural memory.
- **21. A mind with a conscience.** `decent_agent` part 2 — the observer gate (fail-closed), the model
  router/providers, the Turing-grid workspace.
- **22. Giving it a voice, and a way to reach you.** The Kokoro TTS voice (🔊) and the platform bridges
  (Discord; Telegram/WhatsApp adapters) — verified and honest about what's live.

### PART SEVEN — AGREEING & GOVERNING: HOW "NO ONE OWNS IT" WORKS
- **23. How strangers agree.** `decent_consensus` — Raft, leader election, rolling back a liar.
- **24. The dashboard and the daemon.** `decent_web` + the core `node`/`protocol_server`/`storage` —
  how all the parts run together as one program you can watch in a browser.
- **25. Keeping the commons a commons.** Anti-capture by design, the AGPL licence, and GitDec (issues
  and code that live in the mesh itself).
- **26. The Business edition.** The public fork: how a company can adopt it and *strengthen* the mesh
  rather than enclose it — utility that comes *from* decentralization, not in spite of it.

### PART EIGHT — WHERE IT STANDS & WHY IT MATTERS
- **27. An honest ledger.** What works today, what is partial, what is still ahead (from
  `notes/status.md`) — written without hype, because that is the whole point.
- **28. One woman, no permission, a working system.** The close: tying ErnosDecent back to the Theory
  of Everything and the wider corpus; the refusal of despair; the invitation to run it, fork it,
  audit it, and build.

### Back matter
- **Glossary** — every translated term, in plain English.
- **Appendix A — Run it yourself.** The simplest honest path to booting a node.
- **Appendix B — The wider work.** Short, honest pointers to the Theory of Everything, ErnosPlain,
  and the *Last Mind* series (where the four-masks argument and its named claims live).
- **A note on sources & honesty.** How the status was verified; the attribution guardrail.

---

## F. Guardrails (carried into every chapter)
- **Attribution, not republication.** The four-masks thesis is presented as *Maria's argument from her
  other books*; specific grave allegations against living individuals are **not** restated as this
  book's findings — readers are pointed to the *Last Mind* series. (See `notes/philosophy-and-voice.md`.)
- **Her worldview is hers.** Totalizing claims are rendered faithfully as her view, recorded with
  respect, not asserted as settled fact by the book.
- **Status is verified.** No capability is claimed beyond `notes/status.md`; the manuscript's Part
  Seven and every "Where it stands" line are checked against the code in Phase D.

---

## G. Scale & process
- ~28 chapters; comprehensive (~300+ pages). Drafted chapter-by-chapter (parallel writers from the
  notes), then edited by me for one consistent voice and zero jargon.
- **Checkpoints:** (1) now — these notes + this outline, for Maria to steer; (2) after a sample
  chapter, to lock the voice before the full draft; (3) before Phase E design, on the finished text.
