import hashlib
import sqlite3
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

SCHEMA = """
CREATE TABLE delivery_turns (
    turn_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    surface TEXT NOT NULL,
    destination TEXT NOT NULL DEFAULT '',
    state TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    last_error TEXT NOT NULL DEFAULT ''
);
CREATE TABLE delivery_outbox (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    turn_id TEXT NOT NULL,
    sequence INTEGER NOT NULL,
    surface TEXT NOT NULL,
    destination TEXT NOT NULL DEFAULT '',
    kind TEXT NOT NULL,
    payload TEXT NOT NULL,
    terminal INTEGER NOT NULL DEFAULT 0,
    state TEXT NOT NULL DEFAULT 'ready',
    claim_owner TEXT NOT NULL DEFAULT '',
    claim_token TEXT NOT NULL DEFAULT '',
    lease_until INTEGER NOT NULL DEFAULT 0,
    attempts INTEGER NOT NULL DEFAULT 0,
    available_at INTEGER NOT NULL DEFAULT 0,
    created_at INTEGER NOT NULL,
    delivered_at INTEGER NOT NULL DEFAULT 0,
    external_message_id TEXT NOT NULL DEFAULT '',
    last_error TEXT NOT NULL DEFAULT '',
    UNIQUE(turn_id, sequence)
);
CREATE TABLE trace_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    content TEXT NOT NULL DEFAULT '',
    created_at INTEGER NOT NULL DEFAULT 0,
    sent INTEGER NOT NULL DEFAULT 0,
    claim_owner TEXT NOT NULL DEFAULT '',
    claim_token TEXT NOT NULL DEFAULT '',
    lease_until INTEGER NOT NULL DEFAULT 0,
    attempts INTEGER NOT NULL DEFAULT 0,
    available_at INTEGER NOT NULL DEFAULT 0,
    last_error TEXT NOT NULL DEFAULT ''
);
"""


def connect(path):
    conn = sqlite3.connect(path, timeout=10, isolation_level=None)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=10000")
    return conn


def claim(path, turn_id, owner, token, lease_seconds, surface="discord"):
    now = int(time.time())
    with connect(path) as conn:
        return conn.execute(
            """
            UPDATE delivery_outbox
               SET state='claimed', claim_owner=?, claim_token=?, lease_until=?,
                   attempts=attempts+1, last_error=''
             WHERE id=(
                   SELECT id FROM delivery_outbox
                    WHERE turn_id=? AND surface=?
                      AND ((state='ready' AND available_at<=?)
                           OR (state='claimed' AND lease_until<=?))
                    ORDER BY sequence LIMIT 1
             )
               AND ((state='ready' AND available_at<=?)
                    OR (state='claimed' AND lease_until<=?))
            RETURNING id, claim_token
            """,
            (owner, token, now + lease_seconds, turn_id, surface,
             now, now, now, now),
        ).fetchone()


def renew(path, delivery_id, token, lease_seconds):
    with connect(path) as conn:
        return conn.execute(
            """UPDATE delivery_outbox SET lease_until=?
                 WHERE id=? AND state='claimed' AND claim_token=?
                RETURNING id""",
            (int(time.time()) + lease_seconds, delivery_id, token),
        ).fetchone()


def ack(path, delivery_id, token, external_id):
    if not external_id or len(external_id) > 4096:
        return None
    with connect(path) as conn:
        return conn.execute(
            """UPDATE delivery_outbox
                  SET state='delivered', delivered_at=?, external_message_id=?,
                      claim_owner='', claim_token='', lease_until=0
                WHERE id=? AND state='claimed' AND claim_token=?
               RETURNING id""",
            (int(time.time()), external_id, delivery_id, token),
        ).fetchone()


def release(path, delivery_id, token):
    with connect(path) as conn:
        return conn.execute(
            """UPDATE delivery_outbox
                  SET state='ready', claim_owner='', claim_token='', lease_until=0,
                      available_at=?, last_error='simulated_send_failure'
                WHERE id=? AND state='claimed' AND claim_token=?
               RETURNING id""",
            (int(time.time()), delivery_id, token),
        ).fetchone()


