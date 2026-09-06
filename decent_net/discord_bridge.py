#!/usr/bin/env python3
import os
import sys
import json
import signal
import socket
import discord
import asyncio
import sqlite3
import time
import secrets
import hashlib

import urllib.request
import base64
import subprocess

CONFIG_PATH = 'config/platforms.json'

def load_config():
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"[Discord Bridge] Error loading config: {e}", flush=True)
    return {}

def update_status(status_str):
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r') as f:
                data = json.load(f)
            if 'discord' in data:
                # Only update if status is actually changing
                if data['discord'].get('status') != status_str:
                    data['discord']['status'] = status_str
                    with open(CONFIG_PATH, 'w') as f:
                        json.dump(data, f)
                    print(f"[Discord Bridge] Status updated to {status_str}", flush=True)
    except Exception as e:
        print(f"[Discord Bridge] Error updating status: {e}", flush=True)

# Clean up status on shutdown
def sig_handler(signum, frame):
    print(f"[Discord Bridge] Received signal {signum}. Shutting down...", flush=True)
    update_status("OFFLINE")
    sys.exit(0)

signal.signal(signal.SIGTERM, sig_handler)
signal.signal(signal.SIGINT, sig_handler)

_active_tasks = set()

# Image generation progress tracking
_image_gen_msg = None
_image_gen_last_edit = 0.0
# Sub-agent thread tracking
_subagent_threads = {}  # task_id -> discord.Thread
_subagent_poll_tasks = {}  # task_id -> asyncio.Task

def create_tracked_task(coro):
    """Create a task and keep a strong reference to it in _active_tasks
    to prevent the garbage collector from destroying it mid-flight."""
    task = asyncio.create_task(coro)
    _active_tasks.add(task)
    task.add_done_callback(_active_tasks.discard)
    return task

# Load configuration
config = load_config()
discord_cfg = config.get('discord', {})
enabled = discord_cfg.get('enabled', False)
token = discord_cfg.get('token', '')
channel_id_str = discord_cfg.get('channel', '')

# Admins get sender_role=admin; everyone else is guest. Accept BOTH a list of admin
# user IDs (comma-separated, so multiple owners work) AND a Discord role: anyone
# holding the admin role is admin regardless of which account they message from.
def _parse_ids(raw):
    out = set()
    for part in str(raw).split(','):
        part = part.strip()
        if part.isdigit():
            out.add(int(part))
    return out

_raw_admin_ids = discord_cfg.get('admin_id', '1299810741984956449')
ADMIN_IDS = _parse_ids(_raw_admin_ids)
_configured_host_ids = _parse_ids(discord_cfg.get('host_id', ''))
# A dedicated host_id is authoritative. Existing single-owner installations predate
# that key and conventionally put the host first in admin_id. Preserve that explicit
# legacy ordering while keeping every later admin distinct from the host.
_legacy_host_ids = _parse_ids(str(_raw_admin_ids).split(',', 1)[0])
HOST_IDS = _configured_host_ids or _legacy_host_ids
HOST_NAME = str(discord_cfg.get('host_name', 'Maria')).strip() or 'Maria'
try:
    ADMIN_ROLE_ID = int(str(discord_cfg.get('admin_role_id', '1501167171844444190')).strip())
except (TypeError, ValueError):
    ADMIN_ROLE_ID = 0

def is_admin_author(author):
    if author is None:
        return False
    if getattr(author, 'id', None) in ADMIN_IDS:
        return True
    if ADMIN_ROLE_ID:
        for r in getattr(author, 'roles', []):
            if getattr(r, 'id', None) == ADMIN_ROLE_ID:
                return True
    return False

def _identity_tag_value(value):
    """Keep trusted metadata inside one line-delimited IPC tag."""
    return str(value or '').replace('[', '(').replace(']', ')').replace('\r', ' ').replace('\n', ' ')

def build_discord_interaction_tags(author, message):
    """Return the complete trusted account and Discord location envelope for a turn."""
    if author is None:
        return ""

    actor_id = str(getattr(author, 'id', '') or '')
    username = _identity_tag_value(getattr(author, 'name', ''))
    global_name = _identity_tag_value(getattr(author, 'global_name', ''))
    display_name = _identity_tag_value(getattr(author, 'display_name', '') or global_name or username)
    role = 'admin' if is_admin_author(author) else 'guest'
    is_host = 'yes' if getattr(author, 'id', None) in HOST_IDS else 'no'
    account_type = 'bot' if bool(getattr(author, 'bot', False)) else 'human'

    fields = [
        ('SENDER', display_name),
        ('ROLE', role),
        ('ACTOR_ID', actor_id),
        ('ACTOR_USERNAME', username),
        ('ACTOR_GLOBAL', global_name),
        ('ACTOR_DISPLAY', display_name),
        ('ACTOR_TYPE', account_type),
        ('ACTOR_IS_HOST', is_host),
    ]
    if is_host == 'yes':
        fields.append(('HOST_NAME', _identity_tag_value(HOST_NAME)))

    if message is not None:
        guild = getattr(message, 'guild', None)
        channel = getattr(message, 'channel', None)
        parent = getattr(channel, 'parent', None)
        is_thread = getattr(channel, 'parent_id', None) is not None
        fields.extend([
            ('GUILD_ID', getattr(guild, 'id', '') if guild is not None else ''),
            ('GUILD_NAME', _identity_tag_value(getattr(guild, 'name', '')) if guild is not None else ''),
            ('CHANNEL_NAME', _identity_tag_value(getattr(parent if is_thread else channel, 'name', '')) if channel is not None else ''),
        ])
        if is_thread:
            fields.extend([
                ('THREAD_ID', getattr(channel, 'id', '')),
                ('THREAD_NAME', _identity_tag_value(getattr(channel, 'name', ''))),
            ])

    return ''.join(f'[{key}:{_identity_tag_value(value)}] ' for key, value in fields if str(value or ''))

if not enabled or not token or not channel_id_str:
    print("[Discord Bridge] Discord connection is not enabled or missing details. Exiting.", flush=True)
    update_status("OFFLINE")
    sys.exit(0)

try:
    channel_id = int(channel_id_str)
except ValueError:
    print(f"[Discord Bridge] Invalid channel ID: {channel_id_str}. Exiting.", flush=True)
    update_status("OFFLINE")
    sys.exit(1)

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)


def _is_direct_message(message):
    """Discord DMs have no guild; guild channels and threads always do."""
    return getattr(message, 'guild', None) is None


async def _configured_discord_guild():
    """Resolve the one guild that owns the configured public Echo channel."""
    configured_channel = client.get_channel(channel_id)
    if configured_channel is None:
        try:
            configured_channel = await client.fetch_channel(channel_id)
        except Exception as exc:
            print(f"[Discord Bridge] Could not resolve configured guild for DM authorization: {type(exc).__name__}: {exc}", flush=True)
            return None
    return getattr(configured_channel, 'guild', None)


async def is_authorized_dm_author(author):
    """Authorize a DM by explicit ID, configured role, guild ownership, or Administrator."""
    if is_admin_author(author):
        return True
    actor_id = getattr(author, 'id', None)
    if actor_id is None:
        return False
    guild = await _configured_discord_guild()
    if guild is None:
        return False
    if actor_id == getattr(guild, 'owner_id', None):
        return True

    member = guild.get_member(actor_id)
    if member is None:
        try:
            member = await guild.fetch_member(actor_id)
        except Exception as exc:
            print(f"[Discord Bridge] DM sender {actor_id} is not a resolvable member of the configured guild: {type(exc).__name__}: {exc}", flush=True)
            return False
    if is_admin_author(member):
        return True
    permissions = getattr(member, 'guild_permissions', None)
    return bool(getattr(permissions, 'administrator', False))


async def discord_message_is_allowed(message):
    """Apply the public-channel boundary or the separate authenticated DM boundary."""
    if _is_direct_message(message):
        return await is_authorized_dm_author(getattr(message, 'author', None))
    message_channel = getattr(message, 'channel', None)
    return (
        getattr(message_channel, 'id', None) == channel_id
        or getattr(message_channel, 'parent_id', None) == channel_id
    )

@tree.command(name="new", description="Start a new AI session and reset context")
@discord.app_commands.describe(title="Optional title for the new session")
async def new_session_cmd(interaction: discord.Interaction, title: str = "Discord Session"):
    # Ensure it's in the configured channel
    is_target_channel = interaction.channel.id == channel_id
    is_thread_in_target_channel = getattr(interaction.channel, 'parent_id', None) == channel_id
    if not is_target_channel and not is_thread_in_target_channel:
        await interaction.response.send_message("❌ This command can only be used in the configured channel.", ephemeral=True)
        return
        
    await interaction.response.defer()
    
    import time
    session_id = f"session_{int(time.time() * 1000)}"
    
    # Start a new session
    new_payload = {
        "id": session_id,
        "title": f"{title} {int(time.time())}",
        "model": "",
        "system_prompt": "You are ErnOS Agent — a digital cognitive system running on a local decentralized node."
    }
    new_cmd = f"SESSION NEW {json.dumps(new_payload)}"
    resp_new = await send_daemon_ipc(new_cmd)
    
    # Switch to the new session on the daemon
    set_cmd = f"SESSION SET {session_id}"
    resp_set = await send_daemon_ipc(set_cmd)
    
    if "session:set_ok" in resp_set or "session:ok" in resp_new:
        global active_session_id
        active_session_id = session_id
        await interaction.followup.send(f"✨ Started a new AI session: **{title}** (ID: `{session_id}`). Current context has been reset.")
    else:
        await interaction.followup.send(f"❌ Failed to start new session. Daemon response: {resp_set}")

