# ErnosDecent Node Settings User Guide

This guide details every configuration parameter and tab within the Settings interface of your sovereign node.

---

## 1. Platform Adapters

The Platform Adapters sub-tab allows you to enable or disable messaging gateways to legacy chat and communications systems, and configure credentials for each gateway.

### Discord Adapter
- **Toggle Switch**: Turns the Discord relay gateway online or offline.
- **Bot Token**: The OAuth2 bot token generated via the Discord Developer Portal (under Applications -> Bot -> Token). It grants the node access to view and respond to messages.
- **Channel IDs (comma separated)**: A comma-separated list of numeric Discord Channel IDs. The node only listens to and relays messages in these specific channels.
- **Admin IDs / Admin Role ID**: Grant node authorization. Authorization does not identify the person using the account.
- **Host ID / Host Name**: `discord.host_id` maps one stable Discord account to Echo's named host/steward (normally Maria); `discord.host_name` supplies that name. When `host_id` is absent, only the first legacy `admin_id` is treated as the host for backward compatibility. Other admins remain separately identified users.
- **Save Discord Config Button**: Saves the current Discord configuration values and reloads the Discord gateway adapter.

### WhatsApp Adapter
- **Toggle Switch**: Enables or disables the WhatsApp Cloud API gateway.
- **API Token**: A permanent or temporary Meta Graph API access token that has the `whatsapp_business_messaging` permission.
- **Phone Number ID**: The unique ID for the phone number registered under the WhatsApp Business account to send and receive messages.
- **Save WhatsApp Config Button**: Saves the current WhatsApp configuration values and reloads the WhatsApp gateway adapter.

### Telegram Adapter
- **Toggle Switch**: Turns the Telegram bot relay gateway online or offline.
- **Bot Token**: The HTTP API bot token issued by `@BotFather` upon bot creation.
- **Save Telegram Config Button**: Saves the current Telegram configuration values and reloads the Telegram gateway adapter.

---

## 2. Sovereign Node System Configuration (System Config)

This tab configures the daemon's underlying P2P network, Raft consensus database, block storage, and rate-limiting firewall policies.

### Core Node Settings
- **Node Name**: A friendly identifier for your node, visible to other peers in the network and displayed in telemetry logs.
- **Log Level**: Adjusts verbosity of daemon output. Options include:
  - *Debug*: Extremely verbose output including low-level network packets, memory allocations, and state transactions.
  - *Info*: Standard operational logs such as block commits, P2P handshake events, and node state changes.
  - *Warn*: Highlights non-fatal errors, missing optional parameters, or potential connectivity bottlenecks.
  - *Error*: Logs fatal problems that require action (e.g. database corruption, port binding conflicts).
- **Data Directory**: The absolute filepath on the host system where blocks, wallet credentials, DHT cache tables, and database files are persisted (defaulting to `~/.ernosdecent`).

### Storage & DHT Cache
- **Max Content Size (Bytes)**: The maximum permissible file or payload size that the node is willing to store in its Content-Addressable Storage (CAS) engine.
- **DHT TTL (Seconds)**: Time-To-Live for DHT key-value entries. In Kademlia, values are republished periodically; this dictates how long a cached key is considered valid.

### Network Interfaces & Ports
- **Listen Address**: The network interface address that the node binds to. Setting this to `0.0.0.0` allows connections on all interfaces, while `127.0.0.1` restricts daemon access to the local machine.
- **Max P2P Connections**: The maximum number of concurrent TCP sockets the node will open to negotiate peer exchanges.
- **P2P Port**: The network port assigned for standard P2P gossip protocol communication.
- **DHT Port**: The port used by the Kademlia DHT routing engine for peer discovery query lookups.
- **Relay Server Port**: The port assigned for TURN/STUN relay signaling to assist in NAT traversal for firewalled nodes.
- **IPC Port**: The Unix/TCP loopback port for node-daemon communication (typically port `5000`).
- **Web Port**: The port hosting the web application UI and its accompanying WebSocket endpoint (typically port `8080`).
- **Max P2P Message Size (Bytes)**: The payload size limit for standard P2P gossip message transmission.
- **Seed Peer IP/Addr**: The IP address of a stable bootstrapper or seed node used to join the network.
- **Seed Peer Port**: The port of the bootstrapper/seed node.
- **Enable Dynamic Host Election & Fallback Routing**: When enabled, the node participates in consensus-based leader elections to act as a primary network relay if other nodes fail.
- **Static Preferred Host Node**: Overrides election protocols to mark this node as a high-priority root/seed node, bypassing standard fallback mechanisms.

### Raft Consensus Tuning
- **Raft Port**: The port dedicated to executing Raft heartbeat and log synchronization protocols.
- **Election Timeout (ms)**: The duration a follower waits without receiving a heartbeat before declaring a new election cycle.
- **Heartbeat Interval (ms)**: The rate at which the Raft leader sends heartbeats to maintain consensus.

### Firewall & Security Bounds
- **Rate Limit (req/min)**: The maximum number of requests a single IP address can make before trigger events are logged as suspicious.
- **Violations Ban Threshold**: The number of rule violations (e.g. invalid signatures, rate-limit overflow) before the firewall temporarily blocks the offending peer IP.
- **Ban Duration (Seconds)**: The duration an IP remains blacklisted after crossing the violations threshold.

- **Save System Configuration Button**: Validates and writes all system configuration changes to the daemon config file. Note that port changes require a daemon restart.

---

## 3. Hebbian Cognitive Subsystem Prompts (Agent Prompts)

This panel lets you modify the core instructions and cognitive behavior of the local AI agent system.

- **Kernel System Prompt**: The system instructions injected at the base of the LLM context, defining its primary directives, safety parameters, and tool execution boundaries.
- **Agent Persona Base**: The core personality traits, conversational style, and user alignment guidelines.
- **Synaptic Observer Loop Prompt**: The specialized instructions directing the background observation loop. The observer reviews conversational logs to synthesize long-term memories and update Hebbian associations.
- **Save Agent Prompts Button**: Saves the custom prompts into the cognitive system's memory database.

---

## 4. User Registered Plugins & Extensions (Plugins)

Allows you to extend the capabilities of your sovereign node by registering external services, custom script hooks, or decentralized application frontends.

### Registering a Plugin
Clicking the **+ Register Plugin** button displays interactive prompt dialogs to collect:
- **Plugin Name**: The name displayed in the plug-in registry.
- **Endpoint (URL or script name)**: The HTTP/WebSocket URL of the plugin service or the path to a local executable script.
- **Description**: A short summary of what the plugin does.

### Plugin Management Table
Registered plugins are listed in a table showing:
- **Plugin Name**: The identifier of the plugin.
- **Endpoint**: The registered URL or script path.
- **Description**: A brief explanation of the plugin functionality.
- **Status**: The operational status of the plugin (e.g., ACTIVE).
- **Actions**: Contains options to toggle the plugin status (enable/disable) or delete it from the configuration.
