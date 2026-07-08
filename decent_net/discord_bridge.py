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

# Whisper mid-message system: tracks whether the AI is currently processing.
# When True, incoming messages are treated as mid-turn whispers instead of new queries.
_ai_busy = False
_ai_busy_channel_id = None  # channel where the active query originated

def db_write_whisper(session_id, content):
    """Write a mid-turn whisper to SQLite for the react loop to pick up."""
    try:
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        now = int(time.time())
        cursor.execute(
            "INSERT INTO trace_whispers (session_id, content, created_at) VALUES (?, ?, ?)",
            (session_id, content, now)
        )
        conn.commit()
        conn.close()
        return "ok"
    except Exception as e:
        print(f"[Discord Bridge] Failed to write whisper: {e}", flush=True)
        return f"error:{e}"

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

async def _delayed_delete(msg, delay_seconds):
    """Delete a Discord message after a delay. Fire-and-forget via asyncio.create_task."""
    try:
        await asyncio.sleep(delay_seconds)
        await msg.delete()
    except Exception:
        pass

async def send_discord_reply(message, text, speakable=False, edit_msg=None):
    """Send a reply, splitting into chunks if it exceeds Discord's 2000-char limit.
    When speakable=True, a 🔊 button is attached to the final chunk that plays the
    full message audio (the whole text, not just that chunk).
    If edit_msg is provided, it edits that message first instead of creating a new one."""
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
            if edit_msg:
                try:
                    await edit_msg.edit(content=chunks[0], view=None)
                except Exception:
                    await message.reply(chunks[0])
                for idx in range(1, len(chunks)):
                    is_last = (idx == len(chunks) - 1)
                    await message.reply(chunks[idx], view=(view if is_last else None))
            else:
                for idx, chunk in enumerate(chunks):
                    is_last = (idx == len(chunks) - 1)
                    await message.reply(chunk, view=(view if is_last else None))
        else:
            if edit_msg:
                try:
                    await edit_msg.edit(content=text, view=view)
                    print(f"[DELIVERY] edit_msg.edit() succeeded, msg_id={edit_msg.id}", flush=True)
                except Exception as edit_err:
                    print(f"[DELIVERY] edit_msg.edit() FAILED: {type(edit_err).__name__}: {edit_err} — falling back to reply", flush=True)
                    await message.reply(text, view=view)
            else:
                await message.reply(text, view=view)
    except Exception as e:
        print(f"[DELIVERY] send_discord_reply OUTER EXCEPTION: {type(e).__name__}: {e}", flush=True)


async def post_mid_message(channel, content):
    """Post a mid-turn / sub-agent message to a channel, CHUNKED across multiple
    Discord messages (2000-char limit) instead of truncating. Sub-agent results can
    be long summaries — they must arrive in full, like the main agent's reply."""
    body = f"💬 {content}"
    # Split on 1990 to leave headroom under Discord's 2000 hard limit.
    for i in range(0, max(len(body), 1), 1990):
        try:
            await channel.send(body[i:i + 1990])
        except Exception as e:
            print(f"[Discord Bridge] mid_message chunk send error: {e}", flush=True)


# Defence-in-depth: even though the node refuses secret paths before queueing an
# attachment, the bridge independently refuses these markers so a file can never
# be exfiltrated to Discord by a malformed/forged trace row.
_ATTACH_DENY_MARKERS = (
    "/.ssh/", "/.gnupg/", "id_rsa", "id_ed25519", ".env", "ipc-token",
    "/.ernosdecent/", "private_key", ".pem", ".key",
)
_ATTACH_MAX_BYTES = 24 * 1024 * 1024  # 24 MB — under Discord's non-nitro upload cap

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


async def post_attachment(channel, path):
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

def get_db_path():
    return os.path.expanduser("~/.ernosdecent/node.db")

def db_request_cancel(session_id):
    try:
        conn = sqlite3.connect(get_db_path())
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
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, event_type, content, created_at FROM trace_events WHERE sent=0 AND session_id=? ORDER BY id LIMIT 50",
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