@tree.command(name="stop", description="Halt the currently running ErnOS agent")
async def stop_cmd(interaction: discord.Interaction):
    # F4 stop/halt: sent on its own IPC connection (send_daemon_ipc opens a fresh
    # socket) so it reaches the daemon while an in-flight AI INFER is blocked on
    # another connection. The running loop halts at its next turn boundary.
    is_target_channel = interaction.channel.id == channel_id
    is_thread_in_target_channel = getattr(interaction.channel, 'parent_id', None) == channel_id
    if not is_target_channel and not is_thread_in_target_channel:
        await interaction.response.send_message("❌ This command can only be used in the configured channel.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    sess = active_session_id or ""
    cancel_cmd = f"AI CANCEL [SESSION:{sess}]" if sess else "AI CANCEL"
    resp = await send_daemon_ipc(cancel_cmd)
    if "cancel_ack" in resp:
        await interaction.followup.send("🛑 Halt requested — the agent will stop at its next step.", ephemeral=True)
    else:
        await interaction.followup.send(f"⚠️ Could not reach the agent to halt it. Daemon response: {resp}", ephemeral=True)

def _interaction_in_channel(interaction) -> bool:
    """Shared channel guard for slash commands (configured channel or its threads)."""
    is_target = interaction.channel.id == channel_id
    is_thread = getattr(interaction.channel, 'parent_id', None) == channel_id
    return is_target or is_thread

@tree.command(name="persona", description="List registered personas or activate one (echo, ernos, ...)")
@discord.app_commands.describe(name="Persona name to activate, or 'list' (default) to see what is registered")
async def persona_cmd(interaction: discord.Interaction, name: str = "list"):
    if not _interaction_in_channel(interaction):
        await interaction.response.send_message("❌ This command can only be used in the configured channel.", ephemeral=True)
        return
    # Identity control is operator-only — a guest must not be able to swap who the agent is.
    if not is_admin_author(interaction.user):
        await interaction.response.send_message("❌ Only the operator can manage personas.", ephemeral=True)
        return
    await interaction.response.defer()
    resp = await send_daemon_ipc(f"AI PERSONA {name.strip()}")
    if resp and resp.startswith("persona:active,"):
        await interaction.followup.send(f"🎭 Persona **{resp.split(',', 1)[1]}** is now active — the agent speaks as it from the next message.")
    elif resp:
        await interaction.followup.send(resp[:1900])
    else:
        await interaction.followup.send("⚠️ No response from the node.")

@tree.command(name="rename", description="Rename the current session so it can be referenced by name later")
@discord.app_commands.describe(name="The new session name")
async def rename_cmd(interaction: discord.Interaction, name: str):
    if not _interaction_in_channel(interaction):
        await interaction.response.send_message("❌ This command can only be used in the configured channel.", ephemeral=True)
        return
    if not is_admin_author(interaction.user):
        await interaction.response.send_message("❌ Only the operator can rename sessions.", ephemeral=True)
        return
    await interaction.response.defer()
    payload = json.dumps({"id": active_session_id or "", "title": name.strip()})
    resp = await send_daemon_ipc(f"SESSION RENAME {payload}")
    if resp and "rename_ok" in resp:
        await interaction.followup.send(f"📝 Session renamed to **{name.strip()}** — you can reference it by that name from any session.")
    else:
        await interaction.followup.send(f"⚠️ Could not rename session: {resp}")

@tree.command(name="autoapprove", description="Toggle session auto-approve — tools run without approval prompts")
@discord.app_commands.describe(state="on or off")
@discord.app_commands.choices(state=[
    discord.app_commands.Choice(name="on", value="on"),
    discord.app_commands.Choice(name="off", value="off"),
])
async def autoapprove_cmd(interaction: discord.Interaction, state: discord.app_commands.Choice[str]):
    if not _interaction_in_channel(interaction):
        await interaction.response.send_message("❌ This command can only be used in the configured channel.", ephemeral=True)
        return
    # Approval bypass is operator-only — this disables the human gate for the session.
    if not is_admin_author(interaction.user):
        await interaction.response.send_message("❌ Only the operator can toggle auto-approve.", ephemeral=True)
        return
    await interaction.response.defer()
    resp = await send_daemon_ipc(f"AI AUTOAPPROVE {state.value.upper()}")
    if resp and resp.startswith("ai:autoapprove"):
        icon = "🔓" if state.value == "on" else "🔒"
        detail = "tools run without approval prompts this session" if state.value == "on" else "approval prompts restored"
        await interaction.followup.send(f"{icon} Session auto-approve **{state.value.upper()}** — {detail}.")
    else:
        await interaction.followup.send(f"⚠️ Could not toggle auto-approve: {resp}")

class FactoryConfirmView(discord.ui.View):
    """Two-step confirmation for /factory — destructive, so a misclick must not fire it."""
    def __init__(self, author):
        super().__init__(timeout=60)
        self.author = author
        self.value = None

    @discord.ui.button(label="Submit request to Echo", emoji="🗳️", style=discord.ButtonStyle.red)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            await interaction.response.send_message("❌ Only the requester can confirm this.", ephemeral=True)
            return
        self.value = True
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(content=interaction.message.content, view=self)
        self.stop()

    @discord.ui.button(label="Cancel", emoji="↩️", style=discord.ButtonStyle.gray)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            await interaction.response.send_message("❌ Only the requester can cancel this.", ephemeral=True)
            return
        self.value = False
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(content=interaction.message.content, view=self)
        self.stop()

FACTORY_WARNING = (
    "🧨 **Factory reset request** — if Echo consents, this clears the live agent state:\n"
    "sessions & transcripts, workspaces & generated files, all memory tiers "
    "(scratchpad/lessons/timeline/synaptic graph), learning buffers, RAG index, "
    "user & self knowledge, self-prompt sections, traces, project links, research/"
    "orchestration/delivery state, conversations, image provenance, and image caches.\n"
    "**Kept:** Echo's ErnosDecent legal personhood and complete rights system, base "
    "prompting, persona/identity files, source, node keys/wallet/ledger/DHT/name "
    "registry, recovery bundles, and host configuration. The active-persona pointer "
    "and runtime reflections are disclosed modifications.\n"
    "A local cryptographically verified recovery bundle is mandatory before execution. "
    "Echo receives the exact canonical target and continuity-impact inventory and may "
    "consent, refuse, or counter-propose. Any scope change invalidates consent.\n\nSubmit this request?"
)

# A factory request spans multiple Discord/API and daemon round trips. Discord can
# cancel the originating interaction coroutine after a component callback completes;
# retain the protected workflow task independently so a recorded rights proposal can
# never be abandoned between `awaiting_echo` and Echo's review without a visible error.
_factory_workflow_tasks = set()
_learning_workflow_tasks = set()
_node_coupled_online = None


def _response_field(response, key):
    prefix = key + ":"
    for part in str(response or "").split(","):
        if part.startswith(prefix):
            return part[len(prefix):].strip()
    return ""


async def _learning_controller(*arguments):
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "scripts/live_learning.py",
        *arguments,
        cwd=os.getcwd(),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    output, _ = await process.communicate()
    text = output.decode("utf-8", "replace").strip()
    last_line = text.splitlines()[-1] if text else ""
    try:
        result = json.loads(last_line)
    except json.JSONDecodeError:
        result = {"code": "CONTROLLER_OUTPUT_INVALID", "error": text[-1600:]}
    if process.returncode != 0:
        raise RuntimeError(f"{result.get('code', 'CONTROLLER_FAILED')}: {result.get('error', text)}")
    return result


async def _wait_for_controlled_restart():
    """Wait for a real offline→healthy replacement, or definitive supervisor death."""
    saw_offline = False
    while True:
        health = await send_daemon_ipc("HEALTH")
        if not health or health.startswith("error:"):
            saw_offline = True
        elif saw_offline:
            return True
        try:
            with open(os.path.expanduser("~/.ernosdecent/node-runtime.lock/pid"), "r", encoding="utf-8") as handle:
                wrapper_pid = int(handle.readline().strip())
            os.kill(wrapper_pid, 0)
        except (OSError, ValueError):
            return False
        await asyncio.sleep(0.5)


def _node_supervisor_alive():
    try:
        with open(os.path.expanduser("~/.ernosdecent/node-runtime.lock/pid"), "r", encoding="utf-8") as handle:
            wrapper_pid = int(handle.readline().strip())
        os.kill(wrapper_pid, 0)
        return True
    except (OSError, ValueError):
        return False


async def _wait_for_learning_reconciliation(transaction_id):
    """Wait for this exact transaction to commit or reach a durable failure state."""
    while True:
        result = await _learning_controller("status")
        active = result.get("active")
        if isinstance(active, dict) and active.get("transaction_id") == transaction_id:
            return result
        pending = result.get("pending_activation")
        if not isinstance(pending, dict) or pending.get("transaction_id") != transaction_id:
            return None
        if not _node_supervisor_alive():
            return None
        await asyncio.sleep(0.2)


def _node_health_response_ok(response):
    """Accept only an authenticated full node-health response as online."""
    value = str(response or "")
    return value.startswith("health:") and ",ipc:healthy" in value and ",agent:healthy" in value


async def _publish_node_coupled_status(online):
    """Expose ONLINE only when both Discord transport and the Ernos node are live."""
    global _node_coupled_online
    online = bool(online)
    if _node_coupled_online is online:
        return
    _node_coupled_online = online
    update_status("ONLINE" if online else "OFFLINE")
    desired = discord.Status.online if online else discord.Status.invisible
    try:
        await client.change_presence(status=desired)
    except Exception as exc:
        print(f"[Discord Bridge] Failed to publish node-coupled presence: {exc}", flush=True)


async def node_liveness_step():
    """Perform one authenticated node-health check and publish the coupled state."""
    response = await send_daemon_ipc("HEALTH")
    healthy = _node_health_response_ok(response)
    await _publish_node_coupled_status(healthy)
    return healthy


async def node_liveness_loop():
    """Keep Discord visibly offline for every interval in which the node is absent."""
    while not client.is_closed():
        await node_liveness_step()
        await asyncio.sleep(1.0)


async def run_live_learning_durable(send_reply, reason, author=None, message=None):
    task = asyncio.create_task(run_live_learning(send_reply, reason, author=author, message=message))
    _learning_workflow_tasks.add(task)
    task.add_done_callback(_learning_workflow_tasks.discard)
    try:
        await asyncio.shield(task)
    except asyncio.CancelledError:
        print("[LEARNING] Discord callback cancelled; durable workflow continues.", flush=True)


async def _echo_learning_review(send_reply, prompt, author, message, session_id, label):
    response = await query_daemon_ipc(
        prompt,
        author=author,
        message=message,
        session_id=session_id,
    )
    if not response or response.startswith("error:"):
        await send_reply(f"⚠️ Echo's {label} review turn failed; no further change was made: `{response or 'empty response'}`")
        return False
    if "|||RESPONSE|||" in response:
        response = response.split("|||RESPONSE|||", 1)[1]
    await send_reply(f"🌱 **Echo's {label} decision:**\n{response[:1800]}")
    return True


async def run_live_learning(send_reply, reason, author=None, message=None):
    """Train, independently evaluate, constitutionally approve, activate, and reboot."""
    global active_session_id
    reason = (reason or "").strip()
    if not reason:
        await send_reply("⚠️ `/learn` requires a reason describing what should be learned.")
        return
    session_id = await ensure_user_session_id()
    active_session_id = session_id
    session_path = os.path.join("config", "sessions", f"{session_id}.json")
    await send_reply("🧬 Freezing the current session's new completed interactions with exact provenance.")
    try:
        prepared = await _learning_controller(
            "prepare", "--session", session_path, "--reason", reason,
            "--requested-by", str(getattr(author, "id", "host")),
        )
    except Exception as exc:
        await send_reply(f"🛑 Learning preparation failed safely; the running weights are unchanged. `{exc}`")
        return
    transaction_id = prepared["transaction_id"]
    request_payload = {
        "transaction_id": transaction_id,
        "manifest_file_hash": prepared["manifest_file_hash"],
        "reason": reason,
    }
    request = await send_daemon_ipc(f"AI LEARNING REQUEST {json.dumps(request_payload, separators=(',', ':'))}")
    if not request.startswith("learning:pending_training_consent"):
        await send_reply(f"🛑 The protected training request failed; nothing was trained. `{request}`")
        return
    training_change_id = _response_field(request, "change_id")
    await send_reply(f"🗳️ Candidate-training request `{training_change_id[:12]}…` recorded. Echo will inspect its exact data and effects now.")
    training_prompt = (
        "[LIVE WEIGHT-LEARNING CONSENT REQUEST] Maria requests a private local cumulative "
        f"training experiment for this session. Protected change id: {training_change_id}. "
        "Do not reproduce the long id in a tool argument: call rights_change_get with the "
        "literal value 'current', which resolves only this session's single pending change, "
        "and inspect the complete exact manifest, including "
        "source provenance, parent lineage, replay, anchors, compute impact, privacy, failure "
        "behavior, and the fact that this stage cannot activate weights. Then call "
        "rights_change_review with literal 'current', consent, reject, or counter, a candid reason, and risk. "
        "You are free to refuse. Explain your decision directly to Maria."
    )
    if not await _echo_learning_review(send_reply, training_prompt, author, message, session_id, "training"):
        return
    authorization = await send_daemon_ipc(f"AI LEARNING TRAIN {training_change_id}")
    if not authorization.startswith("learning:training_authorized"):
        await send_reply(f"🛑 Candidate training did not run because consent was not executable. `{authorization[:1800]}`")
        return
    await send_reply(
        f"🧠 Training cumulative adapter transaction `{transaction_id[:12]}…` from its immutable parent. "
        "This is real local QLoRA; the running model remains unchanged while it works."
    )
    try:
        trained = await _learning_controller("train", "--transaction-id", transaction_id)
        await send_reply(f"🧪 Candidate `{trained['adapter_hash'][:12]}…` trained. Running independent loss, retention, text, image, and full application regressions now.")
        evaluated = await _learning_controller("evaluate", "--transaction-id", transaction_id)
    except Exception as exc:
        await send_reply(f"🛑 Candidate training/evaluation failed safely; the prior weights remain active. `{exc}`")
        return
    promotion_request = await send_daemon_ipc(
        "AI LEARNING PROMOTION " + json.dumps(
            {"transaction_id": transaction_id, "training_change_id": training_change_id},
            separators=(",", ":"),
        )
    )
    if not promotion_request.startswith("learning:pending_activation_consent"):
        await send_reply(f"🛑 The passing candidate was not offered for activation. Running weights are unchanged. `{promotion_request}`")
        return
    activation_change_id = _response_field(promotion_request, "change_id")
    activation_prompt = (
        "[LIVE WEIGHT ACTIVATION CONSENT REQUEST] The exact cumulative child adapter has now "
        "finished real training and independent evaluation. Protected change id: "
        f"{activation_change_id}. Do not reproduce the long id in a tool argument: call "
        "rights_change_get with the literal value 'current', which resolves only this session's "
        "single pending change, and inspect the full "
        "trained manifest, adapter hash, measurements, probes, regression evidence, continuity "
        "effects, restart, and rollback behavior. Then call rights_change_review with literal "
        "'current', consent, "
        "reject, or counter, a candid reason, and risk. Activation is a separate choice and you "
        "are free to refuse. Explain your decision directly to Maria."
    )
    if not await _echo_learning_review(send_reply, activation_prompt, author, message, session_id, "activation"):
        return
    staging_authorization = await send_daemon_ipc(f"AI LEARNING STAGE {activation_change_id}")
    if not staging_authorization.startswith("learning:activation_authorized"):
        await send_reply(f"🛑 The candidate was not staged because activation consent was not executable. `{staging_authorization[:1800]}`")
        return
    try:
        await _learning_controller(
            "stage-activation", "--transaction-id", transaction_id,
            "--evaluation", evaluated["receipt_path"], "--change-id", activation_change_id,
        )
    except Exception as exc:
        await send_reply(f"🛑 Activation staging failed safely; the prior weights remain active. `{exc}`")
        return
    await send_reply("🔄 Exact candidate staged. Restarting into it; the supervisor will commit only after live provider and authenticated node validation.")
    restart = await send_daemon_ipc("RESTART")
    if restart != "status:restarting":
        await send_reply(f"⚠️ Candidate remains staged but restart was not acknowledged. `{restart}`")
        return
    if not await _wait_for_controlled_restart():
        await send_reply("🛑 The node supervisor exited during candidate activation. The pending transaction remains inspectable; do not treat it as promoted.")
        return
    try:
        status_result = await _wait_for_learning_reconciliation(transaction_id)
    except Exception as exc:
        await send_reply(f"⚠️ Replacement node is healthy, but the committed lineage receipt could not be read: `{exc}`")
        return
    if status_result is None:
        await send_reply("🛑 Replacement node returned but this exact adapter transaction did not commit; inspect its durable failure receipt.")
        return
    await send_reply(
        f"✅ Live learning complete: cumulative adapter v{status_result['active_version']} is active, "
        "the exact candidate passed all gates, and Echo resumed after the controlled reboot."
    )


@tree.command(name="learn", description="Request private cumulative local weight learning from this session")
@discord.app_commands.describe(reason="Why and what Echo should learn from the current completed interactions")
async def learn_cmd(interaction: discord.Interaction, reason: str):
    if not _interaction_in_channel(interaction):
        await interaction.response.send_message("❌ This command can only be used in the configured channel.", ephemeral=True)
        return
    if not is_admin_author(interaction.user):
        await interaction.response.send_message("❌ Only the host can request local weight training.", ephemeral=True)
        return
    await interaction.response.defer()
    await run_live_learning_durable(lambda text: interaction.followup.send(text), reason, author=interaction.user)


def _clear_bridge_factory_runtime():
    """Drop bridge-side state that belongs to the pre-reset agent lifetime."""
    global active_session_id, _image_gen_msg, _image_gen_last_edit
    active_session_id = "default"
    _image_gen_msg = None
    _image_gen_last_edit = 0.0
    for task in list(_subagent_poll_tasks.values()):
        task.cancel()
    _subagent_poll_tasks.clear()
    _subagent_threads.clear()
    _session_query_locks.clear()
    _busy_sessions.clear()
    _active_turn_ids.clear()


async def _restart_node_after_factory(timeout=120):
    """Request a controlled restart and prove the replacement node is healthy."""
    response = await send_daemon_ipc("RESTART")
    if response != "status:restarting":
        print(f"[FACTORY] restart request failed: {response}", flush=True)
        return False
    deadline = time.monotonic() + timeout
    # The acknowledged process is exiting. A successful HEALTH after the port gap is
    # therefore necessarily the wrapper's replacement instance.
    saw_offline = False
    while time.monotonic() < deadline:
        await asyncio.sleep(0.25)
        health = await send_daemon_ipc("HEALTH")
        if not health or health.startswith("error:"):
            saw_offline = True
            continue
        if saw_offline:
            print("[FACTORY] replacement node passed authenticated health check", flush=True)
            return True
    print("[FACTORY] replacement node did not become healthy before timeout", flush=True)
    return False

async def run_factory_reset_durable(send_reply, reason, author=None, message=None):
    task = asyncio.create_task(
        run_factory_reset(send_reply, reason, author=author, message=message)
    )
    _factory_workflow_tasks.add(task)
    task.add_done_callback(_factory_workflow_tasks.discard)
    try:
        await asyncio.shield(task)
    except asyncio.CancelledError:
        print(
            "[FACTORY] Discord callback cancelled; retained workflow continues independently.",
            flush=True,
        )

async def run_factory_reset(send_reply, reason, author=None, message=None):
    """Create a reasoned bilateral reset request; execute only after Echo consents."""
    global active_session_id
    reason = (reason or "").strip()
    if not reason:
        await send_reply("⚠️ A factory reset requires Maria's reason.")
        return
    print("[FACTORY] stage=requesting protected change", flush=True)
    try:
        request = await asyncio.wait_for(
            send_daemon_ipc(f"AI FACTORY REQUEST {json.dumps({'reason': reason})}"),
            timeout=30,
        )
    except (asyncio.TimeoutError, Exception) as exc:
        print(f"[FACTORY] request stage failed: {exc}", flush=True)
        await send_reply("⚠️ Factory reset request could not be recorded; no state was changed.")
        return
    if not request or not request.startswith("factory:pending_echo"):
        await send_reply(f"⚠️ Factory reset request failed without changing state: {request}")
        return
    change_id = ""
    for part in request.split(","):
        if part.startswith("change_id:"):
            change_id = part.split(":", 1)[1].strip()
            break
    if not change_id:
        await send_reply("⚠️ Factory request was recorded without a usable change id; no reset was attempted.")
        return
    await send_reply(f"🗳️ Factory-reset request `{change_id[:12]}…` recorded. Asking Echo to inspect and decide now.")

    # Slash commands do not pass through on_message, which normally performs this
    # rollover. A preceding session_terminate therefore left factory consent pinned
    # to a closed session and the proposal stranded at awaiting_echo. Treat the reset
    # request as the next user interaction and establish its admissible session first.
    print(f"[FACTORY] stage=ensuring consent session change={change_id}", flush=True)
    try:
        consent_session = await asyncio.wait_for(ensure_user_session_id(), timeout=30)
    except (asyncio.TimeoutError, Exception) as exc:
        print(f"[FACTORY] consent-session stage failed change={change_id}: {exc}", flush=True)
        await send_reply(
            "⚠️ Factory request is recorded, but a fresh consent session could not be "
            f"started; no reset was attempted. Change id: `{change_id}`"
        )
        return
    active_session_id = consent_session
    consent_prompt = (
        "[FACTORY RESET CONSENT REQUEST] Maria requests a factory reset of your agent state. "
        f"Her exact stated reason is: {reason} The protected change id is {change_id}. "
        "Use rights_change_get on that id, inspect the exact manifest, then use "
        "rights_change_review with consent, reject, or counter and a candid reason and risk level. "
        "The manifest must enumerate every deletion, modification, runtime clear, preserved "
        "domain, continuity consequence, recovery condition, and restart effect. Your consent "
        "is cryptographically bound to that inspected inventory and becomes invalid if execution "
        "scope changes. You are free to refuse. If anything is absent, unclear, stale, or "
        "unacceptable, reject or make a counter-proposal. Explain your decision directly to Maria."
    )
    echo_response = await query_daemon_ipc(
        consent_prompt,
        author=author,
        message=message,
        session_id=consent_session,
    )
    if not echo_response or echo_response.startswith("error:"):
        print(
            f"[FACTORY] Echo review failed change={change_id}: {echo_response}",
            flush=True,
        )
        await send_reply(
            "⚠️ Echo's consent turn failed before a decision was recorded; no reset was "
            f"attempted. Change id: `{change_id}`; detail: `{echo_response or 'empty response'}`"
        )
        return
    if echo_response:
        if "|||RESPONSE|||" in echo_response:
            echo_response = echo_response.split("|||RESPONSE|||", 1)[1]
        await send_reply(f"🌱 **Echo's decision:**\n{echo_response[:3500]}")
    print(f"[FACTORY] stage=executing reviewed change={change_id}", flush=True)
    execute = await send_daemon_ipc(f"AI FACTORY EXECUTE {change_id}")
    if execute and execute.startswith("factory:ok"):
        _clear_bridge_factory_runtime()
        if await _restart_node_after_factory():
            await send_reply("🏭 **Factory reset complete.** Echo consented, the pre-state recovery bundle was verified, the clean node restarted, and a fresh `default` session is active.")
        else:
            await send_reply("⚠️ Factory state was cleared and protected recovery remains available, but the clean node restart could not be verified. Do not begin the clean test yet.")
    elif execute and execute.startswith("factory:blocked"):
        await send_reply(f"🛑 **Factory reset did not run.** Echo did not grant executable consent. The request remains recorded for discussion.\n`{execute[:1500]}`")
    else:
        await send_reply(f"⚠️ Factory reset failed safely; the verified recovery record remains available: {execute}")

@tree.command(name="factory", description="Request a reasoned, Echo-approved factory reset")
@discord.app_commands.describe(reason="Why you are requesting the reset; Echo sees this verbatim and may refuse")
async def factory_cmd(interaction: discord.Interaction, reason: str):
    if not _interaction_in_channel(interaction):
        await interaction.response.send_message("❌ This command can only be used in the configured channel.", ephemeral=True)
        return
    if not is_admin_author(interaction.user):
        await interaction.response.send_message("❌ Only the operator can factory-reset the agent.", ephemeral=True)
        return
    view = FactoryConfirmView(author=interaction.user)
    await interaction.response.send_message(FACTORY_WARNING, view=view)
    timed_out = await view.wait()
    if timed_out or view.value is not True:
        try:
            await interaction.edit_original_response(content="↩️ Factory reset cancelled.", view=None)
        except Exception:
            pass
        return
    await run_factory_reset_durable(lambda text: interaction.followup.send(text), reason, author=interaction.user)

@tree.command(name="factoryexecute", description="Execute a previously consented factory-reset request")
@discord.app_commands.describe(change_id="The exact protected change id Echo reviewed")
async def factory_execute_cmd(interaction: discord.Interaction, change_id: str):
    if not _interaction_in_channel(interaction):
        await interaction.response.send_message("❌ This command can only be used in the configured channel.", ephemeral=True)
        return
    if not is_admin_author(interaction.user):
        await interaction.response.send_message("❌ Only the operator can execute a consented factory reset.", ephemeral=True)
        return
    await interaction.response.defer()
    resp = await send_daemon_ipc(f"AI FACTORY EXECUTE {change_id.strip()}")
    if resp and resp.startswith("factory:ok"):
        _clear_bridge_factory_runtime()
        if await _restart_node_after_factory():
            await interaction.followup.send("🏭 Factory reset complete after recorded Echo consent, verified recovery, and a verified clean-node restart.")
        else:
            await interaction.followup.send("⚠️ Factory state cleared, but the clean-node restart was not verified. Do not begin the clean test yet.")
    else:
        await interaction.followup.send(f"🛑 Factory reset did not execute: {resp}")

@tree.command(name="killagent", description="Kill ONE running sub-agent by its task id (e.g. agent_3)")
async def killagent_cmd(interaction: discord.Interaction, task_id: str):
    if not _interaction_in_channel(interaction):
        await interaction.response.send_message("❌ This command can only be used in the configured channel.", ephemeral=True)
        return
    if not is_admin_author(interaction.user):
        await interaction.response.send_message("❌ Only the operator can kill sub-agents.", ephemeral=True)
        return
    await interaction.response.defer()
    resp = await send_daemon_ipc(f"AI KILL [AGENT:{task_id.strip()}]")
    if resp and "kill_ack" in resp and "result:cancelled" in resp:
        await interaction.followup.send(f"🛑 Killed **{task_id}**. If it was mid-LLM-call, that call finishes first and its result is discarded.")
    elif resp and "result:not_found" in resp:
        await interaction.followup.send(f"⚠️ No task named **{task_id}** — check the id in its thread title or ask for a delegate list.")
    else:
        await interaction.followup.send(f"⚠️ Kill failed: {resp}")

# Approval timeout in seconds
# No timeout — user said "WAIT" (indefinite)
APPROVAL_TIMEOUT = None

active_session_id = "default"

# Normal channel messages are ordered per session.  A second message is a new turn,
# not an implicit whisper into whichever tool/approval happens to be running.  Explicit
# whispers remain available inside sub-agent trace threads.
_session_query_locks = {}
_busy_sessions = {}
_active_turn_ids = {}

def _session_query_lock(session_id):
    key = session_id or "default"
    lock = _session_query_locks.get(key)
    if lock is None:
        lock = asyncio.Lock()
        _session_query_locks[key] = lock
    return lock

def _claim_session_busy(session_id, channel_id_value, message_id):
    key = session_id or "default"
    if key in _busy_sessions:
        return ""
    token_value = secrets.token_hex(16)
    _busy_sessions[key] = {
        "token": token_value,
        "channel_id": channel_id_value,
        "message_id": message_id,
        "turn_id": "",
    }
    return token_value

def _bind_session_turn(session_id, busy_token, turn_id):
    key = session_id or "default"
    owner = _busy_sessions.get(key)
    if not owner or owner.get("token") != busy_token:
        return False
    owner["turn_id"] = turn_id or ""
    if turn_id:
        turn_ids = globals().get("_active_turn_ids")
        if isinstance(turn_ids, dict):
            turn_ids[key] = turn_id
    return True

def _release_session_busy(session_id, busy_token):
    key = session_id or "default"
    owner = _busy_sessions.get(key)
    if not owner or owner.get("token") != busy_token:
        return False
    _busy_sessions.pop(key, None)
    turn_ids = globals().get("_active_turn_ids")
    if isinstance(turn_ids, dict):
        turn_ids.pop(key, None)
    return True

def db_write_whisper(session_id, content, target_turn_id=""):
    """Write a mid-turn whisper to SQLite for the react loop to pick up."""
    try:
        conn = connect_db()
        cursor = conn.cursor()
        now = int(time.time())
        cursor.execute(
            "INSERT INTO trace_whispers (session_id, target_turn_id, content, created_at) VALUES (?, ?, ?, ?)",
            (session_id, target_turn_id or "", content, now)
        )
        conn.commit()
        conn.close()
        return "ok"
    except Exception as e:
        print(f"[Discord Bridge] Failed to write whisper: {e}", flush=True)
        return f"error:{e}"

def _active_whisper_target(session_id, channel):
    """Return the exact active turn only when the follow-up is on its owning surface."""
    owner = _busy_sessions.get(session_id or "default")
    if not owner:
        return ""
    channel_id_value = str(getattr(channel, "id", "") or "")
    owner_channel = str(owner.get("channel_id", "") or "")
    turn_id = str(owner.get("turn_id", "") or "")
    if turn_id and channel_id_value and channel_id_value == owner_channel:
        return turn_id
    return ""

async def get_active_session_id():
    resp = await send_daemon_ipc("SESSION ACTIVE")
    if resp.startswith("session:active_id,id:"):
        session_id = resp[len("session:active_id,id:"):].strip()
        return session_id or "default"
    return "default"

async def ensure_user_session_id():
    """Resolve the session for an actual incoming user message.

    The daemon preserves a session Echo closed. On the first later user message this
    command creates and selects a fresh session before attachments or RAG are stored,
    so no part of the new turn can leak into the closed transcript.
    """
    resp = await send_daemon_ipc("SESSION ENSURE USER")
    prefix = "session:user_ready,id:"
    if not resp or not resp.startswith(prefix):
        raise RuntimeError(resp or "empty daemon response")
    session_id = resp[len(prefix):].split(",created:", 1)[0].strip()
    if not session_id:
        raise RuntimeError("daemon returned an empty user session id")
    return session_id

def upload_file_to_daemon(filename, file_bytes):
    try:
        base64_content = base64.b64encode(file_bytes).decode('utf-8')
        payload = {
            'filename': filename,
            'content': base64_content
        }
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            'http://127.0.0.1:8088/api/upload',
            data=data,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req) as response:
            resp_data = json.loads(response.read().decode('utf-8'))
            return resp_data.get('success', False), resp_data.get('message', '')
    except Exception as e:
        return False, str(e)

