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

## 2. Dynamic Host Nodes & Fallback Tree

To maintain high availability and survive network partitions or seed node failures, the system implements a dynamic routing and fallback structure.

### A. Fallback Host Architecture
P2P nodes depend on seed hosts to bootstrap themselves into the gossip network and route traffic across NATs (using relay nodes). Rather than relying on a static, single point of failure, ErnosDecent employs a ranked list of available seed hosts:
- **Elected Primary Seed Host**: The highest-priority host currently serving as the main entrypoint and relay gateway for network communications.
- **Dynamic Host Election**: When enabled, the network peers participate in consensus-based leader elections to automatically choose a new host node if the current primary seed goes offline.
- **Static Host Priority**: When enabled, the local node bypasses the fallback election tree to prioritize a manually configured seed node, ensuring stable connection routing to a known trusted host.

### B. Fallback Telemetry Tree Metrics
The hosts list is presented in a live table ranked by active external connections. High connection numbers indicate high capacity, elevating the host's rank. The table displays:
- **Rank**: The calculated priority position (e.g., Rank 1 is the primary seed host, Rank 2 is the secondary fallback, etc.).
- **Node ID / Address**: The target peer's cryptographic node ID and TCP/UDP connection address.
- **Active Connections**: The count of concurrent external TCP socket connections managed by the host.
- **Priority Mode**: Indicates whether the host is dynamically elected or running in static preferred host mode.
- **Last Seen**: The time elapsed since the local node last received a successful ping handshake or keep-alive message from the host, confirming its operational health.

### C. Manual Controls
- **Refresh List Button**: Issues a real-time IPC query to request the latest host election routing tree from the daemon, updating the table with current peer telemetry.
