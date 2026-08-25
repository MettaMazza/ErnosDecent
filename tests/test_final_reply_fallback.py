import ast
import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


BRIDGE_PATH = Path(__file__).resolve().parents[1] / "decent_net" / "discord_bridge.py"


def load_fallback_functions():
    tree = ast.parse(BRIDGE_PATH.read_text(encoding="utf-8"), filename=str(BRIDGE_PATH))
    wanted = {"_final_reply_fallback_path", "_consume_final_reply_fallback"}
    body = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in wanted]
    namespace = {"hashlib": hashlib, "os": os}
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


if __name__ == "__main__":
    unittest.main()