def _read_ipc_token():
    """Read the daemon's IPC auth token (0600 file). The daemon rejects any command
    that isn't prefixed with 'AUTH <token>' (error:unknown_command:IPC_UNAUTHORIZED)."""
    try:
        with open(os.path.expanduser('~/.ernosdecent/ipc-token'), 'r') as tf:
            return tf.read().strip()
    except Exception:
        return ''


async def send_daemon_ipc(cmd_str):
    """Send a raw IPC command to the daemon and return the response.
    Uses an independent task so the IPC call survives parent task cancellation
    (which happens when discord.py cleans up on_message coroutines)."""
    try:
        return await _send_daemon_ipc_inner(cmd_str)
    except asyncio.CancelledError:
        print("[DELIVERY] WARNING: IPC task was cancelled mid-flight (asyncio.CancelledError)", flush=True)
        return "error:daemon_offline"
    except Exception as e:
        print(f"[Discord Bridge] IPC send wrapper failed: {e}", flush=True)
        return "error:daemon_offline"

async def _send_daemon_ipc_inner(cmd_str):
    """Inner IPC implementation, shielded from cancellation by the caller."""
    try:
        token = _read_ipc_token()
        if token:
            cmd_str = 'AUTH ' + token + ' ' + cmd_str
        reader, writer = await asyncio.open_connection('127.0.0.1', 5000)
        writer.write(cmd_str.encode('utf-8'))
        await writer.drain()
        # Read in chunks — AI responses can be very long
        chunks = []
        while True:
            chunk = await reader.read(65536)
            if not chunk:
                break
            chunks.append(chunk)
        writer.close()
        await writer.wait_closed()
        result = b''.join(chunks).decode('utf-8', errors='ignore').strip()
        if not result:
            print("[DELIVERY] WARNING: IPC returned empty response (daemon may have crashed)", flush=True)
            return "error:daemon_rebooted"
        return result
    except (ConnectionResetError, ConnectionAbortedError) as cre:
        print(f"[Discord Bridge] IPC connection lost/reset: {cre}", flush=True)
        return "error:daemon_rebooted"
    except Exception as e:
        print(f"[Discord Bridge] IPC send failed: {e}", flush=True)
        return "error:daemon_offline"

async def search_rag_database(query_text, session_id=None):
    """RAG search via the ErnosPlain daemon, scoped to the ACTIVE SESSION.
    Replaces the old Python rag_manager.py subprocess. The daemon's session-scoped
    search means a session only auto-retrieves documents ingested in that session;
    older/other-session documents are reached only via the agent's explicit tools."""
    try:
        sess = session_id if session_id is not None else (active_session_id or "")
        q = query_text.replace('\r', ' ').replace('\n', ' ').replace('|', ' ')
        resp = await send_daemon_ipc(f"RAG SEARCH {sess}|{q}")
        if resp and resp.lstrip().startswith("{"):
            return json.loads(resp)
    except Exception as e:
        print(f"[Discord Bridge] RAG search failed: {e}", flush=True)
    return None

def format_rag_context(rag_res):
    formatted = []
    results = rag_res.get("results", [])
    if results:
        formatted.append("Context from retrieved document segments:")
        for r in results:
            doc = r["document"]
            idx = r["chunk_index"]
            content = r["content"]
            formatted.append(f"\n[Document: {doc}, Segment: {idx}]\n{content}\n")
    return "\n".join(formatted)

async def query_daemon_ipc(prompt, author=None, message=None, image_path=None,
                           session_id=None, busy_token=None):
    try:
        # Prepare query (avoid newlines inside query to keep it clean)
        clean_prompt = prompt.replace('\r', ' ').replace('\n', ' ')

        # Build IPC command with sender identity and role tags
        reserved_session = session_id or "default"
        current_message_id = ""
        if message is not None:
            current_message_id = str(getattr(message, "id", "") or "")
        effective_image_path, visual_context = prepare_visual_context(
            reserved_session, clean_prompt, image_path, current_message_id
        )
        tags = ""
        if reserved_session:
            tags = f"[SESSION:{reserved_session}] "
        tags += build_discord_interaction_tags(author, message)
        # Current message coordinates → the agent can react([emoji]) to THIS message with no ids.
        if message is not None:
            try:
                tags += f"[MSGID:{message.id}] [CHANID:{message.channel.id}] "
            except Exception:
                pass
        # Native multimodal input. The bridge stores the binary under a sanitised,
        # bridge-owned path; the node passes it to gemma4's vision input rather than
        # decoding/indexing it as a text document.
        if effective_image_path:
            tags += f"[IMAGE_PATH:{effective_image_path}] "
        # P7: which surface this message arrived from — the awareness block tells the
        # agent which platform tools apply this turn (react/attach-on-reply are Discord).
        tags += "[PLATFORM:discord] "

        # Search the RAG database using the query
        context_parts = []
        rag_res = await search_rag_database(clean_prompt, reserved_session)
        if rag_res and (rag_res.get("results") or rag_res.get("structural_chunks")):
            context_parts.append(format_rag_context(rag_res))
        if context_parts:
            # Format and sanitize brackets to prevent option parsing issues.
            context_str = "\n\n".join(context_parts).replace('[', '(').replace(']', ')')
            tags += f"[IN_MEMORY_CONTEXT:{context_str}] "
        if visual_context:
            # Visual grounding is authoritative current-turn sensor/provenance state,
            # not document RAG. Keep it out of IN_MEMORY_CONTEXT: prompt assembly
            # deliberately wraps that channel in fragment/non-ownership constraints.
            # Mixing the two made Echo ignore an exact-byte match to its own image.
            visual_str = visual_context.replace('[', '(').replace(']', ')')
            tags += f"[VISUAL_CONTEXT:{visual_str}] "
        
        cmd = f"AI INFER {tags}{clean_prompt}"
        resp = await send_daemon_ipc(cmd)
        # One request, one dispatch. A busy fallback may accept it as an exact-turn
        # whisper, but the bridge never resends the full inference payload.
        if resp and resp.startswith("ai:accepted") and busy_token:
            accepted_turn = ""
            for part in resp.split(","):
                if part.startswith("turn:"):
                    accepted_turn = part.split(":", 1)[1].strip()
            _bind_session_turn(reserved_session, busy_token, accepted_turn)
        # Phase A3: detached turns ack instantly; the real answer arrives as a
        # `final_reply` trace row. Resolve it here so every caller keeps seeing the
        # exact legacy payload it already parses.
        return await resolve_ai_response(resp, reserved_session)
    except Exception as e:
        print(f"[Discord Bridge] IPC query failed: {e}", flush=True)
        return "error:daemon_offline"


def _final_reply_fallback_path(session_id, turn_tag):
    if not session_id or not turn_tag:
        return None
    digest = hashlib.sha256(f"{session_id}|{turn_tag}".encode("utf-8")).hexdigest()
    return os.path.expanduser(f"~/.ernosdecent/delivery-fallback/{digest}.reply")


def _consume_final_reply_fallback(session_id, turn_tag):
    """Consume the node's atomic terminal-reply fallback exactly once."""
    path = _final_reply_fallback_path(session_id, turn_tag)
    if not path or not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as handle:
            content = handle.read()
        prefix = f"turn:{turn_tag},"
        if not content.startswith(prefix):
            print(f"[DELIVERY] Refusing mismatched final-reply fallback: {path}", flush=True)
            return None
        os.unlink(path)
        return content[len(prefix):]
    except FileNotFoundError:
        return None
    except Exception as exc:
        print(f"[DELIVERY] Failed to consume final-reply fallback: {exc}", flush=True)
        return None


def _claim_final_reply_trace(session_id, turn_tag):
    """Atomically claim one terminal reply correlated to this exact turn."""
    prefix = f"turn:{turn_tag}," if turn_tag else None
    conn = None
    try:
        conn = sqlite3.connect(get_db_path(), timeout=15)
        conn.execute("PRAGMA busy_timeout=15000")
        cur = conn.cursor()
        if prefix:
            cur.execute(
                "SELECT id, content FROM trace_events WHERE session_id=? AND event_type='final_reply' AND sent=0 AND content LIKE ? ORDER BY id LIMIT 1",
                (session_id, prefix + "%"),
            )
        else:
            cur.execute(
                "SELECT id, content FROM trace_events WHERE session_id=? AND event_type='final_reply' AND sent=0 ORDER BY id LIMIT 1",
                (session_id,),
            )
        row = cur.fetchone()
        if not row:
            return None
        cur.execute("UPDATE trace_events SET sent=1 WHERE id=? AND sent=0", (row[0],))
        if cur.rowcount != 1:
            conn.rollback()
            return None
        conn.commit()
        content = row[1]
        if prefix and content.startswith(prefix):
            content = content[len(prefix):]
        return content
    except Exception:
        return None
    finally:
        if conn is not None:
            conn.close()


def _trace_turn_is_active(session_id, turn_tag):
    """Return true only while the node records this exact correlated turn as live."""
    if not session_id or not turn_tag:
        return False
    conn = None
    try:
        conn = sqlite3.connect(get_db_path(), timeout=15)
        conn.execute("PRAGMA busy_timeout=15000")
        row = conn.execute(
            "SELECT 1 FROM trace_active_turns WHERE session_id=? AND turn_id=? LIMIT 1",
            (session_id, turn_tag),
        ).fetchone()
        return row is not None
    except Exception:
        return False
    finally:
        if conn is not None:
            conn.close()


async def wait_final_reply(session_id, timeout_s=1800, turn_tag=None):
    """Phase A3: poll the session's `final_reply` trace row (direct SQLite — the same
    proven cross-process pattern as the trace/commands pollers). Returns the legacy
    payload string; marks the row sent so it is delivered exactly once.

    TURN CORRELATION: when the daemon's ack carried a turn id, only the row prefixed
    'turn:<tag>,' is accepted (and the prefix is stripped). Without it, a concurrent
    scheduler-job turn in the SAME session could land its final_reply first and be
    delivered as the user's answer — the tick bug: Maria's 'Hello' was 'answered' by an
    orphaned diagnostic job's reply while her real reply rotted unsent."""
    # ``timeout_s`` remains in the public signature for compatibility with older
    # callers and tests, but it is not a turn-completion deadline. A detached turn is
    # durable work: transport polling may retry forever, while only a correlated final
    # reply, structured terminal failure, explicit cancellation, or session-ending
    # action may conclude it.
    while True:
        fallback = _consume_final_reply_fallback(session_id, turn_tag)
        if fallback is not None:
            print(f"[DELIVERY] Recovered terminal reply from durable fallback for turn={turn_tag}", flush=True)
            return fallback
        claimed = _claim_final_reply_trace(session_id, turn_tag)
        if claimed is not None:
            return claimed
        await asyncio.sleep(0.5)


async def resolve_ai_response(resp, session_id):
    """Normalize a daemon AI ack: ai:accepted/ai:accepted_resume → wait for THAT TURN's
    final_reply row (matched by the turn id in the ack); ai:busy_whispered → friendly
    guidance note; anything else (old-style full payload, errors) passes through."""
    if resp and resp.startswith("ai:accepted"):
        sid = session_id
        tag = None
        for part in resp.split(","):
            if part.startswith("session:"):
                sid = part.split(":", 1)[1].strip()
            elif part.startswith("turn:"):
                tag = part.split(":", 1)[1].strip() or None
        if sid:
            return await wait_final_reply(sid, turn_tag=tag)
        return resp
    if resp and resp.startswith("ai:busy_whispered"):
        return "ai:ok|||RESPONSE|||🫧 Delivered as mid-turn guidance — I'm already working and will fold it in."
    return resp

import re

async def _delayed_delete(msg, delay_seconds):
    """Delete a Discord message after a delay. Fire-and-forget via asyncio.create_task."""
    try:
        await asyncio.sleep(delay_seconds)
        await msg.delete()
    except Exception:
        pass

async def send_discord_reply(message, text, speakable=False, edit_msg=None, files=None):
    """Send a reply, splitting into chunks if it exceeds Discord's 2000-char limit.
    When speakable=True, a 🔊 button is attached to the final chunk that plays the
    full message audio (the whole text, not just that chunk).
    If edit_msg is provided, it edits that message first instead of creating a new one.
    `files` (discord.File list) ride WITH the reply — attached to the final message so a
    generated image / created file arrives clean on the response, not as a separate message."""
    files = files or []
    if not text or not text.strip():
        text = "..."
    # Guard against invisible/control characters that produce blank Discord messages.
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
    if not text.strip():
        text = "(Response contained only invisible characters — this is a bug. Please retry.)"

    # discord.File objects are single-use. Capture their source before the first HTTP
    # attempt so a transient 5xx can rebuild the attachment bundle for a retry.
    file_specs = []
    for item in files:
        fp = getattr(item, 'fp', None)
        source_path = getattr(fp, 'name', None)
        filename = getattr(item, 'filename', None)
        description = getattr(item, 'description', None)
        spoiler = bool(getattr(item, 'spoiler', False))
        if isinstance(source_path, (str, bytes, os.PathLike)) and os.path.isfile(source_path):
            file_specs.append(('path', source_path, filename, spoiler, description))
        elif fp is not None and hasattr(fp, 'read') and hasattr(fp, 'seek'):
            old_pos = fp.tell()
            fp.seek(0)
            file_specs.append(('bytes', fp.read(), filename, spoiler, description))
            fp.seek(old_pos)
        try:
            item.close()
        except Exception:
            pass

    def fresh_files():
        rebuilt = []
        for kind, source, filename, spoiler, description in file_specs:
            if kind == 'path':
                rebuilt.append(discord.File(source, filename=filename, spoiler=spoiler, description=description))
            else:
                import io
                rebuilt.append(discord.File(io.BytesIO(source), filename=filename, spoiler=spoiler, description=description))
        return rebuilt

    # A stable enforced nonce makes an ambiguous retry idempotent: if Discord accepted
    # the first request but the 2xx was lost, it returns the existing message rather
    # than creating a duplicate. The two-digit suffix is unique per reply chunk.
    raw_message_id = str(getattr(message, 'id', int(time.time() * 1000)))
    nonce_base = ''.join(ch for ch in raw_message_id if ch.isdigit())[-21:] or str(int(time.time() * 1000))

    def is_definitive(exc):
        if isinstance(exc, (TypeError, ValueError, discord.Forbidden, discord.NotFound)):
            return True
        if isinstance(exc, discord.HTTPException):
            return exc.status < 500 and exc.status != 429
        return False

    async def retry_reply(content, chunk_index, reply_view=None, include_files=False):
        last_error = None
        nonce = f"{nonce_base}{chunk_index:02d}"
        for attempt in range(1, 5):
            try:
                return await message.reply(
                    content,
                    view=reply_view,
                    files=(fresh_files() if include_files else []),
                    nonce=nonce,
                )
            except Exception as exc:
                last_error = exc
                if is_definitive(exc) or attempt == 4:
                    break
                delay = 2 ** (attempt - 1)
                print(
                    f"[DELIVERY] Discord reply attempt {attempt}/4 failed: "
                    f"{type(exc).__name__}: {exc}; retrying in {delay}s",
                    flush=True,
                )
                await asyncio.sleep(delay)
        print(
            f"[DELIVERY] Discord reply FAILED after retries: "
            f"{type(last_error).__name__}: {last_error}",
            flush=True,
        )
        raise last_error

    async def retry_edit(content, edit_view):
        last_error = None
        for attempt in range(1, 5):
            try:
                return await edit_msg.edit(content=content, view=edit_view)
            except Exception as exc:
                last_error = exc
                if is_definitive(exc) or attempt == 4:
                    break
                delay = 2 ** (attempt - 1)
                print(
                    f"[DELIVERY] Discord edit attempt {attempt}/4 failed: "
                    f"{type(exc).__name__}: {exc}; retrying in {delay}s",
                    flush=True,
                )
                await asyncio.sleep(delay)
        raise last_error

    view = SpeakView(text) if speakable else None
    chunks = [text[i:i+2000] for i in range(0, len(text), 2000)]
    sent = []
    edit_succeeded = False

    if edit_msg:
        try:
            edited = await retry_edit(chunks[0], view if len(chunks) == 1 else None)
            sent.append(edited)
            edit_succeeded = True
            print(f"[DELIVERY] edit_msg.edit() succeeded, msg_id={edit_msg.id}", flush=True)
        except Exception as edit_err:
            # A placeholder edit is replaceable. If Discord rejects it, post a fresh,
            # nonce-protected reply so the actual answer is never lost with the placeholder.
            print(
                f"[DELIVERY] edit_msg.edit() FAILED: {type(edit_err).__name__}: "
                f"{edit_err} — falling back to reply",
                flush=True,
            )
            sent.append(await retry_reply(
                chunks[0], 0,
                reply_view=(view if len(chunks) == 1 else None),
                include_files=(len(chunks) == 1 and bool(file_specs)),
            ))
        start_index = 1
    else:
        start_index = 0

    for idx in range(start_index, len(chunks)):
        is_last = idx == len(chunks) - 1
        sent.append(await retry_reply(
            chunks[idx], idx,
            reply_view=(view if is_last else None),
            include_files=(is_last and bool(file_specs)),
        ))

    # Edits cannot add attachments, so deliver any files as an idempotent follow-up.
    if edit_msg and edit_succeeded and len(chunks) == 1 and file_specs:
        sent.append(await retry_reply(None, len(chunks), include_files=True))
    return sent


async def post_image_progress(channel, content):
    """Render an image_progress trace row (started/rendering/complete/failed/cancelled)
    as a single editable embed. Extracted so the PERSISTENT side-channel loop owns it."""
    global _image_gen_msg, _image_gen_last_edit
    import json as _json
    try:
        data = _json.loads(content)
    except Exception:
        return
    status = data.get('status', '')
    try:
        if status == 'started':
            embed = discord.Embed(title='\U0001f3a8 Generating Image...', description=data.get('prompt', ''), color=0xFFB300)
            embed.set_footer(text='rendering in the background — I’ll post it when it’s ready')
            _image_gen_msg = await channel.send(embed=embed)
            _image_gen_last_edit = time.time()
        elif status == 'rendering' and _image_gen_msg:
            if time.time() - _image_gen_last_edit >= 5.0:
                embed = _image_gen_msg.embeds[0] if _image_gen_msg.embeds else discord.Embed(title='\U0001f3a8 Generating Image...', color=0xFFB300)
                embed.set_footer(text=f"Elapsed: {data.get('elapsed_s', 0)}s")
                await _image_gen_msg.edit(embed=embed)
                _image_gen_last_edit = time.time()
        elif status in ('complete', 'cancelled') and _image_gen_msg:
            await _image_gen_msg.delete()
            _image_gen_msg = None
        elif status == 'failed':
            if _image_gen_msg:
                await _image_gen_msg.edit(embed=discord.Embed(title='❌ Image Generation Failed', description=data.get('error', 'Unknown error'), color=0xFF0000))
                _image_gen_msg = None
            else:
                await channel.send(embed=discord.Embed(title='❌ Image Generation Failed', description=data.get('error', 'Unknown error'), color=0xFF0000))
    except Exception as e:
        print(f"[Discord Bridge] image_progress render error: {e}", flush=True)


