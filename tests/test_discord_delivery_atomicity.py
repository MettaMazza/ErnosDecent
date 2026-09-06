import ast
import asyncio
import io
import re
import secrets
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path

from discord.http import handle_message_parameters


BRIDGE_PATH = Path(__file__).resolve().parents[1] / "decent_net" / "discord_bridge.py"


def _bridge_tree():
    return ast.parse(
        BRIDGE_PATH.read_text(encoding="utf-8"), filename=str(BRIDGE_PATH)
    )


def load_send_function():
    tree = _bridge_tree()
    function = next(
        node for node in tree.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "send_discord_reply"
    )
    namespace = {
        "asyncio": asyncio,
        "io": io,
        "re": re,
        "DeliveryPayload": type("DeliveryPayload", (), {}),
        "DeliveryAcknowledgeError": type(
            "DeliveryAcknowledgeError", (Exception,), {}
        ),
        "DeliverySendError": type("DeliverySendError", (Exception,), {}),
    }
    namespace["DeliveryOutcomeUnknownError"] = type(
        "DeliveryOutcomeUnknownError",
        (namespace["DeliveryAcknowledgeError"],),
        {},
    )
    exec(
        compile(ast.Module(body=[function], type_ignores=[]), str(BRIDGE_PATH), "exec"),
        namespace,
    )
    return namespace


def load_claimed_send_function():
    tree = _bridge_tree()
    function = next(
        node for node in tree.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "send_claimed_discord"
    )
    namespace = {
        "asyncio": asyncio,
        "DeliveryPayload": type("DeliveryPayload", (), {}),
        "DeliveryAcknowledgeError": type(
            "DeliveryAcknowledgeError", (Exception,), {}
        ),
        "DeliverySendError": type("DeliverySendError", (Exception,), {}),
    }
    namespace["DeliveryOutcomeUnknownError"] = type(
        "DeliveryOutcomeUnknownError",
        (namespace["DeliveryAcknowledgeError"],),
        {},
    )
    exec(
        compile(ast.Module(body=[function], type_ignores=[]), str(BRIDGE_PATH), "exec"),
        namespace,
    )
    return namespace


def load_ack_function():
    wanted = {
        "DeliveryPayload",
        "DeliveryAcknowledgeError",
        "_DeliveryClaimStale",
        "ack_delivery",
    }
    body = [
        node for node in _bridge_tree().body
        if isinstance(node, (ast.ClassDef, ast.AsyncFunctionDef))
        and node.name in wanted
    ]
    namespace = {
        "asyncio": asyncio,
        "sqlite3": sqlite3,
        "time": time,
        "_active_turn_ids": {},
    }
    exec(compile(ast.Module(body=body, type_ignores=[]), str(BRIDGE_PATH), "exec"), namespace)
    return namespace


def load_busy_functions():
    wanted = {
        "_claim_session_busy", "_bind_session_turn", "_release_session_busy",
    }
    body = [
        node for node in _bridge_tree().body
        if isinstance(node, ast.FunctionDef) and node.name in wanted
    ]
    namespace = {"secrets": secrets, "_busy_sessions": {}}
    exec(
        compile(ast.Module(body=body, type_ignores=[]), str(BRIDGE_PATH), "exec"),
        namespace,
    )
    return namespace


def load_recovery_claim_function():
    wanted = {"DeliveryPayload", "db_claim_recovery_delivery"}
    body = [
        node for node in _bridge_tree().body
        if isinstance(node, (ast.ClassDef, ast.FunctionDef))
        and node.name in wanted
    ]
    namespace = {
        "secrets": secrets,
        "sqlite3": sqlite3,
        "time": time,
        "_delivery_owner": "test-recovery",
        "_DELIVERY_LEASE_SECONDS": 120,
    }
    exec(
        compile(ast.Module(body=body, type_ignores=[]), str(BRIDGE_PATH), "exec"),
        namespace,
    )
    return namespace


def load_recovered_delivery_function():
    function = next(
        node for node in _bridge_tree().body
        if isinstance(node, ast.AsyncFunctionDef)
        and node.name == "_deliver_recovered_delivery"
    )
    namespace = {
        "DeliveryAcknowledgeError": type(
            "DeliveryAcknowledgeError", (Exception,), {}
        ),
        "DeliverySendError": type("DeliverySendError", (Exception,), {}),
        "_active_turn_ids": {},
        "os": __import__("os"),
        "_ATTACH_MAX_BYTES": 24 * 1024 * 1024,
    }
    exec(
        compile(ast.Module(body=[function], type_ignores=[]), str(BRIDGE_PATH), "exec"),
        namespace,
    )
    return namespace


