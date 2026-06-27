#!/usr/bin/env python3
import os
import sys
import json
import socket
import discord
import asyncio
import signal

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

ADMIN_IDS = _parse_ids(discord_cfg.get('admin_id', '1299810741984956449'))
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

# Approval timeout in seconds
# No timeout — user said "WAIT" (indefinite)
APPROVAL_TIMEOUT = None

active_session_id = "default"

async def get_active_session_id():
    resp = await send_daemon_ipc("SESSION ACTIVE")
    if resp.startswith("session:active_id,id:"):
        return resp[len("session:active_id,id:"):]
    return "default"

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
    """Send a raw IPC command to the daemon and return the response."""
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
        return b''.join(chunks).decode('utf-8', errors='ignore').strip()
    except Exception as e:
        print(f"[Discord Bridge] IPC send failed: {e}", flush=True)
        return "error:daemon_offline"

async def search_rag_database(query_text):
    """RAG search via the ErnosPlain daemon, scoped to the ACTIVE SESSION.
    Replaces the old Python rag_manager.py subprocess. The daemon's session-scoped
    search means a session only auto-retrieves documents ingested in that session;
    older/other-session documents are reached only via the agent's explicit tools."""
    try:
        global active_session_id
        sess = active_session_id or ""
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

async def query_daemon_ipc(prompt, author=None):
    try:
        # Prepare query (avoid newlines inside query to keep it clean)
        clean_prompt = prompt.replace('\r', ' ').replace('\n', ' ')
        
        # Build IPC command with sender identity and role tags
        global active_session_id
        tags = ""
        if active_session_id:
            tags = f"[SESSION:{active_session_id}] "
        if author is not None:
            username = str(author.display_name).replace('[', '(').replace(']', ')')
            role = "admin" if is_admin_author(author) else "guest"
            tags += f"[SENDER:{username}] [ROLE:{role}] "
            
        # Search the RAG database using the query
        rag_res = await search_rag_database(clean_prompt)
        if rag_res and (rag_res.get("results") or rag_res.get("structural_chunks")):
            # Format and sanitize brackets to prevent option parsing issues
            context_str = format_rag_context(rag_res).replace('[', '(').replace(']', ')')
            tags += f"[IN_MEMORY_CONTEXT:{context_str}] "
        
        cmd = f"AI INFER {tags}{clean_prompt}"
        return await send_daemon_ipc(cmd)
    except Exception as e:
        print(f"[Discord Bridge] IPC query failed: {e}", flush=True)
        return "error:daemon_offline"

import re

async def send_discord_reply(message, text, speakable=False):
    """Send a reply, splitting into chunks if it exceeds Discord's 2000-char limit.
    When speakable=True, a 🔊 button is attached to the final chunk that plays the
    full message audio (the whole text, not just that chunk)."""
    try:
        if not text or not text.strip():
            text = "..."
        # Guard against invisible/control characters that produce blank Discord messages
        cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        if not cleaned.strip():
            text = "(Response contained only invisible characters — this is a bug. Please retry.)"
        view = SpeakView(text) if speakable else None
        if len(text) > 2000:
            chunks = [text[i:i+2000] for i in range(0, len(text), 2000)]
            for idx, chunk in enumerate(chunks):
                is_last = (idx == len(chunks) - 1)
                await message.reply(chunk, view=(view if is_last else None))
        else:
            await message.reply(text, view=view)
    except Exception as e:
        print(f"[Discord Bridge] Failed to send reply message: {e}", flush=True)

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

class StopView(discord.ui.View):
    """A Stop button that allows the original user (or admins) to cancel a running
    AI inference process mid-task by sending an 'AI CANCEL' IPC command."""
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
        
        # Send cancel command to daemon
        sess = self.session_id or "default"
        resp = await send_daemon_ipc(f"AI CANCEL [SESSION:{sess}]")
        print(f"[Discord Bridge] Stop button clicked for session {sess}, daemon ack: {resp}", flush=True)