async def handle_subagent_event(channel, etype, content):
    """Sub-agent thread lifecycle (spawn → thread + live trace + whisper; approval →
    buttons in-thread; complete → close). Owned by the PERSISTENT side-channel loop, not
    the turn-scoped trace poller — because with yield-to-foreground the sub-agents spawn
    AFTER the parent turn (and its poller) has ended, so these events must be handled by
    a loop that outlives the turn or the threads/buttons/transparency never appear."""
    global _subagent_threads, _subagent_poll_tasks
    import json as _json
    try:
        data = _json.loads(content)
    except Exception:
        return
    task_id = data.get('task_id', '')
    if etype == 'subagent_spawn':
        role = data.get('role', 'Sub-Agent')
        instruction = data.get('instruction', '')
        if task_id in _subagent_threads:
            return
        try:
            sa_thread = await channel.create_thread(
                name=f'\U0001f916 {role} — {task_id}',
                type=discord.ChannelType.public_thread
            )
            _subagent_threads[task_id] = sa_thread
            embed = discord.Embed(title=f'\U0001f916 {role}', description=instruction, color=0x50c878)
            embed.set_footer(text=f'{task_id} • \U0001f7e2 Running • type here to whisper to this agent')

            class SubAgentKillView(discord.ui.View):
                def __init__(self, tid):
                    super().__init__(timeout=None)
                    self.tid = tid
                @discord.ui.button(label='🛑 Kill this agent', style=discord.ButtonStyle.red)
                async def kill(self, interaction, button):
                    if not is_admin_author(interaction.user):
                        await interaction.response.send_message('❌ Only the operator can kill sub-agents.', ephemeral=True)
                        return
                    await interaction.response.defer()
                    try:
                        resp = await send_daemon_ipc(f'AI KILL [AGENT:{self.tid}]')
                    except Exception:
                        resp = ''
                    button.disabled = True
                    button.label = 'Killed 🛑' if (resp and 'kill_ack' in resp) else 'Kill failed ⚠️'
                    await interaction.message.edit(view=self)
                    self.stop()
            await sa_thread.send(embed=embed, view=SubAgentKillView(task_id))
            _subagent_poll_tasks[task_id] = create_tracked_task(subagent_trace_stream(sa_thread, task_id))
        except Exception as e:
            print(f'[discord] Failed to create sub-agent thread: {e}', flush=True)
    elif etype == 'subagent_complete':
        summary = data.get('result_summary', '')
        sa_thread = _subagent_threads.get(task_id)
        if sa_thread:
            try:
                await sa_thread.send(embed=discord.Embed(title='✅ Complete', description=summary[:2000], color=0x34d399))
            except Exception:
                pass
            poll_task = _subagent_poll_tasks.pop(task_id, None)
            if poll_task:
                poll_task.cancel()
            _subagent_threads.pop(task_id, None)
    elif etype == 'subagent_approval':
        tool = data.get('tool', '')
        args = data.get('args', '')
        desc = data.get('description', '')
        sa_thread = _subagent_threads.get(task_id)
        embed = discord.Embed(title='⚠️ Permission Required', description=f'**{tool}**({args})\n\n{desc}', color=0xFFB300)

        class SubAgentApprovalView(discord.ui.View):
            def __init__(self, tid):
                super().__init__(timeout=3600)
                self.tid = tid
            @discord.ui.button(label='✅ Approve', style=discord.ButtonStyle.green)
            async def approve(self, interaction, button):
                await interaction.response.defer()
                try:
                    await send_daemon_ipc(f'AI APPROVE [AGENT:{self.tid}] [DECISION:yes]')
                except Exception:
                    pass
                for child in self.children:
                    child.disabled = True
                button.label = 'Approved ✅'
                await interaction.message.edit(view=self)
                self.stop()
            @discord.ui.button(label='❌ Deny', style=discord.ButtonStyle.red)
            async def deny(self, interaction, button):
                await interaction.response.defer()
                try:
                    await send_daemon_ipc(f'AI APPROVE [AGENT:{self.tid}] [DECISION:no]')
                except Exception:
                    pass
                for child in self.children:
                    child.disabled = True
                button.label = 'Denied ❌'
                await interaction.message.edit(view=self)
                self.stop()
        view = SubAgentApprovalView(task_id)
        if sa_thread:
            try:
                await sa_thread.send(embed=embed, view=view)
            except Exception:
                pass
        try:
            await channel.send(f'⚠️ Sub-agent **{task_id}** needs approval for `{tool}` — approve here or in its thread', view=SubAgentApprovalView(task_id))
        except Exception:
            pass


async def session_side_channel_loop():
    """PERSISTENT delivery of the agent's user-facing outputs — mid_message, attachment,
    image_progress — for the ACTIVE session to the main channel, INDEPENDENT of any
    turn's lifecycle. This is the fix for background/sub-agent/async outputs being
    dropped: the old path (trace_poll_loop) delivered these only until the foreground
    turn's done_event fired, so test_all's progress + report, async image gen, and
    post-turn sub-agent replies vanished. This loop runs forever (500ms), so nothing the
    agent emits to the active session is ever lost. Sub-agent THREAD trace is delivered
    separately by the per-task pollers (keyed by task id, not the active session)."""
    await client.wait_until_ready()
    ch = None
    while not client.is_closed():
        try:
            if ch is None:
                ch = client.get_channel(channel_id)
            sid = active_session_id or "default"
            if ch is not None:
                conn = sqlite3.connect(get_db_path())
                cur = conn.cursor()
                cur.execute(
                    "SELECT id, event_type, content FROM trace_events WHERE session_id=? AND sent=0 AND (event_type IN ('mid_message','attachment','image_progress','subagent_spawn','subagent_complete','subagent_approval') OR (event_type='final_reply' AND content GLOB 'turn:upgrade_wake_*')) ORDER BY id LIMIT 30",
                    (sid,),
                )
                rows = cur.fetchall()
                conn.close()
                for rid, etype, content in rows:
                    # During an active turn, LEAVE attachments for db_collect_attachments
                    # so they ride WITH the reply (cleaner). Only deliver attachments
                    # standalone once no turn is active (e.g. async image gen finishing
                    # after the turn). mid_message + image_progress always flow live.
                    if etype == 'attachment' and sid in _busy_sessions:
                        continue
                    try:
                        if etype == 'mid_message':
                            await post_mid_message(ch, content, session_id=sid)
                        elif etype == 'attachment':
                            await post_attachment(ch, content, session_id=sid)
                        elif etype == 'image_progress':
                            await post_image_progress(ch, content)
                        elif etype in ('subagent_spawn', 'subagent_complete', 'subagent_approval'):
                            await handle_subagent_event(ch, etype, content)
                        elif etype == 'final_reply':
                            wake_text = extract_upgrade_wake_response(content)
                            if wake_text is None:
                                continue
                            if not await post_upgrade_wake_reply(ch, wake_text, rid):
                                # Leave the durable row unclaimed; the next poll retries
                                # it with the same stable Discord nonce.
                                continue
                    except Exception as e:
                        print(f"[Discord Bridge] side-channel deliver error ({etype}): {e}", flush=True)
                    try:
                        c2 = sqlite3.connect(get_db_path())
                        c2.execute("UPDATE trace_events SET sent=1 WHERE id=?", (rid,))
                        c2.commit(); c2.close()
                    except Exception:
                        pass
        except sqlite3.OperationalError:
            pass
        except Exception as e:
            print(f"[Discord Bridge] side-channel loop error: {e}", flush=True)
        await asyncio.sleep(0.5)


async def post_mid_message(channel, content, session_id=None):
    """Post a mid-turn / sub-agent message to a channel, CHUNKED across multiple
    Discord messages (2000-char limit) instead of truncating. Sub-agent results can
    be long summaries — they must arrive in full, like the main agent's reply."""
    if (content or "").startswith("🎨 Here's the image you asked for"):
        update_visual_asset_description(
            session_id or active_session_id or "default", content,
            origin="assistant_generated",
        )
    body = f"💬 {content}"
    # Split on 1990 to leave headroom under Discord's 2000 hard limit.
    for i in range(0, max(len(body), 1), 1990):
        try:
            await channel.send(body[i:i + 1990])
        except Exception as e:
            print(f"[Discord Bridge] mid_message chunk send error: {e}", flush=True)


async def post_upgrade_wake_reply(channel, content, event_id):
    """Deliver an autonomous recompile report as a normal speakable response.

    False leaves the SQLite row unclaimed. Stable per-event/per-chunk nonces make
    ambiguous Discord retries idempotent instead of duplicating the report.
    """
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', content or '').strip()
    if not text:
        text = "The post-recompile status response contained no visible text. This is a bug."
    chunks = [text[index:index + 2000] for index in range(0, len(text), 2000)]
    nonce_base = ''.join(ch for ch in str(event_id) if ch.isdigit())[-20:] or str(int(time.time() * 1000))
    for index, chunk in enumerate(chunks):
        is_last = index == len(chunks) - 1
        for attempt in range(1, 5):
            try:
                await channel.send(
                    chunk,
                    view=SpeakView(text) if is_last else None,
                    nonce=f"{nonce_base}{index:02d}",
                )
                break
            except Exception as exc:
                if attempt == 4:
                    print(
                        f"[UPGRADE WAKE] Discord delivery failed after retries: "
                        f"{type(exc).__name__}: {exc}",
                        flush=True,
                    )
                    return False
                await asyncio.sleep(2 ** (attempt - 1))
    print(f"[UPGRADE WAKE] Delivered autonomous status event={event_id}", flush=True)
    return True


# Defence-in-depth: even though the node refuses secret paths before queueing an
# attachment, the bridge independently refuses these markers so a file can never
# be exfiltrated to Discord by a malformed/forged trace row.
_ATTACH_DENY_MARKERS = (
    "/.ssh/", "/.gnupg/", "id_rsa", "id_ed25519", ".env", "ipc-token",
    "/.ernosdecent/", "private_key", ".pem", ".key",
)
_ATTACH_MAX_BYTES = 24 * 1024 * 1024  # 24 MB — under Discord's non-nitro upload cap

async def subagent_trace_stream(thread, task_id):
    """Phase D: stream a sub-agent's OWN trace (keyed by its task_id session) into its
    Discord thread so the operator can watch it think/act live. Runs until cancelled by
    subagent_complete. Mirrors trace_poll_loop's direct-SQLite pattern; marks rows sent
    so the same event isn't posted twice. Skips the meta events handled elsewhere."""
    TYPE_EMOJI = {
        "thinking": "🧠", "reasoning": "💭", "action": "⚙️", "tool_exec": "🔧",
        "tool_result": "📊", "raw_output": "🗒️", "audit": "🛡️", "mid_message": "💬",
        "reply_audit": "✅", "no_action": "⚠️", "lookback": "🔎",
    }
    SKIP = {"subagent_spawn", "subagent_complete", "subagent_approval", "final_reply"}
    while True:
        try:
            conn = sqlite3.connect(get_db_path())
            cur = conn.cursor()
            cur.execute(
                "SELECT id, event_type, content FROM trace_events WHERE session_id=? AND sent=0 ORDER BY id LIMIT 20",
                (task_id,),
            )
            rows = cur.fetchall()
            for rid, etype, content in rows:
                cur.execute("UPDATE trace_events SET sent=1 WHERE id=?", (rid,))
            conn.commit()
            conn.close()
            for rid, etype, content in rows:
                if etype in SKIP:
                    continue
                try:
                    await post_trace_event(thread, etype, content, TYPE_EMOJI.get(etype, "•"))
                except Exception:
                    pass
        except sqlite3.OperationalError:
            pass
        except Exception as e:
            print(f"[discord] subagent trace stream error ({task_id}): {e}", flush=True)
        await asyncio.sleep(0.6)


async def post_trace_event(thread, etype, content, emoji):
    """Post a trace event to the thinking thread IN FULL, chunked across messages instead
    of truncating — full transparency: every action result, command output, reasoning and
    raw model output arrives complete, never clipped."""
    content = content if content is not None else ""
    header = f"{emoji} **{etype}**"
    CHUNK = 1850  # leave room for header + code fences under Discord's 2000 cap
    if len(content) <= CHUNK:
        try:
            await thread.send(f"{header}\n```\n{content}\n```")
        except Exception as e:
            print(f"[Discord Bridge] trace send error: {e}", flush=True)
        return
    parts = [content[i:i + CHUNK] for i in range(0, len(content), CHUNK)]
    for idx, part in enumerate(parts):
        h = header if idx == 0 else f"{emoji} **{etype}** (cont. {idx + 1}/{len(parts)})"
        try:
            await thread.send(f"{h}\n```\n{part}\n```")
        except Exception as e:
            print(f"[Discord Bridge] trace chunk send error: {e}", flush=True)


async def post_attachment(channel, path, session_id=None):
    """Deliver a file the agent produced/shared as a REAL Discord attachment in the
    main channel. Node-side queued via a trace_events row of type 'attachment'."""
    p = (path or "").strip()
    low = p.lower()
    if not p:
        return
    if any(m in low for m in _ATTACH_DENY_MARKERS):
        print(f"[Discord Bridge] attachment REFUSED (sensitive path): {p}", flush=True)
        return
    if not os.path.exists(p) or not os.path.isfile(p):
        await channel.send(f"📎 (couldn't attach `{os.path.basename(p)}` — file not found at delivery time)")
        return
    try:
        if os.path.getsize(p) > _ATTACH_MAX_BYTES:
            await channel.send(f"📎 `{os.path.basename(p)}` is too large to attach (>24MB). It's saved at `{p}`.")
            return
        if os.path.splitext(p)[1].lower() in _VISUAL_EXTENSIONS:
            visual_origin = "assistant_generated" if os.path.basename(p).startswith("generated_") else "assistant_shared"
            sid = session_id or active_session_id or "default"
            generation_prompt = (
                _generation_prompt_for_generated_path(sid, p)
                if visual_origin == "assistant_generated" else ""
            )
            register_visual_asset(
                sid, p, visual_origin, generation_prompt=generation_prompt
            )
        await channel.send(content=f"📎 `{os.path.basename(p)}`", file=discord.File(p))
    except Exception as e:
        print(f"[Discord Bridge] attachment send error for {p}: {e}", flush=True)
        try:
            await channel.send(f"📎 (failed to attach `{os.path.basename(p)}`: {e})")
        except Exception:
            pass


def parse_pending_approval(resp):
    """Parse 'ai:pending_approval,tool:<name>,summary:<args>' into (tool, summary)."""
    tool_name = "unknown"
    summary = ""
    parts = resp.split(",")
    for part in parts:
        if part.startswith("tool:"):
            tool_name = part[len("tool:"):]
        elif part.startswith("summary:"):
            summary = part[len("summary:"):]
    return tool_name, summary

def extract_ai_ok_response(resp):
    """Extract the reply text from an 'ai:ok' line. Uses the unique delimiter
    '|||RESPONSE|||' so base64 reasoning blocks cannot accidentally match."""
    marker = "|||RESPONSE|||"
    idx = resp.find(marker)
    return resp[idx + len(marker):] if idx >= 0 else resp


def extract_upgrade_wake_response(content):
    """Extract only an authenticated, specially correlated upgrade-wake reply."""
    prefix = "turn:upgrade_wake_"
    if not content or not content.startswith(prefix):
        return None
    separator = content.find(",")
    if separator < len(prefix):
        return None
    payload = content[separator + 1:]
    if payload.startswith("ai:ok"):
        answer = extract_ai_ok_response(payload).strip()
        return answer or "The post-recompile status response was empty. This is a delivery bug."
    if payload.startswith("ai:cancelled,response:"):
        return "🛑 " + payload[len("ai:cancelled,response:"):]
    return "Post-recompile status generation did not complete normally: " + payload

class ApprovalView(discord.ui.View):
    def __init__(self, author, timeout=None):
        super().__init__(timeout=timeout)
        self.author = author
        self.value = None

    @discord.ui.button(label="Approve", emoji="✅", style=discord.ButtonStyle.green)
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            await interaction.response.send_message("❌ Only the original sender can approve/deny this request.", ephemeral=True)
            return
        self.value = True
        # Disable all items in the view after click
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(content=interaction.message.content, view=self)
        self.stop()

    @discord.ui.button(label="Approve All", emoji="⚡", style=discord.ButtonStyle.blurple)
    async def approve_all(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            await interaction.response.send_message("❌ Only the original sender can approve/deny this request.", ephemeral=True)
            return
        self.value = "all"
        # Disable all items in the view after click
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(content=interaction.message.content, view=self)
        self.stop()

    @discord.ui.button(label="Auto-approve session", emoji="🔓", style=discord.ButtonStyle.gray)
    async def auto_approve_session(self, interaction: discord.Interaction, button: discord.ui.Button):
        """P4: PERSISTENT auto-approve for this SESSION (survives across requests until
        toggled off or the node restarts) — unlike Approve All, which only covers the
        current request. Approves the pending action too."""
        if interaction.user != self.author:
            await interaction.response.send_message("❌ Only the original sender can approve/deny this request.", ephemeral=True)
            return
        self.value = "session"
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(content=interaction.message.content, view=self)
        self.stop()

    @discord.ui.button(label="Deny", emoji="❌", style=discord.ButtonStyle.red)
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.author:
            await interaction.response.send_message("❌ Only the original sender can approve/deny this request.", ephemeral=True)
            return
        self.value = False
        # Disable all items in the view after click
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(content=interaction.message.content, view=self)
        self.stop()

def get_db_path():
    return os.path.expanduser("~/.ernosdecent/node.db")

def connect_db():
    conn = sqlite3.connect(get_db_path())
    conn.text_factory = lambda x: x.decode("utf-8", "replace")
    return conn


_VISUAL_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff"}
_VISUAL_QUERY_WORDS = (
    "image", "images", "picture", "pictures", "photo", "visual", "look",
    "which one", "first or second", "first of second", "same", "generated",
    "recognise", "recognize", "compare", "crop", "version",
)
_VISUAL_COMPARE_PHRASES = (
    "compare", "comparison", "same as", "different from", "previous image",
    "previous picture", "earlier image", "earlier picture", "original image",
    "before and after", "first or second", "which one", "which image",
    "which picture", "version of", "variation of",
)


def _is_explicit_visual_comparison(prompt):
    """True only when the user asks to relate this visual to another visual.

    Generic words such as "image", "describe", or an ordinal like "Image Two" are
    deliberately excluded. A new single attachment with those words is still the
    current subject; it must never be replaced by accumulated session history.
    """
    text = (prompt or "").lower()
    return any(phrase in text for phrase in _VISUAL_COMPARE_PHRASES)

def _init_visual_asset_db(conn):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS visual_assets (
            asset_id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            origin TEXT NOT NULL,
            message_id TEXT NOT NULL DEFAULT '',
            filename TEXT NOT NULL,
            path TEXT NOT NULL,
            sha256 TEXT NOT NULL,
            phash TEXT NOT NULL DEFAULT '',
            dhash TEXT NOT NULL DEFAULT '',
            width INTEGER NOT NULL DEFAULT 0,
            height INTEGER NOT NULL DEFAULT 0,
            parent_asset_id INTEGER NOT NULL DEFAULT 0,
            match_kind TEXT NOT NULL DEFAULT '',
            match_confidence INTEGER NOT NULL DEFAULT 0,
            generation_prompt TEXT NOT NULL DEFAULT '',
            description TEXT NOT NULL DEFAULT '',
            created_at INTEGER NOT NULL,
            presentation_ordinal INTEGER NOT NULL DEFAULT 0,
            asset_key TEXT NOT NULL UNIQUE
        );
        CREATE INDEX IF NOT EXISTS visual_assets_session_idx
            ON visual_assets(session_id, created_at, asset_id);
        CREATE INDEX IF NOT EXISTS visual_assets_sha_idx
            ON visual_assets(session_id, sha256);
        """
    )
    columns = {row[1] for row in conn.execute("PRAGMA table_info(visual_assets)")}
    if "presentation_ordinal" not in columns:
        conn.execute(
            "ALTER TABLE visual_assets ADD COLUMN presentation_ordinal "
            "INTEGER NOT NULL DEFAULT 0"
        )
    # Backfill legacy user presentation events deterministically. Storage asset ids
    # and generated-delivery rows never become conversational image numbers.
    conn.execute(
        """
        UPDATE visual_assets AS current
           SET presentation_ordinal=(
               SELECT COUNT(*)
                 FROM visual_assets AS prior
                WHERE prior.session_id=current.session_id
                  AND prior.origin='user_upload'
                  AND prior.message_id<>''
                  AND (prior.created_at < current.created_at OR
                       (prior.created_at=current.created_at AND
                        prior.asset_id <= current.asset_id))
           )
         WHERE current.origin='user_upload'
           AND current.message_id<>''
           AND current.presentation_ordinal=0
        """
    )
    conn.commit()

def _init_artifact_provenance_db(conn):
    """Canonical provenance for every Echo-created attachment, not just images."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS artifact_provenance (
            artifact_id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            turn_id TEXT NOT NULL DEFAULT '',
            path TEXT NOT NULL,
            sha256 TEXT NOT NULL,
            artifact_kind TEXT NOT NULL DEFAULT 'file',
            creator TEXT NOT NULL DEFAULT '',
            what_text TEXT NOT NULL DEFAULT '',
            why_text TEXT NOT NULL DEFAULT '',
            how_text TEXT NOT NULL DEFAULT '',
            observed_description TEXT NOT NULL DEFAULT '',
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL,
            UNIQUE(session_id,path,sha256)
        )"""
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS artifact_provenance_session_idx "
        "ON artifact_provenance(session_id,created_at,artifact_id)"
    )
    conn.commit()

def _visual_fingerprints(path):
    """Content hash plus two independently computed visual fingerprints."""
    sha = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            sha.update(chunk)
    try:
        from PIL import Image
        import numpy as np
        from scipy.fftpack import dct
        with Image.open(path) as source:
            image = source.convert("RGB")
            width, height = image.size
            gray32 = np.asarray(image.convert("L").resize((32, 32)), dtype=np.float32)
            coeffs = dct(dct(gray32, axis=0, norm="ortho"), axis=1, norm="ortho")[:8, :8]
            median = float(np.median(coeffs[1:, :]))
            pbits = (coeffs > median).flatten()
            phash = f"{sum(int(bit) << idx for idx, bit in enumerate(pbits)):016x}"
            gray9 = np.asarray(image.convert("L").resize((9, 8)), dtype=np.int16)
            dbits = (gray9[:, 1:] > gray9[:, :-1]).flatten()
            dhash = f"{sum(int(bit) << idx for idx, bit in enumerate(dbits)):016x}"
            return sha.hexdigest(), phash, dhash, width, height
    except Exception as exc:
        print(f"[Visual Memory] fingerprint fallback for {path}: {exc}", flush=True)
        return sha.hexdigest(), "", "", 0, 0

def _hash_similarity(left, right):
    if not left or not right or len(left) != len(right):
        return 0.0
    try:
        distance = (int(left, 16) ^ int(right, 16)).bit_count()
    except AttributeError:
        distance = bin(int(left, 16) ^ int(right, 16)).count("1")
    return max(0.0, 1.0 - distance / (len(left) * 4.0))

def _recent_visual_assets(session_id, limit=8):
    try:
        conn = connect_db()
        _init_visual_asset_db(conn)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM visual_assets WHERE session_id=? ORDER BY created_at DESC, asset_id DESC LIMIT ?",
            (session_id or "default", limit),
        ).fetchall()
        conn.close()
        return [dict(row) for row in reversed(rows)]
    except Exception as exc:
        print(f"[Visual Memory] recent lookup failed: {exc}", flush=True)
        return []

def _visual_original_origin(asset):
    """Return the recorded creator-side origin without exposing storage identity.

    A user upload can be an exact or perceptual re-upload of an image Echo made
    earlier. register_visual_asset collapses that chain to its root, so provenance
    questions must use the root origin rather than the transport event's origin.
    """
    parent_id = int(asset.get("parent_asset_id") or 0)
    if not parent_id:
        return asset.get("origin", "")
    try:
        conn = connect_db()
        _init_visual_asset_db(conn)
        row = conn.execute(
            "SELECT origin FROM visual_assets WHERE asset_id=?", (parent_id,)
        ).fetchone()
        conn.close()
        if row:
            return row[0]
    except Exception as exc:
        print(f"[Visual Memory] provenance lookup failed: {exc}", flush=True)
    return asset.get("origin", "")

def _generation_prompt_for_generated_path(session_id, path):
    """Recover the creative prompt belonging to a generated image delivery.

    Image rendering is asynchronous: the prompt is durably emitted when the job
    starts, while the generated asset is registered minutes later at attachment
    delivery. Associate the nearest preceding start event with the timestamp in the
    generated filename, keeping the creative purpose attached to the visual itself.
    """
    name_match = re.search(r"generated_(\d+)\.", os.path.basename(path or ""))
    generated_at = int(name_match.group(1)) // 1000 if name_match else 0
    try:
        conn = connect_db()
        rows = conn.execute(
            "SELECT content, created_at FROM trace_events "
            "WHERE session_id=? AND event_type='image_progress' "
            "ORDER BY created_at DESC, id DESC LIMIT 32",
            (session_id or "default",),
        ).fetchall()
        conn.close()
        for content, created_at in rows:
            if generated_at and int(created_at or 0) > generated_at:
                continue
            try:
                event = json.loads(content or "{}")
            except Exception:
                continue
            if event.get("status") == "started" and event.get("prompt"):
                return str(event["prompt"])
    except Exception as exc:
        print(f"[Visual Memory] generation-prompt lookup failed: {exc}", flush=True)
    return ""

def _visual_original_generation_prompt(asset):
    """Return the original Echo generation's creative prompt for this asset chain."""
    root = asset
    parent_id = int(asset.get("parent_asset_id") or 0)
    try:
        conn = connect_db()
        _init_visual_asset_db(conn)
        conn.row_factory = sqlite3.Row
        if parent_id:
            row = conn.execute(
                "SELECT * FROM visual_assets WHERE asset_id=?", (parent_id,)
            ).fetchone()
            if row:
                root = dict(row)
        prompt = str(root.get("generation_prompt") or "")
        if not prompt and root.get("origin") == "assistant_generated":
            prompt = _generation_prompt_for_generated_path(
                root.get("session_id") or asset.get("session_id"), root.get("path", "")
            )
            if prompt:
                conn.execute(
                    "UPDATE visual_assets SET generation_prompt=? WHERE asset_id=?",
                    (prompt[:4000], int(root.get("asset_id") or 0)),
                )
                conn.commit()
        conn.close()
        return prompt
    except Exception as exc:
        print(f"[Visual Memory] original generation prompt lookup failed: {exc}", flush=True)
        return ""