def load_cancel_function():
    function = next(
        node for node in _bridge_tree().body
        if isinstance(node, ast.AsyncFunctionDef)
        and node.name == "_request_session_cancel"
    )
    namespace = {"_active_turn_ids": {}}
    exec(
        compile(ast.Module(body=[function], type_ignores=[]), str(BRIDGE_PATH), "exec"),
        namespace,
    )
    return namespace


class FakeFile:
    def __init__(self, stream, filename):
        self.stream = stream
        self.filename = filename


class FakeDiscord:
    File = FakeFile


class FakeSent:
    def __init__(self, message_id=417, events=None):
        self.id = message_id
        self.events = events

    async def edit(self, **kwargs):
        if self.events is not None:
            self.events.append(("external_edit", kwargs))
        return self


class FakeMessage:
    def __init__(self, events, fail_with=None):
        self.events = events
        self.fail_with = fail_with

    async def reply(self, content, **kwargs):
        self.events.append(("external_send", content, kwargs))
        if self.fail_with is not None:
            raise self.fail_with
        return FakeSent()


class FakeEditMessage:
    def __init__(self, events, fail_with=None):
        self.events = events
        self.fail_with = fail_with

    async def edit(self, **kwargs):
        self.events.append(("external_edit", kwargs))
        if self.fail_with is not None:
            raise self.fail_with
        return FakeSent(418)


