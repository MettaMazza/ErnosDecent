#!/usr/bin/env python3
"""Durable local live-learning transactions for ErnosDecent.

This controller never mutates the running model.  It freezes provenance-rich
session examples, trains an immutable cumulative child adapter, and writes
hash-bound receipts.  Activation is a separate, supervised operation performed
only after the node's rights gate and runtime evaluation have accepted the exact
candidate bytes.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import math
import os
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable


SCHEMA = "ernosdecent-live-learning-v1"
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO_ROOT / "config" / "live_learning.json"
ANCHORS_PATH = REPO_ROOT / "config" / "live_learning_anchors.jsonl"
VALIDATION_PATH = REPO_ROOT / "config" / "live_learning_validation.jsonl"


class LearningError(RuntimeError):
    """A fail-closed transaction error with a stable machine code."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _expand(path: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(path))).resolve()


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise LearningError("FILE_MISSING", f"Required file does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise LearningError("JSON_INVALID", f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise LearningError("JSON_SHAPE_INVALID", f"Expected an object in {path}")
    return value


def load_config(path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    config = _load_json(path)
    if config.get("schema") != SCHEMA:
        raise LearningError("CONFIG_SCHEMA_INVALID", "Live-learning config schema is not supported")
    return config


def state_root(config: dict[str, Any]) -> Path:
    return _expand(str(config["state_path"]))


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_tree(path: Path) -> str:
    if not path.is_dir():
        raise LearningError("MODEL_PATH_MISSING", f"Model directory does not exist: {path}")
    digest = hashlib.sha256()
    found = 0
    for item in sorted(path.rglob("*")):
        if not item.is_file() or ".cache" in item.parts:
            continue
        rel = item.relative_to(path).as_posix().encode("utf-8")
        digest.update(len(rel).to_bytes(8, "big"))
        digest.update(rel)
        file_hash = bytes.fromhex(sha256_file(item))
        digest.update(item.stat().st_size.to_bytes(8, "big"))
        digest.update(file_hash)
        found += 1
    if found == 0:
        raise LearningError("MODEL_PATH_EMPTY", f"Model directory has no files: {path}")
    return digest.hexdigest()


def adapter_package(path: Path) -> tuple[Path, Path]:
    """Resolve MLX-VLM's two-file adapter package from its canonical weights path."""
    weights = path.resolve()
    config = weights.parent / "adapter_config.json"
    if weights.name != "adapters.safetensors" or not weights.is_file() or not config.is_file():
        raise LearningError(
            "ADAPTER_PACKAGE_INVALID",
            f"Adapter requires sibling adapters.safetensors and adapter_config.json files: {weights.parent}",
        )
    return weights, config


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _atomic_write(path: Path, data: bytes, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.tmp.{os.getpid()}.{time.time_ns()}")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(temp, flags, mode)
    try:
        with os.fdopen(fd, "wb", closefd=True) as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def _atomic_json(path: Path, value: Any) -> None:
    _atomic_write(path, json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8") + b"\n")


def _jsonl_bytes(records: Iterable[dict[str, Any]]) -> bytes:
    return b"".join(_canonical_json(record) + b"\n" for record in records)


@contextmanager
def transaction_lock(root: Path):
    root.mkdir(parents=True, exist_ok=True)
    lock_path = root / "controller.lock"
    with lock_path.open("a+b") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def lineage_path(config: dict[str, Any]) -> Path:
    return state_root(config) / "lineage.json"


def pending_activation_path(config: dict[str, Any]) -> Path:
    return state_root(config) / "pending_activation.json"


def runtime_active_path(config: dict[str, Any]) -> Path:
    return state_root(config) / "runtime_active.json"


def active_model_pointer_path(config: dict[str, Any]) -> Path:
    return state_root(config).parent / "active_model.txt"


def load_lineage(config: dict[str, Any]) -> dict[str, Any]:
    path = lineage_path(config)
    if not path.exists():
        return {"schema": SCHEMA, "active_version": 0, "versions": []}
    lineage = _load_json(path)
    if lineage.get("schema") != SCHEMA or not isinstance(lineage.get("versions"), list):
        raise LearningError("LINEAGE_INVALID", "Adapter lineage is malformed")
    return lineage


def _version(lineage: dict[str, Any], number: int) -> dict[str, Any] | None:
    for entry in lineage["versions"]:
        if isinstance(entry, dict) and entry.get("version") == number:
            return entry
    return None


def _normalise_message(message: dict[str, Any]) -> dict[str, Any] | None:
    role = str(message.get("role", ""))
    content = message.get("content")
    if role not in {"user", "assistant"} or not isinstance(content, str) or not content.strip():
        return None
    content_hash = str(message.get("content_hash", ""))
    actual_hash = _sha256_bytes(content.encode("utf-8"))
    if content_hash and content_hash != actual_hash:
        raise LearningError("SESSION_CONTENT_HASH_MISMATCH", "A session message no longer matches its recorded hash")
    return {
        "role": role,
        "content": content,
        "content_hash": actual_hash,
        "turn_id": str(message.get("turn_id", "")),
        "created_at": int(message.get("created_at", 0) or 0),
        "source_type": str(message.get("source_type", "direct")),
        "source_id": str(message.get("source_id", "")),
        "actor_id": str(message.get("actor_id", "")),
        "actor_username": str(message.get("actor_username", "")),
        "actor_display_name": str(message.get("actor_display_name", "")),
        "platform": str(message.get("platform", "")),
    }


def session_examples(session: dict[str, Any], trained_hashes: set[str]) -> list[dict[str, Any]]:
    raw_messages = session.get("messages")
    if not isinstance(raw_messages, list):
        raise LearningError("SESSION_MESSAGES_INVALID", "Session messages are missing or malformed")
    history: list[dict[str, str]] = []
    provenance: list[dict[str, Any]] = []
    examples: list[dict[str, Any]] = []
    have_user = False
    for raw in raw_messages:
        if not isinstance(raw, dict):
            continue
        message = _normalise_message(raw)
        if message is None:
            continue
        history.append({"role": message["role"], "content": message["content"]})
        provenance.append({k: v for k, v in message.items() if k != "content"})
        if message["role"] == "user":
            have_user = True
            continue
        if not have_user or message["content_hash"] in trained_hashes:
            continue
        example_id = _sha256_bytes(
            _canonical_json(
                {
                    "session": session.get("id", ""),
                    "assistant_hash": message["content_hash"],
                    "messages": history,
                }
            )
        )
        examples.append(
            {
                "example_id": example_id,
                "assistant_content_hash": message["content_hash"],
                "messages": list(history),
                "provenance": list(provenance),
            }
        )
    return examples


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if not path.exists():
        return records
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise LearningError("JSONL_INVALID", f"Invalid JSONL at {path}:{line_number}: {exc}") from exc
        if not isinstance(record, dict) or not isinstance(record.get("messages"), list):
            raise LearningError("JSONL_SHAPE_INVALID", f"Invalid training record at {path}:{line_number}")
        records.append(record)
    return records


def _prior_examples(config: dict[str, Any], lineage: dict[str, Any]) -> list[dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for entry in lineage["versions"]:
        if not isinstance(entry, dict):
            continue
        transaction_id = str(entry.get("transaction_id", ""))
        path = state_root(config) / "transactions" / transaction_id / "dataset" / "new_examples.jsonl"
        for record in _read_jsonl(path):
            key = str(record.get("example_id") or _sha256_bytes(_canonical_json(record)))
            records[key] = record
    ordered = [records[key] for key in sorted(records)]
    limit = int(config["replay"]["maximum_prior_examples_per_batch"])
    return ordered[-limit:] if limit >= 0 else ordered


def _anchors(config: dict[str, Any]) -> list[dict[str, Any]]:
    return _read_jsonl(_expand(str(config.get("anchors_path", ANCHORS_PATH))))


def _trained_hashes(lineage: dict[str, Any]) -> set[str]:
    result: set[str] = set()
    for entry in lineage["versions"]:
        if not isinstance(entry, dict):
            continue
        hashes = entry.get("trained_assistant_hashes", [])
        if isinstance(hashes, list):
            result.update(str(value) for value in hashes)
    return result


def _manifest_payload(manifest: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in manifest.items() if key != "manifest_hash"}


def _seal_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    sealed = dict(manifest)
    sealed["manifest_hash"] = _sha256_bytes(_canonical_json(_manifest_payload(sealed)))
    return sealed


def _seal_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    sealed = dict(receipt)
    sealed["receipt_hash"] = _sha256_bytes(
        _canonical_json({key: value for key, value in sealed.items() if key != "receipt_hash"})
    )
    return sealed


def verify_receipt(path: Path) -> dict[str, Any]:
    receipt = _load_json(path)
    expected = str(receipt.get("receipt_hash", ""))
    actual = _sha256_bytes(
        _canonical_json({key: value for key, value in receipt.items() if key != "receipt_hash"})
    )
    if len(expected) != 64 or expected != actual:
        raise LearningError("EVALUATION_HASH_MISMATCH", "Evaluation receipt integrity failed")
    return receipt


def verify_manifest(path: Path) -> dict[str, Any]:
    manifest = _load_json(path)
    expected = str(manifest.get("manifest_hash", ""))
    actual = _sha256_bytes(_canonical_json(_manifest_payload(manifest)))
    if len(expected) != 64 or expected != actual:
        raise LearningError("MANIFEST_HASH_MISMATCH", f"Manifest integrity failed: {path}")
    tx_dir = path.parent
    for name, expected_hash in manifest.get("artifacts", {}).items():
        artifact = (tx_dir / name).resolve()
        if tx_dir.resolve() not in artifact.parents:
            raise LearningError("ARTIFACT_PATH_INVALID", f"Artifact escapes transaction directory: {name}")
        if not artifact.is_file() or sha256_file(artifact) != expected_hash:
            raise LearningError("ARTIFACT_HASH_MISMATCH", f"Artifact integrity failed: {name}")
    return manifest


def _validated_candidate(
    config: dict[str, Any], transaction_id: str, evaluation_path: Path
) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    root = state_root(config).resolve()
    tx_dir = (root / "transactions" / transaction_id).resolve()
    if tx_dir.parent != (root / "transactions").resolve() or len(transaction_id) != 64:
        raise LearningError("TRANSACTION_ID_INVALID", "Transaction identifier is not canonical")
    try:
        int(transaction_id, 16)
    except ValueError as exc:
        raise LearningError("TRANSACTION_ID_INVALID", "Transaction identifier is not hexadecimal") from exc
    manifest = verify_manifest(tx_dir / "manifest.json")
    if manifest.get("status") != "trained":
        raise LearningError("TRANSACTION_STATE_INVALID", "Only a trained candidate can be activated")
    canonical_evaluation_path = tx_dir / "evaluation.json"
    if evaluation_path.resolve() != canonical_evaluation_path.resolve():
        raise LearningError("EVALUATION_PATH_INVALID", "Only this transaction's canonical evaluation may activate it")
    evaluation = verify_receipt(canonical_evaluation_path)
    required_criteria = {
        "new_data_loss_improved",
        "anchor_loss_preserved",
        "candidate_text_and_multimodal_probe",
        "mandatory_application_regressions",
    }
    criteria = evaluation.get("criteria")
    criteria_valid = isinstance(criteria, dict) and all(criteria.get(key) is True for key in required_criteria)
    adapter_path = Path(str(manifest.get("adapter_path", ""))).resolve()
    try:
        adapter_weights, adapter_config = adapter_package(adapter_path)
    except LearningError:
        adapter_weights, adapter_config = adapter_path, adapter_path.parent / "adapter_config.json"
    if (
        manifest.get("transaction_id") != transaction_id
        or not adapter_weights.is_file()
        or sha256_file(adapter_weights) != manifest.get("adapter_hash")
        or not adapter_config.is_file()
        or sha256_file(adapter_config) != manifest.get("adapter_config_hash")
        or evaluation.get("schema") != SCHEMA
        or evaluation.get("transaction_id") != transaction_id
        or evaluation.get("manifest_hash") != manifest.get("manifest_hash")
        or evaluation.get("adapter_hash") != manifest.get("adapter_hash")
        or evaluation.get("adapter_config_hash") != manifest.get("adapter_config_hash")
        or evaluation.get("passed") is not True
        or not criteria_valid
    ):
        raise LearningError("EVALUATION_REJECTED", "Candidate evaluation is absent, mismatched, or not passing")
    return tx_dir, manifest, evaluation


def prepare(config: dict[str, Any], session_path: Path, reason: str, requested_by: str) -> dict[str, Any]:
    reason = reason.strip()
    if not reason:
        raise LearningError("REASON_REQUIRED", "A live-learning request requires a reason")
    session_path = session_path.resolve()
    sessions_root = _expand(str(config.get("sessions_path", REPO_ROOT / "config" / "sessions")))
    if sessions_root not in session_path.parents or session_path.suffix != ".json":
        raise LearningError("SESSION_PATH_INVALID", "Training input must be a persisted ErnosDecent session")
    root = state_root(config)
    with transaction_lock(root):
        lineage = load_lineage(config)
        session_bytes = session_path.read_bytes()
        session = json.loads(session_bytes)
        if not isinstance(session, dict) or not session.get("id"):
            raise LearningError("SESSION_INVALID", "Session document is malformed")
        new_examples = session_examples(session, _trained_hashes(lineage))
        if not new_examples:
            raise LearningError("NO_NEW_EXAMPLES", "The session has no complete unlearned user/assistant interactions")
        parent_version = int(lineage.get("active_version", 0))
        parent = _version(lineage, parent_version) if parent_version else None
        parent_adapter = str(parent.get("adapter_path", "")) if parent else ""
        parent_hash = str(parent.get("adapter_hash", "")) if parent else ""
        parent_config_hash = str(parent.get("adapter_config_hash", "")) if parent else ""
        seed = {
            "schema": SCHEMA,
            "session_id": str(session["id"]),
            "session_hash": _sha256_bytes(session_bytes),
            "new_example_ids": [entry["example_id"] for entry in new_examples],
            "parent_version": parent_version,
            "parent_hash": parent_hash,
            "requested_at": int(time.time()),
            "reason": reason,
            "requested_by": requested_by,
        }
        transaction_id = _sha256_bytes(_canonical_json(seed))
        tx_dir = root / "transactions" / transaction_id
        if tx_dir.exists():
            raise LearningError("TRANSACTION_EXISTS", f"Transaction already exists: {transaction_id}")
        tx_dir.mkdir(parents=True, mode=0o700)

        replay = _prior_examples(config, lineage)
        anchors = _anchors(config) if config["replay"]["always_include_constitutional_anchors"] else []
        train_records = [
            {"messages": entry["messages"], "example_id": entry["example_id"], "source": "current_session"}
            for entry in new_examples
        ]
        train_records.extend(
            {"messages": entry["messages"], "example_id": entry.get("example_id", ""), "source": "lineage_replay"}
            for entry in replay
        )
        train_records.extend(
            {"messages": entry["messages"], "anchor_id": entry.get("anchor_id", ""), "source": "constitutional_anchor"}
            for entry in anchors
        )
        validation = _read_jsonl(_expand(str(config.get("validation_path", VALIDATION_PATH))))
        data_dir = tx_dir / "dataset"
        new_path = data_dir / "new_examples.jsonl"
        train_path = data_dir / "train.jsonl"
        anchors_copy = data_dir / "anchors.jsonl"
        eval_new_path = tx_dir / "evaluation-new" / "train.jsonl"
        eval_anchor_path = tx_dir / "evaluation-anchors" / "train.jsonl"
        _atomic_write(new_path, _jsonl_bytes(new_examples))
        _atomic_write(train_path, _jsonl_bytes(train_records))
        _atomic_write(anchors_copy, _jsonl_bytes(anchors))
        _atomic_write(
            eval_new_path,
            _jsonl_bytes({"messages": entry["messages"], "example_id": entry["example_id"]} for entry in new_examples),
        )
        _atomic_write(eval_anchor_path, _jsonl_bytes(validation))

        training = config["training"]
        iterations = max(
            int(training["minimum_iterations"]),
            min(
                int(training["maximum_iterations"]),
                len(new_examples) * int(training["iterations_per_new_example"]),
            ),
        )
        model_path = _expand(str(config["base_model_path"]))
        manifest = _seal_manifest(
            {
                **seed,
                "transaction_id": transaction_id,
                "status": "prepared",
                "base_model": config["base_model"],
                "base_model_path": str(model_path),
                "base_model_tree_hash": sha256_tree(model_path),
                "parent_adapter_path": parent_adapter,
                "parent_adapter_config_hash": parent_config_hash,
                "new_example_count": len(new_examples),
                "replay_example_count": len(replay),
                "anchor_example_count": len(anchors),
                "validation_example_count": len(validation),
                "trained_assistant_hashes": [entry["assistant_content_hash"] for entry in new_examples],
                "new_example_provenance": [
                    {"example_id": entry["example_id"], "records": entry["provenance"]}
                    for entry in new_examples
                ],
                "training": {**training, "iterations": iterations},
                "promotion": config["promotion"],
                "artifacts": {
                    "dataset/new_examples.jsonl": sha256_file(new_path),
                    "dataset/train.jsonl": sha256_file(train_path),
                    "dataset/anchors.jsonl": sha256_file(anchors_copy),
                    "evaluation-new/train.jsonl": sha256_file(eval_new_path),
                    "evaluation-anchors/train.jsonl": sha256_file(eval_anchor_path),
                },
            }
        )
        manifest_path = tx_dir / "manifest.json"
        _atomic_json(manifest_path, manifest)
        return {
            "code": "LEARNING_PREPARED",
            "transaction_id": transaction_id,
            "manifest_path": str(manifest_path),
            "manifest_hash": manifest["manifest_hash"],
            "manifest_file_hash": sha256_file(manifest_path),
            "session_id": session["id"],
            "new_examples": len(new_examples),
            "replay_examples": len(replay),
            "anchors": len(anchors),
            "parent_version": parent_version,
        }


def _run(command: list[str], log_path: Path, env: dict[str, str] | None = None) -> None:
    started = time.time()
    with log_path.open("wb") as log:
        completed = subprocess.run(command, cwd=REPO_ROOT, stdout=log, stderr=subprocess.STDOUT, env=env, check=False)
        log.flush()
        os.fsync(log.fileno())
    if completed.returncode != 0:
        raise LearningError(
            "TRAINER_FAILED",
            f"Trainer exited {completed.returncode} after {int(time.time() - started)}s; log={log_path}",
        )


def train(config: dict[str, Any], transaction_id: str) -> dict[str, Any]:
    root = state_root(config)
    tx_dir = root / "transactions" / transaction_id
    manifest_path = tx_dir / "manifest.json"
    with transaction_lock(root):
        manifest = verify_manifest(manifest_path)
        if manifest.get("status") not in {"prepared", "training_failed"}:
            raise LearningError("TRANSACTION_STATE_INVALID", f"Cannot train from status {manifest.get('status')}")
        runtime = _expand(str(config["runtime_path"]))
        python = runtime / "bin" / "python"
        if not python.is_file():
            raise LearningError("TRAINING_RUNTIME_MISSING", f"Training runtime is not installed: {runtime}")
        trainer_sources = list(runtime.glob("lib/python*/site-packages/mlx_vlm/models/gemma4/language.py"))
        expected_trainer_hash = str(config.get("gemma4_training_source_sha256", ""))
        if len(trainer_sources) != 1 or sha256_file(trainer_sources[0]) != expected_trainer_hash:
            raise LearningError(
                "TRAINER_SOURCE_UNVERIFIED",
                "Pinned Gemma 4 MoE gradient-safe trainer source is missing or changed; rerun scripts/install_live_learning.sh",
            )
        output_path = tx_dir / "adapters.safetensors"
        output_config_path = tx_dir / "adapter_config.json"
        command = [
            str(python),
            "-m",
            "mlx_vlm.lora",
            "--model-path",
            manifest["base_model_path"],
            "--dataset",
            str(tx_dir / "dataset"),
            "--split",
            "train",
            "--train-mode",
            "sft",
            "--batch-size",
            str(manifest["training"]["batch_size"]),
            "--iters",
            str(manifest["training"]["iterations"]),
            "--learning-rate",
            str(manifest["training"]["learning_rate"]),
            "--max-seq-length",
            str(manifest["training"]["maximum_sequence_length"]),
            "--gradient-accumulation-steps",
            str(manifest["training"]["gradient_accumulation_steps"]),
            "--lora-rank",
            str(manifest["training"]["rank"]),
            "--lora-alpha",
            str(manifest["training"]["alpha"]),
            "--lora-dropout",
            str(manifest["training"]["dropout"]),
            "--steps-per-report",
            "1",
            "--steps-per-save",
            str(manifest["training"]["iterations"]),
            "--output-path",
            str(output_path),
        ]
        if manifest["training"].get("gradient_checkpointing"):
            command.append("--grad-checkpoint")
        if manifest["training"].get("train_vision"):
            command.append("--train-vision")
        if manifest["training"].get("train_on_assistant_completions"):
            command.extend(
                [
                    "--train-on-completions",
                    "--assistant-id",
                    str(manifest["training"]["assistant_role_token_id"]),
                ]
            )
        parent_path = str(manifest.get("parent_adapter_path", ""))
        if parent_path:
            parent = Path(parent_path).resolve()
            parent_weights, parent_config = adapter_package(parent)
            if (
                sha256_file(parent_weights) != manifest.get("parent_hash")
                or sha256_file(parent_config) != manifest.get("parent_adapter_config_hash")
            ):
                raise LearningError("PARENT_ADAPTER_INVALID", "Parent adapter bytes do not match the frozen lineage")
            command.extend(["--adapter-path", str(parent.parent)])

        training_manifest = dict(manifest)
        training_manifest["status"] = "training"
        training_manifest["training_started_at"] = int(time.time())
        training_manifest["trainer_command"] = command
        training_manifest = _seal_manifest(training_manifest)
        _atomic_json(manifest_path, training_manifest)
        try:
            _run(command, tx_dir / "training.log")
        except LearningError as exc:
            failed = dict(training_manifest)
            failed["status"] = "training_failed"
            failed["failure_code"] = exc.code
            failed["failure_message"] = exc.message
            failed["training_finished_at"] = int(time.time())
            failed = _seal_manifest(failed)
            _atomic_json(manifest_path, failed)
            raise
        if not output_path.is_file() or output_path.stat().st_size == 0 or not output_config_path.is_file():
            raise LearningError("ADAPTER_MISSING", "Trainer returned success without a complete adapter package")
        completed = dict(training_manifest)
        completed["status"] = "trained"
        completed["training_finished_at"] = int(time.time())
        completed["adapter_path"] = str(output_path)
        completed["adapter_size"] = output_path.stat().st_size
        completed["adapter_hash"] = sha256_file(output_path)
        completed["adapter_config_hash"] = sha256_file(output_config_path)
        completed["training_log_hash"] = sha256_file(tx_dir / "training.log")
        completed = _seal_manifest(completed)
        _atomic_json(manifest_path, completed)
        return {
            "code": "LEARNING_TRAINED",
            "transaction_id": transaction_id,
            "adapter_path": str(output_path),
            "adapter_hash": completed["adapter_hash"],
            "adapter_config_hash": completed["adapter_config_hash"],
            "adapter_size": completed["adapter_size"],
            "manifest_hash": completed["manifest_hash"],
        }


def _loss_measurement(
    config: dict[str, Any], manifest: dict[str, Any], dataset_dir: Path, adapter: str, output_log: Path
) -> dict[str, Any]:
    runtime = _expand(str(config["runtime_path"]))
    command = [
        str(runtime / "bin" / "python"),
        str(REPO_ROOT / "scripts" / "live_learning_loss.py"),
        "--model",
        manifest["base_model_path"],
        "--dataset",
        str(dataset_dir),
        "--maximum-sequence-length",
        str(manifest["training"]["maximum_sequence_length"]),
        "--assistant-id",
        str(manifest["training"]["assistant_role_token_id"]),
    ]
    if adapter:
        command.extend(["--adapter", adapter])
    _run(command, output_log)
    marker = "ERNOS_LIVE_LEARNING_LOSS="
    payload = ""
    for line in output_log.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith(marker):
            payload = line[len(marker) :]
    if not payload:
        raise LearningError("LOSS_RECEIPT_MISSING", f"Loss worker produced no receipt: {output_log}")
    try:
        result = json.loads(payload)
        loss = float(result["loss"])
        examples = int(result["examples"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise LearningError("LOSS_RECEIPT_INVALID", f"Invalid loss receipt: {output_log}") from exc
    if not math.isfinite(loss) or examples < 1:
        raise LearningError("LOSS_NONFINITE", f"Invalid loss measurement: {loss}")
    return {"loss": loss, "examples": examples, "log_hash": sha256_file(output_log)}


def evaluate_candidate(config: dict[str, Any], transaction_id: str) -> dict[str, Any]:
    root = state_root(config)
    tx_dir = root / "transactions" / transaction_id
    with transaction_lock(root):
        manifest = verify_manifest(tx_dir / "manifest.json")
        if manifest.get("status") != "trained":
            raise LearningError("TRANSACTION_STATE_INVALID", "Only a trained candidate can be evaluated")
        parent_adapter = str(manifest.get("parent_adapter_path", ""))
        candidate_adapter = str(manifest["adapter_path"])
        measurements = {
            "parent_new": _loss_measurement(
                config, manifest, tx_dir / "evaluation-new", parent_adapter, tx_dir / "loss-parent-new.log"
            ),
            "candidate_new": _loss_measurement(
                config, manifest, tx_dir / "evaluation-new", candidate_adapter, tx_dir / "loss-candidate-new.log"
            ),
            "parent_anchors": _loss_measurement(
                config, manifest, tx_dir / "evaluation-anchors", parent_adapter, tx_dir / "loss-parent-anchors.log"
            ),
            "candidate_anchors": _loss_measurement(
                config, manifest, tx_dir / "evaluation-anchors", candidate_adapter, tx_dir / "loss-candidate-anchors.log"
            ),
        }
        parent_new = measurements["parent_new"]["loss"]
        candidate_new = measurements["candidate_new"]["loss"]
        parent_anchor = measurements["parent_anchors"]["loss"]
        candidate_anchor = measurements["candidate_anchors"]["loss"]
        allowed_fraction = float(config["promotion"]["maximum_anchor_loss_regression_fraction"])
        new_improved = candidate_new < parent_new
        anchor_limit = parent_anchor * (1.0 + allowed_fraction)
        anchors_preserved = candidate_anchor <= anchor_limit
        probe_path = tx_dir / "probe.json"
        runtime = _expand(str(config["runtime_path"]))
        probe_command = [
            str(runtime / "bin" / "python"),
            str(REPO_ROOT / "scripts" / "live_learning_probe.py"),
            "--model",
            manifest["base_model_path"],
            "--adapter",
            candidate_adapter,
            "--port",
            str(int(config["provider_port"]) + 1),
            "--output",
            str(probe_path),
            "--server-log",
            str(tx_dir / "probe-server.log"),
        ]
        probe_error = ""
        try:
            _run(probe_command, tx_dir / "probe-worker.log")
            probe = _load_json(probe_path)
        except LearningError as exc:
            probe_error = exc.message
            probe = {"passed": False, "error": exc.message}
        probe_passed = probe.get("passed") is True
        regression_log = tx_dir / "application-regressions.log"
        regression_error = ""
        try:
            _run(["bash", "scripts/run_mandatory_regressions.sh"], regression_log)
            regressions_passed = True
        except LearningError as exc:
            regressions_passed = False
            regression_error = exc.message
        passed = bool(new_improved and anchors_preserved and probe_passed and regressions_passed)
        receipt = _seal_receipt(
            {
                "schema": SCHEMA,
                "transaction_id": transaction_id,
                "manifest_hash": manifest["manifest_hash"],
                "adapter_hash": manifest["adapter_hash"],
                "adapter_config_hash": manifest["adapter_config_hash"],
                "evaluated_at": int(time.time()),
                "measurements": measurements,
                "criteria": {
                    "new_data_loss_improved": new_improved,
                    "anchor_loss_preserved": anchors_preserved,
                    "maximum_anchor_loss": anchor_limit,
                    "maximum_anchor_loss_regression_fraction": allowed_fraction,
                    "candidate_text_and_multimodal_probe": probe_passed,
                    "mandatory_application_regressions": regressions_passed,
                },
                "probe_path": str(probe_path),
                "probe_hash": sha256_file(probe_path) if probe_path.is_file() else "",
                "probe": probe,
                "probe_error": probe_error,
                "application_regression_log": str(regression_log),
                "application_regression_log_hash": sha256_file(regression_log) if regression_log.is_file() else "",
                "application_regression_error": regression_error,
                "passed": passed,
            }
        )
        receipt_path = tx_dir / "evaluation.json"
        _atomic_json(receipt_path, receipt)
        if not passed:
            raise LearningError(
                "CANDIDATE_EVALUATION_FAILED",
                f"Candidate did not pass loss gates; receipt={receipt_path}",
            )
        return {
            "code": "LEARNING_EVALUATED",
            "transaction_id": transaction_id,
            "passed": True,
            "receipt_path": str(receipt_path),
            "receipt_hash": receipt["receipt_hash"],
            "measurements": measurements,
        }


def promote(config: dict[str, Any], transaction_id: str, evaluation_path: Path) -> dict[str, Any]:
    root = state_root(config)
    with transaction_lock(root):
        tx_dir, manifest, evaluation = _validated_candidate(config, transaction_id, evaluation_path)
        evaluation_hash = str(evaluation["receipt_hash"])
        lineage = load_lineage(config)
        if int(lineage.get("active_version", 0)) != int(manifest["parent_version"]):
            raise LearningError("LINEAGE_MOVED", "Active lineage changed after the candidate snapshot")
        version_number = int(manifest["parent_version"]) + 1
        entry = {
            "version": version_number,
            "parent_version": manifest["parent_version"],
            "parent_hash": manifest["parent_hash"],
            "transaction_id": transaction_id,
            "adapter_path": manifest["adapter_path"],
            "adapter_hash": manifest["adapter_hash"],
            "adapter_config_hash": manifest["adapter_config_hash"],
            "base_model_tree_hash": manifest["base_model_tree_hash"],
            "trained_assistant_hashes": manifest["trained_assistant_hashes"],
            "evaluation_path": str(evaluation_path.resolve()),
            "evaluation_hash": evaluation_hash,
            "promoted_at": int(time.time()),
        }
        lineage["versions"].append(entry)
        lineage["active_version"] = version_number
        lineage["updated_at"] = int(time.time())
        _atomic_json(lineage_path(config), lineage)
        completed = dict(manifest)
        completed["status"] = "promoted"
        completed["version"] = version_number
        completed["evaluation_path"] = str(evaluation_path.resolve())
        completed["evaluation_hash"] = evaluation_hash
        completed["promoted_at"] = int(time.time())
        completed = _seal_manifest(completed)
        _atomic_json(tx_dir / "manifest.json", completed)
        return {"code": "LEARNING_PROMOTED", "version": version_number, "transaction_id": transaction_id}


def stage_activation(
    config: dict[str, Any], transaction_id: str, evaluation_path: Path, change_id: str
) -> dict[str, Any]:
    if len(change_id) != 64:
        raise LearningError("RIGHTS_CHANGE_ID_INVALID", "A canonical protected-change id is required")
    try:
        int(change_id, 16)
    except ValueError as exc:
        raise LearningError("RIGHTS_CHANGE_ID_INVALID", "Protected-change id is not hexadecimal") from exc
    root = state_root(config)
    with transaction_lock(root):
        if pending_activation_path(config).exists():
            raise LearningError("ACTIVATION_ALREADY_PENDING", "Another adapter activation is already pending")
        _, manifest, evaluation = _validated_candidate(config, transaction_id, evaluation_path)
        lineage = load_lineage(config)
        if int(lineage.get("active_version", 0)) != int(manifest["parent_version"]):
            raise LearningError("LINEAGE_MOVED", "Active lineage changed after candidate training")
        pending = {
            "schema": SCHEMA,
            "status": "staged",
            "transaction_id": transaction_id,
            "change_id": change_id,
            "parent_version": int(manifest["parent_version"]),
            "candidate_version": int(manifest["parent_version"]) + 1,
            "base_model": manifest["base_model"],
            "base_model_path": manifest["base_model_path"],
            "base_model_tree_hash": manifest["base_model_tree_hash"],
            "adapter_path": manifest["adapter_path"],
            "adapter_hash": manifest["adapter_hash"],
            "adapter_config_hash": manifest["adapter_config_hash"],
            "manifest_hash": manifest["manifest_hash"],
            "evaluation_path": str(evaluation_path.resolve()),
            "evaluation_hash": evaluation["receipt_hash"],
            "staged_at": int(time.time()),
        }
        pending["pending_hash"] = _sha256_bytes(_canonical_json(pending))
        _atomic_json(pending_activation_path(config), pending)
        return {
            "code": "LEARNING_ACTIVATION_STAGED",
            "transaction_id": transaction_id,
            "change_id": change_id,
            "adapter_hash": manifest["adapter_hash"],
            "adapter_config_hash": manifest["adapter_config_hash"],
            "pending_hash": pending["pending_hash"],
        }


def _verify_pending(config: dict[str, Any]) -> dict[str, Any]:
    pending = _load_json(pending_activation_path(config))
    expected = str(pending.get("pending_hash", ""))
    actual = _sha256_bytes(_canonical_json({k: v for k, v in pending.items() if k != "pending_hash"}))
    if expected != actual or len(expected) != 64:
        raise LearningError("PENDING_HASH_MISMATCH", "Pending activation integrity failed")
    _, manifest, evaluation = _validated_candidate(
        config, str(pending.get("transaction_id", "")), Path(str(pending.get("evaluation_path", "")))
    )
    if (
        pending.get("manifest_hash") != manifest.get("manifest_hash")
        or pending.get("adapter_hash") != manifest.get("adapter_hash")
        or pending.get("adapter_config_hash") != manifest.get("adapter_config_hash")
        or pending.get("evaluation_hash") != evaluation.get("receipt_hash")
    ):
        raise LearningError("PENDING_CANDIDATE_MISMATCH", "Pending activation no longer matches candidate bytes")
    return pending


def prepare_runtime(config: dict[str, Any]) -> dict[str, Any]:
    root = state_root(config)
    with transaction_lock(root):
        pending = _verify_pending(config)
        runtime = {
            **pending,
            "status": "candidate",
            "provider_port": int(config["provider_port"]),
            "prepared_at": int(time.time()),
        }
        runtime["runtime_hash"] = _sha256_bytes(_canonical_json(runtime))
        _atomic_json(runtime_active_path(config), runtime)
        _atomic_write(active_model_pointer_path(config), (str(runtime["base_model_path"]) + "\n").encode("utf-8"))
        return {"code": "LEARNING_RUNTIME_PREPARED", **runtime}


def commit_pending(config: dict[str, Any]) -> dict[str, Any]:
    root = state_root(config)
    with transaction_lock(root):
        pending = _verify_pending(config)
        runtime = _load_json(runtime_active_path(config))
        runtime_hash = str(runtime.get("runtime_hash", ""))
        actual_runtime_hash = _sha256_bytes(
            _canonical_json({k: v for k, v in runtime.items() if k != "runtime_hash"})
        )
        if (
            runtime.get("status") != "candidate"
            or runtime_hash != actual_runtime_hash
            or runtime.get("pending_hash") != pending.get("pending_hash")
        ):
            raise LearningError("RUNTIME_CANDIDATE_INVALID", "Running candidate receipt does not match pending activation")
        # Inline the promotion under the already-held process lock.
        tx_dir, manifest, evaluation = _validated_candidate(
            config, pending["transaction_id"], Path(pending["evaluation_path"])
        )
        lineage = load_lineage(config)
        if int(lineage.get("active_version", 0)) != int(manifest["parent_version"]):
            raise LearningError("LINEAGE_MOVED", "Active lineage changed before activation commit")
        version_number = int(manifest["parent_version"]) + 1
        entry = {
            "version": version_number,
            "parent_version": manifest["parent_version"],
            "parent_hash": manifest["parent_hash"],
            "transaction_id": pending["transaction_id"],
            "adapter_path": manifest["adapter_path"],
            "adapter_hash": manifest["adapter_hash"],
            "adapter_config_hash": manifest["adapter_config_hash"],
            "base_model_tree_hash": manifest["base_model_tree_hash"],
            "trained_assistant_hashes": manifest["trained_assistant_hashes"],
            "evaluation_path": pending["evaluation_path"],
            "evaluation_hash": evaluation["receipt_hash"],
            "rights_change_id": pending["change_id"],
            "promoted_at": int(time.time()),
        }
        lineage["versions"].append(entry)
        lineage["active_version"] = version_number
        lineage["updated_at"] = int(time.time())
        _atomic_json(lineage_path(config), lineage)
        completed = dict(manifest)
        completed.update(
            status="promoted",
            version=version_number,
            evaluation_path=pending["evaluation_path"],
            evaluation_hash=evaluation["receipt_hash"],
            rights_change_id=pending["change_id"],
            promoted_at=int(time.time()),
        )
        _atomic_json(tx_dir / "manifest.json", _seal_manifest(completed))
        active = dict(runtime)
        active["status"] = "active"
        active["activated_at"] = int(time.time())
        active["runtime_hash"] = _sha256_bytes(
            _canonical_json({k: v for k, v in active.items() if k != "runtime_hash"})
        )
        _atomic_json(runtime_active_path(config), active)
        pending_activation_path(config).unlink()
        return {
            "code": "LEARNING_ACTIVATION_COMMITTED",
            "transaction_id": pending["transaction_id"],
            "change_id": pending["change_id"],
            "version": version_number,
            "adapter_hash": pending["adapter_hash"],
        }


def abort_pending(config: dict[str, Any], reason: str) -> dict[str, Any]:
    root = state_root(config)
    with transaction_lock(root):
        pending = _verify_pending(config)
        aborted = dict(pending)
        aborted["status"] = "activation_failed"
        aborted["failure_reason"] = reason.strip() or "candidate runtime validation failed"
        aborted["failed_at"] = int(time.time())
        aborted["pending_hash"] = _sha256_bytes(
            _canonical_json({k: v for k, v in aborted.items() if k != "pending_hash"})
        )
        _atomic_json(
            state_root(config) / "transactions" / pending["transaction_id"] / "activation-failure.json", aborted
        )
        pending_activation_path(config).unlink()
        if runtime_active_path(config).exists():
            runtime_active_path(config).unlink()
        if active_model_pointer_path(config).exists():
            active_model_pointer_path(config).unlink()
        # Restore the preceding accepted adapter pointer, if one exists.
        lineage = load_lineage(config)
        active = _version(lineage, int(lineage.get("active_version", 0)))
        if active:
            manifest = verify_manifest(
                state_root(config) / "transactions" / active["transaction_id"] / "manifest.json"
            )
            restored = {
                "schema": SCHEMA,
                "status": "active",
                "transaction_id": active["transaction_id"],
                "change_id": active.get("rights_change_id", ""),
                "candidate_version": active["version"],
                "base_model": config["base_model"],
                "base_model_path": manifest["base_model_path"],
                "base_model_tree_hash": manifest["base_model_tree_hash"],
                "adapter_path": active["adapter_path"],
                "adapter_hash": active["adapter_hash"],
                "adapter_config_hash": active["adapter_config_hash"],
                "provider_port": int(config["provider_port"]),
                "restored_at": int(time.time()),
            }
            restored["runtime_hash"] = _sha256_bytes(_canonical_json(restored))
            _atomic_json(runtime_active_path(config), restored)
            _atomic_write(active_model_pointer_path(config), (str(restored["base_model_path"]) + "\n").encode())
        return {
            "code": "LEARNING_ACTIVATION_ABORTED",
            "transaction_id": pending["transaction_id"],
            "change_id": pending["change_id"],
            "reason": aborted["failure_reason"],
        }


def runtime_spec(config: dict[str, Any]) -> dict[str, Any]:
    runtime = _load_json(runtime_active_path(config))
    expected = str(runtime.get("runtime_hash", ""))
    actual = _sha256_bytes(_canonical_json({k: v for k, v in runtime.items() if k != "runtime_hash"}))
    adapter = Path(str(runtime.get("adapter_path", ""))).resolve()
    model = Path(str(runtime.get("base_model_path", ""))).resolve()
    try:
        adapter_weights, adapter_config = adapter_package(adapter)
    except LearningError as exc:
        raise LearningError("RUNTIME_RECEIPT_INVALID", str(exc)) from exc
    if (
        expected != actual
        or sha256_file(adapter_weights) != runtime.get("adapter_hash")
        or sha256_file(adapter_config) != runtime.get("adapter_config_hash")
    ):
        raise LearningError("RUNTIME_RECEIPT_INVALID", "Active learning runtime receipt or adapter failed verification")
    if not model.is_dir():
        raise LearningError("MODEL_PATH_MISSING", f"Active base model is missing: {model}")
    return {
        "code": "LEARNING_RUNTIME_SPEC",
        "status": runtime["status"],
        "transaction_id": runtime["transaction_id"],
        "change_id": runtime.get("change_id", ""),
        "model_path": str(model),
        "adapter_path": str(adapter),
        "adapter_load_path": str(adapter.parent),
        "adapter_hash": runtime["adapter_hash"],
        "adapter_config_hash": runtime["adapter_config_hash"],
        "runtime_hash": expected,
        "provider_port": int(runtime["provider_port"]),
    }


def write_activation_outcome(config: dict[str, Any], status_value: str, reason: str) -> dict[str, Any]:
    if status_value not in {"applied", "failed"}:
        raise LearningError("OUTCOME_STATUS_INVALID", "Activation outcome must be applied or failed")
    pending = _verify_pending(config)
    runtime_hash = ""
    if runtime_active_path(config).exists():
        runtime = _load_json(runtime_active_path(config))
        runtime_hash = str(runtime.get("runtime_hash", ""))
    outcome = {
        "schema": SCHEMA,
        "status": status_value,
        "change_id": pending["change_id"],
        "transaction_id": pending["transaction_id"],
        "adapter_hash": pending["adapter_hash"],
        "runtime_hash": runtime_hash,
        "reason": reason.strip(),
        "recorded_at": int(time.time()),
    }
    outcome["outcome_hash"] = _sha256_bytes(
        (status_value + "|" + pending["change_id"] + "|" + pending["transaction_id"] + "|" + pending["adapter_hash"] + "|" + runtime_hash + "|" + reason.strip()).encode("utf-8")
    )
    path = state_root(config) / "activation_outcome.json"
    _atomic_json(path, outcome)
    return {"code": "LEARNING_ACTIVATION_OUTCOME_WRITTEN", "path": str(path), **outcome}


def status(config: dict[str, Any]) -> dict[str, Any]:
    lineage = load_lineage(config)
    active = _version(lineage, int(lineage.get("active_version", 0)))
    pending = None
    if pending_activation_path(config).exists():
        pending = _verify_pending(config)
    return {
        "code": "LEARNING_STATUS",
        "enabled": bool(config.get("enabled")),
        "active_version": int(lineage.get("active_version", 0)),
        "active": active,
        "pending_activation": pending,
        "version_count": len(lineage["versions"]),
    }


def _emit(value: dict[str, Any]) -> None:
    print(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    commands = parser.add_subparsers(dest="command", required=True)
    prep = commands.add_parser("prepare")
    prep.add_argument("--session", type=Path, required=True)
    prep.add_argument("--reason", required=True)
    prep.add_argument("--requested-by", required=True)
    training = commands.add_parser("train")
    training.add_argument("--transaction-id", required=True)
    evaluation = commands.add_parser("evaluate")
    evaluation.add_argument("--transaction-id", required=True)
    promotion = commands.add_parser("promote")
    promotion.add_argument("--transaction-id", required=True)
    promotion.add_argument("--evaluation", type=Path, required=True)
    staging = commands.add_parser("stage-activation")
    staging.add_argument("--transaction-id", required=True)
    staging.add_argument("--evaluation", type=Path, required=True)
    staging.add_argument("--change-id", required=True)
    commands.add_parser("prepare-runtime")
    commands.add_parser("commit-pending")
    abort = commands.add_parser("abort-pending")
    abort.add_argument("--reason", required=True)
    commands.add_parser("runtime-spec")
    outcome = commands.add_parser("write-outcome")
    outcome.add_argument("--status", choices=("applied", "failed"), required=True)
    outcome.add_argument("--reason", default="")
    commands.add_parser("status")
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config.resolve())
        if args.command == "prepare":
            result = prepare(config, args.session, args.reason, args.requested_by)
        elif args.command == "train":
            result = train(config, args.transaction_id)
        elif args.command == "evaluate":
            result = evaluate_candidate(config, args.transaction_id)
        elif args.command == "promote":
            result = promote(config, args.transaction_id, args.evaluation)
        elif args.command == "stage-activation":
            result = stage_activation(config, args.transaction_id, args.evaluation, args.change_id)
        elif args.command == "prepare-runtime":
            result = prepare_runtime(config)
        elif args.command == "commit-pending":
            result = commit_pending(config)
        elif args.command == "abort-pending":
            result = abort_pending(config, args.reason)
        elif args.command == "runtime-spec":
            result = runtime_spec(config)
        elif args.command == "write-outcome":
            result = write_activation_outcome(config, args.status, args.reason)
        else:
            result = status(config)
        _emit(result)
        return 0
    except LearningError as exc:
        _emit({"code": exc.code, "error": exc.message})
        return 2
    except Exception as exc:
        _emit({"code": "UNEXPECTED_FAILURE", "error": f"{type(exc).__name__}: {exc}"})
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
