# Resource Pooling User Guide

This guide details how your node contributes bandwidth and computational power to the decentralized peer-to-peer network, and how telemetry tracks your contributions.

---

## 1. Decentralized Resource Sharing Architecture

The ErnosDecent mesh network is built on reciprocal cooperation. To avoid reliance on centralized cloud providers, the network leverages the spare bandwidth and compute capacity of its individual node operators. By contributing local resources, you earn routing priority, higher transfer speeds, and elevated slots for decentralized AI and ledger execution.

---

## 2. Bandwidth Pooling

Bandwidth sharing helps route and serve network payloads (messages, Git repository data, and onion-routed web traffic) for other peers.

- **Shared Upload**: The amount of outbound data your node has served to route traffic, seed content-addressed payloads, sync Git repositories, or relay messages for firewalled peer nodes.
- **Shared Download**: The amount of inbound data your node has consumed from the network to sync files, pull repositories, or receive messages.
- **Bandwidth Tier**: A categorization of your node based on your sharing contribution. Nodes that maintain a high upload-to-download ratio are placed in higher tiers (e.g., Premium or Super-Node), giving them priority routing status and faster response times from other peers.
- **Contribution Multiplier**: A dynamic score reflecting your node's net positive contributions. A higher multiplier increases your node's request prioritization and gossip routing speeds across the global network tree.

---

## 3. Compute Pooling Allocation

Compute pooling allows you to delegate CPU/GPU cycles to execute tasks for the cooperative network, such as verifying blocks, interpreting smart contracts, or performing background cognitive loop runs.

- **Active Delegation Slots**: The number of concurrent worker slots your node has made available to the network. These slots are consumed by other nodes to offload smart contract calls, verify transactions, or delegate reasoning loops.
- **Consensus Score**: A trust metric representing the accuracy and reliability of your node's consensus outputs. It rises when your node correctly validates UTXO ledger state mutations and successfully participates in Raft elections, and falls if your node proposes invalid block commits or fails heartbeat deadlines.
- **Compute Contributed Today**: A live progress meter representing the cumulative computational work units (in cycles or task completions) that your node has successfully processed and contributed to the network within the current 24-hour cycle.