class DiscordDeliveryAtomicityTest(unittest.TestCase):
    def make_namespace(self, events):
        namespace = load_send_function()
        namespace["discord"] = FakeDiscord

        async def ack_delivery(delivery, sent_ids, attachment_claims=None):
            events.append(
                ("bundle_ack", tuple(sent_ids), tuple(attachment_claims or []))
            )

        async def release_delivery(delivery, reason):
            events.append(("outbox_release", reason))

        async def release_attachments(ids, reason):
            events.append(("attachment_release", reason))

        async def renew_claim(delivery, stop_event):
            await stop_event.wait()

        async def renew_traces(claims, stop_event):
            await stop_event.wait()

        async def find_prior(message, delivery, nonce):
            return True, None

        namespace.update({
            "ack_delivery": ack_delivery,
            "release_delivery": release_delivery,
            "db_release_attachment_claims": release_attachments,
            "_renew_delivery_lease": renew_claim,
            "_renew_trace_claims": renew_traces,
            "_delivery_nonce": lambda delivery: (
                f"ed{delivery.delivery_id:x}"
                if isinstance(delivery, namespace["DeliveryPayload"])
                else None
            ),
            "_find_confirmed_discord_reply": find_prior,
            "_discord_send_failure_is_definitive": (
                lambda exc: isinstance(exc, (TypeError, ValueError))
            ),
        })
        return namespace

    @staticmethod
    def make_delivery(namespace, attempts=1):
        delivery = namespace["DeliveryPayload"]()
        delivery.delivery_id = 42
        delivery.delivered = False
        delivery.attempts = attempts
        return delivery

    def test_long_reply_is_one_external_send_then_atomic_ack(self):
        events = []
        namespace = self.make_namespace(events)
        send = namespace["send_discord_reply"]
        sent_ids = asyncio.run(send(FakeMessage(events), "x" * 3000))
        self.assertEqual(sent_ids, [417])
        self.assertEqual([event[0] for event in events], ["external_send", "bundle_ack"])
        kwargs = events[0][2]
        self.assertEqual(len(kwargs["files"]), 1)
        self.assertEqual(kwargs["files"][0].filename, "ernos_response.txt")
        self.assertEqual(kwargs["files"][0].stream.getvalue(), b"x" * 3000)

    def test_durable_reply_carries_stable_nonce_before_ack(self):
        events = []
        namespace = self.make_namespace(events)
        delivery = self.make_delivery(namespace)
        sent_ids = asyncio.run(
            namespace["send_discord_reply"](
                FakeMessage(events), "answer", delivery=delivery
            )
        )
        self.assertEqual(sent_ids, [417])
        self.assertEqual(events[0][2]["nonce"], "ed2a")
        self.assertEqual([event[0] for event in events], ["external_send", "bundle_ack"])

    def test_retry_reconciles_prior_nonce_without_second_send(self):
        events = []
        namespace = self.make_namespace(events)
        delivery = self.make_delivery(namespace, attempts=2)

        async def find_prior(message, claimed_delivery, nonce):
            events.append(("history_scan", nonce))
            return True, FakeSent(900)

        namespace["_find_confirmed_discord_reply"] = find_prior
        sent_ids = asyncio.run(
            namespace["send_discord_reply"](
                FakeMessage(events), "answer", delivery=delivery
            )
        )
        self.assertEqual(sent_ids, [900])
        self.assertEqual([event[0] for event in events], ["history_scan", "bundle_ack"])

    def test_ambiguous_send_retains_claim_when_reconciliation_fails(self):
        events = []
        namespace = self.make_namespace(events)
        delivery = self.make_delivery(namespace)

        async def failed_scan(message, claimed_delivery, nonce):
            events.append(("history_scan_failed", nonce))
            return False, None

        namespace["_find_confirmed_discord_reply"] = failed_scan
        with self.assertRaises(namespace["DeliveryOutcomeUnknownError"]):
            asyncio.run(
                namespace["send_discord_reply"](
                    FakeMessage(events, RuntimeError("connection reset")),
                    "answer",
                    delivery=delivery,
                )
            )
        self.assertEqual(
            [event[0] for event in events],
            ["external_send", "history_scan_failed"],
        )

    def test_ambiguous_send_retains_claim_when_history_has_no_match_yet(self):
        events = []
        namespace = self.make_namespace(events)
        delivery = self.make_delivery(namespace)

        async def completed_empty_scan(message, claimed_delivery, nonce):
            events.append(("history_scan_empty", nonce))
            return True, None

        namespace["_find_confirmed_discord_reply"] = completed_empty_scan
        with self.assertRaises(namespace["DeliveryOutcomeUnknownError"]):
            asyncio.run(
                namespace["send_discord_reply"](
                    FakeMessage(events, RuntimeError("gateway timeout")),
                    "answer",
                    delivery=delivery,
                )
            )
        self.assertEqual(
            [event[0] for event in events],
            ["external_send", "history_scan_empty"],
        )

    def test_definitive_rejection_releases_without_ack(self):
        events = []
        namespace = self.make_namespace(events)
        delivery = self.make_delivery(namespace)

        async def failed_scan(message, claimed_delivery, nonce):
            events.append(("history_scan_failed", nonce))
            return False, None

        namespace["_find_confirmed_discord_reply"] = failed_scan
        with self.assertRaises(namespace["DeliverySendError"]):
            asyncio.run(
                namespace["send_discord_reply"](
                    FakeMessage(events, ValueError("invalid payload")),
                    "answer",
                    delivery=delivery,
                )
            )
        self.assertEqual(
            [event[0] for event in events],
            [
                "external_send",
                "history_scan_failed",
                "outbox_release",
                "attachment_release",
            ],
        )

    def test_edit_failure_never_falls_back_to_reply(self):
        events = []
        namespace = self.make_namespace(events)
        with self.assertRaises(namespace["DeliverySendError"]):
            asyncio.run(
                namespace["send_discord_reply"](
                    FakeMessage(events),
                    "answer",
                    edit_msg=FakeEditMessage(events, ValueError("edit rejected")),
                )
            )
        self.assertEqual(
            [event[0] for event in events],
            ["external_edit", "outbox_release", "attachment_release"],
        )

    def test_installed_discord_client_enforces_supplied_nonce(self):
        params = handle_message_parameters(content="answer", nonce="ed2a")
        self.assertEqual(params.payload["nonce"], "ed2a")
        self.assertIs(params.payload["enforce_nonce"], True)

    def test_interactive_delivery_uses_nonce_before_ack(self):
        events = []
        namespace = load_claimed_send_function()
        delivery = self.make_delivery(namespace)

        async def ack_delivery(claimed_delivery, sent_ids):
            events.append(("bundle_ack", tuple(sent_ids)))

        async def release_delivery(claimed_delivery, reason):
            events.append(("outbox_release", reason))

        async def renew_claim(claimed_delivery, stop_event):
            await stop_event.wait()

        async def find_prior(message, claimed_delivery, nonce):
            return True, None

        namespace.update({
            "ack_delivery": ack_delivery,
            "release_delivery": release_delivery,
            "_renew_delivery_lease": renew_claim,
            "_delivery_nonce": lambda claimed_delivery: "ed2a",
            "_find_confirmed_discord_reply": find_prior,
            "_discord_send_failure_is_definitive": lambda exc: False,
        })
        sent = asyncio.run(
            namespace["send_claimed_discord"](
                FakeMessage(events), "approval", delivery, view="active-view"
            )
        )
        self.assertEqual(sent.id, 417)
        self.assertEqual(events[0][2]["nonce"], "ed2a")
        self.assertEqual([event[0] for event in events], ["external_send", "bundle_ack"])

    def test_interactive_retry_restores_view_without_second_send(self):
        events = []
        namespace = load_claimed_send_function()
        delivery = self.make_delivery(namespace, attempts=2)
        prior = FakeSent(901, events)

        async def ack_delivery(claimed_delivery, sent_ids):
            events.append(("bundle_ack", tuple(sent_ids)))

        async def release_delivery(claimed_delivery, reason):
            events.append(("outbox_release", reason))

        async def renew_claim(claimed_delivery, stop_event):
            await stop_event.wait()

        async def find_prior(message, claimed_delivery, nonce):
            events.append(("history_scan", nonce))
            return True, prior

        namespace.update({
            "ack_delivery": ack_delivery,
            "release_delivery": release_delivery,
            "_renew_delivery_lease": renew_claim,
            "_delivery_nonce": lambda claimed_delivery: "ed2a",
            "_find_confirmed_discord_reply": find_prior,
            "_discord_send_failure_is_definitive": lambda exc: False,
        })
        sent = asyncio.run(
            namespace["send_claimed_discord"](
                FakeMessage(events), "approval", delivery, view="replacement-view"
            )
        )
        self.assertEqual(sent.id, 901)
        self.assertEqual(
            [event[0] for event in events],
            ["history_scan", "external_edit", "bundle_ack"],
        )

    def test_interactive_ambiguous_send_retains_claim_after_empty_scan(self):
        events = []
        namespace = load_claimed_send_function()
        delivery = self.make_delivery(namespace)

        async def ack_delivery(claimed_delivery, sent_ids):
            events.append(("bundle_ack", tuple(sent_ids)))

        async def release_delivery(claimed_delivery, reason):
            events.append(("outbox_release", reason))

        async def renew_claim(claimed_delivery, stop_event):
            await stop_event.wait()

        async def completed_empty_scan(message, claimed_delivery, nonce):
            events.append(("history_scan_empty", nonce))
            return True, None

        namespace.update({
            "ack_delivery": ack_delivery,
            "release_delivery": release_delivery,
            "_renew_delivery_lease": renew_claim,
            "_delivery_nonce": lambda claimed_delivery: "ed2a",
            "_find_confirmed_discord_reply": completed_empty_scan,
            "_discord_send_failure_is_definitive": lambda exc: False,
        })
        with self.assertRaises(namespace["DeliveryOutcomeUnknownError"]):
            asyncio.run(
                namespace["send_claimed_discord"](
                    FakeMessage(events, RuntimeError("gateway timeout")),
                    "approval", delivery,
                )
            )
        self.assertEqual(
            [event[0] for event in events],
            ["external_send", "history_scan_empty"],
        )


