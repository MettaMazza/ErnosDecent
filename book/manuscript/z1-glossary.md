# Back Matter

## Glossary — Every Word, in Plain English

Every term the book uses, defined the way it is used here. Nothing in this book required you to already
know any of these; this page is only so you can look one up again.

**ActivityPub** — The open rule-set that lets independent social communities talk to each other (the
standard behind Mastodon). It is how separate servers "federate" — share posts across the lines that
divide them — with no single company in charge.

**AGPL** — The licence ErnosDecent is released under. In plain terms: if you use and change the code,
even just to run it as an online service, you must give your changes back to everyone. It closes the
loophole where a company takes free code, improves it privately, and sells it back.

**AMM (automatic market maker)** — A way to trade one token for another with no buyer waiting on the
other side: a pool of two tokens prices them automatically by a simple rule (when one is bought, it gets
dearer). The "always-open, self-balancing money-changer."

**Block** — One page of the shared ledger: a batch of transactions added in order.

**BM25** — A way of scoring how well a page matches what you searched for, counting rare words more than
common ones.

**Capability** — A signed permission you simply hold, that proves you may do one specific thing — a
*ticket*, not a name on a guest list. It needs no central doorman to check it.

**CDN (content delivery network)** — Normally, a company's farm of servers that store popular content
close to you. Here, the nodes themselves do it: your node relays to a few neighbours while pulling from
a few others.

**Codec** — The method that squeezes audio or video small enough to send and unpacks it at the other
end. ErnosDecent uses real ones — *Opus* for sound, *VP8* for video.

**Consensus** — Agreement, among many equal machines with no boss, on one shared order of events — so the
ledger and shared data do not split into contradictory versions.

**Content-addressed storage** — Storing a file under a name made from its own contents, so identical
files are automatically the same file and nothing can be altered in secret without changing its name.

**CRDT (conflict-free replicated data type)** — Data built so two people's copies can both be edited
offline and then merge automatically, always landing on the same answer, with no central server to
settle the conflict.

**Daemon** — A program that runs quietly and continuously in the background — the node's engine room —
rather than an app you open and watch.

**DEX (decentralized exchange)** — A marketplace for swapping tokens that runs on the network itself,
with no company holding your funds or taking the seat in the middle.

**DHT (distributed hash table)** — A shared address book spread across everyone's machines. To find a
record you ask the neighbour "closest" to it, who points you closer, and in a few hops you find anyone —
with no central directory. ErnosDecent uses the *Kademlia* design.

**DID (decentralized identifier)** — A self-describing name, like `did:key:z6Mk…`, that anyone can verify
on their own machine without consulting a central database. Your name carries its own proof.

**Diffie–Hellman** — A method by which two people, talking in the open, arrive at a shared secret no
eavesdropper can work out — like mixing a colour only the two of them can reproduce.

**DNS (domain name system)** — The internet's phone book, turning names into addresses. ErnosDecent keeps
its phone book in the shared network instead of with central registrars.

**DTLS / SRTP** — The scrambling that keeps a live call readable only at the two ends.

**Ed25519** — The specific, well-tested method ErnosDecent uses for *signing* — stamping something so
anyone can confirm it is genuinely from you and no one can forge it.

**Embeddings** — Turning text into points in a "space of meaning," so the system can find things by what
they mean, not just by matching words. Similar ideas sit near each other.

**End-to-end encryption** — Sealing a message so only the sender and the intended reader hold the keys to
open it; no server in between can read it.

**FFI (foreign function interface)** — The ability of one language to call directly into code written in
another. It is how the plain-English language drives real C libraries (cryptography, audio, video).

**Gas** — A small fuel cost charged to a running program (a smart contract), so a runaway or malicious
program cannot loop forever or drain the network.

**GGUF** — A packaged file format for an AI model — the bundle of learned numbers — that you can download
and run yourself on your own machine.

**Git** — A shared, complete history of a project that records every change and who made it. ErnosDecent
hosts it peer-to-peer, with each change cryptographically signed.

**GitDec** — ErnosDecent's own issue-and-code tracker, kept in the mesh itself rather than on a company's
website that could delete it.

**Hash** — A fingerprint of data: a short string that changes completely if even one byte changes.
ErnosDecent uses *BLAKE3*. Used to name files by their contents and to detect tampering.