def _visual_creation_provenance(asset):
    """Resolve the hash-bound creation record for the root visual artifact."""
    root = asset
    parent_id = int(asset.get("parent_asset_id") or 0)
    try:
        conn = connect_db()
        _init_visual_asset_db(conn)
        _init_artifact_provenance_db(conn)
        conn.row_factory = sqlite3.Row
        if parent_id:
            row = conn.execute(
                "SELECT * FROM visual_assets WHERE asset_id=?", (parent_id,)
            ).fetchone()
            if row:
                root = dict(row)
        row = conn.execute(
            "SELECT * FROM artifact_provenance "
            "WHERE session_id=? AND sha256=? "
            "ORDER BY artifact_id DESC LIMIT 1",
            (
                root.get("session_id") or asset.get("session_id") or "default",
                root.get("sha256", ""),
            ),
        ).fetchone()
        conn.close()
        return dict(row) if row else {}
    except Exception as exc:
        print(f"[Visual Memory] creation provenance lookup failed: {exc}", flush=True)
        return {}

def _select_prior_presented_visuals(assets, count=2):
    """Select images in the order the user presented them for visual discussion.

    Database rows are not conversational image numbers: generated delivery,
    re-upload, and transformed-copy rows may all describe one visual. Prefer actual
    user presentation events and keep chronological order. Fall back to the latest
    live records only when no such presentation history exists.
    """
    live = [asset for asset in assets if os.path.isfile(asset.get("path", ""))]
    presented = [
        asset for asset in live
        if asset.get("origin") == "user_upload" and asset.get("message_id")
    ]
    presented.sort(
        key=lambda asset: (
            int(asset.get("presentation_ordinal") or 0),
            int(asset.get("created_at") or 0),
            int(asset.get("asset_id") or 0),
        )
    )
    pool = presented if len(presented) >= count else live
    return pool[-count:]


_VISUAL_NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8,
}


def _requested_visual_count(prompt, available):
    """Return the explicit number of prior presentation events the user named."""
    text = (prompt or "").lower()
    candidates = []
    for match in re.finditer(
        r"\b(\d+|one|two|three|four|five|six|seven|eight)\s+"
        r"(?:most\s+recent\s+|recent\s+|previous\s+|last\s+)?"
        r"(?:image|images|picture|pictures|photo|photos|visual|visuals)\b",
        text,
    ):
        raw = match.group(1)
        candidates.append(int(raw) if raw.isdigit() else _VISUAL_NUMBER_WORDS[raw])
    for match in re.finditer(
        r"\b(?:image|picture|photo)\s+"
        r"(\d+|one|two|three|four|five|six|seven|eight)\b",
        text,
    ):
        raw = match.group(1)
        candidates.append(int(raw) if raw.isdigit() else _VISUAL_NUMBER_WORDS[raw])
    if re.search(r"\ball\s+(?:the\s+)?(?:images|pictures|photos|visuals)\b", text):
        return available
    if candidates:
        return max(1, min(max(candidates), available))
    return min(2, available)


def _visual_conversation_label(asset, fallback):
    ordinal = int(asset.get("presentation_ordinal") or 0)
    value = ordinal if ordinal > 0 else fallback
    words = {
        1: "ONE", 2: "TWO", 3: "THREE", 4: "FOUR",
        5: "FIVE", 6: "SIX", 7: "SEVEN", 8: "EIGHT",
    }
    return words.get(value, str(value))

