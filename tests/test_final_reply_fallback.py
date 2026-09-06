import ast
import asyncio
import hashlib
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


BRIDGE_PATH = Path(__file__).resolve().parents[1] / "decent_net" / "discord_bridge.py"


def load_fallback_functions():
    tree = ast.parse(BRIDGE_PATH.read_text(encoding="utf-8"), filename=str(BRIDGE_PATH))
    wanted = {
        "_final_reply_fallback_path",
        "_consume_final_reply_fallback",
        "_claim_final_reply_trace",
        "_trace_turn_is_active",
        "wait_final_reply",
        "extract_ai_ok_response",
        "extract_upgrade_wake_response",
    }
    body = [
        node for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in wanted
    ]
    namespace = {"asyncio": asyncio, "hashlib": hashlib, "os": os, "sqlite3": sqlite3}
    exec(compile(ast.Module(body=body, type_ignores=[]), str(BRIDGE_PATH), "exec"), namespace)
    return namespace


class FinalReplyFallbackTest(unittest.TestCase):
    def test_exact_correlated_payload_is_consumed_once(self):
        funcs = load_fallback_functions()
        with tempfile.TemporaryDirectory() as home, patch.dict(os.environ, {"HOME": home}):
            path = Path(funcs["_final_reply_fallback_path"]("session-a", "t_nonce"))
            path.parent.mkdir(parents=True)
            path.write_text("turn:t_nonce,ai:ok|||RESPONSE|||recovered", encoding="utf-8")
            recovered = funcs["_consume_final_reply_fallback"]("session-a", "t_nonce")
            self.assertEqual(recovered, "ai:ok|||RESPONSE|||recovered")
            self.assertFalse(path.exists())
            self.assertIsNone(funcs["_consume_final_reply_fallback"]("session-a", "t_nonce"))

    def test_mismatched_payload_is_not_delivered_or_deleted(self):
        funcs = load_fallback_functions()
        with tempfile.TemporaryDirectory() as home, patch.dict(os.environ, {"HOME": home}):
            path = Path(funcs["_final_reply_fallback_path"]("session-a", "t_expected"))
            path.parent.mkdir(parents=True)
            path.write_text("turn:t_wrong,ai:ok|||RESPONSE|||wrong", encoding="utf-8")
            self.assertIsNone(funcs["_consume_final_reply_fallback"]("session-a", "t_expected"))
            self.assertTrue(path.exists())

    def test_only_correlated_upgrade_wake_reply_is_unsolicited(self):
        funcs = load_fallback_functions()
        extract = funcs["extract_upgrade_wake_response"]
        self.assertEqual(
            extract("turn:upgrade_wake_ab12,ai:ok|||RESPONSE|||Committed and healthy."),
            "Committed and healthy.",
        )
        self.assertIsNone(extract("turn:t_user,ai:ok|||RESPONSE|||ordinary reply"))
        self.assertIsNone(extract("ai:ok|||RESPONSE|||uncorrelated reply"))

    def test_trace_reply_claim_and_active_turn_are_exactly_correlated(self):
        funcs = load_fallback_functions()
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "node.db"
            conn = sqlite3.connect(db_path)
            conn.execute(
                "CREATE TABLE trace_events (id INTEGER PRIMARY KEY, session_id TEXT, event_type TEXT, content TEXT, sent INTEGER)"
            )
            conn.execute(
                "CREATE TABLE trace_active_turns (session_id TEXT, turn_id TEXT, created_at INTEGER, PRIMARY KEY(session_id, turn_id))"
            )
            conn.execute(
                "INSERT INTO trace_events VALUES (1, 'session-a', 'final_reply', 'turn:t_other,wrong', 0)"
            )
            conn.execute(
                "INSERT INTO trace_events VALUES (2, 'session-a', 'final_reply', 'turn:t_exact,ai:ok|||RESPONSE|||right', 0)"
            )
            conn.execute("INSERT INTO trace_active_turns VALUES ('session-a', 't_exact', 1)")
            conn.commit()
            conn.close()
            funcs["get_db_path"] = lambda: str(db_path)
            self.assertTrue(funcs["_trace_turn_is_active"]("session-a", "t_exact"))
            self.assertFalse(funcs["_trace_turn_is_active"]("session-a", "t_other"))
            self.assertEqual(
                funcs["_claim_final_reply_trace"]("session-a", "t_exact"),
                "ai:ok|||RESPONSE|||right",
            )
            self.assertIsNone(funcs["_claim_final_reply_trace"]("session-a", "t_exact"))
            remaining = sqlite3.connect(db_path).execute(
                "SELECT sent FROM trace_events WHERE id=1"
            ).fetchone()[0]
            self.assertEqual(remaining, 0)


class FinalReplyLifetimeTest(unittest.IsolatedAsyncioTestCase):
    async def test_terminal_row_after_legacy_timeout_is_still_delivered(self):
        funcs = load_fallback_functions()
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"HOME": tmp}):
            db_path = Path(tmp) / "node.db"
            conn = sqlite3.connect(db_path)
            conn.execute(
                "CREATE TABLE trace_events (id INTEGER PRIMARY KEY, session_id TEXT, event_type TEXT, content TEXT, sent INTEGER)"
            )
            conn.execute(
                "CREATE TABLE trace_active_turns (session_id TEXT, turn_id TEXT, created_at INTEGER, PRIMARY KEY(session_id, turn_id))"
            )
            conn.commit()
            conn.close()
            funcs["get_db_path"] = lambda: str(db_path)

            async def commit_after_deadline():
                await asyncio.sleep(0.05)
                writer = sqlite3.connect(db_path)
                writer.execute(
                    "INSERT INTO trace_events VALUES (1, 'session-a', 'final_reply', 'turn:t_exact,ai:ok|||RESPONSE|||late-but-valid', 0)"
                )
                writer.commit()
                writer.close()

            writer_task = asyncio.create_task(commit_after_deadline())
            result = await funcs["wait_final_reply"]("session-a", timeout_s=0.01, turn_tag="t_exact")
            await writer_task
            self.assertEqual(result, "ai:ok|||RESPONSE|||late-but-valid")

    def test_active_turn_delivery_has_no_wall_clock_terminal_error(self):
        source = BRIDGE_PATH.read_text(encoding="utf-8")
        function = next(
            node for node in ast.parse(source).body
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "wait_final_reply"
        )
        rendered = ast.unparse(function)
        self.assertNotIn("turn_timeout", rendered)
        self.assertNotIn("hard_deadline", rendered)
        self.assertNotIn("monotonic", rendered)

    def test_web_delivery_has_no_active_turn_deadline(self):
        web_source = (BRIDGE_PATH.parents[1] / "decent_web" / "web_server.ep").read_text(encoding="utf-8")
        start = web_source.index("define web_wait_final_reply")
        end = web_source.index("define web_resolve_ai_response", start)
        function = web_source[start:end]
        self.assertNotIn("turn_timeout", function)
        self.assertNotIn("1800000", function)


if __name__ == "__main__":
    unittest.main()