def claim_trace(path, session_id, owner, token, lease_seconds):
    now = int(time.time())
    with connect(path) as conn:
        return conn.execute(
            """UPDATE trace_events
                  SET claim_owner=?, claim_token=?, lease_until=?, attempts=attempts+1,
                      last_error=''
                WHERE id=(
                      SELECT id FROM trace_events
                       WHERE session_id=? AND sent=0 AND event_type!='final_reply'
                         AND ((claim_token='' AND available_at<=?)
                              OR (claim_token!='' AND lease_until<=?))
                       ORDER BY id LIMIT 1
                )
                  AND sent=0
                  AND ((claim_token='' AND available_at<=?)
                       OR (claim_token!='' AND lease_until<=?))
             RETURNING id, claim_token""",
            (owner, token, now + lease_seconds, session_id,
             now, now, now, now),
        ).fetchone()


def ack_trace(path, trace_id, token):
    with connect(path) as conn:
        return conn.execute(
            """UPDATE trace_events
                  SET sent=1, claim_owner='', claim_token='', lease_until=0,
                      last_error=''
                WHERE id=? AND sent=0 AND claim_token=?
             RETURNING id""",
            (trace_id, token),
        ).fetchone()


def release_trace(path, trace_id, token):
    with connect(path) as conn:
        return conn.execute(
            """UPDATE trace_events
                  SET claim_owner='', claim_token='', lease_until=0,
                      available_at=?, last_error='simulated_surface_failure'
                WHERE id=? AND sent=0 AND claim_token=?
             RETURNING id""",
            (int(time.time()), trace_id, token),
        ).fetchone()


def webui_receipt(namespace, row_id, durable_identity):
    digest = hashlib.sha256(
        f"{namespace}|{row_id}|{durable_identity}".encode("utf-8")
    ).hexdigest()
    return f"{namespace}:{row_id}:{digest}"


class DeliveryProtocolTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory(prefix="ernos-delivery-")
        self.db_path = str(Path(self.tempdir.name) / "node.db")
        now = int(time.time())
        with connect(self.db_path) as conn:
            conn.executescript(SCHEMA)
            conn.execute(
                "INSERT INTO delivery_turns VALUES (?,?,?,?,?,?,?,?)",
                ("turn-test", "session-test", "discord", "1|2|3", "awaiting_delivery", now, now, ""),
            )
            conn.execute(
                """INSERT INTO delivery_outbox
                   (turn_id,sequence,surface,destination,kind,payload,terminal,state,
                    available_at,created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                ("turn-test", 1, "discord", "1|2|3", "final", "payload", 1, "ready", now, now),
            )
            conn.execute(
                """INSERT INTO trace_events
                   (session_id,event_type,content,created_at)
                   VALUES ('session-test','mid_message','visible note',?)""",
                (now,),
            )
            conn.execute(
                """INSERT INTO trace_events
                   (session_id,event_type,content,created_at)
                   VALUES ('session-test','final_reply','must stay out of trace',?)""",
                (now,),
            )

    def tearDown(self):
        self.tempdir.cleanup()

    def test_atomic_claim_has_one_winner(self):
        barrier = threading.Barrier(3)

        def contender(name):
            barrier.wait(timeout=5)
            return claim(self.db_path, "turn-test", name, f"token-{name}", 10)

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(contender, name) for name in ("a", "b")]
            barrier.wait(timeout=5)
            # Calling result() is deliberate: worker exceptions must fail unittest.
            results = [future.result(timeout=15) for future in futures]

        self.assertEqual(sum(row is not None for row in results), 1)
        with connect(self.db_path) as conn:
            self.assertEqual(conn.execute("SELECT state FROM delivery_outbox").fetchone()[0], "claimed")

    def test_empty_external_receipt_cannot_mark_delivered(self):
        first = claim(self.db_path, "turn-test", "sender", "sender-token", 10)
        self.assertIsNotNone(first)
        delivery_id = first[0]
        self.assertIsNone(ack(self.db_path, delivery_id, "sender-token", ""))
        with connect(self.db_path) as conn:
            state, external_id = conn.execute(
                "SELECT state, external_message_id FROM delivery_outbox"
            ).fetchone()
        self.assertEqual((state, external_id), ("claimed", ""))

    def test_ipc_handler_never_invents_an_external_receipt(self):
        node_source = (REPO_ROOT / "node.ep").read_text(encoding="utf-8")
        self.assertIn("missing_external_receipt", node_source)
        self.assertNotIn('set dia_external to "ipc:client_confirmed"', node_source)

    def test_slow_send_heartbeat_prevents_lease_reclaim(self):
        first = claim(self.db_path, "turn-test", "sender", "sender-token", 2)
        self.assertIsNotNone(first)
        delivery_id = first[0]
        stop = threading.Event()
        heartbeat_errors = []

        def heartbeat():
            try:
                while not stop.wait(0.2):
                    renewed = renew(self.db_path, delivery_id, "sender-token", 2)
                    if renewed is None:
                        raise AssertionError("delivery lease renewal lost its exact claim")
            except BaseException as exc:
                heartbeat_errors.append(f"{type(exc).__name__}: {exc}")

        heart = threading.Thread(target=heartbeat)
        heart.start()
        # The external send lasts beyond the original lease. A restart consumer must
        # still lose because token-checked heartbeats extend ownership.
        try:
            time.sleep(2.5)
            stolen = claim(self.db_path, "turn-test", "recovery", "recovery-token", 2)
        finally:
            stop.set()
            heart.join(timeout=5)
        self.assertFalse(heart.is_alive(), "delivery heartbeat thread did not stop")
        self.assertEqual(heartbeat_errors, [], "delivery heartbeat failed")
        self.assertIsNone(stolen)
        self.assertIsNotNone(ack(self.db_path, delivery_id, "sender-token", "discord:confirmed"))
        with connect(self.db_path) as conn:
            state, external_id = conn.execute(
                "SELECT state, external_message_id FROM delivery_outbox"
            ).fetchone()
        self.assertEqual((state, external_id), ("delivered", "discord:confirmed"))

    def test_failed_send_releases_then_restart_recovers(self):
        first = claim(self.db_path, "turn-test", "old-process", "old-token", 10)
        self.assertIsNotNone(first)
        delivery_id = first[0]

        # No ACK occurs on the failure path.
        self.assertIsNotNone(release(self.db_path, delivery_id, "old-token"))
        with connect(self.db_path) as conn:
            state, delivered_at = conn.execute(
                "SELECT state, delivered_at FROM delivery_outbox"
            ).fetchone()
        self.assertEqual((state, delivered_at), ("ready", 0))

        recovered = claim(self.db_path, "turn-test", "new-process", "new-token", 10)
        self.assertIsNotNone(recovered)
        # Model the bridge ordering contract: external API confirms first, ACK second.
        events = ["external_send_confirmed"]
        self.assertIsNotNone(ack(self.db_path, delivery_id, "new-token", "discord:recovered"))
        events.append("outbox_delivered")
        self.assertEqual(events, ["external_send_confirmed", "outbox_delivered"])
        with connect(self.db_path) as conn:
            state, attempts = conn.execute(
                "SELECT state, attempts FROM delivery_outbox"
            ).fetchone()
        self.assertEqual((state, attempts), ("delivered", 2))

    def test_webui_socket_write_without_browser_receipt_is_not_delivered(self):
        with connect(self.db_path) as conn:
            conn.execute("UPDATE delivery_turns SET surface='webui'")
            conn.execute("UPDATE delivery_outbox SET surface='webui'")

        first = claim(
            self.db_path, "turn-test", "web-old", "web-old-token", 10,
            surface="webui",
        )
        self.assertIsNotNone(first)
        delivery_id = first[0]

        # Kernel acceptance of begin/content/commit frames is not a browser receipt.
        events = ["websocket_frames_written"]
        with connect(self.db_path) as conn:
            state, delivered_at = conn.execute(
                "SELECT state, delivered_at FROM delivery_outbox"
            ).fetchone()
        self.assertEqual((state, delivered_at), ("claimed", 0))

        # Missing/mismatched receipt releases the exact claim; a restart reclaims it.
        self.assertIsNotNone(release(self.db_path, delivery_id, "web-old-token"))
        events.append("claim_released_without_delivery")
        recovered = claim(
            self.db_path, "turn-test", "web-restart", "web-new-token", 10,
            surface="webui",
        )
        self.assertIsNotNone(recovered)
        stable_receipt = webui_receipt("outbox", delivery_id, "turn-test|1")
        self.assertIsNotNone(
            ack(
                self.db_path, delivery_id, "web-new-token",
                f"webui-receipt:{stable_receipt}",
            )
        )
        events.extend(["browser_receipt", "outbox_delivered"])
        self.assertEqual(
            events,
            ["websocket_frames_written", "claim_released_without_delivery",
             "browser_receipt", "outbox_delivered"],
        )

    def test_webui_crash_after_browser_receipt_replays_idempotently(self):
        with connect(self.db_path) as conn:
            conn.execute("UPDATE delivery_turns SET surface='webui'")
            conn.execute("UPDATE delivery_outbox SET surface='webui'")

        first = claim(
            self.db_path, "turn-test", "web-before-crash", "web-crash-token", 10,
            surface="webui",
        )
        self.assertIsNotNone(first)
        delivery_id = first[0]
        stable_receipt = webui_receipt("outbox", delivery_id, "turn-test|1")

        # The browser applies once and persists the stable receipt, then the server
        # crashes before storage_delivery_ack. The row remains claimed, not delivered.
        browser_receipts = {stable_receipt}
        render_count = 1
        with connect(self.db_path) as conn:
            self.assertEqual(
                conn.execute("SELECT state FROM delivery_outbox").fetchone()[0],
                "claimed",
            )
            conn.execute("UPDATE delivery_outbox SET lease_until=0")

        recovered = claim(
            self.db_path, "turn-test", "web-after-crash", "web-recovery-token", 10,
            surface="webui",
        )
        self.assertIsNotNone(recovered)
        recovered_receipt = webui_receipt("outbox", recovered[0], "turn-test|1")
        if recovered_receipt not in browser_receipts:
            render_count += 1
            browser_receipts.add(recovered_receipt)
        self.assertEqual(render_count, 1, "recovery re-applied an acknowledged browser unit")
        self.assertIsNotNone(
            ack(
                self.db_path, delivery_id, "web-recovery-token",
                f"webui-receipt:{recovered_receipt}",
            )
        )
        with connect(self.db_path) as conn:
            state, attempts, external_id = conn.execute(
                "SELECT state, attempts, external_message_id FROM delivery_outbox"
            ).fetchone()
        self.assertEqual(
            (state, attempts, external_id),
            ("delivered", 2, f"webui-receipt:{stable_receipt}"),
        )

    def test_trace_claim_is_exclusive_and_ack_follows_surface_write(self):
        barrier = threading.Barrier(3)

        def contender(name):
            barrier.wait(timeout=5)
            return claim_trace(
                self.db_path, "session-test", name,
                f"trace-token-{name}", 10,
            )

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(contender, name) for name in ("a", "b")]
            barrier.wait(timeout=5)
            # Calling result() is deliberate: worker exceptions must fail unittest.
            results = [future.result(timeout=15) for future in futures]

        self.assertEqual(sum(row is not None for row in results), 1)
        winner = next(row for row in results if row is not None)
        trace_id, token = winner
        with connect(self.db_path) as conn:
            self.assertEqual(
                conn.execute("SELECT sent FROM trace_events WHERE id=?", (trace_id,)).fetchone()[0],
                0,
            )
        events = ["surface_write_confirmed"]
        with connect(self.db_path) as conn:
            self.assertEqual(
                conn.execute("SELECT sent FROM trace_events WHERE id=?", (trace_id,)).fetchone()[0],
                0,
                "trace row was marked sent before the browser receipt",
            )
        events.append("browser_receipt")
        self.assertIsNotNone(ack_trace(self.db_path, trace_id, token))
        events.append("trace_sent")
        self.assertEqual(
            events,
            ["surface_write_confirmed", "browser_receipt", "trace_sent"],
        )
        with connect(self.db_path) as conn:
            legacy_reply = conn.execute(
                "SELECT sent, claim_token FROM trace_events WHERE event_type='final_reply'"
            ).fetchone()
        self.assertEqual(legacy_reply, (0, ""))

    def test_trace_failed_write_releases_for_retry(self):
        first = claim_trace(
            self.db_path, "session-test", "failed-sender", "trace-old-token", 10
        )
        self.assertIsNotNone(first)
        trace_id = first[0]
        self.assertIsNone(ack_trace(self.db_path, trace_id, "wrong-token"))
        self.assertIsNotNone(
            release_trace(self.db_path, trace_id, "trace-old-token")
        )
        with connect(self.db_path) as conn:
            sent, owner_token, last_error = conn.execute(
                "SELECT sent, claim_token, last_error FROM trace_events WHERE id=?",
                (trace_id,),
            ).fetchone()
        self.assertEqual((sent, owner_token, last_error),
                         (0, "", "simulated_surface_failure"))
        recovered = claim_trace(
            self.db_path, "session-test", "restart", "trace-new-token", 10
        )
        self.assertIsNotNone(recovered)
        self.assertEqual(recovered[0], trace_id)
        self.assertIsNone(ack_trace(self.db_path, trace_id, "trace-old-token"))
        self.assertIsNotNone(
            ack_trace(self.db_path, trace_id, "trace-new-token")
        )


if __name__ == "__main__":
    unittest.main()