**HD wallet** — A wallet whose every key can be regenerated from one *seed phrase* (a short list of
ordinary words). Keep the words safe and you can rebuild the whole wallet on a new machine.

**HLS** — A way of streaming video by chopping it into small pieces at several qualities, so playback
adjusts smoothly to a fast or slow connection.

**HTTP server** — A program that answers web requests — what serves a website. Your node can be one.

**Key (public / secret)** — A pair of very long numbers your machine makes. The *public* key is your
name on the network, shareable with anyone; the *secret* key, kept only by you, proves you are you and
unlocks what is yours.

**Keystore** — The encrypted file on your own disk that holds your secret keys, locked with a passphrase
that is deliberately slow to guess.

**Ledger** — A record of who owns what. ErnosDecent's is *shared* — many people keep identical copies and
update them together — instead of held privately by a bank.

**Local-first** — Running on your own machine, with your data living with you, reaching out to others only
when and how you choose — the opposite of "in the cloud."

**Mesh** — Many nodes connected directly to one another, like a net with no centre, instead of all routed
through a central hub.

**Merkle tree** — "Fingerprints of fingerprints": a structure that lets two machines quickly find exactly
which pieces of their data differ.

**Mix network** — A privacy technique that shuffles and randomly delays messages so a watcher cannot link
who sent what to whom by timing.

**Model** — In AI, a large file of learned numbers that predicts text (or speech, or more). Running it
"locally" means on your own computer, so nothing is sent to a company.

**NAT traversal** — The trick that lets two computers behind home routers reach each other directly. Hard;
ErnosDecent does part of it now (relays), with the fuller version still ahead.

**NFT** — A one-of-a-kind digital token recording ownership of a specific item, in the *ERC-721* style,
optionally paying the creator a royalty on resale.

**Node** — One running copy of ErnosDecent — the single program you install. Every node is equal; there
is no head node.

**Noise (XX handshake)** — A modern secret handshake two nodes perform when they connect, so the
conversation is encrypted and both sides are verified from the very first byte.

**Nostr** — A simple open standard for publishing: tiny signed notes passed around by relays that anyone
can run.

**Onion routing** — Wrapping a message in layers of encryption and passing it through several relays, each
peeling one layer, so no single relay sees both where it came from and where it is going. The idea behind
Tor.

**PageRank** — Ranking a page as more trustworthy the more other trusted pages link to it — a
recommendation from someone everyone recommends counts more.

**Peer-to-peer** — Computers talking to one another directly, as equals, with no central server between
them.

**Proof-of-stake** — Deciding who may add the next page to the shared ledger by a fair lottery among those
who have locked up their own coins as a bond: cheat and you lose the bond. Honesty is made the profitable
choice.

**Raft** — The specific consensus method ErnosDecent uses: a group of equals elects a temporary leader,
who proposes new entries the others copy once a majority confirms; if the leader fails or lies, a new one
is elected.

**ReAct loop** — How the agent works through a problem: think, take an action with a tool, observe the
result, repeat — instead of blurting a single answer.

**Relay** — A node that passes traffic along so two others who cannot reach each other directly (behind
routers) still can.

**Seed phrase** — A short list of ordinary words that is a human-friendly form of the one secret behind
all your wallet keys. The words *are* the money; guard them.

**Smart contract** — A small program that holds and moves value and runs exactly as written, releasing
funds only when its conditions are met — an agreement that keeps itself, with no notary or bank to
enforce it.

**Speech-to-text / text-to-speech** — Turning your voice into written words, and turning written words into
spoken voice. ErnosDecent does both on your own machine. Its voice uses a neural model called *Kokoro*.

**Token** — A unit of value you can create on the ledger (in the *ERC-20* style) — your own currency,
points, or shares.

**UTXO ledger** — Tracking money as distinct coins you hold and spend (getting change), like physical
cash, rather than as one running balance — the bookkeeping style Bitcoin uses.

**WebRTC** — The technology for direct, live audio and video between devices, without a company's server
carrying the call.

**WebSocket** — An open, two-way "phone line" between a web page and a program, so updates appear the
moment they happen. It is how the dashboard shows your node live.

**X25519** — The method ErnosDecent uses for *encryption* key agreement — for sealing messages so only the
intended reader can open them (the companion to Ed25519, which is for signing).
