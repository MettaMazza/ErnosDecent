#!/usr/bin/env python3
"""Run the literal production /learn workflow with real Discord delivery and restart.

This operator-invoked acceptance test intentionally changes the production adapter
lineage. It creates a dedicated harmless session, invokes the registered Discord
command callback as the configured host, lets Echo make both rights decisions, and
requires the canonical supervisor to replace and verify the running node.
"""

from __future__ import annotations

import asyncio
import hashlib
import importlib.util
import json
import os
import sqlite3
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
BRIDGE_SPEC = importlib.util.spec_from_file_location(
    "discord_bridge_production_e2e", ROOT / "decent_net" / "discord_bridge.py"
)
assert BRIDGE_SPEC and BRIDGE_SPEC.loader
bridge = importlib.util.module_from_spec(BRIDGE_SPEC)
BRIDGE_SPEC.loader.exec_module(bridge)


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{time.time_ns()}.tmp")
    with temporary.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def response_text(response: str) -> str:
    marker = "|||RESPONSE|||"
    return response.split(marker, 1)[1].strip() if marker in response else response.strip()


def listener_pid(port: int) -> int:
    result = subprocess.run(
        ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    values = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if result.returncode != 0 or len(values) != 1 or not values[0].isdigit():
        raise RuntimeError(f"expected exactly one listener on TCP {port}, got {values!r}")
    return int(values[0])


async def record_discord_liveness(evidence: dict, stop: asyncio.Event) -> None:
    """Capture every persisted Discord/node-coupled status transition."""
    previous = None
    platform_path = ROOT / "config" / "platforms.json"
    while not stop.is_set():
        try:
            value = json.loads(platform_path.read_text(encoding="utf-8"))["discord"]["status"]
        except (OSError, KeyError, TypeError, json.JSONDecodeError):
            value = "UNREADABLE"
        if value != previous:
            evidence["discord_liveness"].append({"status": value, "at_ns": time.time_ns()})
            previous = value
        await asyncio.sleep(0.1)


class DiscordDelivery:
    def __init__(self, token: str, channel_id: int, evidence: dict):
        self.token = token
        self.channel_id = channel_id
        self.evidence = evidence

    def _post(self, content: str) -> dict:
        if not content or len(content) > 2000:
            raise RuntimeError(f"Discord delivery content length is invalid: {len(content)}")
        request = urllib.request.Request(
            f"https://discord.com/api/v10/channels/{self.channel_id}/messages",
            data=json.dumps({"content": content}, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bot {self.token}",
                "Content-Type": "application/json",
                "User-Agent": "ErnosDecent-production-e2e/1",
            },
            method="POST",
        )
        while True:
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    value = json.loads(response.read())
                if not isinstance(value, dict) or not value.get("id"):
                    raise RuntimeError("Discord returned no durable message id")
                return value
            except urllib.error.HTTPError as exc:
                body = exc.read()
                if exc.code != 429:
                    raise RuntimeError(f"Discord delivery failed with HTTP {exc.code}: {body[:500]!r}") from exc
                retry = json.loads(body).get("retry_after")
                if not isinstance(retry, (int, float)) or retry < 0:
                    raise RuntimeError("Discord rate-limit response had no valid retry_after") from exc
                time.sleep(float(retry))

    async def send(self, content=None, **_kwargs):
        text = str(content or "")
        value = await asyncio.to_thread(self._post, text)
        record = {
            "message_id": str(value["id"]),
            "content_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "content": text,
            "sent_at": int(time.time()),
        }
        self.evidence["discord_messages"].append(record)
        print(f"DISCORD_DELIVERED id={record['message_id']} text={text[:160]!r}", flush=True)
        return SimpleNamespace(id=int(value["id"]))


class FakeResponse:
    def __init__(self):
        self.deferred = False

    async def defer(self, **_kwargs):
        self.deferred = True

    async def send_message(self, content, **_kwargs):
        raise RuntimeError(f"slash-command guard rejected production E2E: {content}")


async def require_ipc(command: str, prefix: str) -> str:
    response = await bridge.send_daemon_ipc(command)
    if not response.startswith(prefix):
        raise RuntimeError(f"{command.split(' ', 1)[0]} returned {response!r}, expected {prefix!r}")
    return response


async def main_async() -> int:
    live_config = json.loads((ROOT / "config" / "live_learning.json").read_text(encoding="utf-8"))
    if live_config.get("enabled") is not True:
        raise RuntimeError("production live learning is disabled")
    platform = json.loads((ROOT / "config" / "platforms.json").read_text(encoding="utf-8"))
    discord_config = platform.get("discord", {})
    token = str(discord_config.get("token", ""))
    channel_id = int(str(discord_config.get("channel", "0")))
    host_ids = sorted(bridge.HOST_IDS)
    if not token or not channel_id or not host_ids:
        raise RuntimeError("Discord host configuration is incomplete")
    before = await bridge._learning_controller("status")
    if (ROOT / "config" / "learning" / "live" / "pending_activation.json").exists():
        raise RuntimeError("a production activation is already pending")
    original_session = await bridge.get_active_session_id()
    stamp = int(time.time() * 1000)
    session_id = f"session_live_learning_e2e_{stamp}"
    marker = f"ERNOS_LIVE_LEARNING_PRODUCTION_E2E_{stamp}"
    evidence_path = Path.home() / ".ernosdecent" / "live-learning" / "production-validation" / f"{stamp}.json"
    evidence = {
        "schema": "ernosdecent-live-learning-production-e2e-v1",
        "started_at": int(time.time()),
        "original_session": original_session,
        "validation_session": session_id,
        "marker": marker,
        "before": before,
        "discord_messages": [],
        "discord_liveness": [],
        "result": "RUNNING",
    }
    atomic_json(evidence_path, evidence)
    delivery = DiscordDelivery(token, channel_id, evidence)
    author = SimpleNamespace(
        id=host_ids[0], name="production-e2e-host", global_name="Maria",
        display_name="Maria", bot=False, roles=[],
    )
    channel = SimpleNamespace(id=channel_id, parent_id=None, name="production-e2e", guild=None)
    interaction = SimpleNamespace(
        user=author,
        channel=channel,
        response=FakeResponse(),
        followup=SimpleNamespace(send=delivery.send),
    )
    liveness_stop = asyncio.Event()
    liveness_task = asyncio.create_task(record_discord_liveness(evidence, liveness_stop))
    try:
        payload = {
            "id": session_id,
            "title": f"Live Learning Production E2E {stamp}",
            "model": "",
            "system_prompt": "You are Echo running a production live-learning validation session.",
        }
        await require_ipc("SESSION NEW " + json.dumps(payload, separators=(",", ":")), "session:ok")
        await require_ipc(f"SESSION SET {session_id}", "session:set_ok")
        bridge.active_session_id = session_id
        baseline = await bridge.query_daemon_ipc(
            f"Reply with this exact marker and nothing else: {marker}",
            author=author,
            session_id=session_id,
        )
        if marker not in response_text(baseline):
            raise RuntimeError(f"real baseline turn did not return its marker: {baseline[:800]}")
        original_node_pid = listener_pid(5000)
        await bridge.learn_cmd.callback(
            interaction,
            "Learn the completed validation exchange as a harmless production proof of cumulative local weight training, retention, rights review, activation, restart, and recovery.",
        )
        if not interaction.response.deferred:
            raise RuntimeError("registered /learn handler did not defer its Discord interaction")
        after = await bridge._learning_controller("status")
        expected_version = int(before.get("active_version", 0)) + 1
        if int(after.get("active_version", 0)) != expected_version:
            raise RuntimeError(f"lineage version did not advance exactly once: {after}")
        active = after.get("active")
        if not isinstance(active, dict):
            raise RuntimeError(f"lineage has no committed active transaction: {after}")
        transaction_id = str(active.get("transaction_id", ""))
        previous_active = before.get("active")
        previous_transaction_id = (
            str(previous_active.get("transaction_id", "")) if isinstance(previous_active, dict) else ""
        )
        if (
            len(transaction_id) != 64
            or transaction_id == previous_transaction_id
            or int(active.get("parent_version", -1)) != int(before.get("active_version", 0))
        ):
            raise RuntimeError(f"lineage did not commit one new child transaction: {after}")
        committed_manifest = json.loads(
            (ROOT / "config" / "learning" / "live" / "transactions" / transaction_id / "manifest.json").read_text(
                encoding="utf-8"
            )
        )
        if (
            committed_manifest.get("session_id") != session_id
            or committed_manifest.get("status") != "promoted"
            or int(committed_manifest.get("version", -1)) != expected_version
        ):
            raise RuntimeError(f"committed transaction is not the fresh validation session: {committed_manifest}")
        runtime = await bridge._learning_controller("runtime-spec")
        if (
            runtime.get("status") != "active"
            or runtime.get("transaction_id") != transaction_id
            or runtime.get("adapter_hash") != active.get("adapter_hash")
        ):
            raise RuntimeError(f"production runtime does not match committed lineage: {runtime}")
        health = await require_ipc("HEALTH", "health:")
        status = await require_ipc("STATUS", "status:active")
        if ",agent:healthy" not in health or ",ipc:healthy" not in health:
            raise RuntimeError(f"replacement health is incomplete: {health}")
        replacement_node_pid = listener_pid(5000)
        if replacement_node_pid == original_node_pid:
            raise RuntimeError(f"node listener was not replaced: PID {original_node_pid}")
        while True:
            current_discord_status = json.loads(
                (ROOT / "config" / "platforms.json").read_text(encoding="utf-8")
            )["discord"]["status"]
            if current_discord_status == "ONLINE":
                break
            if not bridge._node_supervisor_alive():
                raise RuntimeError("node supervisor exited before Discord liveness recovered")
            await asyncio.sleep(0.1)
        await asyncio.sleep(0.15)
        liveness_states = [item["status"] for item in evidence["discord_liveness"]]
        if not liveness_states or liveness_states[0] != "ONLINE":
            raise RuntimeError(f"Discord was not ONLINE before the controlled restart: {liveness_states}")
        try:
            offline_index = liveness_states.index("OFFLINE")
            recovery_index = liveness_states.index("ONLINE", offline_index + 1)
        except ValueError as exc:
            raise RuntimeError(
                f"Discord did not prove ONLINE->OFFLINE->ONLINE node coupling: {liveness_states}"
            ) from exc
        probe_path = evidence_path.with_name(f"{stamp}-post-restart-probe.json")
        probe_log = evidence_path.with_name(f"{stamp}-post-restart-provider.log")
        probe = await asyncio.create_subprocess_exec(
            str(Path(os.path.expanduser(live_config["runtime_path"])) / "bin" / "python"),
            str(ROOT / "scripts" / "live_learning_probe.py"),
            "--model", str(runtime["model_path"]),
            "--adapter", str(runtime["adapter_path"]),
            "--port", str(runtime["provider_port"]),
            "--existing-server", "--output", str(probe_path),
            "--server-log", str(probe_log),
            cwd=ROOT,
        )
        if await probe.wait() != 0:
            raise RuntimeError("independent post-restart text/image probe failed")
        probe_receipt = json.loads(probe_path.read_text(encoding="utf-8"))
        if probe_receipt.get("passed") is not True:
            raise RuntimeError(f"post-restart probe receipt failed: {probe_receipt}")
        with sqlite3.connect(Path.home() / ".ernosdecent" / "node.db") as database:
            rights = database.execute(
                "SELECT category,status,proposed_hash FROM rights_changes WHERE target=? ORDER BY proposed_at,change_id",
                (active["transaction_id"],),
            ).fetchall()
        categories = {row[0]: row[1] for row in rights}
        if categories.get("model_weight_training") != "applied" or categories.get("model_weight_activation") != "applied":
            raise RuntimeError(f"rights receipts are not both applied: {rights}")
        if json.loads((ROOT / "config" / "platforms.json").read_text(encoding="utf-8"))["discord"]["status"] != "ONLINE":
            raise RuntimeError("Discord did not recover ONLINE after authenticated node health")
        if not any(item["content"].startswith("✅ Live learning complete:") for item in evidence["discord_messages"]):
            raise RuntimeError("Discord never received the production completion reply")
        evidence.update(
            result="PASS",
            completed_at=int(time.time()),
            after=after,
            health_hash=hashlib.sha256(health.encode("utf-8")).hexdigest(),
            status_hash=hashlib.sha256(status.encode("utf-8")).hexdigest(),
            rights_receipts=[{"category": row[0], "status": row[1], "proposed_hash": row[2]} for row in rights],
            post_restart_probe=str(probe_path),
            original_node_pid=original_node_pid,
            replacement_node_pid=replacement_node_pid,
            discord_recovery_transition_index=recovery_index,
        )
        atomic_json(evidence_path, evidence)
        print("ERNOS_LIVE_LEARNING_PRODUCTION_E2E=" + json.dumps({"result": "PASS", "evidence": str(evidence_path), "version": expected_version}, separators=(",", ":")))
        return 0
    except Exception as exc:
        evidence.update(result="FAIL", completed_at=int(time.time()), error=f"{type(exc).__name__}: {exc}")
        atomic_json(evidence_path, evidence)
        raise
    finally:
        liveness_stop.set()
        await liveness_task
        if original_session and original_session != "default":
            restored = await bridge.send_daemon_ipc(f"SESSION SET {original_session}")
            evidence["original_session_restore"] = restored
            atomic_json(evidence_path, evidence)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main_async()))
