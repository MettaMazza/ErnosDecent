# Phase 14: Node Daemon & Cross-Platform Packaging

> **Archived design record.** This proposal predates authenticated IPC/WebSocket
> control and the current port layout. Use [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)
> and the repository README for implemented behavior.

This plan outlines the architecture, design, and integration details for the final phase of ErnosDecent: the coordination daemon (`node.ep`) and the control CLI (`decent_cli/`).

## Goal Description

To unify all 13 completed peer-to-peer subsystems into a single running daemon (`node.ep`) that acts as a background process (daemon), and build a CLI client (`decent_cli.ep`) that communicates with it over a local socket connection (IPC) to inspect and control the node.

---

## Proposed Changes

### Core Subsystems Coordination

We will build the node coordinator at the root of the workspace.

#### [NEW] [node.ep](../node.ep)
The daemon executable coordinating all subsystems. It does the following:
1. **Bootstrap Sequence**:
   - Initializes libsodium cryptography (`init_crypto()`).
   - Loads/generates node keypair and DID (`create_identity()`).
   - Initializes local storage databases (content store, CRDT index).
   - Starts peer routing tables (Kademlia DHT).
2. **Daemon Threads**:
   - Spawns background loop for DHT discovery and Noise overlay peer syncing.
   - Spawns election tick timers and append entries replication loops for the Raft consensus group.
   - Starts TCP socket listener for SMTP (port 25), IMAP (port 143), and HTTP (port 8080) hosting.
3. **IPC Server**:
   - Listens on `127.0.0.1:5000` for command connections from `decent_cli`.
   - Reads incoming commands (e.g. `STATUS`, `STOP`, `WALLET_BALANCE`), executes the corresponding subsystem calls, and writes the text/JSON responses back.

#### [NEW] [decent_cli/decent_cli.ep](../decent_cli/decent_cli.ep)
The command-line control interface client:
1. **Argument Parsing**: Parses CLI args (e.g., `status`, `stop`, `peer add <did>`, `wallet balance`, `mail list`).
2. **Socket Client**:
   - Connects to the daemon's local IPC port (`127.0.0.1:5000`).
   - Sends the parsed command text.
   - Receives and formats the daemon's response to `stdout`.

#### [NEW] [decent_cli/test_cli.ep](../decent_cli/test_cli.ep)
Integration test checking daemon boot and CLI command execution:
1. Starts the `node.ep` daemon thread.
2. Simulates CLI calls via the socket IPC interface.
3. Asserts correct status outputs, wallet balances, and clean shutdown on `STOP` command.

---

## Verification Plan

### Automated Tests
- Build and run the integration test suite:
  ```bash
  "/Users/mettamazza/Desktop/ErnosPlain Programing Language/target/release/ernos" decent_cli/test_cli.ep && ./decent_cli/test_cli
  ```
- Asserts that all IPC commands respond with valid metrics.

### Manual Verification
- Compile the final daemon and CLI:
  ```bash
  "/Users/mettamazza/Desktop/ErnosPlain Programing Language/target/release/ernos" node.ep
  "/Users/mettamazza/Desktop/ErnosPlain Programing Language/target/release/ernos" decent_cli/decent_cli.ep
  ```
- Start the daemon `./node` in one terminal window.
- In another window, run command clients:
  - `./decent_cli/decent_cli status`
  - `./decent_cli/decent_cli wallet balance`
  - `./decent_cli/decent_cli stop` (verifies clean shutdown of all threads).
