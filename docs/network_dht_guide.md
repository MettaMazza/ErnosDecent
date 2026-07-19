# Network & Kademlia DHT User Guide

This guide details how your node interacts with the decentralized P2P network, utilizes the Kademlia DHT key-value store, and participates in dynamic host elections and fallback routing.

---

## 1. Decentralized Kademlia DHT Key-Value Store

The Distributed Hash Table (DHT) is a decentralized storage network that allows keys to map to values across all online nodes in the peer-to-peer network without relying on a central database.

### A. Core DHT Actions
The DHT panel provides direct interfaces to query and publish values to the distributed network:
- **Store Action**:
  - Takes a user-defined **Key** and **Value** and distributes it across the P2P network.
  - The node computes the hash of the key, locates the closest active peer nodes in the routing table (using the XOR distance metric), and dispatches RPC requests to store the key-value pair on those target peers.
  - Key-value stores persist on target nodes according to the configured DHT TTL (Time-To-Live).
- **Get Action**:
  - Retrieves the value associated with a specific **Key** from the network.
  - The node queries its local routing table, finds the closest peers to the requested key, and sends lookup queries. If those peers do not have the value, they return the contact information of closer peers they know about. The lookup loop runs recursively until the value is found or lookup limits are reached.

### B. Telemetry & Logs
The DHT Key-Value Store panel contains an operations log box at the bottom. It displays real-time execution outputs, including:
- Success or error notifications for store actions (e.g. peer contact results).
- Returned payload content, target peer addresses, and query performance metrics for get requests.

---

## 2. Bootstrap and Host Election

> **Public-bootstrap pre-launch status — 19 July 2026:** TCP `9100` and `9101` on the
> operated node were independently reachable, while DDNS and public forwarding for
> `9102` through `9104` remained deferred. Consequently, the repository intentionally
> ships no automatic public seed. Fresh nodes require an explicit seed or a verified
> cached peer until the complete launch gate below has been verified.

A node can join an existing mesh only when it knows at least one reachable DHT endpoint. Bootstrap candidates are tried in this order:

1. An explicit `--seed host:port` value or `network.seed_addr`/`network.seed_port` configuration.
2. Previously verified endpoints stored in `~/.ernosdecent/peers.txt`.

No external seed is hard-coded. Shipping a literal third-party or residential IP would make an unverifiable availability claim. The operated bootstrap node is configured with `network.is_static_host = 1`; it serves as a root and does not dial the operated default aliases that will represent itself. Explicitly configured and previously verified cached peers remain eligible. When no non-self candidate exists, the node explicitly becomes a mesh root and waits for other nodes to connect.

Each candidate must have a dialable host and a port from 1 through 65535. Wildcard listener addresses such as `0.0.0.0`, `::`, and `[::]` are rejected and removed from the peer cache. A connection is accepted as a DHT bootstrap only after the remote endpoint returns an actual framed `DHT_PONG`; connection, send, receive, invalid-response, close, registration, and invalid-endpoint failures have distinct error codes.

The node advertises `network.public_host`, or its detected public IP, in outbound DHT and relay registration. The configuration loader, generated configuration, saved configuration, and dashboard all preserve `network.public_host`. If neither produces an advertisable address, outbound bootstrap is disabled instead of publishing a wildcard or loopback fallback as a remote endpoint.

Raft host election operates among peers that have already connected. It does not create connectivity, discover an offline seed, or convert an unreachable endpoint into a reachable one. Operators remain responsible for running at least one seed node and exposing TCP `9101` through every host firewall and NAT device. Full mesh service requires TCP `9100` through `9104`; IPC `5000` and Web `8088` remain loopback control surfaces.

A hostname may be added to `ernos_default_seeds()` only after its A/AAAA record resolves to the operated node and an independent external probe receives a valid framed `DHT_PONG` on TCP `9101`. The static root must set that same hostname as `network.public_host`. This prevents both stale residential-IP defaults and DNS-alias self-bootstrap loops.

The public-bootstrap launch gate is complete only when all of the following are true:

1. A stable DDNS hostname follows the operated node's current public address.
2. TCP `9100` through `9104` are independently reachable from outside the operator LAN.
3. A remote client receives a valid framed `DHT_PONG` from the hostname on `9101`.
4. The operated node advertises that hostname and does not add itself as a peer.
5. Only after steps 1–4 pass is the hostname added to `ernos_default_seeds()`.
