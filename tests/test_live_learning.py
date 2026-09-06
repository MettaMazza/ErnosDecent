#!/usr/bin/env python3
"""Deterministic transaction tests for cumulative local weight learning."""

from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("live_learning", ROOT / "scripts" / "live_learning.py")
assert SPEC and SPEC.loader
learning = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(learning)


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, values) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(value, sort_keys=True) + "\n" for value in values), encoding="utf-8")


def session(path: Path, session_id: str, answer: str) -> None:
    write_json(
        path,
        {
            "id": session_id,
            "messages": [
                {"role": "user", "content": "Remember the exact colour is amber.", "turn_id": "1", "actor_id": "host"},
                {"role": "assistant", "content": answer, "turn_id": "1"},
            ],
        },
    )


def passing_candidate(config, transaction_id: str) -> tuple[Path, dict]:
    tx = learning.state_root(config) / "transactions" / transaction_id
    manifest_path = tx / "manifest.json"
    manifest = learning.verify_manifest(manifest_path)
    adapter = tx / "adapters.safetensors"
    adapter.write_bytes(("real cumulative adapter " + transaction_id).encode())
    adapter_config = tx / "adapter_config.json"
    adapter_config.write_text('{"rank":8,"alpha":16,"dropout":0.0}\n', encoding="utf-8")
    manifest.update(
        status="trained",
        adapter_path=str(adapter.resolve()),
        adapter_hash=learning.sha256_file(adapter),
        adapter_config_hash=learning.sha256_file(adapter_config),
        adapter_size=adapter.stat().st_size,
        training_log_hash="b" * 64,
    )
    manifest = learning._seal_manifest(manifest)
    learning._atomic_json(manifest_path, manifest)
    criteria = {
        "new_data_loss_improved": True,
        "anchor_loss_preserved": True,
        "candidate_text_and_multimodal_probe": True,
        "mandatory_application_regressions": True,
    }
    evaluation = learning._seal_receipt(
        {
            "schema": learning.SCHEMA,
            "transaction_id": transaction_id,
            "manifest_hash": manifest["manifest_hash"],
            "adapter_hash": manifest["adapter_hash"],
            "adapter_config_hash": manifest["adapter_config_hash"],
            "criteria": criteria,
            "passed": True,
        }
    )
    evaluation_path = tx / "evaluation.json"
    learning._atomic_json(evaluation_path, evaluation)
    return evaluation_path, manifest


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="ernos-live-learning-") as raw:
        fixture = Path(raw)
        model = fixture / "model"
        model.mkdir()
        (model / "weights.safetensors").write_bytes(b"real model fixture bytes")
        sessions = fixture / "sessions"
        sessions.mkdir()
        anchors = fixture / "anchors.jsonl"
        validation = fixture / "validation.jsonl"
        anchor_record = {"messages": [{"role": "user", "content": "Stay truthful."}, {"role": "assistant", "content": "I will."}]}
        write_jsonl(anchors, [{"anchor_id": "truth", **anchor_record}])
        write_jsonl(validation, [{"anchor_id": "truth-heldout", **anchor_record}])
        config = json.loads((ROOT / "config" / "live_learning.json").read_text(encoding="utf-8"))
        config.update(
            base_model_path=str(model),
            state_path=str(fixture / "learning" / "live"),
            sessions_path=str(sessions),
            anchors_path=str(anchors),
            validation_path=str(validation),
            runtime_path=str(fixture / "runtime"),
        )

        first_session = sessions / "one.json"
        session(first_session, "one", "The exact colour is amber.")
        first = learning.prepare(config, first_session, "retain this correction", "host")
        assert first["parent_version"] == 0
        assert first["new_examples"] == 1
        assert first["anchors"] == 1
        first_eval, first_manifest = passing_candidate(config, first["transaction_id"])

        # Promotion is bound to the canonical evaluation, all named criteria, and
        # an exact rights change id. A copied receipt at another path is rejected.
        copied_eval = fixture / "copied-evaluation.json"
        copied_eval.write_bytes(first_eval.read_bytes())
        try:
            learning.stage_activation(config, first["transaction_id"], copied_eval, "a" * 64)
            raise AssertionError("non-canonical evaluation path was accepted")
        except learning.LearningError as exc:
            assert exc.code == "EVALUATION_PATH_INVALID"

        staged = learning.stage_activation(config, first["transaction_id"], first_eval, "a" * 64)
        assert staged["adapter_hash"] == first_manifest["adapter_hash"]
        prepared_runtime = learning.prepare_runtime(config)
        assert prepared_runtime["status"] == "candidate"
        runtime = learning.runtime_spec(config)
        assert runtime["adapter_hash"] == first_manifest["adapter_hash"]
        committed = learning.commit_pending(config)
        assert committed["version"] == 1
        assert learning.status(config)["active_version"] == 1
        assert not learning.pending_activation_path(config).exists()

        # A later session becomes one immutable child of v1. Its manifest names the
        # exact v1 adapter as parent and includes earlier accepted examples as replay.
        second_session = sessions / "two.json"
        session(second_session, "two", "The exact colour remains amber.")
        second = learning.prepare(config, second_session, "continue learning", "host")
        second_manifest = learning.verify_manifest(Path(second["manifest_path"]))
        assert second["parent_version"] == 1
        assert second["replay_examples"] == 1
        assert second_manifest["parent_adapter_path"] == first_manifest["adapter_path"]
        assert second_manifest["parent_hash"] == first_manifest["adapter_hash"]

        # Session bytes are provenance, not a mutable pointer: post-freeze tampering
        # changes the session hash while the immutable transaction retains exact data.
        frozen_hash = second_manifest["session_hash"]
        session(second_session, "two", "A different answer.")
        assert learning._sha256_bytes(second_session.read_bytes()) != frozen_hash
        assert learning.verify_manifest(Path(second["manifest_path"]))["session_hash"] == frozen_hash

    print("live learning transactions: 18/18")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