def db_get_pending_deletes():
    pending = []
    try:
        conn = sqlite3.connect(get_db_path())
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
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        cursor.execute("DELETE FROM trace_pending_deletes WHERE id=?", (pid,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[Discord Bridge] Failed to complete delete: {e}", flush=True)

def db_schedule_delete(thread_id, delay_secs):
    try:
        conn = sqlite3.connect(get_db_path())
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

async def _handle_approval_bg(message, resp, reply_msg, trace_ctx):
    """Background task wrapper for handle_tool_approval.
    Runs independently of on_message so discord.py can't cancel it."""
    global _ai_busy, _ai_busy_channel_id
    try:
        await handle_tool_approval(message, resp, edit_msg=reply_msg)
    except Exception as e:
        print(f"[DELIVERY] _handle_approval_bg EXCEPTION: {type(e).__name__}: {e}", flush=True)
        try:
            await message.reply(f"⚠️ Error during approval flow: {e}")
        except Exception:
            pass
    finally:
        _ai_busy = False
        _ai_busy_channel_id = None
        if trace_ctx:
            await _cleanup_traces(trace_ctx)

async def _handle_clarify_bg(message, resp, reply_msg, trace_ctx):
    """Background task wrapper for handle_clarification.
    Runs independently of on_message so discord.py can't cancel it."""
    global _ai_busy, _ai_busy_channel_id
    try:
        await handle_clarification(message, resp, edit_msg=reply_msg)
    except Exception as e:
        print(f"[DELIVERY] _handle_clarify_bg EXCEPTION: {type(e).__name__}: {e}", flush=True)
        try:
            await message.reply(f"⚠️ Error during clarification flow: {e}")
        except Exception:
            pass
    finally:
        _ai_busy = False
        _ai_busy_channel_id = None
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
        ipc_resp = await send_daemon_ipc("AI APPROVE")
    elif view.value == "all":
        await approval_msg.edit(content=f"⚡ **Approved All** `{tool_name}` — executing subsequent actions automatically...", view=view)
        ipc_resp = await send_daemon_ipc("AI APPROVE_ALL")
    else:
        await approval_msg.edit(content=f"❌ **Denied** `{tool_name}` — cancelled.", view=view)
        ipc_resp = await send_daemon_ipc("AI DENY")
        
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
        await send_discord_reply(message, ai_resp, speakable=True, edit_msg=edit_msg)
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
        ipc_resp = await send_daemon_ipc("AI CLARIFY __USE_CURRENT__")
    else:
        answer = view.value
        if answer == "__USE_CURRENT__":
            await clar_msg.edit(content="✅ Proceeding with current understanding.", view=view)
        else:
            await clar_msg.edit(content=f"✅ Got it: `{answer}`", view=view)
        ipc_resp = await send_daemon_ipc(f"AI CLARIFY {answer}")

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

async def _start_ai_with_traces(message, query_text, author, reply_msg=None):
    """Start an AI query with a trace thread. Returns (resp, trace_ctx) where trace_ctx
    contains the lifecycle objects needed to keep polling alive across approval/clarification
    flows. The caller MUST call _cleanup_traces(trace_ctx) when the full response cycle ends."""
    global active_session_id
    sess = active_session_id or "default"

    trace_ctx = {
        "thread": None,
        "initial_msg": None,
        "done_event": asyncio.Event(),
        "trace_task": None,
        "reply_msg": reply_msg,
    }

    # Create a trace thread attached to the user's message
    try:
        thread = await message.create_thread(
            name=f"🔍 ErnOS Trace — {query_text[:50]}",
            auto_archive_duration=60
        )
        trace_ctx["thread"] = thread
        trace_ctx["initial_msg"] = await thread.send(
            "🔍 **ErnOS Reasoning Trace** — live stream of thinking, tool calls, and audit results.\n*This thread auto-deletes 2 minutes after the response.*",
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

    # Run the actual AI query (blocking IPC call)
    resp = await query_daemon_ipc(query_text, author=author)

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
    update_status("ONLINE")

    # Start the node<->bridge RPC poll loop (idempotent — guard against double-start).
    if not getattr(client, "_bridge_poll_started", False):
        client._bridge_poll_started = True
        create_tracked_task(bridge_poll_loop())
        print("[Discord Bridge] node<->bridge RPC poll loop started.", flush=True)
    
    # Start the pending-deletes cleanup loop (crash resilience for trace threads)
    if not getattr(client, "_cleanup_started", False):
        client._cleanup_started = True
        create_tracked_task(pending_deletes_cleanup_loop())
        print("[Discord Bridge] Pending trace thread cleanup loop started.", flush=True)

    # Sync slash commands globally
    try:
        synced = await tree.sync()
        print(f"[Discord Bridge] Synced {len(synced)} command(s) with Discord API.", flush=True)
    except Exception as e:
        print(f"[Discord Bridge] Failed to sync command tree: {e}", flush=True)

# (First on_message handler removed — Python replaces event handlers, so only the
# second registration below is active. The dead handler was identical except for a
# broken IPC-based file upload path that sent JSON to a pipe-delimited endpoint.)

async def _run_query_bg(message, reply_msg):
    """Independently scheduled background task to run the AI query.
    By running on the global loop, this is immune to discord.py event cancellations."""
    global _ai_busy, _ai_busy_channel_id
    trace_ctx = None
    bg_launched = False
    try:
        async with message.channel.typing():
            resp, trace_ctx = await _start_ai_with_traces(message, message.content, author=message.author, reply_msg=reply_msg)
            print(f"[DELIVERY] IPC resp: len={len(resp) if resp else 'None'} prefix={repr(resp[:80]) if resp else 'None'}", flush=True)
            print(f"[DELIVERY] reply_msg={'id=' + str(reply_msg.id) if reply_msg else 'None'}", flush=True)
        
            # Parse the standard daemon response format
            if resp.startswith("ai:pending_approval,"):
                print("[DELIVERY] Branch: pending_approval — launching background task", flush=True)
                create_tracked_task(_handle_approval_bg(message, resp, reply_msg, trace_ctx))
                bg_launched = True
                return
            elif resp.startswith("ai:clarify,"):
                print("[DELIVERY] Branch: clarify — launching background task", flush=True)
                create_tracked_task(_handle_clarify_bg(message, resp, reply_msg, trace_ctx))
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
            await send_discord_reply(message, ai_resp, speakable=True, edit_msg=None)
            print("[DELIVERY] send_discord_reply returned OK", flush=True)
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
            _ai_busy = False
            _ai_busy_channel_id = None
            if trace_ctx:
                await _cleanup_traces(trace_ctx)


@client.event
async def on_message(message):
    global _ai_busy, _ai_busy_channel_id, active_session_id
    # Ignore bot's own messages
    if message.author == client.user:
        return
    
    # Listen only to the configured channel or threads within it
    is_target_channel = message.channel.id == channel_id
    is_thread_in_target_channel = getattr(message.channel, 'parent_id', None) == channel_id
    if not is_target_channel and not is_thread_in_target_channel:
        return

    # Process attachments first (uploads/RAG indexing via HTTP /api/upload)
    if message.attachments:
        for attachment in message.attachments:
            ext = os.path.splitext(attachment.filename)[1].lower()
            supported_extensions = ['.pdf', '.txt', '.md', '.markdown', '.json', '.js', '.py', '.ep', '.ts', '.c', '.h']
            if ext not in supported_extensions:
                await message.reply(f"⚠️ Unsupported attachment format: `{attachment.filename}`. Supported types: {', '.join(supported_extensions)}")
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
    has_text = len(message.content.strip()) > 0
    if has_text:
        print(f"[Discord Bridge] Processing message from {message.author}: {message.content}", flush=True)
        
        # Whisper detection: if AI is busy processing, treat incoming messages as
        # mid-turn guidance instead of queuing a new AI query. The whisper is written
        # to SQLite and picked up by the react loop before its next LLM call.
        if _ai_busy and message.channel.id == _ai_busy_channel_id:
            sess = active_session_id or "default"
            result = db_write_whisper(sess, message.content)
            if result == "ok":
                try:
                    whisper_ack = await message.reply("🫧 **Whisper received** — your guidance will reach the agent on its next reasoning step.")
                    # Auto-delete the acknowledgement after 5 seconds to keep the chat clean
                    create_tracked_task(_delayed_delete(whisper_ack, 5.0))
                except Exception:
                    pass
            else:
                try:
                    await message.reply(f"⚠️ Could not queue whisper: {result}")
                except Exception:
                    pass
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
        reply_msg = None
        try:
            reply_msg = await message.reply("🧠 Thinking...", view=StopView(author=message.author, session_id=sess))
        except Exception as e:
            print(f"[Discord Bridge] Failed to send initial thinking reply: {e}", flush=True)

        # Set busy flag — stays True across the entire background run
        _ai_busy = True
        _ai_busy_channel_id = message.channel.id
        create_tracked_task(_run_query_bg(message, reply_msg))
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

