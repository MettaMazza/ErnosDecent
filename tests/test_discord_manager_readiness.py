import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "decent_net" / "discord_manager.py"
SPEC = importlib.util.spec_from_file_location("discord_manager_readiness", MODULE_PATH)
discord_manager = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(discord_manager)


class FakeProcess:
    def __init__(self, return_code=None):
        self.return_code = return_code
        self.terminated = False
        self.killed = False

    def poll(self):
        return self.return_code

    def terminate(self):
        self.terminated = True
        self.return_code = 0

    def kill(self):
        self.killed = True
        self.return_code = -9

    def wait(self, timeout=None):
        if self.return_code is None:
            raise subprocess.TimeoutExpired("fake", timeout)
        return self.return_code


class DiscordManagerReadinessTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.config_path = Path(self.tempdir.name) / "platforms.json"
        self.log_path = Path(self.tempdir.name) / "discord.log"
        self.config_patch = mock.patch.object(discord_manager, "CONFIG_PATH", str(self.config_path))
        self.log_patch = mock.patch.object(discord_manager, "LOG_PATH", str(self.log_path))
        self.config_patch.start()
        self.log_patch.start()
        self.addCleanup(self.config_patch.stop)
        self.addCleanup(self.log_patch.stop)

    def write_config(self, discord):
        self.config_path.write_text(json.dumps({"discord": discord}), encoding="utf-8")

    def test_disabled_bridge_persists_verified_offline(self):
        self.write_config({"enabled": False, "token": "", "channel": "", "status": "ONLINE"})
        with mock.patch.object(discord_manager, "kill_existing_bridge", return_value=True):
            result = discord_manager.main([])
        saved = json.loads(self.config_path.read_text(encoding="utf-8"))
        self.assertEqual(result, 0)
        self.assertEqual(saved["discord"]["status"], "OFFLINE")

    def test_enabled_bridge_clears_stale_online_and_fails_without_ack(self):
        self.write_config({"enabled": True, "token": "secret", "channel": "123", "status": "ONLINE"})
        process = FakeProcess()
        with mock.patch.object(discord_manager, "kill_existing_bridge", return_value=True), \
             mock.patch.object(discord_manager.subprocess, "Popen", return_value=process), \
             mock.patch.object(discord_manager, "wait_for_bridge_ready", return_value=False):
            result = discord_manager.main([])
        saved = json.loads(self.config_path.read_text(encoding="utf-8"))
        self.assertEqual(result, 1)
        self.assertEqual(saved["discord"]["status"], "OFFLINE")
        self.assertTrue(process.terminated)

    def test_controlled_node_restart_preserves_single_live_bridge(self):
        self.write_config({"enabled": True, "token": "secret", "channel": "123", "status": "ONLINE"})
        with mock.patch.dict(os.environ, {"ERNOS_PRESERVE_DISCORD_BRIDGE": "1"}), \
             mock.patch.object(discord_manager, "find_existing_bridge_pids", return_value=[4321]), \
             mock.patch.object(discord_manager, "kill_existing_bridge") as kill_bridge, \
             mock.patch.object(discord_manager.subprocess, "Popen") as popen:
            result = discord_manager.main([])
        self.assertEqual(result, 0)
        kill_bridge.assert_not_called()
        popen.assert_not_called()

    def test_wait_accepts_only_live_process_with_online_ack(self):
        self.write_config({"enabled": True, "token": "secret", "channel": "123", "status": "ONLINE"})
        self.assertTrue(discord_manager.wait_for_bridge_ready(FakeProcess(), timeout_seconds=0.1))

    def test_wait_rejects_process_exit_before_ack(self):
        self.write_config({"enabled": True, "token": "secret", "channel": "123", "status": "OFFLINE"})
        self.assertFalse(discord_manager.wait_for_bridge_ready(FakeProcess(return_code=2), timeout_seconds=0.1))

    def test_malformed_config_fails_without_overwrite(self):
        malformed = "{not-json"
        self.config_path.write_text(malformed, encoding="utf-8")
        result = discord_manager.main([])
        self.assertEqual(result, 1)
        self.assertEqual(self.config_path.read_text(encoding="utf-8"), malformed)

    def test_selected_ipc_port_is_passed_only_through_child_environment(self):
        self.write_config({"enabled": True, "token": "secret", "channel": "123", "status": "OFFLINE"})
        process = FakeProcess()
        with mock.patch.object(discord_manager, "kill_existing_bridge", return_value=True), \
             mock.patch.object(discord_manager.subprocess, "Popen", return_value=process) as popen, \
             mock.patch.object(discord_manager, "wait_for_bridge_ready", return_value=True):
            result = discord_manager.main(["--ipc-port", "6123"])
        self.assertEqual(result, 0)
        args, kwargs = popen.call_args
        self.assertEqual(args[0], ["python3", discord_manager.BRIDGE_SCRIPT])
        self.assertEqual(kwargs["env"]["ERNOS_IPC_PORT"], "6123")


if __name__ == "__main__":
    unittest.main()
