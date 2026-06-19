# Sovereign Identity & Name Registry User Guide

This guide details the sovereign identity system and decentralized name registry mechanisms used by your node.

---

## 1. Sovereign Identity System (`decent_id`)

The core of ErnosDecent's trustless model is the Sovereign Identity subsystem. Instead of registering an account with a central entity or credentials provider, your identity is derived entirely from local cryptography.

### A. Decentralized Identifiers (DIDs)
A Decentralized Identifier (DID) is a W3C standard string that uniquely identifies you across the network without relying on a centralized database. ErnosDecent implements the **W3C DID Core v1.0** specification using two methods:
- **`did:key`**: A public key-based self-certifying identifier. The public key is encoded directly into the DID string, allowing anyone to resolve it locally without network queries.
- **`did:peer`**: A pairwise private identifier used to establish direct, secure connections between two specific peers.

### B. Cryptographic Keypairs
Each identity consists of two distinct types of cryptographic keypairs:
- **Signing Keypair (Ed25519)**:
  - Used for authentication, repository checkouts, commit signing (e.g. GitDec), message signatures, and session validation.
  - Ensures non-repudiation: only the holder of the secret signing key can generate valid signatures.
- **Encryption Keypair (X25519)**:
  - Used for end-to-end encryption (E2EE) in direct messaging, session key agreement (using Noise protocol or Diffie-Hellman), and securing file payloads.

### C. Deterministic Generation & Encoding
A `did:key` identifier is generated deterministically from an Ed25519 signing public key using the following steps:
1. Prepend the public key bytes with the **multicodec** identifier for Ed25519 (`0xed01` represented as hex).
2. Encode the resulting bytes using **Base58btc** (the Bitcoin alphabet variant).
3. Prepend the multibase encoding prefix **`z`** to signify Base58btc encoding.
4. Prepend the method prefix **`did:key:`**.
   *Example*: `did:key:z6MkjajSim1uQ5WFKx9acnwPF4Na3iHZjTehVPc97BPaJy29`

### D. Identity Lifecycle & Persistence
On daemon startup, the system checks if an identity already exists:
- **Load Existing**: The node loads saved identity credentials from persistent storage (`~/.ernosdecent` or SQLite database).
- **Create New**: If no identity exists, the daemon automatically generates a fresh pair of Ed25519 and X25519 keys on its first execution, derives the `did:key`, constructs a local DID Document, and saves them securely.

---

## 2. Decentralized Name Registry & Resolver (`decent_name`)

Since long DID strings (e.g. `did:key:z6Mk...`) are difficult for humans to write and remember, the decentralized Name Registry binds human-readable handles to cryptographic DIDs.

### A. Top-Level Domains (TLDs)
The registry is built on native peer-to-peer TLD mappings:
- **`.decent`**: Reserved for user handles, node profiles, and peer routing records (e.g. `alice.decent`).
- **`.ernos`**: Reserved for internal systems, developer utilities, and network daemon interfaces.

To prevent collision and namespace pollution, registration scripts enforce strict TLD validation: names must end in `.decent` or `.ernos`.

### B. The Resolution Workflow
When you request a name lookup (e.g. searching for `alice.decent`), the resolver processes the query through a 4-tier pipeline:
1. **In-Memory Cache**: The resolver first checks a fast local hashmap cache. If the record exists and is within its Time-to-Live (TTL) limit (default: 300 seconds), it returns the DID immediately.
2. **Persistent Storage (SQLite)**: If the name is missing from the cache, the resolver queries the node's local SQLite database. If a matching record is found, it updates the memory cache and returns the DID.
3. **Distributed Hash Table (DHT)**: If the local database has no record, the node queries the decentralized Kademlia DHT network using the key `name:<requested_name>` (e.g., `name:alice.decent`). If the DHT returns a value, the node saves it to local persistence, caches it, and returns the DID.
4. **Remote Peer DNS Resolver**: If all local and DHT options fail, the resolver establishes a direct transport socket connection to a known stable peer node and dispatches a `NAME_RESOLVE` RPC query. Upon receiving a response, the resolver validates it, saves it to persistence, adds it to the cache, and returns the DID.

### C. Name Registration & Ownership
To register a handle:
- The node verifies the name is not already taken locally.
- It writes the mapping `<name> -> <owner_did>` to the local SQLite database.
- It broadcasts the mapping as a key-value store request to the public DHT routing engine, securing your name lease across the network. Only the DID owner who registered the name can update or re-sign its routing destination.