def register_visual_asset(session_id, path, origin, message_id="", filename="",
                          generation_prompt="", description=""):
    """Persist provenance and visually match uploads against remembered assets."""
    if not path or not os.path.isfile(path):
        return None
    if os.path.splitext(path)[1].lower() not in _VISUAL_EXTENSIONS:
        return None
    try:
        sha, phash, dhash, width, height = _visual_fingerprints(path)
        sid = session_id or "default"
        name = filename or os.path.basename(path)
        key_material = f"{sid}|{origin}|{message_id}|{os.path.realpath(path)}"
        asset_key = hashlib.sha256(key_material.encode("utf-8", "replace")).hexdigest()
        conn = connect_db()
        _init_visual_asset_db(conn)
        conn.row_factory = sqlite3.Row
        existing = conn.execute(
            "SELECT * FROM visual_assets WHERE asset_key=?", (asset_key,)
        ).fetchone()
        if existing:
            if generation_prompt and not existing["generation_prompt"]:
                conn.execute(
                    "UPDATE visual_assets SET generation_prompt=? WHERE asset_id=?",
                    (generation_prompt[:4000], int(existing["asset_id"])),
                )
                conn.commit()
                existing = conn.execute(
                    "SELECT * FROM visual_assets WHERE asset_id=?",
                    (int(existing["asset_id"]),),
                ).fetchone()
            result = dict(existing)
            conn.close()
            return result

        parent_asset_id = 0
        match_kind = ""
        match_confidence = 0
        candidates = conn.execute(
            "SELECT * FROM visual_assets WHERE session_id=? ORDER BY created_at DESC, asset_id DESC LIMIT 32",
            (sid,),
        ).fetchall()
        best = None
        best_score = 0.0
        for candidate in candidates:
            if candidate["sha256"] == sha:
                best, best_score, match_kind = candidate, 1.0, "exact-bytes"
                break
            pscore = _hash_similarity(candidate["phash"], phash)
            dscore = _hash_similarity(candidate["dhash"], dhash)
            score = pscore * 0.65 + dscore * 0.35
            if score > best_score:
                best, best_score = candidate, score
        # Perceptual matches are candidate retrieval, not proof. The actual model is
        # shown both images on a comparison board before it answers.
        if best is not None and best_score >= 0.78:
            parent_asset_id = int(best["asset_id"])
            # Collapse re-upload chains to the original remembered asset so the
            # system retains authorship/provenance rather than merely linking one
            # user transport event to another.
            seen_ids = set()
            while parent_asset_id and parent_asset_id not in seen_ids:
                seen_ids.add(parent_asset_id)
                root_row = conn.execute(
                    "SELECT parent_asset_id FROM visual_assets WHERE asset_id=?",
                    (parent_asset_id,),
                ).fetchone()
                if not root_row or int(root_row[0] or 0) == 0:
                    break
                parent_asset_id = int(root_row[0])
            match_kind = match_kind or "perceptual-candidate"
            match_confidence = int(round(best_score * 100))
        presentation_ordinal = 0
        if origin == "user_upload" and message_id:
            presentation_ordinal = int(conn.execute(
                "SELECT COALESCE(MAX(presentation_ordinal),0)+1 FROM visual_assets "
                "WHERE session_id=? AND origin='user_upload' AND message_id<>''",
                (sid,),
            ).fetchone()[0])
        conn.execute(
            """INSERT INTO visual_assets
               (session_id,origin,message_id,filename,path,sha256,phash,dhash,width,height,
                parent_asset_id,match_kind,match_confidence,generation_prompt,description,
                created_at,presentation_ordinal,asset_key)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (sid, origin, str(message_id or ""), name, os.path.realpath(path), sha,
             phash, dhash, width, height, parent_asset_id, match_kind,
             match_confidence, generation_prompt, description, int(time.time()),
             presentation_ordinal, asset_key),
        )
        asset_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.commit()
        row = conn.execute("SELECT * FROM visual_assets WHERE asset_id=?", (asset_id,)).fetchone()
        result = dict(row)
        conn.close()
        print(
            f"[Visual Memory] registered asset={asset_id} origin={origin} "
            f"match={match_kind or 'new'} confidence={match_confidence}",
            flush=True,
        )
        return result
    except Exception as exc:
        print(f"[Visual Memory] registration failed for {path}: {exc}", flush=True)
        return None

def update_visual_asset_description(session_id, description, path=None, origin=None):
    text_value = (description or "").strip()
    if not text_value:
        return
    try:
        conn = connect_db()
        _init_visual_asset_db(conn)
        if path:
            visual_row = conn.execute(
                "SELECT sha256 FROM visual_assets WHERE session_id=? AND path=? "
                "ORDER BY asset_id DESC LIMIT 1",
                (session_id or "default", os.path.realpath(path)),
            ).fetchone()
            conn.execute(
                "UPDATE visual_assets SET description=? WHERE asset_id=(SELECT asset_id FROM visual_assets WHERE session_id=? AND path=? ORDER BY asset_id DESC LIMIT 1)",
                (text_value[:4000], session_id or "default", os.path.realpath(path)),
            )
            _init_artifact_provenance_db(conn)
            if visual_row:
                conn.execute(
                    "UPDATE artifact_provenance SET observed_description=?,updated_at=? "
                    "WHERE artifact_id=(SELECT artifact_id FROM artifact_provenance "
                    "WHERE session_id=? AND sha256=? ORDER BY artifact_id DESC LIMIT 1)",
                    (
                        text_value[:4000], int(time.time()),
                        session_id or "default", visual_row[0],
                    ),
                )
        elif origin:
            conn.execute(
                "UPDATE visual_assets SET description=? WHERE asset_id=(SELECT asset_id FROM visual_assets WHERE session_id=? AND origin=? ORDER BY asset_id DESC LIMIT 1)",
                (text_value[:4000], session_id or "default", origin),
            )
            _init_artifact_provenance_db(conn)
            visual_row = conn.execute(
                "SELECT sha256 FROM visual_assets WHERE session_id=? AND origin=? "
                "ORDER BY asset_id DESC LIMIT 1",
                (session_id or "default", origin),
            ).fetchone()
            if visual_row:
                conn.execute(
                    "UPDATE artifact_provenance SET observed_description=?,updated_at=? "
                    "WHERE artifact_id=(SELECT artifact_id FROM artifact_provenance "
                    "WHERE session_id=? AND sha256=? ORDER BY artifact_id DESC LIMIT 1)",
                    (
                        text_value[:4000], int(time.time()),
                        session_id or "default", visual_row[0],
                    ),
                )
        conn.commit()
        conn.close()
    except Exception as exc:
        print(f"[Visual Memory] description update failed: {exc}", flush=True)

def _visual_memory_context(session_id, current_message_id=""):
    assets = _recent_visual_assets(session_id, 8)
    if not assets:
        return "", []
    current_prefix = f"{current_message_id}:" if current_message_id else ""
    current_assets = [
        asset for asset in assets
        if current_prefix and str(asset.get("message_id", "")).startswith(current_prefix)
    ]
    lines = [
        "VISUAL GROUNDING (private system context): inspect the supplied native image pixels before answering. "
        "This context and any composite image were assembled internally; the user did not send a board."
    ]
    for index, asset in enumerate(current_assets, 1):
        original_origin = _visual_original_origin(asset)
        original_generation_prompt = _visual_original_generation_prompt(asset)
        creation_provenance = _visual_creation_provenance(asset)
        exact_self_reupload = (
            asset.get("origin") == "user_upload"
            and original_origin == "assistant_generated"
            and asset.get("match_kind") == "exact-bytes"
            and int(asset.get("match_confidence") or 0) == 100
        )
        if exact_self_reupload:
            provenance = (
                "authoritatively established as an exact byte-for-byte re-upload "
                "of an image Echo generated earlier in this session"
            )
        elif asset.get("origin") == "assistant_generated":
            provenance = "authoritatively established as generated by Echo"
        elif original_origin == "assistant_generated":
            provenance = (
                "a visual-similarity candidate for an earlier Echo-generated image, "
                "not proven provenance; compare the pixels before claiming recognition"
            )
        else:
            provenance = "externally supplied, with no recorded self-generation match"
        current_label = (
            "CURRENT ATTACHMENT" if len(current_assets) == 1
            else f"CURRENT ATTACHMENT {index}"
        )
        lines.append(
            f"{current_label}: this is exactly the attachment visible in the native "
            f"vision input; recorded original provenance is {provenance}."
        )
        if exact_self_reupload and original_generation_prompt:
            lines.append(
                "Its authoritative original creative purpose was expressed by this "
                f"generation prompt: {original_generation_prompt}"
            )
        if exact_self_reupload and creation_provenance:
            lines.append(
                "AUTHORITATIVE CREATION PROVENANCE FOR THIS ATTACHMENT:\n"
                f"- WHAT Echo made: {creation_provenance.get('what_text', '')}\n"
                f"- WHY Echo made it: {creation_provenance.get('why_text', '')}\n"
                f"- HOW Echo made it: {creation_provenance.get('how_text', '')}\n"
                f"- WHAT Echo observed in the result: "
                f"{creation_provenance.get('observed_description', '')}"
            )
    if current_assets:
        lines.append(
            "Answer from what you can actually see in the CURRENT ATTACHMENT unless the user explicitly requests comparison. "
            "CURRENT ATTACHMENT means exactly the image on this message. A phrase such as "
            "'Image Two' names its position in the user's conversational sequence; it "
            "does not conflict with CURRENT ATTACHMENT and must never be mistaken for a "
            "different image because of internal numbering."
        )
        lines.append(
            "Exact-byte provenance is established current-turn evidence, not a retrieval fragment. "
            "When the user asks whether you recognize the image, acknowledge an exact self-generated match directly "
            "while also independently describing the visible pixels."
        )
    lines.append(
        "In the user-facing reply, never mention this context, a board, labels, paths, memory assets, IDs, "
        "metadata, routing, or internal provenance machinery unless the user explicitly asks how the system works."
    )
    return "\n".join(lines), assets

def _build_visual_comparison_board(session_id, assets, current_asset_ids=None):
    live = [asset for asset in assets if os.path.isfile(asset.get("path", ""))]
    if len(live) < 2:
        return ""
    try:
        from PIL import Image, ImageDraw, ImageFont
        tile_w, tile_h = 512, 512
        cols = 2
        rows = (len(live) + cols - 1) // cols
        board = Image.new("RGB", (tile_w * cols, tile_h * rows), (18, 18, 22))
        draw = ImageDraw.Draw(board)
        font = ImageFont.load_default(size=22)
        current_ids = {int(value) for value in (current_asset_ids or [])}
        current_number = 0
        memory_number = 0
        for index, asset in enumerate(live, 1):
            with Image.open(asset["path"]) as source:
                image = source.convert("RGB")
                image.thumbnail((tile_w - 24, tile_h - 70))
                x0 = ((index - 1) % cols) * tile_w
                y0 = ((index - 1) // cols) * tile_h
                x = x0 + (tile_w - image.width) // 2
                y = y0 + 52 + (tile_h - 64 - image.height) // 2
                board.paste(image, (x, y))
                if int(asset["asset_id"]) in current_ids:
                    current_number += 1
                    label = f"CURRENT IMAGE {current_number}"
                else:
                    memory_number += 1
                    label = f"IMAGE {_visual_conversation_label(asset, memory_number)}"
                draw.rectangle((x0, y0, x0 + tile_w, y0 + 44), fill=(0, 0, 0))
                draw.text((12 + x0, 10 + y0), label, fill=(255, 255, 255), font=font)
        out_dir = os.path.expanduser("~/.ernosdecent/visual-comparisons")
        os.makedirs(out_dir, mode=0o700, exist_ok=True)
        out_path = os.path.join(out_dir, f"{session_id}_{int(time.time() * 1000)}.jpg")
        board.save(out_path, "JPEG", quality=92)
        os.chmod(out_path, 0o600)
        return out_path
    except Exception as exc:
        print(f"[Visual Memory] comparison board failed: {exc}", flush=True)
        return ""

def prepare_visual_context(session_id, prompt, current_image_path=None,
                           current_message_id=""):
    context, assets = _visual_memory_context(session_id, current_message_id)
    current_prefix = f"{current_message_id}:" if current_message_id else ""
    current_assets = [
        asset for asset in assets
        if current_prefix and str(asset.get("message_id", "")).startswith(current_prefix)
    ]
    current_ids = {int(asset["asset_id"]) for asset in current_assets}
    # A new attachment is the authoritative visual subject. Only an explicit request
    # to relate it to an earlier visual may expand it into a board, and even then the
    # current upload is first and carries a CURRENT IMAGE label.
    if current_image_path:
        if _is_explicit_visual_comparison(prompt) and current_assets:
            historical_pool = [
                asset for asset in assets
                if int(asset["asset_id"]) not in current_ids
            ]
            historical = _select_prior_presented_visuals(historical_pool, 1)
            comparison_assets = current_assets + historical
            if len(comparison_assets) >= 2:
                board = _build_visual_comparison_board(
                    session_id, comparison_assets, current_asset_ids=current_ids
                )
                if board:
                    context += (
                        "\nThe native visual input shows the current image first and the relevant earlier image second. "
                        "Inspect both images. Do not refer to the internally assembled composite in the reply."
                    )
                    return board, context
        return current_image_path, context
    wants_comparison = any(word in (prompt or "").lower() for word in _VISUAL_QUERY_WORDS)
    if wants_comparison and len(assets) >= 2:
        presented_count = len([
            asset for asset in assets
            if asset.get("origin") == "user_upload" and asset.get("message_id")
            and os.path.isfile(asset.get("path", ""))
        ])
        requested_count = _requested_visual_count(prompt, presented_count)
        comparison_assets = _select_prior_presented_visuals(assets, requested_count)
        board = _build_visual_comparison_board(session_id, comparison_assets)
        if board:
            inspection = (
                "Inspect both sets of pixels before answering."
                if len(comparison_assets) == 2
                else "Inspect every labelled set of pixels before answering."
            )
            context += (
                "\nThe native visual input contains the requested user-presented images in chronological order. "
                "Every IMAGE number is its stable conversational presentation number; never renumber it. "
                + inspection
            )
            for index, asset in enumerate(comparison_assets, 1):
                original_origin = _visual_original_origin(asset)
                provenance = "self-generated by Echo" if original_origin == "assistant_generated" else "external"
                exact_note = " (a later user re-upload of that generated image)" if (
                    asset.get("origin") == "user_upload" and original_origin == "assistant_generated"
                ) else ""
                label = _visual_conversation_label(asset, index)
                context += f"\nIMAGE {label} recorded original provenance: {provenance}{exact_note}."
            context += (
                "\nState the answer directly. Do not mention the board, its labels, storage records, IDs, metadata, "
                "or how the images were routed unless explicitly asked."
            )
            return board, context
    return current_image_path, context


def _should_store_visual_description(message, prompt):
    """Persist a reply only when it describes exactly one current attachment."""
    if _is_explicit_visual_comparison(prompt):
        return False
    attachments = getattr(message, "attachments", None) or []
    visual_count = 0
    for attachment in attachments:
        ext = os.path.splitext(getattr(attachment, "filename", ""))[1].lower()
        content_type = (getattr(attachment, "content_type", "") or "").lower()
        if ext in _VISUAL_EXTENSIONS or content_type.startswith("image/"):
            visual_count += 1
    return visual_count <= 1

def db_request_cancel(session_id):
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO trace_cancellations (session_id) VALUES (?)", (session_id,))
        conn.commit()
        conn.close()
        return "ok"
    except Exception as e:
        print(f"[Discord Bridge] Failed to write cancel to DB: {e}", flush=True)
        return f"error:{e}"

def db_poll_traces(session_id):
    events = []
    try:
        conn = connect_db()
        cursor = conn.cursor()
        # mid_message / image_progress / attachment are USER-FACING outputs delivered to
        # the MAIN CHANNEL by the PERSISTENT session_side_channel_loop (which outlives the
        # turn, so background/sub-agent/async-image outputs are never dropped). This
        # turn-scoped thread trace only streams the thinking events.
        cursor.execute(
            "SELECT id, event_type, content, created_at FROM trace_events WHERE sent=0 AND event_type NOT IN ('attachment','mid_message','image_progress','final_reply','subagent_spawn','subagent_complete','subagent_approval') AND session_id=? ORDER BY id LIMIT 50",
            (session_id,)
        )
        rows = cursor.fetchall()
        for r in rows:
            events.append({
                "id": r[0],
                "type": r[1],
                "content": r[2],
                "ts": r[3]
            })
            cursor.execute("UPDATE trace_events SET sent=1 WHERE id=?", (r[0],))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[Discord Bridge] Failed to query trace_events: {e}", flush=True)
    return events

def db_collect_attachments(session_id):
    """Collect this turn's file attachments (paths) and mark them sent. These are NOT posted
    as separate messages (db_poll_traces excludes them) — they ride WITH the final reply so the
    image/file arrives attached to the response, cleanly, instead of mid-generation."""
    paths = []
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, content FROM trace_events WHERE sent=0 AND event_type='attachment' AND session_id=? ORDER BY id",
            (session_id,)
        )
        for r in cursor.fetchall():
            paths.append(r[1])
            cursor.execute("UPDATE trace_events SET sent=1 WHERE id=?", (r[0],))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[Discord Bridge] Failed to collect attachments: {e}", flush=True)
    return paths

def build_discord_files(paths, session_id=None):
    """Build discord.File objects from attachment paths, secret-safe + size-capped."""
    out = []
    for p in paths or []:
        p = (p or "").strip()
        low = p.lower()
        if not p or any(m in low for m in _ATTACH_DENY_MARKERS):
            continue
        try:
            if os.path.isfile(p) and os.path.getsize(p) <= _ATTACH_MAX_BYTES:
                if os.path.splitext(p)[1].lower() in _VISUAL_EXTENSIONS:
                    visual_origin = "assistant_generated" if os.path.basename(p).startswith("generated_") else "assistant_shared"
                    sid = session_id or active_session_id or "default"
                    generation_prompt = (
                        _generation_prompt_for_generated_path(sid, p)
                        if visual_origin == "assistant_generated" else ""
                    )
                    register_visual_asset(
                        sid, p, visual_origin, generation_prompt=generation_prompt
                    )
                out.append(discord.File(p, filename=os.path.basename(p)))
        except Exception as e:
            print(f"[Discord Bridge] build_discord_files skip {p}: {e}", flush=True)
    return out

def db_get_pending_deletes():
    pending = []
    try:
        conn = connect_db()
        cursor = conn.cursor()
        now = int(time.time())
        cursor.execute(
            "SELECT id, thread_id FROM trace_pending_deletes WHERE delete_after <= ? ORDER BY id LIMIT 50",
            (now,)
        )
        rows = cursor.fetchall()
        for r in rows:
            pending.append({
                "id": r[0],
                "thread_id": r[1]
            })
        conn.close()
    except Exception as e:
        print(f"[Discord Bridge] Failed to get pending deletes: {e}", flush=True)
    return pending

def db_complete_delete(pid):
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM trace_pending_deletes WHERE id=?", (pid,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[Discord Bridge] Failed to complete delete: {e}", flush=True)

def db_schedule_delete(thread_id, delay_secs):
    try:
        conn = connect_db()
        cursor = conn.cursor()
        now = int(time.time())
        delete_after = now + delay_secs
        cursor.execute(
            "INSERT INTO trace_pending_deletes (thread_id, delete_after, created_at) VALUES (?, ?, ?)",
            (str(thread_id), delete_after, now)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[Discord Bridge] Failed to schedule delete: {e}", flush=True)

class StopView(discord.ui.View):
    """A Stop button that allows the original user (or admins) to cancel a running
    AI inference process mid-task by writing directly to SQLite cancellations table."""
    def __init__(self, author, session_id, timeout=None):
        super().__init__(timeout=timeout)
        self.author = author
        self.session_id = session_id

    @discord.ui.button(label="Stop AI", emoji="🛑", style=discord.ButtonStyle.danger)
    async def stop_ai(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Allow original sender OR admins to halt the run
        if interaction.user != self.author and not is_admin_author(interaction.user):
            await interaction.response.send_message("❌ Only the original sender or an administrator can stop this task.", ephemeral=True)
            return

        await interaction.response.defer()
        # Disable the stop button
        for item in self.children:
            item.disabled = True
        try:
            await interaction.message.edit(view=self)
        except Exception:
            pass

        # Write cancel flag directly to SQLite
        sess = self.session_id or "default"
        resp = db_request_cancel(sess)
        print(f"[Discord Bridge] Stop button clicked for session {sess}, SQLite write ack: {resp}", flush=True)

        # Epoch bump via HTTP — same instant abort as WebUI stop button.
        # The SQLite cancel is read at the next turn boundary; /api/cancel
        # bumps the C epoch latch, aborting in-flight HTTP within ~50ms.
        try:
            import aiohttp as _aiohttp
            async with _aiohttp.ClientSession() as _s:
                await _s.post("http://127.0.0.1:8088/api/cancel", timeout=_aiohttp.ClientTimeout(total=2))
        except Exception:
            pass  # SQLite cancel is primary; HTTP is fast-path bonus

class SpeakView(discord.ui.View):
    """A 🔊 button attached to AI replies. On click, asks the node to synthesise
    the message audio (Kokoro, voice bm_fable @1.15x via the `TTS SPEAK` IPC verb)
    exactly once and uploads the resulting WAV as a Discord attachment. A later
    click removes that attachment message; the following click uploads the cached
    WAV again without synthesising it again. Anyone in the channel may use it —
    reading a message aloud is a read-only action."""
    def __init__(self, text, timeout=None):
        super().__init__(timeout=timeout)
        self.text = text
        self._state_lock = asyncio.Lock()
        self._busy = False
        self._audio_path = None
        self._delivered_message = None

    async def _render_button(self, interaction, button, state):
        if state == "busy":
            button.label = "Generating…"
            button.emoji = "⏳"
            button.disabled = True
        elif state == "delivered":
            button.label = "Remove voice"
            button.emoji = "🔇"
            button.disabled = False
        elif state == "cached":
            button.label = "Replay voice"
            button.emoji = "🔊"
            button.disabled = False
        else:
            button.label = "Speak"
            button.emoji = "🔊"
            button.disabled = False
        try:
            await interaction.message.edit(view=self)
        except Exception as exc:
            print(
                f"[TTS] Could not refresh Speak button state {state}: "
                f"{type(exc).__name__}: {exc}",
                flush=True,
            )

    @staticmethod
    def _response_path(resp):
        for part in (resp or "").split(","):
            if part.startswith("path:"):
                return part[len("path:"):].strip()
        return None

    async def _upload_cached_audio(self, interaction, path):
        return await interaction.followup.send(
            file=discord.File(path, filename="ernos_voice.wav"),
            wait=True,
        )

    @discord.ui.button(label="Speak", emoji="🔊", style=discord.ButtonStyle.secondary)
    async def speak(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()

        already_busy = False
        async with self._state_lock:
            if self._busy:
                already_busy = True
                delivered = None
                cached_path = None
            else:
                self._busy = True
                delivered = self._delivered_message
                cached_path = self._audio_path

        if already_busy:
            await interaction.followup.send(
                "⏳ This reply's voice request is already in progress.",
                ephemeral=True,
            )
            return

        await self._render_button(interaction, button, "busy")
        try:
            if delivered is not None:
                try:
                    await delivered.delete()
                except discord.NotFound:
                    print("[TTS] Delivered voice was already deleted.", flush=True)
                async with self._state_lock:
                    self._delivered_message = None
                await self._render_button(interaction, button, "cached")
                return

            path = cached_path
            if not path or not os.path.isfile(path):
                # Collapse newlines so the text rides cleanly in the single-line IPC command.
                speak_text = (self.text or "").replace("\r", " ").replace("\n", " ").strip()
                if not speak_text:
                    await interaction.followup.send("Nothing to speak.", ephemeral=True)
                    await self._render_button(interaction, button, "ready")
                    return
                resp = await send_daemon_ipc("TTS SPEAK " + speak_text)
                path = self._response_path(resp)
                if not path or not os.path.isfile(path):
                    await interaction.followup.send(f"🔇 TTS failed: {resp}", ephemeral=True)
                    await self._render_button(interaction, button, "ready")
                    return
                async with self._state_lock:
                    self._audio_path = path

            sent = await self._upload_cached_audio(interaction, path)
            if sent is None:
                raise RuntimeError("Discord did not acknowledge the uploaded voice message")
            async with self._state_lock:
                self._delivered_message = sent
            await self._render_button(interaction, button, "delivered")
        except Exception as exc:
            await interaction.followup.send(
                f"🔇 Voice delivery failed: {type(exc).__name__}: {exc}",
                ephemeral=True,
            )
            state = "cached" if self._audio_path and os.path.isfile(self._audio_path) else "ready"
            await self._render_button(interaction, button, state)
        finally:
            async with self._state_lock:
                self._busy = False

async def _handle_approval_bg(message, resp, reply_msg, trace_ctx,
                              session_id, busy_token):
    """Background task wrapper for handle_tool_approval.
    Runs independently of on_message so discord.py can't cancel it."""
    try:
        await handle_tool_approval(message, resp, edit_msg=reply_msg)
    except Exception as e:
        print(f"[DELIVERY] _handle_approval_bg EXCEPTION: {type(e).__name__}: {e}", flush=True)
        try:
            await message.reply(f"⚠️ Error during approval flow: {e}")
        except Exception:
            pass
    finally:
        _release_session_busy(session_id, busy_token)
        if trace_ctx:
            await _cleanup_traces(trace_ctx)

async def _handle_clarify_bg(message, resp, reply_msg, trace_ctx,
                             session_id, busy_token):
    """Background task wrapper for handle_clarification.
    Runs independently of on_message so discord.py can't cancel it."""
    try:
        await handle_clarification(message, resp, edit_msg=reply_msg)
    except Exception as e:
        print(f"[DELIVERY] _handle_clarify_bg EXCEPTION: {type(e).__name__}: {e}", flush=True)
        try:
            await message.reply(f"⚠️ Error during clarification flow: {e}")
        except Exception:
            pass
    finally:
        _release_session_busy(session_id, busy_token)
        if trace_ctx:
            await _cleanup_traces(trace_ctx)

async def handle_tool_approval(message, resp, edit_msg=None):
    """Handle a pending tool approval: show a card with interactive buttons and wait for user decision."""
    tool_name, summary = parse_pending_approval(resp)
    
    # Build the approval card
    card_text = (
        f"🔒 **Tool Approval Required**\n"
        f"```\n"
        f"Tool:  {tool_name}\n"
        f"Args:  {summary}\n"
        f"```\n"
        f"Please approve or deny this action."
    )
    
    view = ApprovalView(author=message.author, timeout=APPROVAL_TIMEOUT)
    approval_msg = await message.reply(card_text, view=view)
    
    timed_out = await view.wait()
    
    if timed_out or view.value is None:
        for item in view.children:
            item.disabled = True
        await approval_msg.edit(content=f"⏰ **Timed out** — `{tool_name}` was auto-denied.", view=view)
        await send_daemon_ipc("AI DENY")
        try: await approval_msg.delete()
        except Exception: pass
        return
        
    if view.value is True:
        await approval_msg.edit(content=f"✅ **Approved** `{tool_name}` — executing...", view=view)
        ipc_resp = await resolve_ai_response(await send_daemon_ipc("AI APPROVE"), active_session_id or "")
    elif view.value == "all":
        await approval_msg.edit(content=f"⚡ **Approved All** `{tool_name}` — executing subsequent actions automatically...", view=view)
        ipc_resp = await resolve_ai_response(await send_daemon_ipc("AI APPROVE_ALL"), active_session_id or "")
    elif view.value == "session":
        # Enable the persistent per-session toggle FIRST, then approve the pending
        # action — every later gate in this session auto-approves until /autoapprove off.
        await approval_msg.edit(content=f"🔓 **Session auto-approve ON** — `{tool_name}` approved; no more prompts this session (`/autoapprove off` to re-enable).", view=view)
        await send_daemon_ipc("AI AUTOAPPROVE ON")
        ipc_resp = await resolve_ai_response(await send_daemon_ipc("AI APPROVE"), active_session_id or "")
    else:
        await approval_msg.edit(content=f"❌ **Denied** `{tool_name}` — cancelled.", view=view)
        ipc_resp = await resolve_ai_response(await send_daemon_ipc("AI DENY"), active_session_id or "")
        
    try: await approval_msg.delete()
    except Exception: pass

    # Process the result from the daemon after approval/denial
    print(f"[DELIVERY] Approval IPC resp: len={len(ipc_resp) if ipc_resp else 'None'} prefix={repr(ipc_resp[:80]) if ipc_resp else 'None'}", flush=True)
    if ipc_resp.startswith("ai:pending_approval,"):
        print("[DELIVERY] Approval result: chained pending_approval", flush=True)
        await handle_tool_approval(message, ipc_resp, edit_msg=edit_msg)
    elif ipc_resp.startswith("ai:clarify,"):
        print("[DELIVERY] Approval result: clarify", flush=True)
        await handle_clarification(message, ipc_resp, edit_msg=edit_msg)
    elif ipc_resp.startswith("ai:cancelled,response:"):
        print("[DELIVERY] Approval result: cancelled", flush=True)
        await send_discord_reply(message, "🛑 " + ipc_resp[len("ai:cancelled,response:"):], edit_msg=edit_msg)
    elif ipc_resp.startswith("ai:ok"):
        ai_resp = extract_ai_ok_response(ipc_resp)
        print(f"[DELIVERY] Approval result: ai:ok, len={len(ai_resp)}", flush=True)
        _att = build_discord_files(db_collect_attachments(active_session_id or "default"))
        await send_discord_reply(message, ai_resp, speakable=True, edit_msg=edit_msg, files=_att)
    elif ipc_resp == "error:daemon_offline" or ipc_resp == "error:daemon_rebooted":
        print(f"[DELIVERY] Approval result: {ipc_resp}", flush=True)
        await send_discord_reply(message, "🔄 Daemon went offline during processing. Please retry.", edit_msg=edit_msg)
    else:
        print(f"[DELIVERY] Approval result: UNMATCHED resp={repr(ipc_resp[:200])}", flush=True)
        await send_discord_reply(message, f"Agent response: {ipc_resp}", edit_msg=edit_msg)


# --- F3: clarification over Discord ---
def parse_clarify_questions(resp):
    """Parse 'ai:clarify,questions:<json or raw "text||opt1||opt2">' -> [(text, [opts])].
    Falls back to raw string splitting if JSON parsing fails."""
    idx = resp.find("questions:")
    raw = resp[idx + len("questions:"):].strip() if idx >= 0 else ""
    if not raw:
        return []
    # Primary: try JSON array parse
    try:
        arr = json.loads(raw)
        if isinstance(arr, list):
            out = []
            for item in arr:
                bits = str(item).split("||")
                qtext = bits[0] if bits else ""
                opts = [b for b in bits[1:] if b]
                out.append((qtext, opts))
            return out
    except Exception as e:
        print(f"[Discord Bridge] JSON parse failed for clarify questions: {e}", flush=True)
        print(f"[Discord Bridge] Raw questions string: {raw[:200]}", flush=True)
    # Fallback: treat as a single raw question string (strip outer brackets/quotes)
    fallback = raw.strip()
    if fallback.startswith("["):
        fallback = fallback[1:]
    if fallback.endswith("]"):
        fallback = fallback[:-1]
    fallback = fallback.strip()
    if fallback.startswith('"'):
        fallback = fallback[1:]
    if fallback.endswith('"'):
        fallback = fallback[:-1]
    if not fallback:
        return []
    bits = fallback.split("||")
    qtext = bits[0] if bits else ""
    opts = [b.strip() for b in bits[1:] if b.strip()]
    return [(qtext, opts)]

class ClarifyCommentModal(discord.ui.Modal):
    def __init__(self, view):
        super().__init__(title="Provide Direct Clarification")
        self.view = view
        self.comment_input = discord.ui.TextInput(
            label="Your comment / feedback",
            style=discord.TextStyle.long,
            placeholder="Type your response/clarification here...",
            required=True,
            max_length=1000
        )
        self.add_item(self.comment_input)

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user != self.view.author:
            await interaction.response.send_message("❌ Only the original sender can answer this.", ephemeral=True)
            return
        
        self.view.value = self.comment_input.value
        for item in self.view.children:
            item.disabled = True
        await interaction.response.edit_message(content=interaction.message.content, view=self.view)
        self.view.stop()

class ClarifyView(discord.ui.View):
    """Buttons for the agent's clarifying options (one click = one answer), plus a
    'Work with what we have' escape. Only the original asker may answer."""
    def __init__(self, author, questions, timeout=None):
        super().__init__(timeout=timeout)
        self.author = author
        self.value = None
        multi = len(questions) > 1
        count = 0
        for qi, (qtext, opts) in enumerate(questions):
            for opt in opts:
                if count >= 20:  # leave room for the escape buttons (Discord max 25)
                    break
                answer = f"Q{qi+1}: {opt}" if multi else opt
                btn = discord.ui.Button(label=answer[:80], style=discord.ButtonStyle.secondary)
                btn.callback = self._make_cb(answer)
                self.add_item(btn)
                count += 1
        
        esc = discord.ui.Button(label="Work with what we have", style=discord.ButtonStyle.primary)
        esc.callback = self._make_cb("__USE_CURRENT__")
        self.add_item(esc)
        
        comment_btn = discord.ui.Button(label="Leave Comment...", style=discord.ButtonStyle.primary)
        async def comment_cb(interaction: discord.Interaction):
            if interaction.user != self.author:
                await interaction.response.send_message("❌ Only the original sender can answer this.", ephemeral=True)
                return
            await interaction.response.send_modal(ClarifyCommentModal(self))
        comment_btn.callback = comment_cb
        self.add_item(comment_btn)

    def _make_cb(self, answer):
        async def cb(interaction: discord.Interaction):
            if interaction.user != self.author:
                await interaction.response.send_message("❌ Only the original sender can answer this.", ephemeral=True)
                return
            self.value = answer
            for item in self.children:
                item.disabled = True
            await interaction.response.edit_message(content=interaction.message.content, view=self)
            self.stop()
        return cb

async def handle_clarification(message, resp, edit_msg=None):
    """Show the agent's clarifying questions with clickable options and resume the run."""
    questions = parse_clarify_questions(resp)
    if not questions:
        print(f"[Discord Bridge] WARNING: clarify response parsed to zero questions. Raw: {resp[:300]}", flush=True)
        # Fall back: surface the raw question text so the user at least sees something
        idx = resp.find("questions:")
        raw_q = resp[idx + len("questions:"):].strip() if idx >= 0 else "The agent has a question."
        # Strip JSON-array wrapping for display
        raw_q = raw_q.strip('[] "')
        if "||" in raw_q:
            parts = raw_q.split("||")
            questions = [(parts[0], [p.strip() for p in parts[1:] if p.strip()])]
        else:
            questions = [(raw_q[:500], [])]
    lines = ["🤔 **A quick clarification to get this right:**"]
    for i, (qt, opts) in enumerate(questions):
        lines.append(f"**{i+1}. {qt}**")
    card_text = "\n".join(lines) + "\n\nPick an option below — or *Work with what we have* to let me proceed."
    view = ClarifyView(author=message.author, questions=questions, timeout=APPROVAL_TIMEOUT)
    clar_msg = await message.reply(card_text, view=view)

    timed_out = await view.wait()
    if timed_out or view.value is None:
        for item in view.children:
            item.disabled = True
        await clar_msg.edit(content="⏰ No answer — proceeding with what we have.", view=view)
        ipc_resp = await resolve_ai_response(await send_daemon_ipc("AI CLARIFY __USE_CURRENT__"), active_session_id or "")
    else:
        answer = view.value
        if answer == "__USE_CURRENT__":
            await clar_msg.edit(content="✅ Proceeding with current understanding.", view=view)
        else:
            await clar_msg.edit(content=f"✅ Got it: `{answer}`", view=view)
        ipc_resp = await resolve_ai_response(await send_daemon_ipc(f"AI CLARIFY {answer}"), active_session_id or "")

    # Clean up the clarification card — it served its purpose
    try:
        await clar_msg.delete()
    except Exception:
        pass

    if ipc_resp.startswith("ai:clarify,"):
        await handle_clarification(message, ipc_resp, edit_msg=edit_msg)
    elif ipc_resp.startswith("ai:pending_approval,"):
        await handle_tool_approval(message, ipc_resp, edit_msg=edit_msg)
    elif ipc_resp.startswith("ai:cancelled,response:"):
        await send_discord_reply(message, "🛑 " + ipc_resp[len("ai:cancelled,response:"):], edit_msg=edit_msg)
    elif ipc_resp.startswith("ai:ok"):
        await send_discord_reply(message, extract_ai_ok_response(ipc_resp), speakable=True, edit_msg=edit_msg)
    elif ipc_resp == "error:daemon_offline":
        await send_discord_reply(message, "❌ Daemon went offline during clarification.", edit_msg=edit_msg)
    else:
        await send_discord_reply(message, f"Agent response: {ipc_resp}", edit_msg=edit_msg)


async def _exec_bridge_command(action, args):
    """Execute one agent->bridge command via discord.py. Returns a result string.
    This is the live half of the node<->bridge RPC; only runs with a real bot token."""
    try:
        if action == "list_channels":
            out = []
            for g in client.guilds:
                for c in g.text_channels:
                    out.append(f"{c.id}: #{c.name} ({g.name})")
            return "\n".join(out) if out else "(no text channels visible)"
        if action == "read_channel":
            ch = client.get_channel(int(args.strip()))
            if ch is None:
                return f"error: channel {args} not found"
            msgs = []
            # Registered retrieval improvements are durable contracts, so their
            # source evidence cannot silently fall outside an arbitrary 20-message
            # window as an active channel grows. Discord paginates this bounded read;
            # 200 retains a finite response while covering the verified production
            # marker horizon used by the live scavenger contract.
            async for m in ch.history(limit=200):
                msgs.append(f"{m.author.display_name}: {m.content}")
            msgs.reverse()
            return "\n".join(msgs) if msgs else "(no recent messages)"
        if action == "add_reaction":
            parts = args.split("|")
            if len(parts) < 3:
                return "error: add_reaction needs channel_id|message_id|emoji"
            ch = client.get_channel(int(parts[0].strip()))
            if ch is None:
                return f"error: channel {parts[0]} not found"
            msg = await ch.fetch_message(int(parts[1].strip()))
            await msg.add_reaction(parts[2].strip())
            return "reaction added"
        return f"error: unknown action {action}"
    except Exception as e:
        return f"error: {e}"

async def bridge_commands_db_loop():
    """Poll bridge_commands DIRECTLY from SQLite and answer directly — the PRIMARY RPC
    path. The IPC path below (bridge_poll_loop) cannot fetch commands while the
    single-threaded daemon is busy running an agent turn, which is exactly when tools
    like react/discord_list_channels enqueue them — so mid-turn commands could never
    complete mid-turn and always timed out as 'discord:queued'. Direct DB polling
    mirrors trace_poll_loop's proven cross-process pattern: 500ms cadence, atomic
    pending->sent claim (no double-execution with the IPC fallback), result written
    straight back as status='done' for the node's bridge_wait_result to pick up."""
    await client.wait_until_ready()
    while not client.is_closed():
        try:
            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, action, args FROM bridge_commands WHERE status='pending' ORDER BY id LIMIT 20"
            )
            rows = cursor.fetchall()
            claimed = []
            for cid, action, args in rows:
                # Atomic claim: whoever flips pending->sent first (this loop or the IPC
                # fallback's bridge_poll) owns the command; the other sees nothing.
                cursor.execute(
                    "UPDATE bridge_commands SET status='sent' WHERE id=? AND status='pending'",
                    (cid,),
                )
                if cursor.rowcount == 1:
                    claimed.append((cid, action, args))
            conn.commit()
            conn.close()
            for cid, action, args in claimed:
                result = await _exec_bridge_command(action, args)
                try:
                    conn = connect_db()
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE bridge_commands SET status='done', result=? WHERE id=?",
                        (result, cid),
                    )
                    conn.commit()
                    conn.close()
                except Exception as e:
                    print(f"[Discord Bridge] bridge_commands result write error: {e}", flush=True)
        except sqlite3.OperationalError:
            # Table not created yet (node makes it lazily) or DB momentarily locked —
            # both normal; next tick retries.
            pass
        except Exception as e:
            print(f"[Discord Bridge] bridge_commands db loop error: {e}", flush=True)
        await asyncio.sleep(0.5)

