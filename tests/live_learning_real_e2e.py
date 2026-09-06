#!/usr/bin/env python3
"""Resource-intensive real two-generation Gemma 4 adapter acceptance test.

This is intentionally excluded from the fast mandatory suite. It loads and trains
the actual local 26B checkpoint twice, evaluates both candidates with real loss and
multimodal inference, and proves generation two resumed generation one. It never
changes the production lineage or running node.
"""

from __future__ import annotations

import importlib.util
import json
import os
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("live_learning", ROOT / "scripts" / "live_learning.py")
assert SPEC and SPEC.loader
learning = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(learning)


def atomic_session(path: Path, session_id: str, nonce: str) -> None:
    value = {
        "id": session_id,
        "created_at": int(time.time()),
        "messages": [
            {
                "role": "user",
                "content": f"In validation generation {nonce}, what exact phrase belongs to Zaffron Delta?",
                "turn_id": "1",
                "created_at": int(time.time()),
                "source_type": "direct",
                "source_id": "real-e2e",
                "actor_id": "validation-host",
                "actor_username": "validation-host",
                "actor_display_name": "Validation Host",
                "platform": "isolated-local-test",
            },
            {
                "role": "assistant",
                "content": f"Zaffron Delta {nonce} is the amber sprout that remembers rain.",
                "turn_id": "1",
                "created_at": int(time.time()),
                "source_type": "observed",
                "source_id": "real-e2e",
                "platform": "isolated-local-test",
            },
        ],
    }
    learning._atomic_json(path, value)


def one_generation(config: dict, session_path: Path, nonce: str, change_digit: str) -> tuple[dict, dict]:
    prepared = learning.prepare(config, session_path, f"real cumulative adapter proof {nonce}", "validation-host")
    trained = learning.train(config, prepared["transaction_id"])
    evaluated = learning.evaluate_candidate(config, prepared["transaction_id"])
    staged = learning.stage_activation(
        config,
        prepared["transaction_id"],
        Path(evaluated["receipt_path"]),
        change_digit * 64,
    )
    learning.prepare_runtime(config)
    committed = learning.commit_pending(config)
    assert committed["adapter_hash"] == trained["adapter_hash"] == staged["adapter_hash"]
    return prepared, committed


def main() -> int:
    stamp = str(int(time.time()))
    evidence = Path(os.path.expanduser(f"~/.ernosdecent/live-learning/validation/{stamp}"))
    sessions = evidence / "sessions"
    sessions.mkdir(parents=True, exist_ok=False)
    config = json.loads((ROOT / "config" / "live_learning.json").read_text(encoding="utf-8"))
    config.update(
        state_path=str(evidence / "state" / "live"),
        sessions_path=str(sessions),
        base_model_path=os.path.expanduser(str(config["base_model_path"])),
        runtime_path=os.path.expanduser(str(config["runtime_path"])),
        anchors_path=str((ROOT / "config" / "live_learning_anchors.jsonl").resolve()),
        validation_path=str((ROOT / "config" / "live_learning_validation.jsonl").resolve()),
    )
    config["training"].update(minimum_iterations=2, maximum_iterations=2, iterations_per_new_example=2)

    first_session = sessions / "generation-one.json"
    atomic_session(first_session, "generation-one", "ONE-7KQ")
    first_prepared, first_commit = one_generation(config, first_session, "ONE-7KQ", "a")

    second_session = sessions / "generation-two.json"
    atomic_session(second_session, "generation-two", "TWO-9XR")
    second_prepared, second_commit = one_generation(config, second_session, "TWO-9XR", "b")
    second_tx = learning.state_root(config) / "transactions" / second_prepared["transaction_id"]
    second_manifest = learning.verify_manifest(second_tx / "manifest.json")
    training_log = (second_tx / "training.log").read_text(encoding="utf-8", errors="replace")
    assert first_commit["version"] == 1
    assert second_commit["version"] == 2
    assert second_prepared["parent_version"] == 1
    assert second_manifest["parent_hash"] == first_commit["adapter_hash"]
    assert second_manifest["parent_adapter_path"].endswith("adapters.safetensors")
    assert second_manifest["parent_adapter_config_hash"]
    assert "Resuming from adapter path" in training_log
    assert first_commit["adapter_hash"] != second_commit["adapter_hash"]
    summary = {
        "result": "PASS",
        "evidence_root": str(evidence),
        "base_model": config["base_model"],
        "generation_one": first_commit,
        "generation_two": second_commit,
        "generation_two_parent": {
            "version": second_prepared["parent_version"],
            "hash": second_manifest["parent_hash"],
            "path": second_manifest["parent_adapter_path"],
        },
        "real_resume_log_hash": learning.sha256_file(second_tx / "training.log"),
    }
    learning._atomic_json(evidence / "acceptance.json", summary)
    print("ERNOS_LIVE_LEARNING_REAL_E2E=" + json.dumps(summary, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
