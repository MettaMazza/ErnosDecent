# Messaging & Social Protocols User Guide

This guide details the operations of the peer-to-peer messaging client and federated social publishing systems.

---

## 1. Decentralized P2P Encrypted Messaging (`decent_msg`)

ErnosDecent features a fully peer-to-peer, encrypted messaging system that operates without central servers or message routing directories.

### A. Communication Channels
Group channels allow nodes to publish and subscribe to specific chat topics over the P2P gossip protocol:
- **Default Channels**:
  - `#general-mesh`: The main chat room for global peer communication and gossip.
  - `#raft-consensus`: A channel dedicated to consensus logs, election updates, and node state reports.
  - `#local-ai-dev`: Discussion and prompt exchanges relating to local LLM inference execution.
- **Mechanism**: Every channel message is cryptographically signed by its sender's signing key and broadcast to all subscribed peers in the Gossipsub tree.

### B. Direct Messages (DMs)
Direct Messages offer private, end-to-end encrypted (E2EE) communication between two specific peer identities (DIDs):
- **E2EE Handshake**: Direct messages establish secure tunnels using X25519 key agreements (Diffie-Hellman exchanges) to derive symmetric session keys.
- **Symmetric Encryption**: Messages are encrypted locally using symmetric ciphers (e.g. AES-GCM or ChaCha20-Poly1305) before transmission, ensuring only the target recipient holds the keys to decrypt the message payload.

### C. Message Storage & Persistence
Unlike web-based chat clients, all message histories, channels, and conversation threads are stored locally in the node's SQLite database (`decent_msg/messages.db` or root persistent storage). Conversations and message statuses are loaded dynamically on page startup.

---

## 2. Federated Social Publishing (`decent_social`)

ErnosDecent integrates two open social protocols to aggregate updates and broadcast social publications across the wider decentralized web.

### A. The Nostr Protocol
Nostr (Notes and Other Stuff Transmitted by Relays) is a lightweight, censorship-resistant social protocol:
- **Key-Based Identity**: Users are identified by their public cryptographic keys. Posts, reactions, and profile updates are constructed as JSON events and signed using Ed25519 private keys.
- **SHA256 Event Serialization**: Events are strictly serialized and hashed via SHA256 before signing, ensuring payload integrity.
- **Relay Servers**: Nodes push signed events to multiple independent Nostr relays over WebSockets. Relays do not store account details; they only store and query signed events based on subscription filters.
- **GitDec Integration**: Nostr is also used as a metadata channel for GitDec (decentralized Git engine), syncing repository manifests (`gitdec.json`) and commit notifications across collaborators.

### B. ActivityPub Federation
ActivityPub is the W3C standard for federated social networking. It uses actor inbox and outbox delivery models to federate content across Fediverse instances (such as Mastodon, Lemmy, and Pixelfed). Your node is equipped with a local inbox and outbox handler to register followers and route social activities directly.

### C. Unified Chronological Feed
The social interface aggregates posts from both Nostr relays and ActivityPub inboxes. The unified feed normalizes these distinct protocols into a standardized schema and sorts them chronologically to show a cohesive Digital Feed on your dashboard.