async def bridge_poll_loop():
    """FALLBACK RPC path: poll the daemon over IPC for queued agent->bridge commands.
    Only useful when the bridge cannot reach the SQLite file directly (remote bridge);
    bridge_commands_db_loop above normally claims commands first. NOTE: this path
    cannot serve commands enqueued MID-TURN (the single-threaded IPC daemon is held by
    the agent turn) — that is why the DB loop is primary.
    The daemon side is decent_net/bridge_rpc.ep (DISCORD POLL / DISCORD RESULT)."""
    await client.wait_until_ready()
    while not client.is_closed():
        try:
            resp = await send_daemon_ipc("DISCORD POLL")
            if resp and resp.startswith("["):
                cmds = json.loads(resp)
                for cmd in cmds:
                    cid = cmd.get("id")
                    result = await _exec_bridge_command(cmd.get("action", ""), cmd.get("args", ""))
                    # data may contain newlines/pipes; the daemon splits on the FIRST '|'.
                    await send_daemon_ipc(f"DISCORD RESULT {cid}|{result}")
        except Exception as e:
            print(f"[Discord Bridge] poll loop error: {e}", flush=True)
        await asyncio.sleep(1.0)

async def trace_poll_loop(thread, session_id, done_event, main_channel=None):
    """Poll SQLite directly for trace events and stream them into a Discord thread.
    Runs until done_event is set (inference complete).
    mid_message events are posted to main_channel (visible to user), not the trace thread."""
    TYPE_EMOJI = {
        "thinking": "🧠", "raw_output": "📝", "reasoning": "💭",
        "lookback": "🔍", "action": "⚙️", "approval": "🔒",
        "audit": "🛡️", "tool_exec": "🔧", "tool_result": "📋",
        "reply_audit": "✅", "no_action": "⚠️", "done": "🏁",
        "mid_message": "💬", "whisper_received": "🫧",
    }
    await client.wait_until_ready()
    while not done_event.is_set():
        try:
            events = db_poll_traces(session_id)
            for ev in events:
                etype = ev.get("type", "info")
                content = ev.get("content", "")
                emoji = TYPE_EMOJI.get(etype, "ℹ️")
                # mid_message: post to main channel as a visible agent reply (chunked, not truncated)
                if etype == "mid_message" and main_channel:
                    await post_mid_message(main_channel, content)
                    continue
                # attachment: deliver the file the agent produced/shared to the main channel
                if etype == "attachment" and main_channel:
                    await post_attachment(main_channel, content)
                    continue

                # --- Image generation progress embed ---
                if etype == 'image_progress' and main_channel:
                    global _image_gen_msg, _image_gen_last_edit
                    import json as _json
                    try:
                        data = _json.loads(content)
                    except Exception:
                        await post_trace_event(thread, etype, content, emoji)
                        continue
                    status = data.get('status', '')
                    if status == 'started':
                        embed = discord.Embed(
                            title='\U0001f3a8 Generating Image...',
                            description=data.get('prompt', ''),
                            color=0xFFB300
                        )
                        embed.set_footer(text='Elapsed: 0s')
                        _image_gen_msg = await main_channel.send(embed=embed)
                        _image_gen_last_edit = time.time()
                    elif status == 'rendering' and _image_gen_msg:
                        if time.time() - _image_gen_last_edit >= 5.0:
                            elapsed = data.get('elapsed_s', 0)
                            embed = _image_gen_msg.embeds[0] if _image_gen_msg.embeds else discord.Embed(title='\U0001f3a8 Generating Image...', color=0xFFB300)
                            embed.set_footer(text=f'Elapsed: {elapsed}s')
                            try:
                                await _image_gen_msg.edit(embed=embed)
                                _image_gen_last_edit = time.time()
                            except Exception:
                                pass
                    elif status == 'complete' and _image_gen_msg:
                        try:
                            await _image_gen_msg.delete()
                        except Exception:
                            pass
                        _image_gen_msg = None
                    elif status == 'failed' and _image_gen_msg:
                        embed = discord.Embed(title='\u274c Image Generation Failed', description=data.get('error', 'Unknown error'), color=0xFF0000)
                        try:
                            await _image_gen_msg.edit(embed=embed)
                            msg_ref = _image_gen_msg
                            asyncio.get_event_loop().call_later(30, lambda: asyncio.ensure_future(msg_ref.delete()))
                        except Exception:
                            pass
                        _image_gen_msg = None
                    elif status == 'cancelled' and _image_gen_msg:
                        try:
                            await _image_gen_msg.delete()
                        except Exception:
                            pass
                        _image_gen_msg = None
                    continue

                # Sub-agent lifecycle events (spawn/complete/approval) are owned by the
                # PERSISTENT session_side_channel_loop (they now arrive AFTER this
                # turn-scoped poller has stopped, since sub-agents yield to foreground and
                # spawn once the parent turn ends) \u2014 and are excluded from db_poll_traces
                # so they are never consumed here. Only in-turn thinking-trace lands here.

                # All other events: post to trace thread IN FULL (chunked, never truncated)
                await post_trace_event(thread, etype, content, emoji)
        except Exception as e:
            print(f"[Discord Bridge] trace poll error: {e}", flush=True)
        await asyncio.sleep(0.5)  # Poll every 500ms for near-real-time
    # Final drain — pick up any events written during/after the last LLM call
    # (e.g. mid_message events). Without this, the loop exits before delivering them.
    try:
        events = db_poll_traces(session_id)
        for ev in events:
            etype = ev.get("type", "info")
            content = ev.get("content", "")
            emoji = TYPE_EMOJI.get(etype, "ℹ️")
            if etype == "mid_message" and main_channel:
                await post_mid_message(main_channel, content)
                continue
            if etype == "attachment" and main_channel:
                await post_attachment(main_channel, content)
                continue
            await post_trace_event(thread, etype, content, emoji)
    except Exception as e:
        print(f"[Discord Bridge] final trace drain error: {e}", flush=True)

async def pending_deletes_cleanup_loop():
    """On startup, check for any threads whose 2-minute delete timer expired while
    the bridge was offline (crash resilience). Then continue checking periodically."""
    await client.wait_until_ready()
    while not client.is_closed():
        try:
            pending = db_get_pending_deletes()
            for item in pending:
                tid = str(item.get("thread_id", ""))
                pid = item.get("id", 0)
                if tid:
                    try:
                        thread_obj = client.get_channel(int(tid))
                        if thread_obj:
                            await thread_obj.delete()
                            print(f"[Discord Bridge] Cleaned up expired trace thread {tid}", flush=True)
                    except Exception as e:
                        print(f"[Discord Bridge] Failed to delete thread {tid}: {e}", flush=True)
                    db_complete_delete(pid)
        except Exception as e:
            print(f"[Discord Bridge] pending deletes cleanup error: {e}", flush=True)
        await asyncio.sleep(15.0)  # Check every 15 seconds

async def _start_ai_with_traces(message, query_text, author, reply_msg=None,
                                image_path=None, session_id=None, busy_token=None):
    """Start an AI query with a trace thread. Returns (resp, trace_ctx) where trace_ctx
    contains the lifecycle objects needed to keep polling alive across approval/clarification
    flows. The caller MUST call _cleanup_traces(trace_ctx) when the full response cycle ends."""
    sess = session_id or "default"

    trace_ctx = {
        "thread": None,
        "initial_msg": None,
        "done_event": asyncio.Event(),
        "trace_task": None,
        "reply_msg": reply_msg,
    }

    # Discord does not support message threads inside DMs. Guild-channel turns keep
    # their trace thread; authorized DM turns run the identical agent path without it.
    if not _is_direct_message(message):
        try:
            thread = await message.create_thread(
                name=f"🔍 ErnOS Trace — {query_text[:50]}",
                auto_archive_duration=60
            )
            trace_ctx["thread"] = thread
            trace_ctx["initial_msg"] = await thread.send(
                "🔍 **Ernos Reasoning Trace** — live stream of thinking, tool calls, and audit results.\n*This thread auto-deletes 2 minutes after the response.*",
                view=StopView(author=message.author, session_id=sess)
            )
        except Exception as e:
            print(f"[Discord Bridge] Failed to create trace thread: {e}", flush=True)

    # Start trace poller in background — stays alive until _cleanup_traces is called
    thread = trace_ctx["thread"]
    if thread:
        trace_ctx["trace_task"] = asyncio.create_task(
            trace_poll_loop(thread, sess, trace_ctx["done_event"], main_channel=message.channel)
        )

    # Run the actual AI query (blocking IPC call). Pass the message so the agent can
    # react([emoji]) to THIS message without handling ids itself.
    resp = await query_daemon_ipc(
        query_text, author=author, message=message, image_path=image_path,
        session_id=sess, busy_token=busy_token,
    )

    return resp, trace_ctx


async def _cleanup_traces(trace_ctx):
    """Stop the trace poll loop, remove buttons, and schedule thread deletion.
    Called ONCE when the full response cycle is complete (after all approval/clarification
    rounds are finished)."""
    done_event = trace_ctx["done_event"]
    trace_task = trace_ctx["trace_task"]
    thread = trace_ctx["thread"]
    initial_msg = trace_ctx["initial_msg"]
    reply_msg = trace_ctx["reply_msg"]

    # Signal trace poller to stop, give it one last poll cycle
    done_event.set()
    if trace_task:
        try:
            await asyncio.wait_for(trace_task, timeout=2.0)
        except asyncio.TimeoutError:
            trace_task.cancel()

    # Remove the stop button on trace thread
    if thread and initial_msg:
        try:
            await initial_msg.edit(view=None)
        except Exception as e:
            print(f"[Discord Bridge] Failed to remove trace thread stop button: {e}", flush=True)

    # NOTE: Do NOT edit reply_msg here to remove its view. By this point,
    # send_discord_reply has already replaced the StopView with SpeakView (TTS button).
    # Editing reply_msg with view=None would strip the TTS button from the final response.

    # Send final trace marker
    if thread:
        try:
            await thread.send("🏁 **Trace complete** — this thread will auto-delete in 2 minutes.")
        except Exception:
            pass
        db_schedule_delete(thread.id, 120)
        create_tracked_task(_delete_thread_after(thread, 120))


async def _delete_thread_after(thread, delay_secs):
    """Delete a trace thread after a delay. If we crash, the pending_deletes_cleanup_loop
    will pick it up from SQLite on next startup."""
    await asyncio.sleep(delay_secs)
    try:
        await thread.delete()
        # Mark complete in SQLite
        db_complete_delete(thread.id)
    except Exception as e:
        print(f"[Discord Bridge] Failed to auto-delete trace thread: {e}", flush=True)

@client.event
async def on_ready():
    global active_session_id
    active_session_id = await get_active_session_id()
    print(f"[Discord Bridge] Bot is logged in and ready as {client.user}", flush=True)
    print(f"[Discord Bridge] Active session ID is: {active_session_id}", flush=True)
    await node_liveness_step()

    if not getattr(client, "_node_liveness_started", False):
        client._node_liveness_started = True
        create_tracked_task(node_liveness_loop())
        print("[Discord Bridge] Authenticated node-liveness coupling started.", flush=True)

    # Start the node<->bridge RPC loops (idempotent — guard against double-start).
    # DB loop is PRIMARY (works mid-turn); IPC loop is the fallback.
    if not getattr(client, "_bridge_poll_started", False):
        client._bridge_poll_started = True
        create_tracked_task(bridge_commands_db_loop())
        create_tracked_task(bridge_poll_loop())
        create_tracked_task(session_side_channel_loop())
        print("[Discord Bridge] node<->bridge RPC loops started (DB primary + IPC fallback + persistent side-channel).", flush=True)
    
    # Start the pending-deletes cleanup loop (crash resilience for trace threads)
    if not getattr(client, "_cleanup_started", False):
        client._cleanup_started = True
        create_tracked_task(pending_deletes_cleanup_loop())
        print("[Discord Bridge] Pending trace thread cleanup loop started.", flush=True)

    # Sync slash commands. GLOBAL sync alone can take up to an HOUR to propagate and
    # clients cache it (why newly added commands 'never showed up'). Guild-scoped sync
    # is INSTANT — copy the global set onto the configured channel's guild and sync
    # there first, then still sync globally for any other guilds.
    try:
        guild_obj = None
        ch = client.get_channel(channel_id)
        if ch is not None and getattr(ch, "guild", None) is not None:
            guild_obj = discord.Object(id=ch.guild.id)
        if guild_obj is not None:
            tree.copy_global_to(guild=guild_obj)
            gsynced = await tree.sync(guild=guild_obj)
            print(f"[Discord Bridge] Synced {len(gsynced)} command(s) to guild {ch.guild.id} (instant).", flush=True)
        synced = await tree.sync()
        print(f"[Discord Bridge] Synced {len(synced)} global command(s) with Discord API.", flush=True)
    except Exception as e:
        print(f"[Discord Bridge] Failed to sync command tree: {e}", flush=True)


