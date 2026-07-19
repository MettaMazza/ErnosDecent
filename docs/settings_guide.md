# ErnosDecent Node Settings User Guide

This guide describes the Settings interface as implemented in July 2026. Saving a
system setting writes `~/.ernosdecent/config.toml`; settings marked **startup** are
read by `node.ep` on the next daemon launch. Settings marked **stored only** currently
round-trip through the UI and TOML but are not consumed by the runtime. They are named
explicitly here so the interface is not represented as enforcing controls it does not.

The dashboard listens on `http://127.0.0.1:8088` by default. Before that listener
starts, the node creates a random per-installation password at
`~/.ernosdecent/web-password`, restricts it to mode `0600`, and prints it once to the
operator log. Read the same value later with
`tr -d '\r\n' < ~/.ernosdecent/web-password; printf '\n'`. If the file is empty or
its permissions cannot be secured, the Web listener fails closed and reports the
error; there is no shared default password.

---

## 1. Platform Adapters

The Platform Adapters sub-tab allows you to enable or disable messaging gateways to legacy chat and communications systems, and configure credentials for each gateway.

### Discord Adapter
- **Toggle Switch**: Turns the Discord relay gateway online or offline.
- **Bot Token**: The OAuth2 bot token generated via the Discord Developer Portal (under Applications -> Bot -> Token). It grants the node access to view and respond to messages.
- **Channel IDs (comma separated)**: A comma-separated list of numeric Discord Channel IDs. The node only listens to and relays messages in these specific channels.
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
- **Node Name — stored only**: A local label retained in the configuration.
- **Log Level — stored only**: Retained in configuration; the logger does not currently apply this value as a filter.
- **Data Directory — stored only**: Retained in configuration. Runtime state currently remains under `~/.ernosdecent`.

### Storage & DHT Cache
- **Max Content Size (Bytes) — stored only**: Retained for a future storage-policy hook; it does not currently enforce a CAS limit.
- **DHT TTL (Seconds) — stored only**: Retained for a future expiry-policy hook; it does not currently change DHT retention.

### Network Interfaces & Ports
- **Listen Address — stored only**: Retained in TOML. The production build binds P2P/DHT/relay/raft/compute to all IPv4 interfaces and forces IPC/Web to loopback.
- **Max P2P Connections — stored only**: No runtime connection cap currently reads this value.
- **P2P Port — startup**: Encrypted peer traffic; default TCP `9100`.
- **DHT Port — startup**: Bootstrap and Kademlia RPC traffic; default TCP `9101`.
- **Relay Server Port — startup**: ErnosDecent relay registration/forwarding; default TCP `9102`. This is not a TURN or STUN server.
- **IPC Port — startup**: Authenticated loopback control plane; default TCP `5000`.
- **Web Port — startup**: Loopback HTTP/WebSocket dashboard; default TCP `8088`.
- **Max P2P Message Size — stored only**: No transport framing limit currently reads this value.
- **Public Hostname or IP — startup**: Address advertised to peers. Empty means detect the current public IPv4 address at launch.
- **Seed Peer Address and Port — startup**: Optional explicit DHT bootstrap endpoint. It takes priority over cached peers and operated defaults.
- **Enable Dynamic Host Election & Fallback Routing — startup**: Starts the host-election loop when set to `1`.
- **Static Preferred Host Node — startup**: Gives this node static-host election priority and prevents the operated root from dialing its own shipped default aliases. Explicit and verified cached peers remain eligible.

### Raft Consensus Tuning
- **Raft Port — startup**: Raft transport listener; default TCP `9103`.
- **Election Timeout and Heartbeat Interval — stored only**: The current Raft runtime does not consume these TOML values.

### Firewall & Security Bounds
- **Rate Limit, Violations Ban Threshold, and Ban Duration — stored only**: The security module has enforcement routines, but these dashboard values are not currently passed into them.

- **Save System Configuration Button**: Parses supplied fields and writes the daemon config file. Startup settings require a daemon restart. Endpoint validity is enforced during node startup; the UI is not a complete semantic validator.

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
