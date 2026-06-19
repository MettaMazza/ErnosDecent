# Sovereign Dashboard — Unified App Implementation Plan

We will design and build a premium, fully integrated Sovereign Dashboard app wired directly into the ErnosDecent node daemon. The dashboard will expose real-time metrics and controls for all 14 peer-to-peer subsystems: Identity/DID, DHT routing, storage collections, E2E encrypted messaging, social publishing (Nostr & ActivityPub), ledger wallet transactions, local transformer AI inference, WebRTC media streaming, onion privacy, search crawl/query, resource pooling, and Raft consensus.

---

## User Review Required

> [!IMPORTANT]
> - **Unified HTTP/WebSocket API**: To power real-time updates and low-latency interaction (e.g. AI streaming chat, instant messages, and live consensus state changes), we will extend the `node.ep` background daemon to serve as a dual HTTP API server (serving static files and REST JSON endpoints) and a WebSocket server (`import "websocket"`) on port `8080`.
> - **Premium Glassmorphic Visuals**: The front-end interface will be implemented as a Single-Page Application (SPA) inside `decent_web/` using vanilla HTML, vanilla CSS (implementing dark mode, glassmorphism, responsive sidebar layout, and micro-animations), and modern JavaScript.
> - **Integration Framework**: Subsystems currently operating in memory inside `node.ep` will export JSON status snapshots through dedicated coordinator controllers. For example, local AI transformer queries will stream token responses back to the Web UI over a WebSocket tunnel.

---

## Open Questions

> [!WARNING]
> - **Port Binding conflicts**: The daemon currently binds to TCP port `5000` for CLI-focused socket IPC. The new HTTP/WebSocket UI server will run on `127.0.0.1:8080`. Please verify if port `8080` is free on your local environment.
> - **Raylib vs Web UI**: We have selected a Web-based interface served natively by the daemon (Option B) to deliver a rich, responsive, and visually stunning dashboard with interactive charts, scrollable lists, and real-time feeds, which would be extremely complex to render from scratch in Raylib coordinates via `gui.ep`. If you prefer a native Raylib desktop window over a browser app, please let us know.

---

## Proposed Changes

We will introduce a new frontend module `decent_web/` and update the coordination daemon to serve this web interface and accept API queries.

### Daemon Web server & API Integration (`/`)

#### [MODIFY] [node.ep](file:///Users/mettamazza/Desktop/ErnosDecent./node.ep)
- Extend daemon start sequences to load and initialize `websocket` and `static_server` standard libraries.
- Launch a new background thread running the web/API listener server on port `8080`.
- Implement API routing handlers returning JSON snapshots:
  - `/api/status`: DID, Raft term, role, uptime, active peer count.
  - `/api/wallet`: Account balances, recent UTXO transaction logs.
  - `/api/storage`: Allocated space, chunk count, CAR archive metrics.
  - `/api/pool`: Mesh node contribution scores, shared bandwidth/compute graphs.
- Implement WebSocket handlers to:
  - Stream real-time logs and peer connection updates.
  - Handle live E2E messaging loops (`decent_msg` channels).
  - Stream local AI inference text completion tokens directly to the client.

#### [MODIFY] [decent_cli/test_cli.ep](file:///Users/mettamazza/Desktop/ErnosDecent./decent_cli/test_cli.ep)
- Add mock assertions and connection queries verifying port `8080` HTTP routing alongside port `5000` IPC socket queries.

---

### Dashboard Frontend Web Client (`decent_web/`)

#### [NEW] [index.html](file:///Users/mettamazza/Desktop/ErnosDecent./decent_web/index.html)
- SPA structure containing:
  - Sidebar navigation (Overview, Identity, Storage, Social & Msg, Wallet, AI Playground, Telemetry).
  - Main panel dynamically swapping sections.
  - Real-time notification banner and console logger.
  - Clean semantic layout with accessible elements and unique IDs for automated testing.

#### [NEW] [style.css](file:///Users/mettamazza/Desktop/ErnosDecent./decent_web/style.css)
- Premium dark mode stylesheet:
  - Vibrant neon color palette (neon violet, cyan, amber, deep obsidian gradients).
  - Glassmorphic panels using `backdrop-filter: blur(16px)` and translucent borders.
  - Responsive flexbox/grid layout adjusting from desktop displays to mobile.
  - Smooth micro-animations for hover effects, state transitions, and loading skeletons.
  - Custom scrollbars and modern Google Font typography (e.g., *Outfit* and *JetBrains Mono*).

#### [NEW] [app.js](file:///Users/mettamazza/Desktop/ErnosDecent./decent_web/app.js)
- Application client-side core controller:
  - Establishes a WebSocket connection to the local daemon at `ws://127.0.0.1:8080/ws`.
  - Manages UI state and event routing (sending chat messages, posting Nostr notes, querying search terms).
  - Updates DOM nodes with incoming telemetry JSON updates.
  - Handles AI query streams, rendering characters as they arrive in real-time.

---

## Verification Plan

### Automated Tests
- Validate that the updated daemon compiles and passes standard tests:
  ```bash
  "/Users/mettamazza/Desktop/ErnosPlain Programing Language/target/release/ernos" node.ep
  ```
- Run integration check verifying the daemon accepts TCP connections on `8080`.

### Manual Verification
1. Start the daemon in the workspace:
   ```bash
   ./node
   ```
2. Open a web browser and navigate to:
   ```text
   http://127.0.0.1:8080
   ```
3. Verify that the Sovereign Dashboard loads with its premium dark interface.
4. Test interactive elements:
   - Navigate through tabs (Overview, Wallet, AI Playground).
   - Enter a prompt in the AI Playground tab, submit, and verify that the LLM response streams in real-time.
   - Run a mock ledger wallet transfer, verifying balance updates in the UI.
   - Stop the daemon using the stop control or command-line client, verifying the app handles disconnect states gracefully.