class DiscordSessionOrderingTest(unittest.TestCase):
    def test_busy_ownership_is_per_session_and_token_guarded(self):
        namespace = load_busy_functions()
        claim_busy = namespace["_claim_session_busy"]
        bind_turn = namespace["_bind_session_turn"]
        release_busy = namespace["_release_session_busy"]

        token_a = claim_busy("session-a", 10, 100)
        token_b = claim_busy("session-b", 20, 200)
        self.assertTrue(token_a)
        self.assertTrue(token_b)
        self.assertNotEqual(token_a, token_b)
        self.assertEqual(claim_busy("session-a", 30, 300), "")
        self.assertTrue(bind_turn("session-a", token_a, "turn-a"))
        self.assertEqual(
            namespace["_busy_sessions"]["session-a"]["turn_id"], "turn-a"
        )

        self.assertTrue(release_busy("session-a", token_a))
        replacement = claim_busy("session-a", 30, 300)
        self.assertTrue(replacement)
        self.assertFalse(release_busy("session-a", token_a))
        self.assertFalse(bind_turn("session-a", token_a, "stale-turn"))
        self.assertEqual(
            namespace["_busy_sessions"]["session-a"]["token"], replacement
        )
        self.assertTrue(release_busy("session-a", replacement))
        self.assertIn("session-b", namespace["_busy_sessions"])

    def test_text_commands_are_dispatched_before_busy_whisper_routing(self):
        tree = _bridge_tree()
        on_message = next(
            node for node in tree.body
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "on_message"
        )
        source = ast.get_source_segment(
            BRIDGE_PATH.read_text(encoding="utf-8"), on_message
        )
        busy_index = source.index("if sess in _busy_sessions")
        for command in (
            "/stop", "/factory", "/persona", "/rename", "/autoapprove",
            "/new",
        ):
            self.assertLess(source.index(command), busy_index, command)
        self.assertNotIn("_ai_busy", BRIDGE_PATH.read_text(encoding="utf-8"))

    def test_stop_uses_exact_turn_then_session_only_validation_fallback(self):
        namespace = load_cancel_function()
        commands = []

        async def send(command):
            commands.append(command)
            if "[TURN:" in command:
                return "ai:cancel_ack,session:session-a,turn:turn-a"
            return "ai:cancel_ack,session:session-a,validation_job:job-a"

        namespace["send_daemon_ipc"] = send
        namespace["_active_turn_ids"]["session-a"] = "turn-a"
        turn_id, response = asyncio.run(
            namespace["_request_session_cancel"]("session-a")
        )
        self.assertEqual(turn_id, "turn-a")
        self.assertIn("turn:turn-a", response)
        self.assertEqual(
            commands[-1], "AI CANCEL [SESSION:session-a] [TURN:turn-a]"
        )

        namespace["_active_turn_ids"].pop("session-a")
        turn_id, response = asyncio.run(
            namespace["_request_session_cancel"]("session-a")
        )
        self.assertEqual(turn_id, "")
        self.assertIn("validation_job:job-a", response)
        self.assertEqual(commands[-1], "AI CANCEL [SESSION:session-a]")

    def test_query_uses_reserved_session_not_mutable_active_session(self):
        tree = _bridge_tree()
        query = next(
            node for node in tree.body
            if isinstance(node, ast.AsyncFunctionDef)
            and node.name == "query_daemon_ipc"
        )
        arg_names = [arg.arg for arg in query.args.args]
        self.assertIn("session_id", arg_names)
        self.assertIn("busy_token", arg_names)
        referenced_names = {
            node.id for node in ast.walk(query) if isinstance(node, ast.Name)
        }
        self.assertNotIn("active_session_id", referenced_names)


class DiscordRecoveryOrderingTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory(prefix="ernos-recovery-order-")
        self.db_path = str(Path(self.tempdir.name) / "node.db")
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(
                """
                CREATE TABLE delivery_turns (
                    turn_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL
                );
                CREATE TABLE delivery_outbox (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    turn_id TEXT NOT NULL,
                    sequence INTEGER NOT NULL,
                    surface TEXT NOT NULL,
                    destination TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    terminal INTEGER NOT NULL,
                    state TEXT NOT NULL,
                    claim_owner TEXT NOT NULL DEFAULT '',
                    claim_token TEXT NOT NULL DEFAULT '',
                    lease_until INTEGER NOT NULL DEFAULT 0,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    available_at INTEGER NOT NULL DEFAULT 0,
                    created_at INTEGER NOT NULL,
                    last_error TEXT NOT NULL DEFAULT ''
                );
                """
            )
        self.namespace = load_recovery_claim_function()
        self.namespace["connect_db"] = lambda: sqlite3.connect(self.db_path)

    def tearDown(self):
        self.tempdir.cleanup()

    def insert_turn(self, turn_id, session_id, destination, state, created_at,
                    lease_until=0, kind="progress"):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO delivery_turns VALUES (?,?)",
                (turn_id, session_id),
            )
            conn.execute(
                """INSERT INTO delivery_outbox
                   (turn_id,sequence,surface,destination,kind,payload,terminal,
                    state,lease_until,available_at,created_at)
                   VALUES (?,1,'discord',?,?,?,1,?,?,0,?)""",
                (turn_id, destination, kind, turn_id, state, lease_until, created_at),
            )

    def test_progress_cannot_overtake_earlier_unacknowledged_parent(self):
        now = int(time.time())
        self.insert_turn(
            "parent", "session-a", "10|100|1000", "claimed", now - 30,
            lease_until=now + 120,
        )
        self.insert_turn(
            "report", "session-a", "10|100|1000", "ready", now - 20,
            kind="background_completion",
        )
        self.assertIsNone(self.namespace["db_claim_recovery_delivery"]())
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE delivery_outbox SET state='delivered' WHERE turn_id='parent'"
            )
        claimed = self.namespace["db_claim_recovery_delivery"]()
        self.assertIsNotNone(claimed)
        self.assertEqual(claimed.turn_id, "report")
        self.assertEqual(claimed.kind, "background_completion")
        self.assertEqual(claimed.destination, "10|100|1000")
        with sqlite3.connect(self.db_path) as conn:
            state, token = conn.execute(
                "SELECT state,claim_token FROM delivery_outbox WHERE turn_id='report'"
            ).fetchone()
        self.assertEqual(state, "claimed")
        self.assertTrue(token)

    def test_blocked_session_does_not_block_a_different_session(self):
        now = int(time.time())
        self.insert_turn(
            "parent-a", "session-a", "10|100|1000", "claimed", now - 40,
            lease_until=now + 120,
        )
        self.insert_turn(
            "progress-a", "session-a", "10|100|1000", "ready", now - 30,
        )
        self.insert_turn(
            "progress-b", "session-b", "10|200|2000", "ready", now - 20,
        )
        claimed = self.namespace["db_claim_recovery_delivery"]()
        self.assertIsNotNone(claimed)
        self.assertEqual(claimed.turn_id, "progress-b")