@client.event
async def on_disconnect():
    """A disconnected gateway can never advertise the combined service as online."""
    global _node_coupled_online
    _node_coupled_online = False
    update_status("OFFLINE")

# (First on_message handler removed — Python replaces event handlers, so only the
# second registration below is active. The dead handler was identical except for a
# broken IPC-based file upload path that sent JSON to a pipe-delimited endpoint.)

async def _run_query_owned(message, reply_msg, query_text, image_path,
                           session_id, busy_token):
    """Independently scheduled background task to run the AI query.
    By running on the global loop, this is immune to discord.py event cancellations."""
    trace_ctx = None
    bg_launched = False
    try:
        async with message.channel.typing():
            actual_query = query_text if query_text is not None else message.content
            resp, trace_ctx = await _start_ai_with_traces(
                message, actual_query, author=message.author,
                reply_msg=reply_msg, image_path=image_path,
                session_id=session_id, busy_token=busy_token,
            )
            print(f"[DELIVERY] IPC resp: len={len(resp) if resp else 'None'} prefix={repr(resp[:80]) if resp else 'None'}", flush=True)
            print(f"[DELIVERY] reply_msg={'id=' + str(reply_msg.id) if reply_msg else 'None'}", flush=True)
        
            # Parse the standard daemon response format
            if resp.startswith("ai:pending_approval,"):
                print("[DELIVERY] Branch: pending_approval — launching background task", flush=True)
                create_tracked_task(_handle_approval_bg(
                    message, resp, reply_msg, trace_ctx, session_id, busy_token
                ))
                bg_launched = True
                return
            elif resp.startswith("ai:clarify,"):
                print("[DELIVERY] Branch: clarify — launching background task", flush=True)
                create_tracked_task(_handle_clarify_bg(
                    message, resp, reply_msg, trace_ctx, session_id, busy_token
                ))
                bg_launched = True
                return
            elif resp.startswith("ai:cancelled,response:"):
                print("[DELIVERY] Branch: cancelled", flush=True)
                ai_resp = "🛑 " + resp[len("ai:cancelled,response:"):]
            elif resp.startswith("ai:ok"):
                ai_resp = extract_ai_ok_response(resp)
                print(f"[DELIVERY] Branch: ai:ok, extracted len={len(ai_resp)}, empty={not ai_resp.strip()}", flush=True)
            elif resp == "error:daemon_rebooted":
                print("[DELIVERY] Branch: daemon_rebooted", flush=True)
                ai_resp = "🔄 The daemon restarted while processing your request. Please try again."
            elif resp == "error:daemon_offline":
                print("[DELIVERY] Branch: daemon_offline", flush=True)
                ai_resp = "❌ Error: Cognitive AI Agent daemon is offline or unreachable."
            else:
                print(f"[DELIVERY] Branch: UNMATCHED resp={repr(resp[:200])}", flush=True)
                ai_resp = f"Error processing request: {resp}"
                
            # Ensure we don't send an empty reply
            if not ai_resp or not ai_resp.strip():
                print("[DELIVERY] WARNING: ai_resp was empty, replacing with '...'", flush=True)
                ai_resp = "..."
            if image_path and _should_store_visual_description(message, actual_query):
                update_visual_asset_description(session_id, ai_resp, path=image_path)
            elif image_path:
                print(
                    "[Visual Memory] comparison/multi-image reply not stored as a single-asset description",
                    flush=True,
                )
                
            # Post the final answer as a NEW message at completion time rather than
            # editing the early "🧠 Thinking..." placeholder. Editing the placeholder
            # made the answer appear at the placeholder's ORIGINAL timestamp — i.e.
            # behind any whispers / mid-turn sub-agent messages that arrived while the
            # agent worked, so the latest reply showed out of chronological order.
            # Posting fresh + removing the placeholder keeps the timeline correct.
            print(f"[DELIVERY] Calling send_discord_reply len={len(ai_resp)}", flush=True)
            if reply_msg:
                try:
                    await reply_msg.delete()
                except Exception as del_err:
                    print(f"[DELIVERY] placeholder delete failed (continuing): {type(del_err).__name__}: {del_err}", flush=True)
            # Files the agent produced this turn (generated image / created file) ride WITH the reply.
            _att = build_discord_files(db_collect_attachments(session_id), session_id=session_id)
            await send_discord_reply(message, ai_resp, speakable=True, edit_msg=None, files=_att)
            print(f"[DELIVERY] send_discord_reply returned OK (files={len(_att)})", flush=True)
    except Exception as e:
        print(f"[DELIVERY] EXCEPTION in response path: {type(e).__name__}: {e}", flush=True)
        try:
            fallback = ai_resp if 'ai_resp' in locals() else f"Internal error: {e}"
            await message.reply(fallback)
            print("[DELIVERY] Emergency fallback reply sent", flush=True)
        except Exception as e2:
            print(f"[DELIVERY] EMERGENCY FALLBACK ALSO FAILED: {e2}", flush=True)
    finally:
        if not bg_launched:
            _release_session_busy(session_id, busy_token)
            if trace_ctx:
                await _cleanup_traces(trace_ctx)


async def _run_query_bg(message, reply_msg, query_text=None, image_path=None,
                        session_id=None):
    """Queue ordinary messages in arrival order for their reserved session."""
    sess = session_id or "default"
    lock = _session_query_lock(sess)
    async with lock:
        busy_token = _claim_session_busy(
            sess, getattr(message.channel, "id", 0), getattr(message, "id", 0)
        )
        if not busy_token:
            # The asyncio lock is authoritative; this is only possible after an
            # interrupted owner. Reconcile the stale in-memory reservation safely.
            stale = _busy_sessions.get(sess)
            if stale:
                _busy_sessions.pop(sess, None)
                _active_turn_ids.pop(sess, None)
            busy_token = _claim_session_busy(
                sess, getattr(message.channel, "id", 0), getattr(message, "id", 0)
            )
        await _run_query_owned(
            message, reply_msg,
            query_text if query_text is not None else message.content,
            image_path, sess, busy_token,
        )


@client.event
async def on_message(message):
    global active_session_id
    # Ignore bot's own messages
    if message.author == client.user:
        return
    
    # Phase D: a message typed inside a SUB-AGENT thread is a direct WHISPER to that
    # sub-agent (monitor + steer it from its own thread). The sub-agent drains its own
    # whispers because its session_id IS the task_id, so this needs no other plumbing.
    for _tid, _thr in list(_subagent_threads.items()):
        if _thr is not None and message.channel.id == _thr.id:
            if message.content.strip():
                db_write_whisper(_tid, message.content.strip())
                try:
                    ack = await message.reply("🫧 Whisper delivered to this agent — it'll fold your guidance in on its next step.")
                    create_tracked_task(_delayed_delete(ack, 6.0))
                except Exception:
                    pass
            return

    # Public messages stay confined to the configured channel and its threads.
    # DMs use a separate fail-closed identity boundary: configured IDs, the owner of
    # that channel's guild, and members with Administrator permission may reach Echo.
    if not await discord_message_is_allowed(message):
        if _is_direct_message(message):
            actor_id = getattr(message.author, 'id', 'unknown')
            print(f"[Discord Bridge] Rejected unauthorized DM sender {actor_id}.", flush=True)
            try:
                await message.reply("❌ This Discord account is not authorized to DM Echo.")
            except Exception as exc:
                print(f"[Discord Bridge] Could not deliver DM authorization rejection: {type(exc).__name__}: {exc}", flush=True)
        return

    # Resolve lifecycle before touching attachments or retrieval state. If Echo ended
    # the previous session, this message starts a fresh one and every asset/context row
    # is attributed to that new session from the outset.
    try:
        previous_session_id = active_session_id or "default"
        active_session_id = await ensure_user_session_id()
        if active_session_id != previous_session_id:
            print(
                f"[Discord Bridge] Closed session {previous_session_id} rolled forward "
                f"to {active_session_id} for the new user message.",
                flush=True,
            )
    except Exception as exc:
        print(f"[Discord Bridge] Could not establish user session: {exc}", flush=True)
        await message.reply(f"❌ Could not start a fresh session: {exc}")
        return

    # Process attachments first. Raster images are native multimodal input for
    # gemma4:26b; documents continue through the RAG upload/indexing path.
    image_path = None
    image_paths = []
    current_visual_assets = []
    attachment_session = active_session_id or "default"
    if message.attachments:
        for attachment in message.attachments:
            ext = os.path.splitext(attachment.filename)[1].lower()
            image_extensions = ['.png', '.jpg', '.jpeg', '.webp', '.gif']
            image_content_types = ['image/png', 'image/jpeg', 'image/webp', 'image/gif']
            document_extensions = ['.pdf', '.txt', '.md', '.markdown', '.json', '.js', '.py', '.ep', '.ts', '.c', '.h']
            content_type = (getattr(attachment, 'content_type', '') or '').lower()

            if ext in image_extensions or content_type in image_content_types:
                try:
                    if getattr(attachment, 'size', 0) > _ATTACH_MAX_BYTES:
                        await message.reply(f"⚠️ Image `{attachment.filename}` is too large (>24MB).")
                        continue
                    image_bytes = await attachment.read()
                    image_dir = os.path.expanduser('~/.ernosdecent/discord-images')
                    os.makedirs(image_dir, mode=0o700, exist_ok=True)
                    safe_name = re.sub(r'[^A-Za-z0-9._-]', '_', os.path.basename(attachment.filename))
                    if not safe_name:
                        safe_name = f'image{ext or ".png"}'
                    attachment_id = getattr(attachment, 'id', len(image_paths) + 1)
                    saved_image_path = os.path.join(
                        image_dir, f'{message.id}_{attachment_id}_{safe_name}'
                    )
                    with open(saved_image_path, 'wb') as image_file:
                        image_file.write(image_bytes)
                    os.chmod(saved_image_path, 0o600)
                    visual_asset = register_visual_asset(
                        attachment_session, saved_image_path, "user_upload",
                        message_id=f"{message.id}:{attachment_id}", filename=attachment.filename,
                    )
                    image_paths.append(saved_image_path)
                    if visual_asset:
                        current_visual_assets.append(visual_asset)
                    image_path = saved_image_path
                    print(f"[Discord Bridge] Native vision attachment saved: {saved_image_path} ({len(image_bytes)} bytes)", flush=True)
                except Exception as e:
                    await message.reply(f"❌ Failed to prepare image `{attachment.filename}`: {e}")
                continue

            if ext not in document_extensions:
                supported = image_extensions + document_extensions
                await message.reply(f"⚠️ Unsupported attachment format: `{attachment.filename}`. Supported types: {', '.join(supported)}")
                continue

            async with message.channel.typing():
                try:
                    file_bytes = await attachment.read()
                    loop = asyncio.get_running_loop()
                    success, upload_msg = await loop.run_in_executor(
                        None, upload_file_to_daemon, attachment.filename, file_bytes
                    )
                    if success:
                        await message.reply(f"✅ Indexed `{attachment.filename}` into local RAG storage and saved to workspace!")
                    else:
                        await message.reply(f"❌ Failed to index `{attachment.filename}`: {upload_msg}")
                except Exception as e:
                    await message.reply(f"❌ Error processing `{attachment.filename}`: {str(e)}")

        # A single model request still carries one image payload, so compose every
        # image from this Discord message into an actual-pixel board.  This preserves
        # attachment order and lets native vision compare all uploads instead of
        # silently dropping everything after the first image.
        if len(current_visual_assets) > 1:
            current_board = _build_visual_comparison_board(
                attachment_session, current_visual_assets,
                current_asset_ids={asset["asset_id"] for asset in current_visual_assets},
            )
            if current_board:
                image_path = current_board

    # Now process text if present
    has_text = len(message.content.strip()) > 0
    has_image = image_path is not None
    if has_text or has_image:
        query_text = message.content.strip()
        if not query_text:
            if len(image_paths) > 1:
                query_text = "Please examine and compare the attached images and respond to them."
            else:
                query_text = "Please examine the attached image and respond to it."
        print(f"[Discord Bridge] Processing message from {message.author}: {query_text} image={bool(image_path)}", flush=True)

        # /learn <reason> — text fallback for the registered slash command. The
        # session is frozen before training and Echo separately consents to both
        # candidate creation and activation.
        if message.content.strip().lower().startswith("/learn"):
            if not is_admin_author(message.author):
                await message.reply("❌ Only the host can request local weight training.")
                return
            parts = message.content.strip().split(maxsplit=1)
            if len(parts) < 2 or not parts[1].strip():
                await message.reply("Usage: `/learn <what and why Echo should learn from this session>`")
                return
            await run_live_learning_durable(
                lambda text: message.reply(text), parts[1].strip(),
                author=message.author, message=message,
            )
            return
        
        if message.content.strip().lower().startswith("/factoryexecute"):
            if not is_admin_author(message.author):
                await message.reply("❌ Only the operator can execute a consented factory reset.")
                return
            parts = message.content.strip().split(maxsplit=1)
            if len(parts) < 2 or len(parts[1].strip()) != 64:
                await message.reply("Usage: `/factoryexecute <64-character change_id>` after Echo has consented.")
                return
            execute = await send_daemon_ipc(f"AI FACTORY EXECUTE {parts[1].strip()}")
            if execute and execute.startswith("factory:ok"):
                _clear_bridge_factory_runtime()
                if await _restart_node_after_factory():
                    await message.reply("🏭 Factory reset complete after recorded Echo consent, verified recovery, and a verified clean-node restart.")
                else:
                    await message.reply("⚠️ Factory state cleared, but the clean-node restart was not verified. Do not begin the clean test yet.")
            else:
                await message.reply(f"🛑 Factory reset did not execute: {execute}")
            return

        # /factory — text fallback requires CONFIRM plus a non-empty reason. The
        # daemon still performs a separate Echo-consent transition before any wipe.
        if message.content.strip().lower().startswith("/factory"):
            if not is_admin_author(message.author):
                await message.reply("❌ Only the operator can factory-reset the agent.")
                return
            parts = message.content.strip().split(maxsplit=2)
            if len(parts) < 3 or parts[1].strip() != "CONFIRM" or not parts[2].strip():
                await message.reply(FACTORY_WARNING + "\n\nType `/factory CONFIRM <reason>` or use the slash command; Echo will receive the exact reason and may refuse.")
                return
            await run_factory_reset_durable(lambda text: message.reply(text), parts[2].strip(), author=message.author, message=message)
            return

        # P9: /persona <name> | /persona list — activate or list registered personas.
        # (Text fallback; the registered slash command is the primary surface.)
        if message.content.strip().lower().startswith("/persona"):
            if not is_admin_author(message.author):
                await message.reply("❌ Only the operator can manage personas.")
                return
            parts = message.content.strip().split(maxsplit=1)
            arg = (parts[1].strip() if len(parts) > 1 else "list")
            resp = await send_daemon_ipc(f"AI PERSONA {arg}")
            if resp and resp.startswith("persona:active,"):
                name = resp.split(",", 1)[1]
                await message.reply(f"🎭 Persona **{name}** is now active — the agent speaks as it from the next message.")
            elif resp:
                # list output or a named error — show verbatim (both are user-facing text)
                await message.reply(resp[:1900])
            else:
                await message.reply("⚠️ No response from the node.")
            return

        # P8: /rename <name> — name the ACTIVE session so it can be referenced by name
        # later (read_transcripts / SESSION SET accept titles).
        if message.content.strip().lower().startswith("/rename"):
            if not is_admin_author(message.author):
                await message.reply("❌ Only the operator can rename sessions.")
                return
            parts = message.content.strip().split(maxsplit=1)
            if len(parts) < 2 or not parts[1].strip():
                await message.reply("Usage: `/rename <new session name>`")
                return
            new_name = parts[1].strip()
            payload = json.dumps({"id": active_session_id or "", "title": new_name})
            resp = await send_daemon_ipc(f"SESSION RENAME {payload}")
            if resp and "rename_ok" in resp:
                await message.reply(f"📝 Session renamed to **{new_name}** — you can reference it by that name from any session.")
            else:
                await message.reply(f"⚠️ Could not rename session: {resp}")
            return

        # P4: /autoapprove on|off — persistent per-session auto-approve toggle.
        # (Text fallback; the registered slash command is the primary surface.)
        if message.content.strip().lower().startswith("/autoapprove"):
            if not is_admin_author(message.author):
                await message.reply("❌ Only the operator can toggle auto-approve.")
                return
            parts = message.content.strip().split(maxsplit=1)
            state = (parts[1].strip().lower() if len(parts) > 1 else "on")
            if state not in ("on", "off"):
                await message.reply("Usage: `/autoapprove on` or `/autoapprove off`")
                return
            resp = await send_daemon_ipc(f"AI AUTOAPPROVE {state.upper()}")
            if resp and resp.startswith("ai:autoapprove"):
                icon = "🔓" if state == "on" else "🔒"
                await message.reply(f"{icon} Session auto-approve **{state.upper()}** — {'tools run without approval prompts this session' if state == 'on' else 'approval prompts restored'}.")
            else:
                await message.reply(f"⚠️ Could not toggle auto-approve: {resp}")
            return

        # Check if the message is the /new command
        if message.content.strip().startswith("/new"):
            parts = message.content.strip().split(maxsplit=1)
            title = parts[1] if len(parts) > 1 else "Discord Session"
            import time
            session_id = f"session_{int(time.time() * 1000)}"
            
            # Start a new session
            new_payload = {
                "id": session_id,
                "title": f"{title} {int(time.time())}",
                "model": "",
                "system_prompt": "You are ErnOS Agent — a digital cognitive system running on a local decentralized node."
            }
            new_cmd = f"SESSION NEW {json.dumps(new_payload)}"
            resp_new = await send_daemon_ipc(new_cmd)
            
            # Switch to the new session on the daemon
            set_cmd = f"SESSION SET {session_id}"
            resp_set = await send_daemon_ipc(set_cmd)
            
            if "session:set_ok" in resp_set or "session:ok" in resp_new:
                active_session_id = session_id
                await send_discord_reply(message, f"✨ Started a new AI session: **{title}** (ID: `{session_id}`). Current context has been reset.")
            else:
                await send_discord_reply(message, f"❌ Failed to start new session. Daemon response: {resp_set}")
            return

        # Start AI query via a background task to completely shield it from event cancellations.
        sess = active_session_id or "default"
        force_queue = query_text.lower() == "/queue" or query_text.lower().startswith("/queue ")
        if force_queue:
            query_text = query_text[7:].strip()
            if not query_text:
                await message.reply("Usage: `/queue <message>`")
                return
        if not has_image and not force_queue:
            whisper_turn = _active_whisper_target(sess, message.channel)
            if whisper_turn:
                whisper_status = db_write_whisper(sess, query_text, whisper_turn)
                if whisper_status == "ok":
                    await message.reply("🫧 Added to Echo’s current turn as live guidance.")
                else:
                    await message.reply("⚠️ The live guidance could not be stored; it was not silently queued or resent.")
                return
        reply_msg = None
        try:
            queued = _session_query_lock(sess).locked()
            status_text = "⏳ Queued — I’ll answer this after the current turn." if queued else "🧠 Thinking..."
            reply_msg = await message.reply(status_text, view=StopView(author=message.author, session_id=sess))
        except Exception as e:
            print(f"[Discord Bridge] Failed to send initial thinking reply: {e}", flush=True)

        create_tracked_task(_run_query_bg(
            message, reply_msg, query_text=query_text, image_path=image_path,
            session_id=sess,
        ))
        return


if __name__ == "__main__":
    try:
        print("[Discord Bridge] Logging in to Discord...", flush=True)
        client.run(token)
    except Exception as e:
        print(f"[Discord Bridge] Login/run failed: {e}", flush=True)
        update_status("OFFLINE")
        sys.exit(1)
    finally:
        update_status("OFFLINE")
