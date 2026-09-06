#!/usr/bin/env python3
"""Regression tests for the transactional self-recompile/deployment contract."""

from __future__ import annotations

import hashlib
import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]


class UpgradeFixture:
    def __init__(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="ernos-upgrade-")
        self.root = Path(self.temp.name)
        shutil.copy2(REPO / "upgrade.sh", self.root / "upgrade.sh")
        (self.root / "upgrade.sh").chmod(0o755)
        self._write_executable(self.root / "node", b"old-node\n")
        build = """#!/bin/bash
set -eu
if [ -f FAIL_BUILD ]; then
  echo 'injected build failure' >&2
  exit 23
fi
if [ "${1:-}" = "test" ]; then
  echo 'test gate passed'
  exit 0
fi
[ -n "${ERNOS_NODE_OUTPUT:-}" ]
printf 'candidate-node\\n' > "$ERNOS_NODE_OUTPUT"
chmod 755 "$ERNOS_NODE_OUTPUT"
"""
        (self.root / "build.sh").write_text(build, encoding="utf-8")
        (self.root / "build.sh").chmod(0o755)
        scripts = self.root / "scripts"
        scripts.mkdir()
        gate_runner = """#!/bin/bash
set -eu
echo '[mandatory-gate] integrity verified for fixture files.'
[ "${1:-}" = "--verify-only" ] && exit 0
bash build.sh test
"""
        (scripts / "run_mandatory_regressions.sh").write_text(
            gate_runner, encoding="utf-8"
        )
        (scripts / "run_mandatory_regressions.sh").chmod(0o755)
        state = self.root / "config" / "upgrades"
        state.mkdir(parents=True)
        manifest = state / "mandatory-regressions.sha256"
        manifest.write_text("version=1\n", encoding="utf-8")
        seal_dir = self.root / "fixture-home" / ".ernosdecent"
        seal_dir.mkdir(parents=True)
        (seal_dir / "mandatory-regressions.seal").write_text(
            hashlib.sha256(manifest.read_bytes()).hexdigest() + "\n",
            encoding="ascii",
        )

    @staticmethod
    def _write_executable(path: Path, data: bytes) -> None:
        path.write_bytes(data)
        path.chmod(path.stat().st_mode | stat.S_IXUSR)

    def run(self, *args: str, expected: int = 0) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            ["bash", "upgrade.sh", *args],
            cwd=self.root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=20,
            check=False,
            env={**os.environ, "HOME": str(self.root / "fixture-home")},
        )
        if result.returncode != expected:
            raise AssertionError(
                f"upgrade.sh {' '.join(args)} returned {result.returncode}, "
                f"expected {expected}:\n{result.stdout}"
            )
        return result

    def close(self) -> None:
        self.temp.cleanup()


class TransactionalUpgradeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fx = UpgradeFixture()

    def tearDown(self) -> None:
        self.fx.close()

    def test_success_path_never_changes_live_node_before_activation(self) -> None:
        old = (self.fx.root / "node").read_bytes()
        prepared = self.fx.run("prepare")
        self.assertIn("PREPARE_OK", prepared.stdout)
        self.assertEqual((self.fx.root / "node").read_bytes(), old)

        change_id = "a" * 64
        staged = self.fx.run("stage", change_id)
        self.assertIn(f"change_id={change_id}", staged.stdout)
        self.assertEqual((self.fx.root / "node").read_bytes(), old)

        self.fx.run("activate")
        self.assertEqual((self.fx.root / "node").read_bytes(), b"candidate-node\n")
        outcome = self.fx.run("success")
        self.assertIn("status=applied", outcome.stdout)
        receipt = (self.fx.root / "config/upgrades/outcome.env").read_text()
        self.assertIn(f"change_id={change_id}", receipt)
        self.assertIn("status=applied", receipt)

    def test_failed_candidate_restores_exact_old_executable(self) -> None:
        old = (self.fx.root / "node").read_bytes()
        old_hash = hashlib.sha256(old).hexdigest()
        self.fx.run("prepare")
        self.fx.run("stage", "b" * 64)
        self.fx.run("activate")
        self.fx.run("rollback")
        self.assertEqual((self.fx.root / "node").read_bytes(), old)
        self.assertEqual(hashlib.sha256((self.fx.root / "node").read_bytes()).hexdigest(), old_hash)
        outcome = self.fx.run("failure", "injected_health_failure")
        self.assertIn("status=failed", outcome.stdout)

    def test_build_failure_creates_no_prepared_or_pending_transaction(self) -> None:
        (self.fx.root / "FAIL_BUILD").write_text("1\n", encoding="utf-8")
        result = self.fx.run("prepare", expected=1)
        self.assertIn("test gate failed", result.stdout)
        self.assertFalse((self.fx.root / "config/upgrades/prepared.env").exists())
        self.assertFalse((self.fx.root / "config/upgrades/pending.env").exists())
        self.assertFalse((self.fx.root / "config/upgrades/prepare.lock").exists())
        self.assertEqual(
            list((self.fx.root / "config/upgrades").glob("*.tmp.*")), []
        )
        self.assertNotIn("unbound variable", result.stdout)
        self.assertEqual((self.fx.root / "node").read_bytes(), b"old-node\n")

    def test_tampered_candidate_is_rejected_before_activation(self) -> None:
        self.fx.run("prepare")
        self.fx.run("stage", "c" * 64)
        candidate = self.fx.root / "config/upgrades/candidate.node"
        candidate.write_bytes(candidate.read_bytes() + b"tampered")
        result = self.fx.run("activate", expected=1)
        self.assertIn("candidate hash mismatch", result.stdout)
        self.assertEqual((self.fx.root / "node").read_bytes(), b"old-node\n")

    def test_gate_manifest_change_is_rejected_before_staging(self) -> None:
        self.fx.run("prepare")
        manifest = self.fx.root / "config" / "upgrades" / "mandatory-regressions.sha256"
        manifest.write_text("version=1\ntampered\n", encoding="utf-8")
        result = self.fx.run("stage", "d" * 64, expected=1)
        self.assertIn("manifest differs from the operator seal", result.stdout)
        self.assertFalse(
            (self.fx.root / "config" / "upgrades" / "pending.env").exists()
        )
        self.assertEqual((self.fx.root / "node").read_bytes(), b"old-node\n")

    def test_runtime_supervisor_owns_replacement_and_health_commit(self) -> None:
        upgrade = (REPO / "upgrade.sh").read_text(encoding="utf-8")
        supervisor = (REPO / "run_node.sh").read_text(encoding="utf-8")
        build = (REPO / "build.sh").read_text(encoding="utf-8")
        compiler = (REPO / "decent_agent/compiler_tool.ep").read_text(encoding="utf-8")
        react = (REPO / "decent_agent/react_loop.ep").read_text(encoding="utf-8")
        rights = (REPO / "decent_agent/rights.ep").read_text(encoding="utf-8")
        node = (REPO / "node.ep").read_text(encoding="utf-8")
        bridge = (REPO / "decent_net/discord_bridge.py").read_text(encoding="utf-8")

        self.assertNotIn("kill -9", upgrade)
        self.assertNotIn("nohup ./node", upgrade)
        self.assertNotIn("node_next", compiler)
        self.assertNotIn("resume.json", compiler)
        self.assertIn("ernos-node-compile", build)
        self.assertIn('ERNOS_NODE_OUTPUT:-./node', build)
        self.assertNotIn("$ERNOS node.ep 2>&1", build)
        self.assertIn('ipc_cmd 5 "UPGRADE RECONCILE"', supervisor)
        self.assertIn("wait_for_node_health", supervisor)
        self.assertIn("improvement_test_gate.py live", supervisor)
        self.assertIn("improvement_test_gate.py complete", supervisor)
        self.assertIn('map_insert(ctx and "repair_gate_call_repeats"', react)
        self.assertNotIn("Repeated identical repair-gate violation; halted without execution", react)
        self.assertIn("Action: improvement_test_scaffold([])", react)
        self.assertIn("Action: improvement_test_validate([])", react)
        self.assertIn("Action: improvement_test_freeze([])", react)
        self.assertLess(
            supervisor.index("improvement_test_gate.py live"),
            supervisor.index("bash upgrade.sh success"),
        )
        self.assertIn("bash upgrade.sh rollback", supervisor)
        self.assertIn("verify_operator_regression_gate", supervisor)
        self.assertIn("run_mandatory_regressions.sh", upgrade)
        self.assertIn("gate_manifest_hash", upgrade)
        self.assertIn("define rights_reconcile_upgrade", rights)
        self.assertIn("define node_upgrade_wake_create", node)
        self.assertIn("define node_upgrade_wake_dispatch", node)
        self.assertIn('set ok to map_insert(tctx and "upgrade_wake" and 1)', node)
        self.assertIn('set ok to map_insert(tctx and "improvement_recovery_wake" and 1)', node)
        self.assertIn("[AUTHENTICATED POST-RECOMPILE WAKE EVENT]", node)
        self.assertIn("[AUTHENTICATED POST-ROLLBACK IMPROVEMENT RECOVERY]", node)
        self.assertIn("Rollback is temporary containment, not completion", node)
        self.assertIn("improvement_e2e_hash=", node)
        self.assertIn("improvement_live_hash=", node)
        self.assertIn("improvement_live_status=", node)
        self.assertIn("improvement_failure_fingerprint=", node)
        self.assertIn(
            "set improvement_failure_attempt to int_to_string(get_json_value(improvement_failure_attempt_node))",
            node,
        )
        self.assertIn("Never claim a file or capability beyond this receipt", node)
        self.assertIn("record-failure --detail replacement_failed_authenticated_health", supervisor)
        self.assertIn("record-failure --detail frozen_improvement_live_e2e_failed", supervisor)
        tools_source = (REPO / "decent_agent/tools.ep").read_text(encoding="utf-8")
        self.assertIn("proposed source bytes are identical to the current file", tools_source)
        self.assertIn('durable_state equals "repair_required"', tools_source)
        self.assertIn("wake_status:", node)
        self.assertIn("turn:upgrade_wake_*", bridge)
        self.assertIn("extract_upgrade_wake_response", bridge)
        self.assertIn("post_upgrade_wake_reply", bridge)

    def test_long_running_work_checkpoints_without_terminal_iteration_cap(self) -> None:
        react = (REPO / "decent_agent/react_loop.ep").read_text(encoding="utf-8")

        self.assertIn("repeat while finished == 0:", react)
        self.assertNotIn("repeat while finished == 0 and also loop_idx < max_iters", react)
        self.assertNotIn("Max turns reached.", react)
        self.assertNotIn("Iteration cap (", react)
        self.assertIn('"iteration_checkpoint"', react)
        self.assertIn("Continuing unfinished work after", react)
        self.assertIn("The current task is unfinished. Continue from the exact accumulated prompt", react)
        self.assertGreaterEqual(react.count("set loop_idx to 0"), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