class DiscordIndependentRecoveryTest(unittest.TestCase):
    class Payload(str):
        def __new__(cls, value, kind):
            obj = super().__new__(cls, value)
            obj.kind = kind
            obj.session_id = "session-a"
            obj.turn_id = "background-turn"
            obj.delivery_id = 7
            return obj

    def make_namespace(self, events):
        namespace = load_recovered_delivery_function()

        async def resolve_target(delivery):
            return object()

        async def send_reply(target, body, **kwargs):
            events.append(("send", body, kwargs))

        async def release(delivery, reason, retry_delay_s=1):
            events.append(("release", reason, retry_delay_s))

        async def unexpected(*args, **kwargs):
            raise AssertionError("foreground trace/interactive path was used")

        namespace.update({
            "_resolve_recovery_target": resolve_target,
            "send_discord_reply": send_reply,
            "release_delivery": release,
            "handle_tool_approval": unexpected,
            "handle_clarification": unexpected,
            "db_collect_attachments": lambda session_id: (_ for _ in ()).throw(
                AssertionError("background progress stole trace attachments")
            ),
            "build_discord_files": unexpected,
            "extract_ai_ok_response": lambda value: (
                str(value).split("|||RESPONSE|||", 1)[1]
                if "|||RESPONSE|||" in str(value) else str(value)
            ),
            "_attachment_safe_canonical": lambda value: "",
            "discord": FakeDiscord,
        })
        return namespace

    def test_progress_and_completion_use_exact_payload_without_trace_poller(self):
        for kind in (
            "progress", "completion", "background_progress",
            "background_completion",
        ):
            events = []
            namespace = self.make_namespace(events)
            visible_text = f"{kind} text"
            stored_text = visible_text
            if kind == "background_completion":
                stored_text = f"ai:ok|||RESPONSE|||{visible_text}"
            payload = self.Payload(stored_text, kind)
            asyncio.run(namespace["_deliver_recovered_delivery"](payload))
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0][0:2], ("send", visible_text))
            self.assertEqual(events[0][2]["files"], [])
            self.assertIs(events[0][2]["delivery"], payload)

    def test_invalid_attachment_releases_exact_outbox_claim(self):
        events = []
        namespace = self.make_namespace(events)
        payload = self.Payload("/forbidden/secret.key", "attachment")
        asyncio.run(namespace["_deliver_recovered_delivery"](payload))
        self.assertEqual(events[0][0], "release")
        self.assertIn("recovery_route_failed:ValueError", events[0][1])
        self.assertEqual(events[0][2], 30)


class DiscordBundleAckTransactionTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory(prefix="ernos-discord-ack-")
        self.db_path = str(Path(self.tempdir.name) / "node.db")
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(
                """
                CREATE TABLE delivery_outbox (
                    id INTEGER PRIMARY KEY,
                    state TEXT NOT NULL,
                    delivered_at INTEGER NOT NULL DEFAULT 0,
                    external_message_id TEXT NOT NULL DEFAULT '',
                    claim_owner TEXT NOT NULL DEFAULT '',
                    claim_token TEXT NOT NULL DEFAULT '',
                    lease_until INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT NOT NULL DEFAULT ''
                );
                CREATE TABLE trace_events (
                    id INTEGER PRIMARY KEY,
                    sent INTEGER NOT NULL DEFAULT 0,
                    claim_owner TEXT NOT NULL DEFAULT '',
                    claim_token TEXT NOT NULL DEFAULT '',
                    lease_until INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT NOT NULL DEFAULT ''
                );
                """
            )
        self.namespace = load_ack_function()
        self.namespace["connect_db"] = lambda: sqlite3.connect(self.db_path)

    def tearDown(self):
        self.tempdir.cleanup()

    def make_delivery(self, delivery_id, token):
        return self.namespace["DeliveryPayload"](
            "payload",
            delivery_id=delivery_id,
            turn_id="turn",
            session_id="session",
            sequence=1,
            kind="final",
            terminal=False,
            destination="1|2|3",
            claim_token=token,
        )

    def test_outbox_and_attachments_commit_together_after_confirmation(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO delivery_outbox (id,state,claim_token) VALUES (1,'claimed','outbox-token')"
            )
            conn.execute(
                "INSERT INTO trace_events (id,claim_token) VALUES (10,'trace-a')"
            )
            conn.execute(
                "INSERT INTO trace_events (id,claim_token) VALUES (11,'trace-b')"
            )
        delivery = self.make_delivery(1, "outbox-token")
        result = asyncio.run(
            self.namespace["ack_delivery"](
                delivery,
                [417],
                [
                    {"id": 10, "claim_token": "trace-a"},
                    {"id": 11, "claim_token": "trace-b"},
                ],
            )
        )
        self.assertIs(result, True)
        with sqlite3.connect(self.db_path) as conn:
            outbox = conn.execute(
                "SELECT state, external_message_id FROM delivery_outbox WHERE id=1"
            ).fetchone()
            traces = conn.execute(
                "SELECT id, sent FROM trace_events ORDER BY id"
            ).fetchall()
        self.assertEqual(outbox, ("delivered", "417"))
        self.assertEqual(traces, [(10, 1), (11, 1)])

    def test_stale_attachment_rolls_back_outbox_and_other_attachment(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO delivery_outbox (id,state,claim_token) VALUES (2,'claimed','outbox-token')"
            )
            conn.execute(
                "INSERT INTO trace_events (id,claim_token) VALUES (20,'trace-a')"
            )
            conn.execute(
                "INSERT INTO trace_events (id,claim_token) VALUES (21,'different-token')"
            )
        delivery = self.make_delivery(2, "outbox-token")
        with self.assertRaises(self.namespace["DeliveryAcknowledgeError"]):
            asyncio.run(
                self.namespace["ack_delivery"](
                    delivery,
                    [418],
                    [
                        {"id": 20, "claim_token": "trace-a"},
                        {"id": 21, "claim_token": "stale-token"},
                    ],
                )
            )
        with sqlite3.connect(self.db_path) as conn:
            outbox_state = conn.execute(
                "SELECT state FROM delivery_outbox WHERE id=2"
            ).fetchone()[0]
            traces = conn.execute(
                "SELECT id, sent FROM trace_events WHERE id>=20 ORDER BY id"
            ).fetchall()
        self.assertEqual(outbox_state, "claimed")
        self.assertEqual(traces, [(20, 0), (21, 0)])

    def test_empty_or_noncanonical_discord_id_cannot_ack(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO delivery_outbox (id,state,claim_token) VALUES (3,'claimed','outbox-token')"
            )
        delivery = self.make_delivery(3, "outbox-token")
        for invalid_ids in ([], [""], ["not-a-snowflake"], ["0"], ["9" * 33]):
            with self.assertRaises(self.namespace["DeliveryAcknowledgeError"]):
                asyncio.run(
                    self.namespace["ack_delivery"](
                        delivery, invalid_ids
                    )
                )
        with sqlite3.connect(self.db_path) as conn:
            state, external_id = conn.execute(
                "SELECT state, external_message_id FROM delivery_outbox WHERE id=3"
            ).fetchone()
        self.assertEqual((state, external_id), ("claimed", ""))


if __name__ == "__main__":
    unittest.main()