class SpeakView(discord.ui.View):
    """A 🔊 button attached to AI replies. On click, asks the node to synthesise
    the message audio (Kokoro, voice bm_fable @1.15x via the `TTS SPEAK` IPC verb)
    and uploads the resulting WAV as a Discord attachment. Anyone in the channel
    may play it — reading a message aloud is a read-only action."""
    def __init__(self, text, timeout=None):
        super().__init__(timeout=timeout)
        self.text = text

    @discord.ui.button(label="Speak", emoji="🔊", style=discord.ButtonStyle.secondary)
    async def speak(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        # Collapse newlines so the text rides cleanly in the single-line IPC command.
        speak_text = (self.text or "").replace("\r", " ").replace("\n", " ").strip()
        if not speak_text:
            await interaction.followup.send("Nothing to speak.", ephemeral=True)
            return
        resp = await send_daemon_ipc("TTS SPEAK " + speak_text)
        path = None
        for part in resp.split(","):
            if part.startswith("path:"):
                path = part[len("path:"):].strip()
        if not path or not os.path.exists(path):
            await interaction.followup.send(f"🔇 TTS failed: {resp}", ephemeral=True)
            return
        try:
            await interaction.followup.send(file=discord.File(path, filename="ernos_voice.wav"))
        except Exception as e:
            await interaction.followup.send(f"🔇 Failed to upload audio: {e}", ephemeral=True)

async def handle_tool_approval(message, resp):
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
        return
        
    if view.value is True:
        await approval_msg.edit(content=f"✅ **Approved** `{tool_name}` — executing...", view=view)
        ipc_resp = await send_daemon_ipc("AI APPROVE")
    elif view.value == "all":
        await approval_msg.edit(content=f"⚡ **Approved All** `{tool_name}` — executing subsequent actions automatically...", view=view)
        ipc_resp = await send_daemon_ipc("AI APPROVE_ALL")
    else:
        await approval_msg.edit(content=f"❌ **Denied** `{tool_name}` — cancelled.", view=view)
        ipc_resp = await send_daemon_ipc("AI DENY")
        
    # Process the result from the daemon after approval/denial
    if ipc_resp.startswith("ai:pending_approval,"):
        # Chained approval — another gated tool in the same ReAct loop
        await handle_tool_approval(message, ipc_resp)
    elif ipc_resp.startswith("ai:ok"):
        ai_resp = extract_ai_ok_response(ipc_resp)
        await send_discord_reply(message, ai_resp, speakable=True)
    elif ipc_resp == "error:daemon_offline":
        await send_discord_reply(message, "❌ Daemon went offline during approval.")
    else:
        await send_discord_reply(message, f"Agent response: {ipc_resp}")

# --- F3: clarification over Discord ---
def parse_clarify_questions(resp):
    """Parse 'ai:clarify,questions:<json array of "text||opt1||opt2">' -> [(text, [opts])]."""
    idx = resp.find("questions:")
    raw = resp[idx + len("questions:"):] if idx >= 0 else "[]"
    try:
        arr = json.loads(raw)
    except Exception:
        arr = []
    out = []
    for item in arr:
        bits = str(item).split("||")
        qtext = bits[0] if bits else ""
        opts = [b for b in bits[1:] if b]
        out.append((qtext, opts))
    return out

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
                if count >= 20:  # leave room for the escape button (Discord max 25)
                    break
                answer = f"Q{qi+1}: {opt}" if multi else opt
                btn = discord.ui.Button(label=answer[:80], style=discord.ButtonStyle.secondary)
                btn.callback = self._make_cb(answer)
                self.add_item(btn)
                count += 1
        esc = discord.ui.Button(label="Work with what we have", style=discord.ButtonStyle.primary)
        esc.callback = self._make_cb("__USE_CURRENT__")
        self.add_item(esc)

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

async def handle_clarification(message, resp):
    """Show the agent's clarifying questions with clickable options and resume the run."""
    questions = parse_clarify_questions(resp)
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
        ipc_resp = await send_daemon_ipc("AI CLARIFY __USE_CURRENT__")
    else:
        answer = view.value
        await clar_msg.edit(content=f"✅ Got it: `{answer}`", view=view)
        ipc_resp = await send_daemon_ipc(f"AI CLARIFY {answer}")

    if ipc_resp.startswith("ai:clarify,"):
        await handle_clarification(message, ipc_resp)
    elif ipc_resp.startswith("ai:pending_approval,"):
        await handle_tool_approval(message, ipc_resp)
    elif ipc_resp.startswith("ai:cancelled,response:"):
        await send_discord_reply(message, "🛑 " + ipc_resp[len("ai:cancelled,response:"):])
    elif ipc_resp.startswith("ai:ok"):
        await send_discord_reply(message, extract_ai_ok_response(ipc_resp), speakable=True)
    elif ipc_resp == "error:daemon_offline":
        await send_discord_reply(message, "❌ Daemon went offline during clarification.")
    else:
        await send_discord_reply(message, f"Agent response: {ipc_resp}")

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
            async for m in ch.history(limit=20):
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

async def bridge_poll_loop():
    """Poll the daemon for queued agent->bridge commands, execute them, and return
    results — making the otherwise one-way bridge bidirectional (node<->bridge RPC).
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

async def trace_poll_loop(thread, session_id, done_event):
    """Poll the daemon for trace events and stream them into a Discord thread.
    Runs until done_event is set (inference complete)."""
    TYPE_EMOJI = {
        "thinking": "🧠", "raw_output": "📝", "reasoning": "💭",
        "lookback": "🔍", "action": "⚙️", "approval": "🔒",
        "audit": "🛡️", "tool_exec": "🔧", "tool_result": "📋",
        "reply_audit": "✅", "no_action": "⚠️", "done": "🏁",
    }
    await client.wait_until_ready()
    while not done_event.is_set():
        try:
            resp = await send_daemon_ipc(f"TRACE POLL {session_id}")
            if resp and resp.startswith("["):
                events = json.loads(resp)
                for ev in events:
                    etype = ev.get("type", "info")
                    content = ev.get("content", "")
                    emoji = TYPE_EMOJI.get(etype, "ℹ️")
                    # Truncate to Discord's 2000-char limit
                    msg = f"{emoji} **{etype}**\n```\n{content[:1800]}\n```"
                    if len(msg) > 2000:
                        msg = msg[:1997] + "..."
                    try:
                        await thread.send(msg)
                    except Exception as e:
                        print(f"[Discord Bridge] trace thread send error: {e}", flush=True)
        except Exception as e:
            print(f"[Discord Bridge] trace poll error: {e}", flush=True)
        await asyncio.sleep(0.5)  # Poll every 500ms for near-real-time

async def pending_deletes_cleanup_loop():
    """On startup, check for any threads whose 2-minute delete timer expired while
    the bridge was offline (crash resilience). Then continue checking periodically."""
    await client.wait_until_ready()
    while not client.is_closed():
        try:
            resp = await send_daemon_ipc("TRACE PENDING_DELETES")
            if resp and resp.startswith("["):
                pending = json.loads(resp)
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
                        await send_daemon_ipc(f"TRACE COMPLETE_DELETE {pid}")
        except Exception as e:
            print(f"[Discord Bridge] pending deletes cleanup error: {e}", flush=True)
        await asyncio.sleep(15.0)  # Check every 15 seconds

async def _run_ai_with_traces(message, query_text, author):
    """Run an AI query with a trace thread for full transparency.
    Creates a thread, polls traces in parallel, then schedules cleanup."""
    global active_session_id
    sess = active_session_id or "default"

    # Create a trace thread attached to the user's message
    initial_msg = None
    try:
        thread = await message.create_thread(
            name=f"🔍 ErnOS Trace — {query_text[:50]}",
            auto_archive_duration=60  # 1 hour archive (minimum Discord allows)
        )
        initial_msg = await thread.send(
            "🔍 **ErnOS Reasoning Trace** — live stream of thinking, tool calls, and audit results.\n*This thread auto-deletes 2 minutes after the response.*",
            view=StopView(author=message.author, session_id=sess)
        )
    except Exception as e:
        print(f"[Discord Bridge] Failed to create trace thread: {e}", flush=True)
        thread = None

    # Start trace poller in background
    done_event = asyncio.Event()
    trace_task = None
    if thread:
        trace_task = asyncio.create_task(trace_poll_loop(thread, sess, done_event))

    # Run the actual AI query (blocking IPC call)
    resp = await query_daemon_ipc(query_text, author=author)

    # Signal trace poller to stop, give it one last poll cycle
    done_event.set()
    if trace_task:
        try:
            await asyncio.wait_for(trace_task, timeout=2.0)
        except asyncio.TimeoutError:
            trace_task.cancel()

    # Disable the stop button
    if thread and initial_msg:
        try:
            disabled_view = StopView(author=message.author, session_id=sess)
            for item in disabled_view.children:
                item.disabled = True
            await initial_msg.edit(view=disabled_view)
        except Exception as e:
            print(f"[Discord Bridge] Failed to disable stop button: {e}", flush=True)

    # Send final trace marker
    if thread:
        try:
            await thread.send("🏁 **Trace complete** — this thread will auto-delete in 2 minutes.")
        except Exception:
            pass
        # Schedule crash-resilient deletion via SQLite
        await send_daemon_ipc(f"TRACE SCHEDULE_DELETE {thread.id} 120")
        # Also schedule local deletion
        asyncio.create_task(_delete_thread_after(thread, 120))

    return resp

async def _delete_thread_after(thread, delay_secs):
    """Delete a trace thread after a delay. If we crash, the pending_deletes_cleanup_loop
    will pick it up from SQLite on next startup."""
    await asyncio.sleep(delay_secs)
    try:
        await thread.delete()
        # Mark complete in SQLite
        await send_daemon_ipc(f"TRACE COMPLETE_DELETE {thread.id}")
    except Exception as e:
        print(f"[Discord Bridge] Failed to auto-delete trace thread: {e}", flush=True)

@client.event
async def on_ready():
    global active_session_id
    active_session_id = await get_active_session_id()
    print(f"[Discord Bridge] Bot is logged in and ready as {client.user}", flush=True)
    print(f"[Discord Bridge] Active session ID is: {active_session_id}", flush=True)
    update_status("ONLINE")

    # Start the node<->bridge RPC poll loop (idempotent — guard against double-start).
    if not getattr(client, "_bridge_poll_started", False):
        client._bridge_poll_started = True
        asyncio.create_task(bridge_poll_loop())
        print("[Discord Bridge] node<->bridge RPC poll loop started.", flush=True)
    
    # Start the pending-deletes cleanup loop (crash resilience for trace threads)
    if not getattr(client, "_cleanup_started", False):
        client._cleanup_started = True
        asyncio.create_task(pending_deletes_cleanup_loop())
        print("[Discord Bridge] Pending trace thread cleanup loop started.", flush=True)

    # Sync slash commands globally
    try:
        synced = await tree.sync()
        print(f"[Discord Bridge] Synced {len(synced)} command(s) with Discord API.", flush=True)
    except Exception as e:
        print(f"[Discord Bridge] Failed to sync command tree: {e}", flush=True)

@client.event
async def on_message(message):
    # Ignore bot's own messages
    if message.author == client.user:
        return
    
    # Listen only to the configured channel or threads within it
    is_target_channel = message.channel.id == channel_id
    is_thread_in_target_channel = getattr(message.channel, 'parent_id', None) == channel_id
    if not is_target_channel and not is_thread_in_target_channel:
        return
    
    has_text = message.content and message.content.strip()
    has_attachments = len(message.attachments) > 0
    if not has_text and not has_attachments:
        return
        
    # Process all attachments first
    if has_attachments:
        for attachment in message.attachments:
            ext = os.path.splitext(attachment.filename)[1].lower()
            supported_extensions = ['.pdf', '.txt', '.md', '.markdown']
            if ext not in supported_extensions:
                await message.reply(f"⚠️ Unsupported attachment format: `{attachment.filename}`. Supported types: `pdf, txt, md, markdown`.")
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

    # Now process text if present
    if has_text:
        print(f"[Discord Bridge] Processing message from {message.author}: {message.content}", flush=True)
        
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
                global active_session_id
                active_session_id = session_id
                await send_discord_reply(message, f"✨ Started a new AI session: **{title}** (ID: `{session_id}`). Current context has been reset.")
            else:
                await send_discord_reply(message, f"❌ Failed to start new session. Daemon response: {resp_set}")
            return

        # Run AI query with trace thread for transparency
        async with message.channel.typing():
            resp = await _run_ai_with_traces(message, message.content, author=message.author)
            
            # Parse the standard daemon response format
            if resp.startswith("ai:pending_approval,"):
                # Tool requires user approval before execution
                await handle_tool_approval(message, resp)
                return
            elif resp.startswith("ai:clarify,"):
                # F3: agent is asking the user clarifying questions
                await handle_clarification(message, resp)
                return
            elif resp.startswith("ai:cancelled,response:"):
                ai_resp = "🛑 " + resp[len("ai:cancelled,response:"):]
            elif resp.startswith("ai:ok"):
                ai_resp = extract_ai_ok_response(resp)
            elif resp == "error:daemon_offline":
                ai_resp = "❌ Error: Cognitive AI Agent daemon is offline or unreachable."
            else:
                ai_resp = f"Error processing request: {resp}"
                
            # Ensure we don't send an empty reply
            if not ai_resp or not ai_resp.strip():
                ai_resp = "..."
                
            # Send reply on Discord
            await send_discord_reply(message, ai_resp, speakable=True)

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

