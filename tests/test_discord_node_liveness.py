import ast
import asyncio
import unittest
from pathlib import Path


BRIDGE_PATH = Path(__file__).resolve().parents[1] / "decent_net" / "discord_bridge.py"


class FakeStatus:
    online = "online"
    invisible = "invisible"


class FakeClient:
    def __init__(self):
        self.presence = []

    async def change_presence(self, status):
        self.presence.append(status)


def load_liveness(responses, status_updates):
    tree = ast.parse(BRIDGE_PATH.read_text(encoding="utf-8"), filename=str(BRIDGE_PATH))
    names = {
        "_node_health_response_ok",
        "_publish_node_coupled_status",
        "node_liveness_step",
    }
    functions = [
        node for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names
    ]
    client = FakeClient()

    async def send_daemon_ipc(_command):
        return responses.pop(0)

    namespace = {
        "_node_coupled_online": None,
        "asyncio": asyncio,
        "client": client,
        "discord": type("Discord", (), {"Status": FakeStatus}),
        "send_daemon_ipc": send_daemon_ipc,
        "update_status": status_updates.append,
    }
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(BRIDGE_PATH), "exec"), namespace)
    return namespace, client


def load_reconciliation(results, supervisor_states):
    tree = ast.parse(BRIDGE_PATH.read_text(encoding="utf-8"), filename=str(BRIDGE_PATH))
    function = next(
        node for node in tree.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "_wait_for_learning_reconciliation"
    )

    async def learning_controller(_command):
        return results.pop(0)

    def supervisor_alive():
        return supervisor_states.pop(0)

    namespace = {
        "asyncio": asyncio,
        "_learning_controller": learning_controller,
        "_node_supervisor_alive": supervisor_alive,
    }
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(BRIDGE_PATH), "exec"), namespace)
    return namespace["_wait_for_learning_reconciliation"]


class DiscordNodeLivenessTests(unittest.IsolatedAsyncioTestCase):
    async def test_online_requires_authenticated_node_health_and_tracks_loss_and_recovery(self):
        updates = []
        health = (
            "health:standalone,timestamp:1,checks:25,agent:healthy,"
            "network:healthy,ipc:healthy"
        )
        namespace, client = load_liveness(
            [health, "error:daemon_offline", health], updates
        )

        self.assertTrue(await namespace["node_liveness_step"]())
        self.assertFalse(await namespace["node_liveness_step"]())
        self.assertTrue(await namespace["node_liveness_step"]())
        self.assertEqual(updates, ["ONLINE", "OFFLINE", "ONLINE"])
        self.assertEqual(client.presence, ["online", "invisible", "online"])

    async def test_incomplete_or_unauthenticated_responses_never_publish_online(self):
        updates = []
        namespace, client = load_liveness(
            ["status:active", "health:standalone,ipc:healthy", ""], updates
        )

        self.assertFalse(await namespace["node_liveness_step"]())
        self.assertFalse(await namespace["node_liveness_step"]())
        self.assertFalse(await namespace["node_liveness_step"]())
        self.assertEqual(updates, ["OFFLINE"])
        self.assertEqual(client.presence, ["invisible"])

    async def test_learning_waits_for_the_exact_transaction_commit(self):
        target = "target-transaction"
        wait = load_reconciliation(
            [
                {"active": None, "pending_activation": {"transaction_id": target}},
                {"active": {"transaction_id": target}, "pending_activation": None},
            ],
            [True],
        )
        result = await wait(target)
        self.assertEqual(result["active"]["transaction_id"], target)

    async def test_old_active_version_cannot_mask_target_failure(self):
        target = "target-transaction"
        wait = load_reconciliation(
            [
                {
                    "active": {"transaction_id": "previous-transaction"},
                    "active_version": 7,
                    "pending_activation": {"transaction_id": target},
                },
                {
                    "active": {"transaction_id": "previous-transaction"},
                    "active_version": 7,
                    "pending_activation": None,
                },
            ],
            [True],
        )
        self.assertIsNone(await wait(target))


if __name__ == "__main__":
    unittest.main()
