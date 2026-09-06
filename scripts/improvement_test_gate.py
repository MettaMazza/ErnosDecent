#!/usr/bin/env python3
"""Hash-frozen, self-authored acceptance and live-E2E test transactions.

Echo may author a new regression and E2E test, but the implementation cannot start
until the unchanged body demonstrably fails the exact regression bytes. Once frozen,
the tests are immutable. The mandatory source gate runs the regression; the runtime
supervisor runs both tests against the replacement before committing the upgrade.
"""

from __future__ import annotations

import argparse
import ast
import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "config" / "improvements"
STAGING = STATE / "staging"
FROZEN = STATE / "frozen"
COMPLETED = STATE / "completed"
ABORTED = STATE / "aborted"
RESOLVED = STATE / "resolved"
SUPERSEDED = STATE / "superseded"
ACTIVE = STATE / "active.json"
WORKFLOW = STAGING / "workflow.json"
PLAN_BODY = STAGING / "plan_body.md"
PLAN_DOCUMENT = STAGING / "implementation_plan.md"
PLAN_SCAFFOLD_REQUIRED = STAGING / "plan_scaffold_required"
TRANSPORT_TEMPLATE_RECEIPT = STAGING / "transport_template.json"
SAFE_NAME = re.compile(r"^[a-z][a-z0-9_]{2,63}$")
CRITERION = re.compile(r"^\s*\[([a-z][a-z0-9_]{2,63})\]\s+(.+?)\s*$")
HASH = re.compile(r"^[0-9a-f]{64}$")
MAX_TEST_BYTES = 96_000
MAX_PLAN_BYTES = 48_000
MIN_DISCOVERED_SOURCE_FILES = 2
INCOMPLETE_ARTIFACT = re.compile(
    r"\b(stub|placeholder|dummy|mock(?:ed|ing)?|simulat(?:e|ed|ion)|todo|fixme|not[ -]implemented)\b",
    re.IGNORECASE,
)
SEMANTIC_STOPWORDS = {
    "about", "after", "against", "also", "and", "before", "being", "both",
    "can", "from", "into", "its", "must", "new", "not", "once", "only",
    "should", "that", "the", "their", "then", "this", "through", "using",
    "when", "where", "which", "while", "with", "without",
}


class GateError(RuntimeError):
    """A machine-classifiable gate rejection with a separate human diagnostic."""

    def __init__(self, message: str, *, code: str = "GATE_REJECTED") -> None:
        super().__init__(message)
        self.code = code


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_digest(path: Path) -> str:
    return digest(path.read_bytes())


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".tmp.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def load_record(path: Path) -> dict:
    if not path.is_file() or path.is_symlink():
        raise GateError(f"missing or unsafe record: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GateError(f"malformed record {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise GateError(f"record is not an object: {path}")
    return value


def decode_text(encoded: str, label: str, maximum: int) -> str:
    try:
        value = base64.b64decode(encoded, validate=True).decode("utf-8")
    except (ValueError, UnicodeDecodeError) as exc:
        raise GateError(f"{label} encoding is invalid") from exc
    if not value.strip() or len(value.encode("utf-8")) > maximum:
        raise GateError(f"{label} must be non-empty and no larger than {maximum} UTF-8 bytes")
    return value.strip()


def safe_relative_path(value: str, *, must_exist: bool) -> tuple[str, Path]:
    relative = Path(value.strip())
    if not value.strip() or relative.is_absolute() or ".." in relative.parts:
        raise GateError(f"unsafe repository-relative path: {value!r}")
    resolved = (ROOT / relative).resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise GateError(f"path escapes repository: {value!r}") from exc
    if must_exist and (not resolved.is_file() or resolved.is_symlink()):
        raise GateError(f"path is not a regular source file: {value}")
    return str(resolved.relative_to(ROOT.resolve())), resolved


def is_test_or_gate_path(relative: str) -> bool:
    lowered = relative.lower()
    name = Path(lowered).name
    return (
        lowered.startswith("tests/")
        or "/tests/" in lowered
        or name.startswith("test_")
        or lowered.startswith("config/improvements/")
        or relative == "scripts/improvement_test_gate.py"
    )


def is_operator_trust_root(relative: str) -> bool:
    lowered = relative.lower()
    return lowered in {
        "build.sh",
        "upgrade.sh",
        "run_node.sh",
        "scripts/run_mandatory_regressions.sh",
        "config/upgrades/mandatory-regressions.sha256",
        "scripts/improvement_test_gate.py",
        "decent_agent/compiler_tool.ep",
        "decent_agent/tools.ep",
        "decent_agent/react_loop.ep",
        "decent_agent/prompt.ep",
        "decent_agent/llm.ep",
        "decent_agent/rights.ep",
        "decent_agent/run_test.sh",
    }


def workflow_record() -> dict:
    return load_record(WORKFLOW)


def discovery_source_paths(record: dict) -> list[str]:
    entries = record.get("discovery", [])
    if not isinstance(entries, list):
        raise GateError("workflow discovery ledger is malformed")
    result: list[str] = []
    for entry in entries:
        if (
            isinstance(entry, dict)
            and entry.get("mode") in {"read", "read_range"}
            and isinstance(entry.get("path"), str)
            and not is_test_or_gate_path(entry["path"])
            and entry["path"] not in result
        ):
            result.append(entry["path"])
    return result


def investigation_evidence(record: dict, kind: str) -> list[dict]:
    entries = record.get("investigation_evidence", [])
    if not isinstance(entries, list):
        raise GateError("workflow investigation evidence is malformed")
    return [entry for entry in entries if isinstance(entry, dict) and entry.get("kind") == kind]


def concrete_objective(objective: str) -> str:
    """Return Echo's selected feature without generic-request/exclusion pollution."""
    start_marker = "[CONCRETE FEATURE SELECTED BY ECHO]"
    end_marker = "[/CONCRETE FEATURE SELECTED BY ECHO]"
    start = objective.find(start_marker)
    if start < 0:
        return objective
    start += len(start_marker)
    end = objective.find(end_marker, start)
    if end < 0:
        return objective
    selected = objective[start:end].strip()
    return selected or objective


def objective_requires_discord_retrieval(objective: str) -> bool:
    """Return whether the immutable objective depends on the live Discord read path."""
    lowered = concrete_objective(objective).lower()
    return "discord" in lowered and any(
        marker in lowered
        for marker in ("retrieval", "retrieve", "read", "channel", "message", "scavenger")
    )


def objective_requires_session_transcript(objective: str) -> bool:
    """Return whether the objective consumes a real persisted session transcript."""
    lowered = concrete_objective(objective).lower()
    return any(marker in lowered for marker in ("session id", "session_id")) and any(
        marker in lowered
        for marker in ("transcript", "session summary", "summar", "session metadata", "session store")
    )


def objective_requires_session_label(objective: str) -> bool:
    """Return whether the selected feature binds a supplied label to a real session."""
    lowered = concrete_objective(objective).lower()
    return any(marker in lowered for marker in ("session id", "session_id")) and any(
        marker in lowered for marker in ("label", "human-readable purpose", "human readable purpose")
    ) and any(marker in lowered for marker in ("persist", "attach", "associate", "registry"))


def objective_requires_session_lookup(objective: str) -> bool:
    """Return whether the surface resolves a session title to its exact ID."""
    lowered = concrete_objective(objective).lower()
    has_session_id = any(marker in lowered for marker in ("session id", "session_id"))
    has_title = "title" in lowered
    has_resolution = any(
        marker in lowered
        for marker in ("lookup", "look up", "retrieve", "resolve", "find", "return")
    )
    return has_session_id and has_title and has_resolution


def objective_requires_session_validation(objective: str) -> bool:
    """Return whether the surface checks if an exact session ID is registered."""
    lowered = concrete_objective(objective).lower()
    has_session_id = any(marker in lowered for marker in ("session id", "session_id"))
    has_validation = any(
        marker in lowered
        for marker in ("validate", "validator", "exists", "existence", "session integrity")
    )
    has_registry = any(marker in lowered for marker in ("registry", "registered", "system"))
    return has_session_id and has_validation and has_registry


def objective_requires_session_metadata_lookup(objective: str) -> bool:
    """Return whether an exact session ID must yield real registry metadata."""
    lowered = concrete_objective(objective).lower()
    has_session_id = any(marker in lowered for marker in ("session id", "session_id"))
    has_metadata = "metadata" in lowered
    has_lookup = any(
        marker in lowered
        for marker in ("lookup", "look up", "find", "return", "retrieve", "verify")
    )
    return has_session_id and has_metadata and has_lookup


def objective_uses_marker_transcript(objective: str) -> bool:
    """Return whether a deterministic text fixture is a real input for the surface."""
    if objective_requires_session_transcript(objective) or objective_requires_discord_retrieval(objective):
        return False
    lowered = concrete_objective(objective).lower()
    return bool(explicit_marker_examples(objective)) or any(
        marker in lowered for marker in ("transcript", "text input", "lesson", "correction")
    )


def objective_invocation_fixture(objective: str) -> str:
    """Select one controller-owned, typed production invocation fixture."""
    if objective_requires_discord_retrieval(objective):
        return "configured_discord_channel"
    if objective_requires_session_lookup(objective):
        return "active_session_title_queries"
    if objective_requires_session_label(objective):
        return "active_session_id_and_label"
    if objective_requires_session_metadata_lookup(objective):
        return "existing_missing_session_metadata"
    if objective_requires_session_transcript(objective):
        return "active_session_id"
    if objective_requires_session_validation(objective):
        return "existing_and_missing_session_ids"
    if objective_uses_marker_transcript(objective):
        return "marker_transcript"
    return "no_arguments"


def required_objective_discovery_paths(objective: str) -> list[str]:
    """Map explicit cross-component objectives to their current trust boundaries.

    A numeric minimum catches shallow investigations but cannot prove that the files
    actually responsible for a requested integration were inspected.  These paths
    are controller-owned requirements, so a model cannot satisfy a Discord feature
    by reading two unrelated files and freezing an impossible plan.
    """
    lowered = concrete_objective(objective).lower()
    surfaces = objective_callable_surfaces(objective)
    required: list[str] = []
    if surfaces:
        # Every registered self-authored tool is implemented in the bounded extension
        # registry and every generic acceptance contract requires independent durable
        # readback. These are ownership facts, not model-selected filenames.
        required.extend(("decent_agent/self_extensions.ep", "decent_agent/memory.ep"))
    if "durable memory" in lowered:
        required.append("decent_agent/memory.ep")
    if objective_requires_session_lookup(objective):
        required.append("decent_agent/session.ep")
    if (
        objective_requires_session_transcript(objective)
        or objective_requires_session_label(objective)
        or objective_requires_session_metadata_lookup(objective)
        or objective_requires_session_validation(objective)
    ):
        required.extend(
            (
                "decent_agent/self_extensions.ep",
                "decent_agent/session.ep",
                "decent_agent/memory.ep",
                "decent_agent/tools.ep",
            )
        )
    if objective_requires_discord_retrieval(objective):
        required.extend(
            (
                "decent_agent/self_extensions.ep",
                "decent_agent/tools.ep",
                "decent_net/bridge_rpc.ep",
                "decent_net/discord_bridge.py",
            )
        )
    return list(dict.fromkeys(required))


def required_objective_production_paths(objective: str) -> list[str]:
    """Controller-known production owners for exact cross-component objectives."""
    if objective_callable_surfaces(objective):
        # The core tools controller dispatches registered self-authored actions into
        # this sole non-sealed production owner. Never ask the model to guess it.
        return ["decent_agent/self_extensions.ep"]
    return []


def required_objective_acceptance(objective: str, surface: str = "") -> str:
    """Controller-authored observable contract for every registered capability."""
    surfaces = objective_callable_surfaces(objective)
    surface = surface or (surfaces[0] if surfaces else "")
    if not surface:
        return ""
    markers = objective_marker_fixtures(objective)
    marker_text = " and ".join(
        f"[{family}: {key} | {value}]" for family, key, value in markers
    )
    fixture = objective_invocation_fixture(objective)
    if fixture == "configured_discord_channel":
        observable = (
            f"The configured Discord channel is retrieved through the real live bridge and {surface} "
            f"returns the exact {surface}:ok success prefix."
        )
    elif fixture == "active_session_title_queries":
        observable = (
            f"The current persisted session is resolved once by its exact title and once by a "
            f"controller-proven unique title substring; {surface} returns the exact {surface}:ok "
            "success prefix and the same exact session ID for both calls."
        )
    elif fixture == "active_session_id_and_label":
        observable = (
            f"The current persisted session is addressed using its exact real session ID and an explicit "
            f"nonempty human-readable label; {surface} returns the exact {surface}:ok success prefix "
            "with that exact session ID and label."
        )
    elif fixture == "active_session_id":
        observable = (
            f"The current persisted session transcript is consumed using its real session ID and {surface} "
            f"returns the exact {surface}:ok success prefix with that session ID and a nonzero records count."
        )
    elif fixture == "existing_missing_session_metadata":
        observable = (
            f"The real {surface} production call accepts the current persisted session ID and returns "
            f"the exact {surface}:ok success prefix with that exact ID, title, model, and records count; "
            f"a controller-proven missing ID returns the exact {surface}:not_found result with that missing ID."
        )
    elif fixture == "existing_and_missing_session_ids":
        observable = (
            f"The real {surface} production call accepts the current persisted session ID and a "
            "controller-proven missing session ID; it returns the exact "
            f"{surface}:ok success prefix with exists:true for the real ID and exists:false for the missing ID."
        )
    elif fixture == "marker_transcript":
        observable = (
            f"The controller marker transcript is consumed through the real {surface} boundary and returns "
            f"the exact {surface}:ok success prefix with its observable result."
        )
    else:
        observable = (
            f"The real registered {surface} production call returns the exact {surface}:ok success prefix "
            "with its externally observable result."
        )
    lines = [f"[observable_result] {observable}"]
    if marker_text:
        lines.append(
            f"[marker_persistence] {marker_text} are persisted to durable memory and independently retrievable."
        )
    else:
        lines.append(
            f"[durable_effect] The production call persists a {surface} result under the durable key {surface}, "
            "and the live system independently retrieves that exact key after the call."
        )
    return "\n".join(lines)


def objective_interface_markers(objective: str) -> list[str]:
    """Exact callable/call-site names that must survive investigation compaction."""
    markers: list[str] = []
    if objective_requires_discord_retrieval(objective):
        # Include the language idioms needed to compose the integration, not only the
        # callee names.  Local models otherwise tend to fall back to Python/C syntax
        # after compaction even when the correct APIs were discovered earlier.
        markers.extend(
            (
                "bridge_enqueue",
                "bridge_wait_result",
                "read_channel",
                "storage_db",
                "map_get_val",
                "or else",
                "int_to_string",
                "concat(",
            )
        )
    if objective_requires_session_lookup(objective):
        markers.extend(
            (
                "session_manager_resolve_id",
                'map_get_val(ctx and "sessions")',
                "memory_store",
                "string_length",
                "concat(",
            )
        )
    if objective_requires_session_transcript(objective) or objective_requires_session_label(objective):
        markers.extend(
            (
                'map_get_val(ctx and "sessions")',
                'and "sessions")',
                'map_get_val(sess and "messages")',
                'map_get_val(msg_map and "content")',
                "memory_store",
                "map_get_val",
                "length_list",
            )
        )
    return list(dict.fromkeys(markers))


def exact_interface_evidence(record: dict) -> list[str]:
    """Extract bounded, hash-verified source lines needed after context compaction."""
    discovered = discovery_source_paths(record)
    entries = {
        entry.get("path"): entry
        for entry in record.get("discovery", [])
        if isinstance(entry, dict) and entry.get("path") in discovered
    }
    markers = objective_interface_markers(str(record.get("objective", "")))
    evidence: list[str] = []
    for relative in discovered:
        path = ROOT / relative
        entry = entries.get(relative, {})
        if not path.is_file() or path.is_symlink():
            raise GateError(f"investigated source is no longer a regular file: {relative}")
        current_hash = file_digest(path)
        if current_hash != entry.get("sha256"):
            raise GateError(
                f"investigated source changed after its recorded read: {relative}; "
                "reread the exact path before planning so interface evidence is current"
            )
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        selected: set[int] = set()
        for index, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("import ") and any(
                token in stripped for token in ("bridge_rpc", "memory", "session")
            ):
                selected.add(index)

        # Pick evidence per required marker rather than taking the first N textual
        # matches.  The old first-N policy retained many unrelated storage calls and
        # silently dropped the later, working Discord bridge call site.
        for marker in markers:
            candidates: list[tuple[int, int]] = []
            for index, line in enumerate(lines):
                stripped = line.strip()
                if marker not in stripped:
                    continue
                score = 20
                if stripped.startswith("define "):
                    # A callable definition is the authoritative arity/type contract.
                    # Keep it ahead of ordinary call sites; special working integration
                    # blocks below still receive a larger score and are retained too.
                    score += 300
                else:
                    score += 120
                nearby = "\n".join(lines[max(0, index - 2):min(len(lines), index + 4)])
                if "bridge_enqueue" in nearby and "read_channel" in nearby:
                    score += 500
                if marker in {"int_to_string", "concat("} and "int_to_string" in stripped and "concat(" in stripped:
                    score += 180
                candidates.append((score, index))
            for _, index in sorted(candidates, reverse=True)[:2]:
                selected.add(index)
                # Preserve the complete small working call-site block.  This captures
                # the database acquisition, enqueue arguments, and wait signature as
                # one usable example instead of isolated identifiers.
                nearby = "\n".join(lines[max(0, index - 1):min(len(lines), index + 5)])
                if "bridge_enqueue" in nearby and "read_channel" in nearby:
                    selected.update(range(max(0, index - 1), min(len(lines), index + 5)))

        if not selected:
            first = next((line.strip() for line in lines if line.strip()), "<empty file>")
            evidence.append(f"- `{relative}:1`: `{first.replace('`', chr(39))[:500]}`")
            continue
        for index in sorted(selected):
            stripped = lines[index].strip()
            if not stripped:
                continue
            safe_line = stripped.replace("`", "'")[:500]
            evidence.append(f"- `{relative}:{index + 1}`: `{safe_line}`")
    missing = [marker for marker in markers if not any(marker in line for line in evidence)]
    if missing:
        raise GateError(
            "investigation did not retain exact callable/call-site evidence for: "
            + ",".join(missing)
            + ". Search and read the current defining/calling source before planning"
        )
    return evidence


def verify_objective_investigation(record: dict) -> None:
    """Require requested reference/call-site proof before discovery can freeze."""
    objective = str(record.get("objective", "")).lower()
    needs_language = "string primitive" in objective or "language primitive" in objective
    needs_callsites = "working call site" in objective or "working call-site" in objective
    if needs_language and not investigation_evidence(record, "language_reference"):
        raise GateError(
            "the immutable objective requires exact language-primitive investigation; "
            "call lookup_ernos with the relevant primitive family before planning"
        )
    callsites = investigation_evidence(record, "callsite_search")
    distinct_queries = {str(entry.get("query", "")).lower() for entry in callsites}
    if needs_callsites and len(distinct_queries) < 3:
        raise GateError(
            "the immutable objective requires working-call-site investigation; "
            f"record at least 3 distinct successful codebase_search queries before planning "
            f"(recorded={len(distinct_queries)})"
        )
    discovered = set(discovery_source_paths(record))
    missing_paths = [
        path for path in required_objective_discovery_paths(str(record.get("objective", "")))
        if path not in discovered
    ]
    if missing_paths:
        raise GateError(
            "the immutable objective depends on production interfaces that have not been read: "
            + ",".join(missing_paths)
            + ". The objective requires an exact read of "
            + ",".join(missing_paths)
            + " with codebase_read before planning; "
            "the controller will not infer "
            "cross-component dependencies from an unrelated file count"
        )
    semantic_requirements: list[tuple[str, tuple[str, ...], str]] = []
    if "context value" in objective:
        semantic_requirements.append(("context value", ("memory_mgr", "map_get_val"), "memory_mgr or map_get_val"))
    if "registry function" in objective:
        semantic_requirements.append(("registry function", ("self_extensions_execute", "self_extensions_action_known"), "self_extensions_execute or self_extensions_action_known"))
    if "persistence api" in objective:
        semantic_requirements.append(("persistence API", ("memory_store", "memory_tier_tool"), "memory_store or memory_tier_tool"))
    if needs_language:
        language_queries = {
            str(entry.get("query", "")).lower()
            for entry in investigation_evidence(record, "language_reference")
        }
        if not any(any(token in query for token in ("string_index_of", "substring", "string_trim", "string_length")) for query in language_queries):
            raise GateError(
                "the immutable objective requires an exact string-primitive receipt; "
                "call lookup_ernos for a concrete primitive such as string_index_of, substring, string_trim, or string_length"
            )
    missing_semantic = [
        f"{label} ({guidance})"
        for label, tokens, guidance in semantic_requirements
        if not any(any(token in query for token in tokens) for query in distinct_queries)
    ]
    if missing_semantic:
        raise GateError(
            "working-call-site investigation is missing required semantic interface receipt(s): "
            + ", ".join(missing_semantic)
            + ". Run successful codebase_search calls for those exact current interfaces before planning"
        )


def plan_discovery_paths(record: dict, content: str) -> list[str]:
    """Return the immutable discovery set bound when the plan was approved.

    Later evaluator work may inspect a compiler, runner, protocol adapter, or other
    supporting interface. Those reads remain provenance-recorded, but cannot
    retroactively invalidate an approved plan and create a phase deadlock.

    Workflows created before this snapshot existed are recovered from the exact
    discovered paths already retained in their previously accepted plan body.
    """
    snapshot = record.get("plan_discovery_paths")
    if snapshot is not None:
        if not isinstance(snapshot, list) or any(not isinstance(path, str) for path in snapshot):
            raise GateError("workflow plan discovery snapshot is malformed")
        if len(snapshot) < MIN_DISCOVERED_SOURCE_FILES:
            raise GateError(
                f"plan discovery snapshot requires at least {MIN_DISCOVERED_SOURCE_FILES} distinct source files"
            )
        return list(dict.fromkeys(snapshot))
    discovered = discovery_source_paths(record)
    if record.get("state") != "investigating" and PLAN_BODY.is_file():
        recovered = [path for path in discovered if path in content]
        if len(recovered) >= MIN_DISCOVERED_SOURCE_FILES:
            return recovered
    return discovered


PLAN_HEADINGS = (
    "Objective",
    "Investigation Findings",
    "Production Surface",
    "Implementation",
    "Files",
    "Tests",
    "Risks and Rollback",
)


def plan_callable_surfaces(content: str) -> list[str]:
    sections = re.split(r"^##\s+", content, flags=re.MULTILINE)
    production_section = next(
        (part for part in sections if part.lower().startswith("production surface\n")), ""
    )
    inline_surfaces = [marker.strip() for marker in re.findall(r"`([^`]{3,160})`", production_section)]
    generic = {"main", "tool", "tools", "handler", "process"}
    return list(dict.fromkeys(
        marker.rstrip("()")
        for marker in inline_surfaces
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{2,}(?:\(\))?", marker)
        and marker.rstrip("()").lower() not in generic
    ))


def objective_callable_surfaces(objective: str) -> list[str]:
    """Extract identifiers that the objective actually designates as a surface.

    An improvement objective also names expected output literals and lifecycle tools.
    Treating every underscore-delimited token as a callable made an output prefix such
    as ``e2e_probe:`` compete with a separately named tool such as
    ``e2e_echo_probe``.  Prefer explicit "tool named/called" language; otherwise
    accept exact backticked identifiers and the identifier immediately following an
    implementation verb.  A generic objective with no named surface remains valid;
    ordinary prose following verbs must never be promoted into an identifier.
    """
    objective = concrete_objective(objective)
    identifier = r"[A-Za-z][A-Za-z0-9_]{2,63}"
    named = re.findall(
        rf"\b(?:tool|callable|command|surface|feature|capability)\s+"
        rf"(?:named|called)\s+[`\"']?({identifier})[`\"']?",
        objective,
        flags=re.IGNORECASE,
    )
    reserved = {
        "and", "the", "real", "new", "one", "useful", "feature", "capability",
        "tool", "command", "surface", "implementation", "production", "complete",
    }
    if named:
        return list(dict.fromkeys(item for item in named if item.lower() not in reserved))

    explicit: list[str] = []
    explicit.extend(
        match
        for match in re.findall(r"[`\"']([^`\"']+)[`\"']", objective)
        if re.fullmatch(identifier, match)
    )
    explicit.extend(
        re.findall(
            rf"\b(?:implement|add|create|build|repair|upgrade)\s+"
            rf"(?:(?:exactly|a|an|new|complete|registered|production)\s+)*"
            rf"[`\"']?([A-Za-z][A-Za-z0-9]*_[A-Za-z0-9_]+)[`\"']?",
            objective,
            flags=re.IGNORECASE,
        )
    )
    return list(dict.fromkeys(item for item in explicit if item.lower() not in reserved))


def registered_tool_surface(content: str) -> str | None:
    """Return the exact planned surface when the plan selects AI EVAL_TOOL IPC."""
    sections = re.split(r"^##\s+", content, flags=re.MULTILINE)
    tests_section = next((part for part in sections if part.lower().startswith("tests\n")), "")
    surfaces = plan_callable_surfaces(content)
    if "AI EVAL_TOOL" in tests_section and surfaces:
        # Plans commonly name the public tool first and its internal dispatcher
        # second. AI EVAL_TOOL must receive the declared public boundary.
        return surfaces[0]
    return None


def registered_tool_transport_source(surface: str) -> str:
    """Canonical authenticated raw-TCP evaluator client for a frozen tool surface."""
    return f'''import base64
import json
import os
import socket
from urllib.parse import urlparse

SURFACE = {surface!r}
PREFIX = "eval_tool:ok,name:" + SURFACE + ",result_b64:"

def _endpoint():
    raw = os.environ.get("ERNOS_NODE_URL", "http://127.0.0.1:5000")
    parsed = urlparse(raw if "://" in raw else "//" + raw)
    return parsed.hostname or "127.0.0.1", parsed.port or 5000

def _ipc(command):
    token_path = os.path.expanduser("~/.ernosdecent/ipc-token")
    with open(token_path, "r", encoding="utf-8") as handle:
        token = handle.read().strip()
    with socket.create_connection(_endpoint(), timeout=10) as connection:
        connection.sendall(("AUTH " + token + " " + command).encode("utf-8"))
        connection.shutdown(socket.SHUT_WR)
        chunks = []
        while True:
            chunk = connection.recv(65536)
            if not chunk:
                break
            chunks.append(chunk)
    return b"".join(chunks).decode("utf-8")

def eval_planned_tool(*args):
    encoded = base64.b64encode(json.dumps(list(args)).encode("utf-8")).decode("ascii")
    response = _ipc("AI EVAL_TOOL " + SURFACE + " " + encoded)
    assert response.startswith(PREFIX), "planned production tool did not return its authenticated result: " + response
    result = base64.b64decode(response[len(PREFIX):]).decode("utf-8")
    print("EVAL_BOUNDARY_OK name=" + SURFACE)
    return result

def get_memory():
    return _ipc("AGENT GET MEMORY")

def configured_discord_channel():
    root = os.environ.get("ERNOS_SOURCE_ROOT", os.getcwd())
    with open(os.path.join(root, "config", "platforms.json"), "r", encoding="utf-8") as handle:
        channel = str(json.load(handle).get("discord", {{}}).get("channel", "")).strip()
    assert channel.isdigit(), "configured Discord channel ID is unavailable"
    return channel

def active_session_id():
    root = os.environ.get("ERNOS_SOURCE_ROOT", os.getcwd())
    tracker = os.path.join(root, "config", "sessions", "active_session.txt")
    with open(tracker, "r", encoding="utf-8") as handle:
        session_id = handle.read().strip()
    assert session_id and "/" not in session_id and "\\\\" not in session_id, "active session ID is unavailable"
    assert os.path.isfile(os.path.join(root, "config", "sessions", session_id + ".json")), "active session record is unavailable"
    return session_id

def active_session_title_queries():
    root = os.environ.get("ERNOS_SOURCE_ROOT", os.getcwd())
    sessions_dir = os.path.join(root, "config", "sessions")
    session_id = active_session_id()
    records = []
    for filename in os.listdir(sessions_dir):
        if not filename.endswith(".json"):
            continue
        path = os.path.join(sessions_dir, filename)
        try:
            with open(path, "r", encoding="utf-8") as handle:
                record = json.load(handle)
        except (OSError, ValueError, TypeError):
            continue
        record_id = str(record.get("id", "")).strip()
        title = str(record.get("title", "")).strip()
        if record_id and title:
            records.append((record_id, title))
    active_titles = [title for record_id, title in records if record_id == session_id]
    assert len(active_titles) == 1, "active session title is unavailable"
    exact_title = active_titles[0]
    exact_matches = [record_id for record_id, title in records if title.casefold() == exact_title.casefold()]
    assert exact_matches == [session_id], "active session title is not unique"
    candidates = []
    for width in range(4, len(exact_title)):
        candidates.extend((exact_title[-width:], exact_title[:width]))
    for candidate in candidates:
        candidate = candidate.strip()
        if len(candidate) < 4 or candidate.casefold() == exact_title.casefold():
            continue
        matches = [record_id for record_id, title in records if candidate.casefold() in title.casefold()]
        if matches == [session_id] and candidate.casefold() != session_id.casefold():
            return session_id, exact_title, candidate
    raise AssertionError("active session has no controller-proven unique title substring")

def existing_and_missing_session_ids():
    root = os.environ.get("ERNOS_SOURCE_ROOT", os.getcwd())
    sessions_dir = os.path.join(root, "config", "sessions")
    existing = active_session_id()
    known = {{
        filename[:-5]
        for filename in os.listdir(sessions_dir)
        if filename.endswith(".json")
    }}
    missing = "session_controller_proven_missing"
    suffix = 0
    while missing in known:
        suffix += 1
        missing = "session_controller_proven_missing_" + str(suffix)
    assert existing in known and missing not in known
    return existing, missing

def existing_missing_session_metadata():
    root = os.environ.get("ERNOS_SOURCE_ROOT", os.getcwd())
    sessions_dir = os.path.join(root, "config", "sessions")
    active = active_session_id()
    complete = []
    known = set()
    for filename in sorted(os.listdir(sessions_dir)):
        if not filename.endswith(".json"):
            continue
        path = os.path.join(sessions_dir, filename)
        try:
            with open(path, "r", encoding="utf-8") as handle:
                record = json.load(handle)
        except (OSError, ValueError, TypeError):
            continue
        session_id = str(record.get("id", "")).strip()
        title = str(record.get("title", "")).strip()
        model = str(record.get("model", "")).strip()
        messages = record.get("messages", [])
        if session_id:
            known.add(session_id)
        if session_id and title and model and isinstance(messages, list):
            complete.append((session_id, title, model, len(messages)))
    assert complete, "no persisted session has complete title/model/messages metadata"
    selected = next((item for item in complete if item[0] == active), complete[0])
    missing = "session_controller_proven_missing"
    suffix = 0
    while missing in known:
        suffix += 1
        missing = "session_controller_proven_missing_" + str(suffix)
    assert selected[0] in known and missing not in known
    return selected[0], missing, selected[1], selected[2], selected[3]
'''


def registered_tool_boundary_reached(output: str, surface: str) -> bool:
    """True only after the authenticated production evaluator decoded a real result."""
    return f"EVAL_BOUNDARY_OK name={surface}" in output


def registered_tool_argument_guidance(workflow: dict) -> str:
    objective = str(workflow.get("objective", ""))
    if objective_requires_discord_retrieval(objective):
        return (
            "This surface's real production argument is a Discord channel ID. Call "
            "eval_planned_tool(configured_discord_channel()); NEVER pass transcript text or marker "
            "fixtures as the channel argument. Evidence must come from the live bridge read. Use "
            "get_memory() to independently verify any durable lesson/correction values actually "
            "present in that channel."
        )
    if objective_requires_session_lookup(objective):
        return (
            "This surface takes exactly one title query. Set session_id, exact_title, unique_title = "
            "active_session_title_queries(); call eval_planned_tool(exact_title) and "
            "eval_planned_tool(unique_title), and require both results to contain the same exact session_id. "
            "The controller proves the exact title and substring each resolve uniquely in persisted state. "
            "Use get_memory() to independently verify the exact resolved ID and query provenance."
        )
    if objective_requires_session_label(objective):
        return (
            "This surface takes exactly two real production arguments: the existing persisted session ID "
            "and an explicit label. Set session_id = active_session_id() and label = "
            '"codex-e2e-checkpoint-label", then call eval_planned_tool(session_id, label). '
            "The implementation must verify that exact session through ctx.sessions, persist both exact "
            "values, and return both. Use get_memory() to independently verify both exact values."
        )
    if objective_requires_session_transcript(objective):
        return (
            "This surface's real production argument is one persisted session ID. Call "
            "eval_planned_tool(active_session_id()); never pass transcript text, a reconstructed path, "
            "or the evaluator session name. The implementation must load that exact production session, "
            "report a nonzero records count, and persist its summary under the plan-bound durable key."
        )
    if objective_requires_session_metadata_lookup(objective):
        return (
            "This surface takes exactly one session_id. Set existing_id, missing_id, title, model, records = "
            "existing_missing_session_metadata(); call eval_planned_tool(existing_id), then "
            "eval_planned_tool(missing_id), then eval_planned_tool(existing_id) again. Require the existing "
            "result to contain the exact ID, title, model, and records count, and the missing result to contain "
            "the exact surface:not_found code plus missing ID. Use get_memory() to verify the final exact metadata."
        )
    if objective_requires_session_validation(objective):
        return (
            "This surface takes exactly one session_id. Set existing_id, missing_id = "
            "existing_and_missing_session_ids(); call eval_planned_tool(existing_id), then "
            "eval_planned_tool(missing_id), then eval_planned_tool(existing_id) again for durable "
            "readback. Require exists:true only for the existing ID and exists:false only for the "
            "controller-proven missing ID. Use get_memory() to verify the final exact existing ID and result."
        )
    marker_contract = objective
    if PLAN_BODY.is_file() and not PLAN_BODY.is_symlink():
        marker_contract += "\n" + PLAN_BODY.read_text(encoding="utf-8", errors="replace")
    if objective_uses_marker_transcript(marker_contract):
        transcript = " ".join(
            f"[{family}: {key} | {value}]"
            for family, key, value in objective_marker_fixtures(marker_contract)
        )
        return (
            f"Call eval_planned_tool({json.dumps(transcript)}) with exactly one text argument."
        )
    return (
        "Call eval_planned_tool() with no arguments; the plan binds its observable result and durable key."
    )


def transport_template() -> None:
    workflow = workflow_record()
    if workflow.get("state") not in {"tests_authoring", "tests_validated"}:
        raise GateError("registered-tool transport template is available only during evaluator authoring")
    if not PLAN_BODY.is_file() or file_digest(PLAN_BODY) != workflow.get("plan_body_hash"):
        raise GateError("implementation plan bytes do not match the controller-recorded plan hash")
    surface = registered_tool_surface(PLAN_BODY.read_text(encoding="utf-8"))
    if not surface:
        raise GateError("the current plan does not define one exact AI EVAL_TOOL production surface")
    criteria = acceptance_criteria((STAGING / "acceptance.txt").read_text(encoding="utf-8"))
    names = ", ".join(f"test_{criterion_id}" for criterion_id in criteria)
    atomic_json(TRANSPORT_TEMPLATE_RECEIPT, {
        "version": 1,
        "plan_hash": workflow.get("plan_body_hash", ""),
        "surface": surface,
        "viewed_at": int(time.time()),
    })
    print(
        f"REGISTERED_TOOL_TRANSPORT_TEMPLATE surface={surface} required_tests={names}\n"
        "The controller prepends this client byte-for-byte to BOTH evaluator files. Submit the named "
        "tests only as standalone top-level `def test_<criterion_id>():` functions: no unittest class, "
        "imports, transport, or main block. The surface is already bound: call "
        + registered_tool_argument_guidance(workflow) + " NEVER pass the "
        "surface name and NEVER wrap the argument in a list. Call get_memory() for independent durable "
        "evidence. Any model-supplied transport copy is discarded before linting. Every test "
        "must assert the desired post-change output or durable effect. On unchanged source the canonical "
        "client's production-call assertion supplies the causal failure; NEVER assert an unknown, missing, "
        "unregistered, or error state.\n\n"
        + registered_tool_transport_source(surface)
    )


def scaffold_evaluators() -> None:
    """Generate the plan-bound behavioral evaluators the controller can know exactly.

    The model still owns the feature design and implementation. Boilerplate transport,
    real argument selection, acceptance names, exact requested output, and independent
    durable-memory evidence are controller facts and must not be regenerated through a
    probabilistic prose turn.
    """
    workflow = workflow_record()
    if workflow.get("state") != "tests_authoring":
        raise GateError("evaluator scaffold is available only during evaluator authoring")
    if not PLAN_BODY.is_file() or file_digest(PLAN_BODY) != workflow.get("plan_body_hash"):
        raise GateError("implementation plan bytes do not match the controller-recorded plan hash")
    plan = PLAN_BODY.read_text(encoding="utf-8")
    surface = registered_tool_surface(plan)
    if not surface:
        raise GateError("evaluator scaffold requires one exact registered AI EVAL_TOOL production surface")
    acceptance_path = STAGING / "acceptance.txt"
    if not acceptance_path.is_file() or acceptance_path.is_symlink():
        raise GateError("evaluator scaffold requires retained acceptance criteria")
    criteria = acceptance_criteria(acceptance_path.read_text(encoding="utf-8"))
    objective = str(workflow.get("objective", ""))
    contract = objective + "\n" + plan
    outputs = explicit_output_literals(contract)
    expected = f"{surface}:ok"
    if expected not in outputs:
        raise GateError(
            f"the frozen plan does not bind the observable `{expected}` result; restart evaluator authoring "
            "through improvement_plan_scaffold so implementation and evidence share one exact success contract"
        )
    markers = objective_marker_fixtures(contract)
    fixture = objective_invocation_fixture(objective)
    if objective_requires_discord_retrieval(objective):
        argument_lines = [
            "    channel_id = configured_discord_channel()",
            "    result = eval_planned_tool(channel_id)",
        ]
    elif objective_requires_session_lookup(objective):
        argument_lines = [
            "    session_id, exact_title, unique_title = active_session_title_queries()",
            "    exact_result = eval_planned_tool(exact_title)",
            "    result = eval_planned_tool(unique_title)",
        ]
    elif objective_requires_session_label(objective):
        argument_lines = [
            "    session_id = active_session_id()",
            '    label = "codex-e2e-checkpoint-label"',
            "    result = eval_planned_tool(session_id, label)",
        ]
    elif objective_requires_session_transcript(objective):
        argument_lines = [
            "    session_id = active_session_id()",
            "    result = eval_planned_tool(session_id)",
        ]
    elif objective_requires_session_metadata_lookup(objective):
        argument_lines = [
            "    existing_id, missing_id, title, model, records = existing_missing_session_metadata()",
            "    existing_result = eval_planned_tool(existing_id)",
            "    missing_result = eval_planned_tool(missing_id)",
            "    result = eval_planned_tool(existing_id)",
        ]
    elif objective_requires_session_validation(objective):
        argument_lines = [
            "    existing_id, missing_id = existing_and_missing_session_ids()",
            "    existing_result = eval_planned_tool(existing_id)",
            "    missing_result = eval_planned_tool(missing_id)",
            "    result = eval_planned_tool(existing_id)",
        ]
    elif fixture == "marker_transcript":
        transcript = " ".join(f"[{family}: {key} | {value}]" for family, key, value in markers)
        argument_lines = [f"    result = eval_planned_tool({transcript!r})"]
    else:
        argument_lines = ["    result = eval_planned_tool()"]

    regression_functions: list[str] = []
    e2e_functions: list[str] = []
    for criterion_id in criteria:
        regression_lines = [
            f"def test_{criterion_id}():",
            *argument_lines,
            f"    assert {expected!r} in result",
        ]
        e2e_lines = list(regression_lines)
        if objective_requires_session_lookup(objective):
            regression_lines.extend(
                (
                    f"    assert {expected!r} in exact_result",
                    "    assert session_id in exact_result",
                    "    assert session_id in result",
                    "    assert exact_title != unique_title",
                )
            )
            e2e_lines.extend(regression_lines[-4:])
            e2e_lines.extend(
                (
                    "    memory = get_memory()",
                    f"    assert {surface!r} in memory",
                    "    assert session_id in memory",
                    "    assert unique_title in memory",
                )
            )
        elif objective_requires_session_label(objective):
            regression_lines.extend(
                (
                    "    assert session_id in result",
                    "    assert label in result",
                )
            )
            e2e_lines.extend(regression_lines[-2:])
            e2e_lines.extend(
                (
                    "    memory = get_memory()",
                    f"    assert {surface!r} in memory",
                    "    assert session_id in memory",
                    "    assert label in memory",
                )
            )
        elif objective_requires_session_transcript(objective):
            regression_lines.extend(
                (
                    "    assert session_id in result",
                    "    assert \"records:\" in result",
                    "    assert \"records:0\" not in result",
                )
            )
            e2e_lines.extend(regression_lines[-3:])
            e2e_lines.extend(
                (
                    "    memory = get_memory()",
                    f"    assert {surface!r} in memory",
                    "    assert session_id in memory",
                )
            )
        elif objective_requires_session_metadata_lookup(objective):
            regression_lines.extend(
                (
                    f"    assert {expected!r} in existing_result",
                    "    assert existing_id in existing_result",
                    "    assert title in existing_result",
                    "    assert model in existing_result",
                    "    assert ('records:' + str(records)) in existing_result",
                    f"    assert {f'{surface}:not_found'!r} in missing_result",
                    "    assert missing_id in missing_result",
                )
            )
            e2e_lines.extend(regression_lines[-7:])
            e2e_lines.extend(
                (
                    "    memory = get_memory()",
                    f"    assert {surface!r} in memory",
                    "    assert existing_id in memory",
                    "    assert title in memory",
                    "    assert model in memory",
                    "    assert ('records:' + str(records)) in memory",
                )
            )
        elif objective_requires_session_validation(objective):
            regression_lines.extend(
                (
                    f"    assert {expected!r} in existing_result",
                    f"    assert {expected!r} in missing_result",
                    "    assert existing_id in existing_result",
                    "    assert 'exists:true' in existing_result",
                    "    assert missing_id in missing_result",
                    "    assert 'exists:false' in missing_result",
                    "    assert 'exists:false' not in existing_result",
                    "    assert 'exists:true' not in missing_result",
                )
            )
            e2e_lines.extend(regression_lines[-8:])
            e2e_lines.extend(
                (
                    "    memory = get_memory()",
                    f"    assert {surface!r} in memory",
                    "    assert existing_id in memory",
                    "    assert 'exists:true' in memory",
                )
            )
        if markers:
            regression_lines.append("    memory = get_memory()")
            e2e_lines.append("    memory = get_memory()")
            for family, key, value in markers:
                for lines in (regression_lines, e2e_lines):
                    lines.append(f"    marker = {f'[{family}: {key} | {value}]'!r}")
                    lines.append(f"    assert {key!r} in memory")
                    lines.append(f"    assert {value!r} in memory")
        elif not objective_requires_session_lookup(objective) and not objective_requires_session_transcript(objective) and not objective_requires_session_label(objective) and not objective_requires_session_metadata_lookup(objective) and not objective_requires_session_validation(objective):
            e2e_lines.extend(
                (
                    "    memory = get_memory()",
                    f"    assert {surface!r} in memory",
                )
            )
        regression_functions.append("\n".join(regression_lines))
        e2e_functions.append("\n".join(e2e_lines))
    regression_behavior = "\n\n".join(regression_functions)
    e2e_behavior = "\n\n".join(e2e_functions)

    atomic_json(TRANSPORT_TEMPLATE_RECEIPT, {
        "version": 1,
        "plan_hash": workflow.get("plan_body_hash", ""),
        "surface": surface,
        "viewed_at": int(time.time()),
        "source": "controller_scaffold",
    })
    regression_encoded = base64.b64encode(regression_behavior.encode("utf-8")).decode("ascii")
    e2e_encoded = base64.b64encode(e2e_behavior.encode("utf-8")).decode("ascii")
    write_artifact("regression", regression_encoded)
    write_artifact("e2e", e2e_encoded)
    print(
        f"IMPROVEMENT_EVALUATORS_SCAFFOLDED surface={surface} criteria={len(criteria)} "
        f"expected={expected} argument={fixture} "
        "evidence=real_tool_plus_independent_memory"
    )


def parse_plan(
    content: str, record: dict, *, required_discovery: list[str] | None = None
) -> list[str]:
    encoded = content.encode("utf-8")
    if len(encoded) < 500 or len(encoded) > MAX_PLAN_BYTES:
        raise GateError(f"implementation plan must be 500-{MAX_PLAN_BYTES} UTF-8 bytes")
    if re.search(r"^\s*[-*]\s*\[[ xX]\]", content, re.MULTILINE):
        raise GateError("plan body may not contain self-reported checkboxes; controller receipts own checklist state")
    missing = [heading for heading in PLAN_HEADINGS if not re.search(
        rf"^##\s+{re.escape(heading)}\s*$", content, re.MULTILINE | re.IGNORECASE
    )]
    if missing:
        raise GateError(f"implementation plan is missing required heading(s): {', '.join(missing)}")
    sections = re.split(r"^##\s+", content, flags=re.MULTILINE)
    files_section = next((part for part in sections if part.lower().startswith("files\n")), "")
    planned: list[str] = []
    for line in files_section.splitlines()[1:]:
        match = re.fullmatch(r"\s*-\s+([^:]+):\s+(.{20,})\s*", line)
        if not match:
            if line.strip():
                raise GateError("every Files entry must use '- repository/path: concrete reason and responsibility'")
            continue
        path_text = match.group(1).strip()
        if len(path_text) >= 2 and path_text.startswith("`") and path_text.endswith("`"):
            path_text = path_text[1:-1].strip()
        relative, _ = safe_relative_path(path_text, must_exist=False)
        if is_test_or_gate_path(relative):
            raise GateError(
                f"plan may not modify operator-sealed test/gate path: {relative}; "
                "do not invent, relocate, or list regression/E2E evaluator files anywhere in the plan. "
                "The controller owns those artifacts after improvement_test_begin; under ## Tests, "
                "describe only the desired behavior through the exact Production Surface"
            )
        if is_operator_trust_root(relative):
            guidance = ""
            if relative == "decent_agent/tools.ep":
                guidance = "; register complete self-authored tools through decent_agent/self_extensions.ep"
            raise GateError(f"plan may not modify operator-sealed deployment/controller path: {relative}{guidance}")
        if relative in planned:
            raise GateError(f"duplicate planned implementation path: {relative}")
        planned.append(relative)
    if not planned:
        raise GateError("implementation plan must name at least one production file under ## Files")
    discovered = (
        required_discovery
        if required_discovery is not None
        else plan_discovery_paths(record, content)
    )
    if len(discovered) < MIN_DISCOVERED_SOURCE_FILES:
        raise GateError(
            f"deep investigation requires reads of at least {MIN_DISCOVERED_SOURCE_FILES} distinct non-test source files"
        )
    objective = str(record.get("objective", "")).lower()
    if "durable memory" in objective and "decent_agent/memory.ep" not in discovered:
        raise GateError(
            "a durable-memory improvement requires an exact read of decent_agent/memory.ep "
            "before planning so persistence and retrieval use current production interfaces"
        )
    missing_refs = [path for path in discovered if path not in content]
    if missing_refs:
        raise GateError(
            "plan must retain every exact investigated source path; missing=" + ",".join(missing_refs)
        )
    allowed_paths = set(discovered) | set(planned)
    referenced_paths = set(re.findall(
        r"`((?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+\.(?:ep|py|js|ts|c|h|sh))`",
        content,
    ))
    unknown_paths = sorted(referenced_paths - allowed_paths)
    if unknown_paths:
        raise GateError(
            "plan contains an uninvestigated or non-planned backticked source path; "
            "use exact discovered bytes and declare every production implementation target under Files. "
            "Never name evaluator/test file paths in the plan: the controller creates those later from "
            "improvement_test_write. Unknown path(s): "
            + ",".join(unknown_paths)
        )
    production_section = next(
        (part for part in sections if part.lower().startswith("production surface\n")), ""
    )
    if not any(path in production_section for path in discovered):
        raise GateError("Production Surface must cite an exact investigated source path and its callable interface")
    callable_surfaces = plan_callable_surfaces(content)
    if not callable_surfaces:
        raise GateError(
            "Production Surface must name at least one exact backticked callable/tool/command identifier "
            "that the live E2E will invoke (for example `feature_name()` or `feature_tool`)"
        )
    tests_section = next((part for part in sections if part.lower().startswith("tests\n")), "")
    try:
        reject_incomplete_artifact(tests_section, "plan test strategy")
    except GateError as exc:
        raise GateError(str(exc)) from exc
    if re.search(r"\b(non[- ]existent|broken)\b", tests_section, re.IGNORECASE):
        raise GateError(
            "plan test strategy may not treat a missing/broken artifact as behavioral evidence; "
            "the regression must invoke the exact production surface and reach an assertion about its absent outcome"
        )
    if re.search(
        r"\b(?:asserts?|expects?|verifies?|checks?)\s+(?:an?\s+)?(?:error|failure|unknown)|"
        r"\bunknown\s+(?:action|tool|command)|"
        r"\b(?:unregistered|unimplemented|not[- ]yet[- ]implemented|not implemented)\b",
        tests_section,
        re.IGNORECASE,
    ):
        raise GateError(
            "plan test strategy may not assert the current missing/unknown/error state; "
            "both evaluators must assert the desired post-implementation production outcome and fail causally before the change"
        )
    if not any(marker in tests_section for marker in callable_surfaces):
        raise GateError(
            "Tests must cite the exact callable/tool/command identifier from Production Surface "
            "so the regression and live E2E cannot drift to a different helper"
        )
    registered_extension = (
        "decent_agent/self_extensions.ep" in planned
        or "self_extensions_execute" in production_section
        or re.search(r"\bregistered\s+self-extension\b", content, re.IGNORECASE) is not None
    )
    if registered_extension and "AI EVAL_TOOL" not in tests_section:
        raise GateError(
            "a registered self-extension plan must bind Tests to authenticated AI EVAL TOOL "
            "and the exact public tool identifier; call improvement_plan_scaffold after this rejection"
        )
    if int(record.get("version", 0)) >= 3:
        evidence_section = next(
            (part for part in sections if part.lower().startswith("exact interface evidence\n")), ""
        )
        missing_evidence_paths = [path for path in discovered if f"`{path}:" not in evidence_section]
        missing_evidence_markers = [
            marker for marker in objective_interface_markers(str(record.get("objective", "")))
            if marker not in evidence_section
        ]
        if missing_evidence_paths or missing_evidence_markers:
            raise GateError(
                "Exact Interface Evidence must preserve hash-verified source-line facts for every "
                "investigated path and required callable; missing_paths="
                + ",".join(missing_evidence_paths)
                + " missing_callables="
                + ",".join(missing_evidence_markers)
            )
        if int(record.get("version", 0)) >= 4 and objective_requires_discord_retrieval(
            str(record.get("objective", ""))
        ):
            working_patterns = {
                "Discord read_channel enqueue call": r"set\s+[A-Za-z_][A-Za-z0-9_]*\s+to\s+bridge_enqueue\([^`\n]*\"discord\"[^`\n]*\"read_channel\"",
                "bridge result wait call": r"(?:set|return)\s+[^`\n]*bridge_wait_result\(",
            }
            if int(record.get("version", 0)) >= 5:
                working_patterns["extension storage context"] = r"map_insert\([^`\n]*\"storage_db\""
            else:
                working_patterns["storage database acquisition"] = r"set\s+[A-Za-z_][A-Za-z0-9_]*\s+to\s+storage_get_db\(\)"
            missing_working_facts = [
                label for label, pattern in working_patterns.items()
                if re.search(pattern, evidence_section) is None
            ]
            if missing_working_facts:
                raise GateError(
                    "Exact Interface Evidence must retain the complete real Discord working call site; missing="
                    + ",".join(missing_working_facts)
                )
    return planned


def read_plan() -> None:
    record = workflow_record()
    active = load_record(ACTIVE) if ACTIVE.exists() else None
    if not PLAN_BODY.is_file():
        print(
            f"IMPROVEMENT_PLAN_PENDING state={record.get('state')} "
            f"source_reads={len(discovery_source_paths(record))} plan_version=0 "
            "next=improvement_plan_write; no plan bytes exist yet"
        )
        return
    refresh_plan_document(record, active)
    print(PLAN_DOCUMENT.read_text(encoding="utf-8"))


def plan_scaffold(surface_b64: str, production_path_b64s: list[str]) -> None:
    """Generate a canonical plan from the durable investigation ledger."""
    workflow = workflow_record()
    if workflow.get("state") != "investigating":
        raise GateError("plan scaffold is available only during the investigating phase")
    verify_objective_investigation(workflow)
    surface = decode_text(surface_b64, "production surface", 256).strip()
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{2,63}", surface):
        raise GateError("production surface must be one exact 3-64 character callable/tool identifier")
    objective = str(workflow.get("objective", "")).strip()
    explicit_objective_surfaces = set(objective_callable_surfaces(objective))
    if explicit_objective_surfaces and surface not in explicit_objective_surfaces:
        raise GateError(
            f"plan scaffold surface `{surface}` does not match the exact callable named in the durable objective; "
            f"expected one of={','.join(sorted(explicit_objective_surfaces))}. "
            "Copy the objective's identifier byte-for-byte; do not approximate or reconstruct it"
        )
    completed = completed_surface_match(surface)
    if completed is not None:
        resolve_already_completed(workflow, completed, surface=surface)
        return
    if not production_path_b64s:
        raise GateError("plan scaffold requires at least one investigated production path")
    production_paths: list[str] = []
    for encoded_path in production_path_b64s:
        path_text = decode_text(encoded_path, "production path", 2_000).strip()
        production_path, _ = safe_relative_path(path_text, must_exist=False)
        if production_path in production_paths:
            raise GateError(f"duplicate plan scaffold production path: {production_path}")
        production_paths.append(production_path)
    required_production_paths = workflow.get("required_production_paths", [])
    if not isinstance(required_production_paths, list) or any(
        not isinstance(path, str) for path in required_production_paths
    ):
        raise GateError("controller-owned production path state is malformed")
    if required_production_paths and production_paths != required_production_paths:
        raise GateError(
            "plan scaffold production paths contradict the controller-owned production owner; "
            f"required={','.join(required_production_paths)} submitted={','.join(production_paths)}. "
            "Use the exact registered candidate owner selected from durable transaction state",
            code="CANDIDATE_REPAIR_REQUIRED",
        )
    discovered = discovery_source_paths(workflow)
    missing_production = [path for path in production_paths if path not in discovered]
    if missing_production:
        raise GateError(
            "each plan scaffold production path must be one exact investigated source path; missing="
            + ",".join(missing_production)
            + "; discovered="
            + ",".join(discovered)
        )
    discovery_by_path = {
        item["path"]: item
        for item in workflow.get("discovery", [])
        if isinstance(item, dict) and item.get("path") in discovered
    }
    findings = []
    for path in discovered:
        item = discovery_by_path.get(path, {})
        findings.append(
            f"- `{path}` was read from current source and hash-recorded "
            f"({item.get('sha256', 'unknown hash')}, {item.get('size', 'unknown')} bytes); "
            "its exact interfaces and responsibilities constrain this implementation."
        )
    primary_path = production_paths[0]
    file_entries = "\n".join(
        f"- `{path}`: Implement the complete planned production responsibility for `{surface}` "
        "using the exact investigated interfaces, including input validation, durable side effects, and observable reporting."
        for path in production_paths
    )
    rollback_paths = ", ".join(f"`{path}`" for path in production_paths)
    success_literal = f"{surface}:ok"
    interface_evidence = exact_interface_evidence(workflow)
    integration_contract = ""
    if objective_requires_discord_retrieval(objective):
        integration_contract = f"""
For this Discord retrieval surface, register `{surface}` with exactly one `channel_id` argument. Its dispatch branch must require `length_list(args_list) != 1`, bind `set channel_id to get_list(args_list and 0)`, and pass that value to the proven `bridge_enqueue` call. The authenticated evaluator supplies `configured_discord_channel()` as this argument; do not rediscover configuration inside the extension, change the surface to zero arguments, or modify any existing registered action's behavior.
"""
    elif objective_requires_session_lookup(objective):
        integration_contract = f"""
For this session-title lookup surface, register `{surface}` with exactly one `title_query` argument. Its dispatch branch must require `length_list(args_list) != 1`, bind `set title_query to get_list(args_list and 0)`, and reject an empty query. Resolve only through the investigated runtime owner: `set sessions_mgr to map_get_val(ctx and "sessions")`, followed by `set resolved_id to session_manager_resolve_id(sessions_mgr and title_query)`; reject an empty result because it means the title query is unknown or ambiguous. Persist a value containing both the exact supplied query and exact resolved ID with the four-argument call `memory_store(memory_mgr and 2 and "{surface}" and lookup_value)`, where zero is success and only nonzero is failure. Return `{success_literal},session_id:<exact resolved id>,query:<exact supplied query>`. The authenticated evaluator calls the production surface once with the exact active-session title and once with a controller-proven unique substring, requiring both calls to return the same exact active-session ID, then independently retrieves the durable result. Import and reuse the existing `session_manager_resolve_id` implementation; do not reconstruct paths, scan files inside the extension, hardcode a session, mutate session state, or add test-only behavior.
"""
    elif objective_requires_session_label(objective):
        integration_contract = f"""
For this session-label surface, register `{surface}` with exactly two arguments, `session_id` and `label`. Its dispatch branch must require `length_list(args_list) != 2`, bind both values from `args_list`, reject an empty or path-like session ID, and reject an empty label. Resolve the already-loaded persisted session only through the investigated runtime contract: `set sessions_mgr to map_get_val(ctx and "sessions")`, then `set sessions_map to map_get_val(sessions_mgr and "sessions")`, and require `map_contains(sessions_map and session_id) == 1`; never reconstruct a session path or invent a separate sessions context value. Persist a value containing the exact session ID and exact supplied label with the four-argument call `memory_store(memory_mgr and 2 and "{surface}" and label_value)`, where zero is success and only nonzero is failure. Return `{success_literal},session_id:<exact id>,label:<exact label>`. The authenticated evaluator supplies `active_session_id()` and the explicit label `codex-e2e-checkpoint-label`, then independently retrieves memory and asserts both exact values. Do not summarize the transcript, substitute a hardcoded label, modify session history, or add test-only behavior.
"""
    elif objective_requires_session_metadata_lookup(objective):
        integration_contract = f"""
For this session-metadata lookup surface, register `{surface}` with exactly one `session_id` argument. Reject empty or path-like input. Resolve only through `ctx.sessions`: bind its `sessions` map, test membership, and load the exact session map for a registered ID. Return `{success_literal},session_id:<exact id>,title:<exact title>,model:<exact model>,records:<exact message count>` using the real `title`, `model`, and `messages` fields. For an unregistered ID return `{surface}:not_found,session_id:<exact missing id>` without claiming success. Persist the complete successful metadata result with `memory_store(memory_mgr and 2 and "{surface}" and metadata_value)`, treating zero as success and nonzero as failure. The evaluator derives all expected metadata from the real active persisted session, proves a second ID is absent, exercises both calls, repeats the successful call, and independently confirms the exact durable metadata. Do not hardcode metadata, reconstruct paths, scan files in the extension, return only a boolean, or add test-only behavior.
"""
    elif objective_requires_session_transcript(objective):
        integration_contract = f"""
For this session-transcript surface, register `{surface}` with exactly one `session_id` argument. Its dispatch branch must require `length_list(args_list) != 1` and reject an empty or path-like ID. Resolve the already-loaded persisted session only through the investigated runtime contract: `set sessions_mgr to map_get_val(ctx and "sessions")`, then `set sessions_map to map_get_val(sessions_mgr and "sessions")`, require `map_contains(sessions_map and session_id) == 1`, and bind `set sess to map_get_val(sessions_map and session_id)`. Process the real `messages` list, reading each message's real `role` and `content` fields; never invent a `text` field or a separate `sessions_dir` context value. Set the reported record count to `length_list(messages)`, so it counts the complete consumed transcript rather than only messages containing a chosen label. It must reject a missing, malformed, or empty session instead of reporting success. Persist the generated summary with the exact four-argument call `memory_store(memory_mgr and 2 and "{surface}" and summary_value)` and a value that includes the exact session ID and `records:<nonzero count>`. Return `{success_literal},session_id:<exact id>,records:<nonzero count>` followed by the real structured summary. The authenticated evaluator supplies `active_session_id()` and independently reads memory; do not accept transcript text, reconstruct a different session, modify session history, or add test-only behavior.
"""
    elif objective_requires_session_validation(objective):
        integration_contract = f"""
For this session-validation surface, register `{surface}` with exactly one `session_id` argument. Its dispatch branch must require `length_list(args_list) != 1`, bind the exact supplied ID, and reject empty or path-like input. Resolve existence only through the investigated runtime contract: `set sessions_mgr to map_get_val(ctx and "sessions")`, `set sessions_map to map_get_val(sessions_mgr and "sessions")`, and `map_contains(sessions_map and session_id)`. Return `{success_literal},session_id:<exact id>,exists:true` for a registered ID and `{success_literal},session_id:<exact id>,exists:false` for an unregistered ID. Persist the exact queried ID and boolean result with `memory_store(memory_mgr and 2 and "{surface}" and validation_value)`, treating zero as success and nonzero as failure. The evaluator supplies both a real active ID and a controller-proven missing ID, verifies both outcomes, repeats the real-ID call, and independently confirms the exact durable result. Do not hardcode an ID, reconstruct a path, scan files in the extension, mutate session state, or substitute a zero-input status check.
"""
    elif objective_uses_marker_transcript(objective):
        integration_contract = f"""
For this text-input surface, register `{surface}` with exactly one transcript argument and process the controller's complete marker transcript through the real production implementation. Persist its resulting durable facts through `memory_store`; do not replace the argument with configuration, a file path, a hardcoded result, or test-only behavior.
"""
    else:
        integration_contract = f"""
For this zero-input surface, register `{surface}` with exactly zero arguments and perform the complete production behavior described by the objective. Persist its real result through `memory_store` under the exact durable key `{surface}` so the live evaluator can independently retrieve the outcome. The durable receipt supplements the observable behavior; it must not replace or simulate that behavior.
"""
    content = f"""## Objective
{objective}

## Investigation Findings
{chr(10).join(findings)}

## Exact Interface Evidence
The following hash-verified source lines are the authoritative callable, import, and call-site facts to use after context compaction. Do not invent replacement APIs.
{chr(10).join(interface_evidence)}

## Production Surface
The exact registered production surface is `{surface}`, implemented from `{primary_path}` and dispatched through the real production boundary established by the investigated source paths above.

## Implementation
Implement the complete objective in the declared production file using only the exact interfaces retained by the investigation. Register `{surface}`, validate its real input, perform the required behavior and durable writes, and return an observable summary beginning exactly `{success_literal}` without stubs, placeholders, mocks, simulations, or test-only branches.
{integration_contract}

## Files
{file_entries}

## Tests
Both evaluators invoke `{surface}` through authenticated AI EVAL_TOOL at its real production boundary and assert `{success_literal}` output exactly. The live E2E independently inspects the resulting durable state so output text without the required production side effect cannot pass.

## Evaluation Contract
Invocation Fixture: `{objective_invocation_fixture(objective)}`. Required success prefix: `{success_literal}`. Durable readback: authenticated `AGENT GET MEMORY` must contain the exact key `{surface}` after the production call. This controller-owned contract selects the argument class and readback boundary; generated reasoning cannot substitute a different fixture.

## Risks and Rollback
Malformed input handling, incomplete persistence, or dispatch regressions fail the frozen behavioral evaluators and mandatory suite. Rollback restores the exact pre-change bytes of {rollback_paths} and leaves the failed transaction and evaluator hashes retained as provenance.
"""
    plan_write(base64.b64encode(content.encode()).decode(), structured=True)


def progress_states(record: dict, active: dict | None = None) -> list[tuple[str, bool]]:
    state = str(record.get("state", "investigating"))
    order = {
        "investigating": 0,
        "planned": 2,
        "tests_authoring": 3,
        "tests_validated": 4,
        "frozen": 5,
        "implementing": 5,
        "verified": 7,
        "live_passed": 8,
        "completed": 9,
        "aborted": -1,
    }
    rank = order.get(state, 0)
    source_count = len(discovery_source_paths(record))
    written = set((active or {}).get("implementation_paths", []))
    planned = set(record.get("planned_files", []))
    implementation_complete = bool(planned) and planned.issubset(written)
    return [
        ("Authoritative unchanged-source baseline passed", True),
        (f"Deep source investigation recorded ({source_count}/{MIN_DISCOVERED_SOURCE_FILES} distinct files minimum)", source_count >= MIN_DISCOVERED_SOURCE_FILES),
        ("Implementation plan validated and hash-recorded", rank >= 2),
        ("Regression and live E2E evaluators authored", rank >= 3),
        ("Causal pre-change regression validated", rank >= 4),
        ("Acceptance, plan, and evaluators hash-frozen", rank >= 5),
        ("Every planned production file changed and individually checked", implementation_complete),
        ("Complete operator-sealed mandatory verification passed", rank >= 7),
        ("Replacement passed the real live E2E evaluator", rank >= 8),
        ("Authenticated replacement committed and workflow completed", rank >= 9),
    ]


def render_plan(record: dict, active: dict | None = None) -> str:
    body = PLAN_BODY.read_text(encoding="utf-8") if PLAN_BODY.is_file() else ""
    checklist = "\n".join(f"- [{'x' if done else ' '}] {label}" for label, done in progress_states(record, active))
    plan_bound = set(record.get("plan_discovery_paths", []))
    if not plan_bound and body:
        plan_bound = set(path for path in discovery_source_paths(record) if path in body)
    discovery = "\n".join(
        f"- `{entry['path']}` — {entry['mode']}, scope "
        f"`{'plan-bound' if entry['path'] in plan_bound else 'supplemental'}`, "
        f"sha256 `{entry['sha256']}`, {entry['size']} bytes"
        for entry in record.get("discovery", [])
        if isinstance(entry, dict) and all(key in entry for key in ("path", "mode", "sha256", "size"))
    )
    return (
        "# Self-Recursive Improvement Implementation Plan\n\n"
        "## Controller Progress\n\n" + checklist + "\n\n"
        "## Verified Discovery Ledger\n\n" + (discovery or "- No verified source reads recorded.") + "\n\n"
        "## Echo's Investigated Plan\n\n" + body.strip() + "\n"
    )


def refresh_plan_document(record: dict, active: dict | None = None) -> None:
    if PLAN_BODY.is_file():
        PLAN_DOCUMENT.write_text(render_plan(record, active), encoding="utf-8")


def investigate_begin(objective_b64: str) -> None:
    if ACTIVE.exists():
        raise GateError("a frozen improvement transaction is already active")
    if WORKFLOW.exists():
        existing = workflow_record()
        if existing.get("state") not in {"completed", "aborted"}:
            raise GateError(
                f"a durable improvement workflow already exists in state {existing.get('state')!r}; read its status and resume it"
            )
    STAGING.mkdir(parents=True, exist_ok=True)
    for name in ("name.txt", "acceptance.txt", "regression.py", "e2e.py", "validation.json", "lint.json", "plan_body.md", "implementation_plan.md", "plan_scaffold_required", "transport_template.json"):
        path = STAGING / name
        if path.exists():
            if path.is_symlink() or not path.is_file():
                raise GateError(f"unsafe staging artifact blocks new workflow: {name}")
            path.unlink()
    objective = decode_text(objective_b64, "improvement objective", 8_000)
    if len(objective) < 40:
        raise GateError("improvement objective must explain the intended capability in at least 40 characters")
    selected_surfaces = objective_callable_surfaces(objective)
    for surface in selected_surfaces:
        if completed_surface_match(surface) is not None:
            raise GateError(
                f"selected surface {surface!r} already has a permanent completion receipt; "
                "retain the green baseline and select a different new registered tool",
                code="FEATURE_ALREADY_EXISTS",
            )
    record = {
        "version": 5,
        "objective": objective,
        "state": "investigating",
        "discovery": [],
        "required_discovery_paths": required_objective_discovery_paths(objective),
        "required_production_paths": required_objective_production_paths(objective),
        "required_surface": (selected_surfaces or [""])[0],
        "required_acceptance": required_objective_acceptance(objective),
        "validation_attempts": [],
        "created_at": int(time.time()),
    }
    atomic_json(WORKFLOW, record)
    print("IMPROVEMENT_INVESTIGATION_OK phase=investigating source_reads=0 required=2")


def record_discovery(path_b64: str, mode: str) -> None:
    record = workflow_record()
    if mode not in {"read", "read_range", "metadata"}:
        raise GateError("discovery mode must be read, read_range, or metadata")
    decoded = decode_text(path_b64, "discovery path", 4_000)
    relative, resolved = safe_relative_path(decoded, must_exist=True)
    state = record.get("state")
    if state in {"frozen", "implementing", "verified", "repair_required"}:
        if mode not in {"read", "read_range"}:
            raise GateError("only exact source rereads are legal after evaluator freeze")
        active = load_record(ACTIVE)
        verify_frozen_bytes(active)
        planned = active.get("planned_files", [])
        if not isinstance(planned, list) or relative not in planned:
            planned_text = ",".join(planned) if isinstance(planned, list) else "<malformed>"
            raise GateError(
                "post-freeze reread is limited to exact production paths declared in the frozen plan; "
                f"requested={relative} planned={planned_text}",
                code="PLAN_SCOPE_MISSING",
            )
        current_hash = file_digest(resolved)
        baseline_hashes = active.get("implementation_baseline_hashes", {})
        baseline_hash = baseline_hashes.get(relative) if isinstance(baseline_hashes, dict) else None
        if state == "frozen" and current_hash != baseline_hash:
            raise GateError(
                "planned source changed outside the protected implementation path before the first recorded write; "
                f"path={relative} expected={baseline_hash} actual={current_hash}"
            )
        print(
            f"IMPROVEMENT_REREAD_OK path={relative} mode={mode} state={state} "
            f"sha256={current_hash} scope=frozen-plan"
        )
        return
    if state not in {"investigating", "planned", "tests_authoring", "tests_validated"}:
        raise GateError(f"source discovery is not legal in workflow state {state!r}")
    if is_test_or_gate_path(relative):
        raise GateError("test and gate files do not count as implementation discovery")
    entries = record.setdefault("discovery", [])
    entry = {
        "path": relative,
        "mode": mode,
        "scope": "plan" if record.get("state") == "investigating" else "supplemental",
        "sha256": file_digest(resolved),
        "size": resolved.stat().st_size,
        "recorded_at": int(time.time()),
    }
    entries[:] = [item for item in entries if not (
        isinstance(item, dict) and item.get("path") == relative and item.get("mode") == mode
    )]
    entries.append(entry)
    record["discovery_hash"] = digest(json.dumps(entries, sort_keys=True).encode())
    atomic_json(WORKFLOW, record)
    refresh_plan_document(record)
    print(
        f"IMPROVEMENT_DISCOVERY_OK path={relative} mode={mode} "
        f"scope={entry['scope']} source_reads={len(discovery_source_paths(record))} "
        f"required={MIN_DISCOVERED_SOURCE_FILES}"
    )


def record_investigation_evidence(kind: str, query_b64: str) -> None:
    record = workflow_record()
    if record.get("state") != "investigating":
        raise GateError("investigation evidence may be recorded only before plan validation")
    if kind not in {"language_reference", "callsite_search"}:
        raise GateError("investigation evidence kind must be language_reference or callsite_search")
    query = decode_text(query_b64, "investigation query", 512).strip()
    if len(query) < 2:
        raise GateError("investigation query must contain at least 2 characters")
    matches = 0
    if kind == "callsite_search":
        query_lower = query.lower()
        for path in ROOT.rglob("*"):
            if not path.is_file() or path.is_symlink() or path.suffix not in {".ep", ".py", ".js", ".sh"}:
                continue
            try:
                relative_path = path.relative_to(ROOT)
            except ValueError:
                continue
            relative = str(relative_path)
            if is_test_or_gate_path(relative) or any(part.startswith(".") for part in relative_path.parts):
                continue
            if any(part in {"build", "dist", "vendor", "node_modules", "config"} for part in relative_path.parts):
                continue
            try:
                matches += path.read_text(encoding="utf-8", errors="ignore").lower().count(query_lower)
            except OSError:
                continue
        if matches == 0:
            raise GateError(f"call-site query has no current non-test production match: {query}")
    entries = record.setdefault("investigation_evidence", [])
    if not isinstance(entries, list):
        raise GateError("workflow investigation evidence is malformed")
    entries[:] = [entry for entry in entries if not (
        isinstance(entry, dict)
        and entry.get("kind") == kind
        and str(entry.get("query", "")).lower() == query.lower()
    )]
    entries.append({"kind": kind, "query": query, "matches": matches, "recorded_at": int(time.time())})
    record["investigation_evidence_hash"] = digest(json.dumps(entries, sort_keys=True).encode())
    atomic_json(WORKFLOW, record)
    print(f"IMPROVEMENT_INVESTIGATION_EVIDENCE_OK kind={kind} query={query} matches={matches}")


def plan_write(content_b64: str, *, structured: bool = False) -> None:
    record = workflow_record()
    if record.get("state") not in {"investigating", "planned"}:
        raise GateError(f"plan authoring is not legal in workflow state {record.get('state')!r}")
    if PLAN_SCAFFOLD_REQUIRED.exists() and not structured:
        raise GateError(
            "a prior free-form plan was rejected; improvement_plan_scaffold is now the only legal plan-authoring route"
        )
    verify_objective_investigation(record)
    content = decode_text(content_b64, "implementation plan", MAX_PLAN_BYTES)
    bound_discovery = discovery_source_paths(record)
    try:
        planned = parse_plan(content, record, required_discovery=bound_discovery)
    except GateError:
        if len(bound_discovery) >= MIN_DISCOVERED_SOURCE_FILES:
            PLAN_SCAFFOLD_REQUIRED.write_text("required\n", encoding="utf-8")
        raise
    planned_surfaces = plan_callable_surfaces(content)
    required_surface = str(record.get("required_surface", "")).strip()
    if not required_surface and planned_surfaces:
        required_surface = planned_surfaces[0]
    required_acceptance = str(record.get("required_acceptance", "")).strip()
    if not required_acceptance:
        required_acceptance = required_objective_acceptance(
            str(record.get("objective", "")), required_surface
        )
    if not required_acceptance:
        raise GateError("validated registered plan did not yield a controller-owned acceptance contract")
    # The controller must never persist a planned transaction whose own mechanical
    # next transition will be rejected. Validate the exact generated contract before
    # writing either the plan body or the planned workflow state.
    acceptance_criteria(required_acceptance)
    reject_nonbehavioral_acceptance(required_acceptance)
    validate_acceptance_retains_explicit_markers(
        str(record.get("objective", "")) + "\n" + content,
        required_acceptance,
    )
    PLAN_BODY.write_text(content + "\n", encoding="utf-8")
    record["state"] = "planned"
    record["planned_files"] = planned
    record["planned_surfaces"] = planned_surfaces
    record["required_surface"] = required_surface
    record["required_acceptance"] = required_acceptance
    record["invocation_fixture"] = objective_invocation_fixture(str(record.get("objective", "")))
    record["plan_discovery_paths"] = bound_discovery
    record["plan_discovery_hash"] = digest(json.dumps(bound_discovery).encode())
    record["plan_body_hash"] = file_digest(PLAN_BODY)
    record["plan_version"] = int(record.get("plan_version", 0)) + 1
    record["planned_at"] = int(time.time())
    atomic_json(WORKFLOW, record)
    PLAN_SCAFFOLD_REQUIRED.unlink(missing_ok=True)
    refresh_plan_document(record)
    print(
        f"IMPROVEMENT_PLAN_OK version={record['plan_version']} files={len(planned)} "
        f"hash={record['plan_body_hash']} next=improvement_test_begin"
    )


def begin_stage(name: str, acceptance_b64: str) -> None:
    if not SAFE_NAME.fullmatch(name):
        raise GateError("name must match [a-z][a-z0-9_]{2,63}")
    completed_matches = [
        record for record in all_completed()
        if str(record.get("name", "")).strip().lower() == name.lower()
    ]
    if completed_matches:
        resolve_already_completed(workflow_record(), completed_matches[-1], requested_name=name)
        return
    record = workflow_record()
    if record.get("state") != "planned":
        raise GateError("tests cannot begin until deep discovery and a validated implementation plan are complete")
    acceptance = decode_text(acceptance_b64, "acceptance criteria", 8_000)
    acceptance_criteria(acceptance)
    reject_nonbehavioral_acceptance(acceptance)
    plan_contract = record.get("objective", "")
    if PLAN_BODY.is_file():
        plan_contract += "\n" + PLAN_BODY.read_text(encoding="utf-8")
    validate_acceptance_retains_explicit_markers(plan_contract, acceptance)
    for path in (STAGING / "name.txt", STAGING / "acceptance.txt", STAGING / "regression.py", STAGING / "e2e.py"):
        if path.exists():
            raise GateError("mutable evaluator artifacts already exist; resume them instead of overwriting")
    (STAGING / "name.txt").write_text(name, encoding="utf-8")
    (STAGING / "acceptance.txt").write_text(acceptance, encoding="utf-8")
    TRANSPORT_TEMPLATE_RECEIPT.unlink(missing_ok=True)
    (STAGING / "regression.py").write_text("", encoding="utf-8")
    (STAGING / "e2e.py").write_text("", encoding="utf-8")
    record["state"] = "tests_authoring"
    record["name"] = name
    record["acceptance_hash"] = digest(acceptance.encode())
    atomic_json(WORKFLOW, record)
    refresh_plan_document(record)
    print(f"IMPROVEMENT_STAGING_OK name={name} phase=tests_authoring plan_hash={record['plan_body_hash']}")


def resolve_surface(surface_b64: str) -> None:
    """Resolve an attempted installed public tool at its exact execution boundary."""
    surface = decode_text(surface_b64, "production surface", 256).strip()
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{2,63}", surface):
        raise GateError("production surface must be one exact 3-64 character callable/tool identifier")
    completed = completed_surface_match(surface)
    if completed is None:
        raise GateError(f"no current permanent completion receipt owns production surface {surface!r}")
    if ACTIVE.exists():
        raise GateError("cannot resolve an already-completed capability while another frozen transaction is active")
    if WORKFLOW.exists():
        workflow = workflow_record()
        if workflow.get("state") in {"investigating", "planned", "tests_authoring", "tests_validated"}:
            resolve_already_completed(workflow, completed, surface=surface)
            return
    print(
        f"IMPROVEMENT_ALREADY_COMPLETE id={completed['id']} "
        f"name={completed.get('name', surface)} surface={surface} "
        "workflow=already_terminal permanent_regression=enabled"
    )


def superseded_ids() -> set[str]:
    if not SUPERSEDED.exists():
        return set()
    result: set[str] = set()
    for path in sorted(SUPERSEDED.glob("*.json")):
        receipt = load_record(path)
        transaction_id = receipt.get("transaction_id")
        if (
            receipt.get("version") != 1
            or not isinstance(transaction_id, str)
            or not HASH.fullmatch(transaction_id)
            or path.stem != transaction_id
        ):
            raise GateError(f"malformed supersession receipt: {path}")
        completed_path = COMPLETED / f"{transaction_id}.json"
        completed = load_record(completed_path)
        for field in ("acceptance_hash", "regression_hash", "e2e_hash"):
            if receipt.get(field) != completed.get(field):
                raise GateError(f"supersession receipt does not bind completed {field}: {transaction_id}")
        reason = receipt.get("reason")
        if not isinstance(reason, str) or len(reason.strip()) < 80:
            raise GateError(f"supersession receipt needs a complete evidence-backed reason: {transaction_id}")
        result.add(transaction_id)
    return result


def all_completed() -> list[dict]:
    if not COMPLETED.exists():
        return []
    superseded = superseded_ids()
    return [
        load_record(path)
        for path in sorted(COMPLETED.glob("*.json"))
        if path.stem not in superseded
    ]


def completed_surface_match(surface: str) -> dict | None:
    """Return the current permanent receipt that owns an exact public surface."""
    target = surface.strip().lower()
    for record in reversed(all_completed()):
        surfaces = record.get("planned_surfaces", [])
        if isinstance(surfaces, list) and any(
            isinstance(item, str) and item.strip().lower() == target
            for item in surfaces
        ):
            return record
    return None


def resolve_already_completed(
    workflow: dict, completed: dict, *, requested_name: str = "", surface: str = ""
) -> None:
    """Close a duplicate workflow without inventing a second implementation.

    The immutable completion receipt remains authoritative. The abandoned planning
    bytes are retained separately for provenance, while the workflow's terminal
    state is installed with one atomic replace so a restart cannot reconstruct a
    permanent planned/repair lock.
    """
    if ACTIVE.exists():
        raise GateError("cannot resolve an already-completed capability while another frozen transaction is active")
    if workflow.get("state") not in {"investigating", "planned", "tests_authoring", "tests_validated"}:
        raise GateError(f"already-completed resolution is not legal in workflow state {workflow.get('state')!r}")
    completed_id = str(completed.get("id", ""))
    if not HASH.fullmatch(completed_id):
        raise GateError("matched completed capability has no valid immutable transaction id")
    matched_surface = surface.strip()
    if not matched_surface:
        planned_surfaces = workflow.get("planned_surfaces", [])
        if isinstance(planned_surfaces, list) and planned_surfaces:
            matched_surface = str(planned_surfaces[0]).strip()
    matched_name = str(completed.get("name", requested_name)).strip()
    stamp = str(time.time_ns())
    resolution_id = digest(
        (completed_id + "\n" + str(workflow.get("objective", "")) + "\n" + stamp).encode()
    )
    RESOLVED.mkdir(parents=True, exist_ok=True)
    archived_files: list[str] = []
    for source in sorted(STAGING.iterdir()):
        if source == WORKFLOW or not source.is_file() or source.is_symlink():
            continue
        destination = RESOLVED / f"{resolution_id}.{source.name}"
        shutil.copy2(source, destination)
        archived_files.append(str(destination.relative_to(ROOT)))
    resolved = dict(workflow)
    resolved.update({
        "state": "completed",
        "resolution": "already_complete",
        "resolution_id": resolution_id,
        "resolved_at": int(time.time()),
        "completed_transaction_id": completed_id,
        "completed_name": matched_name,
        "completed_surface": matched_surface,
        "archived_files": archived_files,
    })
    atomic_json(RESOLVED / f"{resolution_id}.json", resolved)
    atomic_json(WORKFLOW, resolved)
    print(
        f"IMPROVEMENT_ALREADY_COMPLETE id={completed_id} name={matched_name} "
        f"surface={matched_surface or 'unknown'} resolution={resolution_id} "
        "workflow=closed permanent_regression=enabled"
    )


def normalized_terms(text: str) -> set[str]:
    terms: set[str] = set()
    for raw in re.findall(r"[a-z][a-z0-9_]{2,}", text.lower()):
        for token in raw.split("_"):
            if len(token) >= 3 and token not in SEMANTIC_STOPWORDS:
                terms.add(token)
    return terms


def acceptance_criteria(acceptance: str) -> dict[str, str]:
    """Parse explicit, stable acceptance IDs instead of guessing lexical meaning."""
    criteria: dict[str, str] = {}
    malformed: list[str] = []
    for line in acceptance.splitlines():
        if not line.strip():
            continue
        match = CRITERION.fullmatch(line)
        if not match:
            malformed.append(line.strip()[:120])
            continue
        criterion_id, description = match.groups()
        if criterion_id in criteria:
            raise GateError(f"duplicate acceptance criterion id: {criterion_id}")
        if len(description) < 20:
            raise GateError(f"acceptance criterion {criterion_id} is too short to be observable")
        criteria[criterion_id] = description
    if malformed:
        raise GateError(
            "acceptance criteria must use one '[criterion_id] observable outcome' per line; "
            f"first malformed line={malformed[0]!r}"
        )
    if len(criteria) < 2 or len(criteria) > 16:
        raise GateError("acceptance criteria require 2-16 explicit [criterion_id] outcome lines")
    return criteria


NONBEHAVIORAL_ACCEPTANCE = re.compile(
    r"\b(file|module|directory)\s+(exists?|is present)|"
    r"\btests?\s+pass(?:es|ed)?\b|"
    r"\b(?:regression|e2e|unit|integration)\s+tests?\b|"
    r"\btests?\s+(?:attempts?|asserts?|raises?|expects?|verifies?|checks?|fails?)\b|"
    r"\b(?:assertionerror|assertion|test fixture|test harness)\b|"
    r"\b(?:unregistered|unimplemented|not[- ]yet[- ]implemented|not implemented)\b|"
    r"\breturn\s*code\s+(?:is|equals?)\s*(?:zero|0)\b|"
    r"\bcommand\s+(?:runs?|succeeds?|completes?)\b",
    re.IGNORECASE,
)

MECHANICAL_CRITERION_ID = re.compile(r"(?:^|_)(?:test|tests|regression|e2e|fixture|harness)(?:_|$)")


def reject_nonbehavioral_acceptance(acceptance: str) -> None:
    for criterion_id, description in acceptance_criteria(acceptance).items():
        if MECHANICAL_CRITERION_ID.search(criterion_id):
            raise GateError(
                f"acceptance criterion id {criterion_id} names test machinery; "
                "name the externally observable production outcome instead"
            )
        match = NONBEHAVIORAL_ACCEPTANCE.search(description)
        if match:
            raise GateError(
                f"acceptance criterion {criterion_id} describes test mechanics or artifact presence "
                f"({match.group(0)!r}); specify the externally observable production behavior and durable effect"
            )


def validate_python_test(content: str, kind: str) -> ast.AST:
    encoded = content.encode("utf-8")
    if len(encoded) < 160 or len(encoded) > MAX_TEST_BYTES:
        raise GateError(f"{kind} test must be 160-{MAX_TEST_BYTES} UTF-8 bytes")
    try:
        tree = ast.parse(content, filename=f"generated_{kind}.py")
    except SyntaxError as exc:
        raise GateError(f"{kind} test is not valid Python: {exc}") from exc
    tests = [
        node for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_")
    ]
    assertions = [node for node in ast.walk(tree) if isinstance(node, ast.Assert)]
    assertion_calls = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr.startswith("assert")
    ]
    if not tests:
        raise GateError(f"{kind} test needs at least one named test_* function")
    if not (assertions or assertion_calls):
        raise GateError(f"{kind} test needs an observable assert or assertion method")
    for assertion in assertions:
        if isinstance(assertion.test, ast.Constant) and isinstance(assertion.test.value, bool):
            raise GateError(f"{kind} test contains a literal assert that proves no behavior")
    if kind == "regression" and "ERNOS_TEST_PHASE" in content:
        raise GateError("regression test may not branch on the gate phase")
    forbidden = ("active.json", "completed/", "aborted/", "improvement_test_gate.py")
    if any(marker in content for marker in forbidden):
        raise GateError(f"{kind} test refers to gate internals")
    if kind == "e2e":
        outward = ("urllib", "http.client", "socket", "subprocess", "127.0.0.1", "localhost")
        if not any(marker in content for marker in outward):
            raise GateError("E2E test must exercise a process, socket, HTTP, IPC, or localhost surface")
    return tree


def call_name(node: ast.Call) -> str:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        parts = [node.func.attr]
        value = node.func.value
        while isinstance(value, ast.Attribute):
            parts.append(value.attr)
            value = value.value
        if isinstance(value, ast.Name):
            parts.append(value.id)
        return ".".join(reversed(parts))
    return ""


def command_tokens(tree: ast.AST) -> set[str]:
    """Collect literal command tokens even when argv is assigned to a helper variable."""
    tokens: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.List, ast.Tuple)):
            for element in node.elts:
                if isinstance(element, ast.Constant) and isinstance(element.value, str):
                    tokens.add(element.value.strip().lower())
    return tokens


def validate_regression_observes_behavior(tree: ast.AST) -> None:
    assertions = [node for node in ast.walk(tree) if isinstance(node, ast.Assert)]
    if assertions and all(
        any(
            isinstance(child, ast.Call)
            and call_name(child).split(".")[-1] in {"exists", "is_file", "find_spec"}
            for child in ast.walk(assertion.test)
        )
        for assertion in assertions
    ):
        raise GateError(
            "regression proves only module/file presence; assert observable production behavior instead"
        )


def validate_evaluator_scratch(tree: ast.AST, kind: str) -> None:
    """Keep evaluator-owned writes out of repository and durable state."""
    direct_writes: list[ast.Call] = []
    has_temp_owner = False
    literal_paths: dict[str, str] = {}
    repository_write_targets: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            value = node.value
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                for target in targets:
                    if isinstance(target, ast.Name):
                        literal_paths[target.id] = value.value

    def literal_path(arg: ast.AST) -> str | None:
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            return arg.value
        if isinstance(arg, ast.Name):
            return literal_paths.get(arg.id)
        return None

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = call_name(node)
        short = name.split(".")[-1]
        if name in {"tempfile.TemporaryDirectory", "tempfile.mkdtemp", "tempfile.NamedTemporaryFile"}:
            has_temp_owner = True
        if short in {"write_text", "write_bytes", "touch", "mkdir", "makedirs", "remove", "unlink"}:
            direct_writes.append(node)
            if node.args:
                target = literal_path(node.args[0])
                if target and (target.startswith("decent_") or target.startswith("config/") or target.startswith("scripts/") or target.startswith("tests/")):
                    repository_write_targets.append(target)
        if short == "open" and len(node.args) >= 2:
            mode = node.args[1]
            if isinstance(mode, ast.Constant) and isinstance(mode.value, str) and any(
                flag in mode.value for flag in ("w", "a", "x", "+")
            ):
                direct_writes.append(node)
                target = literal_path(node.args[0])
                if target and (target.startswith("decent_") or target.startswith("config/") or target.startswith("scripts/") or target.startswith("tests/")):
                    repository_write_targets.append(target)
        if short == "open":
            for keyword in node.keywords:
                if keyword.arg == "mode" and isinstance(keyword.value, ast.Constant):
                    value = keyword.value.value
                    if isinstance(value, str) and any(flag in value for flag in ("w", "a", "x", "+")):
                        direct_writes.append(node)
                        if node.args:
                            target = literal_path(node.args[0])
                            if target and (target.startswith("decent_") or target.startswith("config/") or target.startswith("scripts/") or target.startswith("tests/")):
                                repository_write_targets.append(target)
    if repository_write_targets:
        raise GateError(
            f"{kind} evaluator attempts to mutate repository/durable source path(s): "
            + ",".join(sorted(set(repository_write_targets)))
            + "; evaluators may write only their own OS-temporary scratch"
        )
    if direct_writes and not has_temp_owner:
        raise GateError(
            f"{kind} evaluator writes scratch data without tempfile ownership; "
            "use TemporaryDirectory/NamedTemporaryFile and keep evaluator-created bytes outside the repository"
        )


def validate_no_swallowed_execution_failures(tree: ast.AST, kind: str) -> None:
    """An evaluator must surface execution failures instead of converting them into evidence."""
    forbidden = {"Exception", "BaseException", "FileNotFoundError", "CalledProcessError", "PermissionError"}
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        names: set[str] = set()
        candidates = node.type.elts if isinstance(node.type, ast.Tuple) else [node.type]
        for candidate in candidates:
            if isinstance(candidate, ast.Name):
                names.add(candidate.id)
            elif isinstance(candidate, ast.Attribute):
                names.add(candidate.attr)
        if names & forbidden:
            raise GateError(
                f"{kind} evaluator catches or swallows production execution failure(s) "
                f"{','.join(sorted(names & forbidden))}; command/import/path/permission failures must fail the evaluator directly"
            )


def validate_tests_assert_desired_outcomes(tree: ast.AST, kind: str) -> None:
    """Reject tests that reward the current absence/error instead of future behavior."""
    forbidden = (
        "unregistered", "unknown action", "unknown tool", "not implemented",
        "not_present", "feature_absent", "missing tool", "missing action",
    )
    for function in ast.walk(tree):
        if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not function.name.startswith("test_"):
            continue
        if any(marker in function.name.lower() for marker in ("not_present", "absent", "unimplemented")):
            raise GateError(
                f"{kind} test {function.name} encodes the current missing state; tests must assert the desired post-change output or durable effect"
            )
        for node in ast.walk(function):
            if not isinstance(node, ast.Assert):
                continue
            rendered = ast.unparse(node.test).lower()
            normalized = re.sub(r"[_:\-]+", " ", rendered)
            error_sentinel = re.search(
                r"['\"]error(?:[_:\- ]+(?:not[_:\- ]+implemented|unimplemented|unknown|missing|unregistered|absent))?['\"]",
                rendered,
            )
            if any(marker in rendered or marker in normalized for marker in forbidden) or error_sentinel or re.search(
                r"(?:'|\")error(?::|['\"])\s+in\s+", rendered
            ):
                raise GateError(
                    f"{kind} test {function.name} asserts a missing/unknown/error state; "
                    "assert the desired post-change production output or durable effect instead. "
                    "The unchanged production call will then fail causally before implementation"
                )


def validate_e2e_matches_plan(content: str, plan: str, planned_files: list[str]) -> None:
    """Require the live evaluator to name the frozen production surface it drives."""
    markers: set[str] = set()
    generic = {"app", "main", "node", "test", "tests", "tool", "tools"}
    for relative in planned_files:
        path = Path(relative)
        markers.add(relative)
        markers.add(path.name)
        if len(path.stem) >= 5 and path.stem.lower() not in generic:
            markers.add(path.stem)
    sections = re.split(r"^##\s+", plan, flags=re.MULTILINE)
    surface = next(
        (part for part in sections if part.lower().startswith("production surface\n")), ""
    )
    for marker in re.findall(r"`([^`]{4,120})`", surface):
        cleaned = marker.strip().rstrip("()")
        if cleaned and cleaned.lower() not in generic:
            markers.add(cleaned)
    if not any(marker in content for marker in markers):
        raise GateError(
            "E2E test does not invoke or name the exact production surface frozen in the plan; "
            "drive the planned executable/API/IPC/tool interface rather than an unrelated helper"
        )


def validate_registered_tool_transport(content: str, plan: str, kind: str) -> None:
    """Fail closed on HTTP/curl lookalikes for the node's authenticated raw-TCP IPC."""
    surface = registered_tool_surface(plan)
    if not surface:
        return
    forbidden = ("requests.", "curl", "/execute", "localhost:8080", "127.0.0.1:8080")
    found = [marker for marker in forbidden if marker in content]
    if found:
        raise GateError(
            f"{kind} evaluator substitutes HTTP/curl for registered-tool IPC ({','.join(found)}); "
            "call improvement_test_transport_template([]) and copy its authenticated raw-TCP client byte-for-byte"
        )
    canonical = registered_tool_transport_source(surface).rstrip() + "\n\n"
    if not content.startswith(canonical):
        raise GateError(
            f"{kind} registered-tool evaluator does not begin with the exact controller-owned transport; "
            "write it through improvement_test_write so the controller installs canonical bytes"
        )
    required = (
        "socket.create_connection",
        "ipc-token",
        "AUTH ",
        "AI EVAL_TOOL ",
        surface,
        "eval_tool:ok,name:",
        ".shutdown(socket.SHUT_WR)",
        ".recv(",
        "while True",
    )
    missing = [marker for marker in required if marker not in content]
    if missing:
        raise GateError(
            f"{kind} registered-tool evaluator is missing authenticated raw-TCP transport element(s): "
            + ",".join(missing)
            + "; call improvement_test_transport_template([]), copy the client byte-for-byte, and add only behavioral test functions"
        )
    if kind.lower() == "e2e" and "AGENT GET MEMORY" not in content:
        raise GateError(
            "E2E registered-tool evaluator must independently inspect durable state with AGENT GET MEMORY; "
            "call improvement_test_transport_template([]) and use get_memory()"
        )


def configured_fixture_aliases(tree: ast.AST, fixture_call: str) -> set[str]:
    """Return local names whose every assignment uses one controller fixture call."""
    assignments: dict[str, list[ast.AST]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        for target in targets:
            if isinstance(target, ast.Name):
                assignments.setdefault(target.id, []).append(node.value)
    valid: set[str] = set()
    for name, values in assignments.items():
        if values and all(
            isinstance(value, ast.Call)
            and isinstance(value.func, ast.Name)
            and value.func.id == fixture_call
            and not value.args
            and not value.keywords
            for value in values
        ):
            valid.add(name)
    return valid


def install_registered_tool_transport(content: str, plan: str, kind: str) -> tuple[str, bool]:
    """Own transport and execution; retain only model-authored behavioral tests."""
    surface = registered_tool_surface(plan)
    if not surface or kind not in {"regression", "e2e"}:
        return content, False
    workflow = workflow_record()
    objective = str(workflow.get("objective", ""))
    try:
        submitted_tree = ast.parse(content)
    except SyntaxError:
        # Preserve the original bytes so the normal lint path returns the exact
        # Python syntax diagnostic instead of masking it as a format error.
        return content, False
    test_functions = [
        node for node in submitted_tree.body
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
    ]
    if not test_functions:
        nested_tests = [
            node for node in ast.walk(submitted_tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("test_")
        ]
        detail = "; unittest classes and nested test methods are not executable by this controller" if nested_tests else ""
        raise GateError(
            f"{kind} registered-tool behavior must contain standalone top-level functions in exact form "
            "`def test_<criterion_id>():` with no class, unittest wrapper, imports, copied transport, or main block"
            f"{detail}. Submit only those functions; call "
            f"the plan-bound production surface because `{surface}` is already bound. "
            + registered_tool_argument_guidance(workflow) + " "
            "and use get_memory() for independent durable evidence"
        )
    invalid_signatures = [
        node.name for node in test_functions
        if node.args.args or node.args.posonlyargs or node.args.kwonlyargs
        or node.args.vararg is not None or node.args.kwarg is not None
    ]
    if invalid_signatures:
        raise GateError(
            f"{kind} registered-tool tests must be zero-argument top-level functions; "
            f"invalid={','.join(invalid_signatures)}. Do not use self/unittest methods"
        )
    for node in ast.walk(submitted_tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
            continue
        if node.func.id != "eval_planned_tool" or not node.args:
            continue
        first = node.args[0]
        if isinstance(first, ast.Constant) and first.value == surface:
            raise GateError(
                f"{kind} passes the already-bound surface `{surface}` into eval_planned_tool. "
                "Pass only the real production arguments directly, for example "
                'eval_planned_tool("[LESSON: fixture_key | fixture_value]")'
            )
        if len(node.args) == 1 and isinstance(first, (ast.List, ast.Tuple)):
            raise GateError(
                f"{kind} wraps registered-tool arguments in an extra list. Pass each argument directly, "
                'for example eval_planned_tool("[LESSON: fixture_key | fixture_value]")'
            )
    if objective_requires_discord_retrieval(objective):
        configured_aliases = configured_fixture_aliases(submitted_tree, "configured_discord_channel")
        calls = [
            node for node in ast.walk(submitted_tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "eval_planned_tool"
        ]
        wrong_calls: list[str] = []
        for node in calls:
            if len(node.args) != 1 or node.keywords:
                wrong_calls.append("argument_count")
                continue
            argument = node.args[0]
            is_configured_channel = (
                isinstance(argument, ast.Call)
                and isinstance(argument.func, ast.Name)
                and argument.func.id == "configured_discord_channel"
                and not argument.args
                and not argument.keywords
            )
            is_configured_alias = isinstance(argument, ast.Name) and argument.id in configured_aliases
            if not is_configured_channel and not is_configured_alias:
                wrong_calls.append(ast.unparse(argument)[:120])
        if not calls or wrong_calls:
            raise GateError(
                f"{kind} Discord-retrieval evaluator must call the real configured channel directly or "
                "through a local name assigned only from configured_discord_channel(). Transcript "
                "strings, marker fixtures, hardcoded channel IDs, and alternate arguments do not prove the configured live bridge; "
                f"invalid={','.join(wrong_calls) if wrong_calls else 'missing production call'}"
            )
    if objective_requires_session_transcript(objective):
        session_aliases = configured_fixture_aliases(submitted_tree, "active_session_id")
        calls = [
            node for node in ast.walk(submitted_tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "eval_planned_tool"
        ]
        wrong_calls: list[str] = []
        for node in calls:
            if len(node.args) != 1 or node.keywords:
                wrong_calls.append("argument_count")
                continue
            argument = node.args[0]
            is_active_session = (
                isinstance(argument, ast.Call)
                and isinstance(argument.func, ast.Name)
                and argument.func.id == "active_session_id"
                and not argument.args
                and not argument.keywords
            )
            is_session_alias = isinstance(argument, ast.Name) and argument.id in session_aliases
            if not is_active_session and not is_session_alias:
                wrong_calls.append(ast.unparse(argument)[:120])
        if not calls or wrong_calls:
            raise GateError(
                f"{kind} session-transcript evaluator must call the exact persisted active session ID "
                "directly or through a local name assigned only from active_session_id(). Transcript text, "
                "reconstructed paths, hardcoded IDs, and alternate arguments do not prove the live session boundary; "
                f"invalid={','.join(wrong_calls) if wrong_calls else 'missing production call'}"
            )
    retained = [
        ast.get_source_segment(content, node) or ast.unparse(node)
        for node in test_functions
    ]
    runner = 'if __name__ == "__main__":\n' + "\n".join(
        f"    {node.name}()" for node in test_functions
    )
    behavior = "\n\n".join(retained) + "\n\n" + runner + "\n"
    canonical = registered_tool_transport_source(surface).rstrip() + "\n\n"
    return canonical + behavior, True


def reject_incomplete_artifact(text: str, label: str) -> None:
    match = INCOMPLETE_ARTIFACT.search(text)
    if match:
        raise GateError(
            f"{label} contains prohibited incomplete-artifact language {match.group(0)!r}; "
            "self-improvements require the full production behavior and real E2E evidence"
        )


def validate_acceptance_coverage(
    acceptance: str, regression_tree: ast.AST, e2e_tree: ast.AST
) -> dict[str, str]:
    criteria = acceptance_criteria(acceptance)
    test_names = {
        node.name
        for tree in (regression_tree, e2e_tree)
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_")
    }
    missing = [criterion_id for criterion_id in criteria if not any(
        name == f"test_{criterion_id}" or name.startswith(f"test_{criterion_id}_")
        for name in test_names
    )]
    if missing:
        raise GateError(
            "frozen tests do not map every acceptance criterion to a causal test function; "
            f"missing={','.join(missing)}. Do not rewrite acceptance. Rewrite kind `regression` or `e2e` "
            "(never `e2e.py`) and define one top-level test_<criterion_id>() for every missing name."
        )
    return criteria


def explicit_marker_families(contract: str) -> set[str]:
    """Return colon-form data-marker families, never structural section wrappers."""
    # These brackets are authenticated request-envelope metadata consumed by the
    # node before the user's feature objective reaches the agent. They describe who,
    # where and how the request arrived; they are not production input markers and
    # must never become acceptance criteria for an unrelated self-improvement.
    transport_families = {
        "SESSION", "SENDER", "ROLE", "MODEL", "MODE", "SYSTEM",
        "ACTOR_ID", "ACTOR_USERNAME", "ACTOR_GLOBAL_NAME",
        "ACTOR_DISPLAY_NAME", "ACTOR_TYPE", "ACTOR_IS_HOST", "HOST_NAME",
        "GUILD_ID", "GUILD_NAME", "CHANNEL_NAME", "THREAD_ID", "THREAD_NAME",
        "IN_MEMORY_CONTEXT", "VISUAL_CONTEXT", "IMAGE_PATH", "MSGID", "CHANID",
        "PLATFORM", "BACKGROUND",
    }
    return {
        match
        for match in re.findall(r"\[([A-Z][A-Z0-9_ -]{1,40}):", contract)
        if match not in transport_families
    }


def explicit_marker_examples(contract: str) -> list[tuple[str, str, str]]:
    """Return concrete marker examples, excluding generic key/value placeholders."""
    examples: list[tuple[str, str, str]] = []
    for family, key, value in re.findall(
        r"\[([A-Z][A-Z0-9_ -]{1,40}):\s*([^|\]\n]{1,120})\s*\|\s*([^\]\n]{1,200})\]",
        contract,
    ):
        normalized = (family.strip(), key.strip(), value.strip())
        if normalized[1].lower() in {"key", "name", "..."} and normalized[2].lower() in {
            "value",
            "...",
        }:
            continue
        if normalized not in examples:
            examples.append(normalized)
    return examples


def objective_marker_fixtures(contract: str) -> list[tuple[str, str, str]]:
    """Return one deterministic concrete fixture for every requested marker family."""
    concrete = {family: (key, value) for family, key, value in explicit_marker_examples(contract)}
    families = explicit_marker_families(contract)
    ordered_families = list(dict.fromkeys(
        family
        for family in re.findall(r"\[([A-Z][A-Z0-9_ -]{1,40}):", contract)
        if family in families
    ))
    if not families:
        lowered = concrete_objective(contract).lower()
        if "lesson" in lowered:
            ordered_families.append("LESSON")
        if "correction" in lowered:
            ordered_families.append("CORRECTION")
        if objective_invocation_fixture(contract) == "marker_transcript" and not ordered_families:
            ordered_families.extend(("LESSON", "CORRECTION"))
        families.update(ordered_families)
    fixtures: list[tuple[str, str, str]] = []
    for family in ordered_families:
        if family in concrete:
            key, value = concrete[family]
        elif family == "LESSON":
            key, value = "fixture_key", "fixture_value"
        else:
            slug = re.sub(r"[^a-z0-9]+", "_", family.lower()).strip("_") or "marker"
            key, value = f"{slug}_key", f"{slug}_value"
        fixtures.append((family, key, value))
    return fixtures


def explicit_output_literals(contract: str) -> list[str]:
    """Extract exact output literals the immutable request explicitly says to assert."""
    return list(dict.fromkeys(
        value.strip()
        for value in re.findall(
            r"\bassert(?:s|ed|ing)?\s+(?:the\s+)?(?:desired\s+)?`([^`]{1,120})`\s+output\b",
            contract,
            flags=re.IGNORECASE,
        )
        if value.strip()
    ))


def assigned_call_names(tree: ast.AST, call_name: str) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        value = node.value
        if not isinstance(value, ast.Call) or not isinstance(value.func, ast.Name):
            continue
        if value.func.id != call_name:
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        for target in targets:
            if isinstance(target, ast.Name):
                names.add(target.id)
    return names


def assertion_observes(assertion: ast.Assert, call_name: str, names: set[str], literal: str) -> bool:
    constants = {
        node.value
        for node in ast.walk(assertion.test)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    # The requested evidence must be its own literal.  A manufactured combined
    # string such as "key: value" is representation-dependent and can pass
    # static validation while failing against the real serialized store.
    if literal not in constants:
        return False
    referenced = {
        node.id for node in ast.walk(assertion.test) if isinstance(node, ast.Name)
    }
    direct_call = any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == call_name
        for node in ast.walk(assertion.test)
    )
    return direct_call or bool(referenced & names)


def validate_explicit_objective_evidence(contract: str, content: str, tree: ast.AST, kind: str) -> None:
    """Bind exact requested output and durable marker evidence to real assertions."""
    output_names = assigned_call_names(tree, "eval_planned_tool")
    memory_names = assigned_call_names(tree, "get_memory")
    assertions = [node for node in ast.walk(tree) if isinstance(node, ast.Assert)]
    missing_output = [
        literal
        for literal in explicit_output_literals(contract)
        if not any(assertion_observes(node, "eval_planned_tool", output_names, literal) for node in assertions)
    ]
    if missing_output:
        raise GateError(
            f"{kind} test does not assert explicit desired output literal(s) from the immutable objective: "
            + ",".join(repr(value) for value in missing_output)
            + ". Assert each literal against the real eval_planned_tool result"
        )

    missing_memory: list[str] = []
    for family, key, value in explicit_marker_examples(contract):
        exact_marker = f"[{family}: {key} | {value}]"
        if exact_marker not in content:
            raise GateError(
                f"{kind} test omits exact marker example required by the immutable objective: {exact_marker}"
            )
        for item in (key, value):
            if not any(assertion_observes(node, "get_memory", memory_names, item) for node in assertions):
                missing_memory.append(f"{family}:{item}")
    if missing_memory:
        raise GateError(
            f"{kind} test does not independently assert every concrete marker key/value against get_memory(): "
            + ",".join(missing_memory)
            + ". Use one exact literal per assertion, for example: mem = get_memory(); "
            "assert \"lesson_probe\" in mem; assert \"lesson_value\" in mem. "
            "A combined literal such as \"lesson_probe: lesson_value\" is rejected."
        )


def validate_acceptance_retains_explicit_markers(contract: str, acceptance: str) -> None:
    """Prevent an authored acceptance contract from weakening literal input families."""
    required = explicit_marker_families(contract)
    accepted = explicit_marker_families(acceptance)
    missing = sorted(required - accepted)
    if missing:
        raise GateError(
            "acceptance criteria omit or misspell explicit marker family/families from the durable objective/plan: "
            + ",".join(f"[{family}]" for family in missing)
            + ". Preserve the existing criterion IDs and copy every family byte-for-byte into an observable "
            "outcome, for example `[criterion] Parse [LESSON: key | value] and "
            "[CORRECTION: key | value] through the production tool.`"
        )


def validate_explicit_marker_coverage(contract: str, e2e_content: str) -> None:
    """Bind literal marker families named by objective/acceptance to live E2E input."""
    if objective_requires_discord_retrieval(contract):
        # For a channel-reading surface the markers are external observations, not
        # arguments. Requiring them inside eval_planned_tool(...) changes a channel
        # ID into transcript text and silently stops testing Discord altogether.
        return
    families = explicit_marker_families(contract)
    missing = [family for family in sorted(families) if f"[{family}:" not in e2e_content]
    if missing:
        raise GateError(
            "E2E test omits explicit input marker family/families required by the durable objective or acceptance: "
            + ",".join(f"[{family}: ...]" for family in missing)
            + ". Include every named marker in the real eval_planned_tool transcript and verify its durable effect"
        )


def validate_no_test_owned_evidence(tree: ast.AST) -> None:
    """Reject E2E assertions whose expected value is manufactured by their command."""
    command_literals: set[str] = set()
    assertion_literals: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and (
            (isinstance(node.func, ast.Attribute) and node.func.attr in {"run", "check_output", "Popen"})
            or (isinstance(node.func, ast.Name) and node.func.id in {"run", "check_output"})
        ):
            for child in ast.walk(node):
                if isinstance(child, ast.Constant) and isinstance(child.value, str) and len(child.value) >= 4:
                    command_literals.add(child.value)
        if isinstance(node, ast.Assert):
            for child in ast.walk(node):
                if isinstance(child, ast.Constant) and isinstance(child.value, str) and len(child.value) >= 4:
                    assertion_literals.add(child.value)
    if command_literals & assertion_literals:
        raise GateError(
            "E2E test asserts evidence embedded in its own subprocess command; "
            "invoke the real production CLI/API/process and assert its independently produced result"
        )
    tokens = command_tokens(tree)
    inline_flags = {"-c", "-e", "--eval", "-command", "-encodedcommand"}
    output_only_commands = {"echo", "/bin/echo", "printf", "/usr/bin/printf", "true", "/usr/bin/true"}
    if tokens & inline_flags:
        raise GateError(
            "E2E test executes inline interpreter/shell code owned by the evaluator; "
            "invoke the real production executable/API/IPC surface instead"
        )
    if tokens & output_only_commands:
        raise GateError(
            "E2E test invokes an output-only command that manufactures its own evidence"
        )


def validate_staging(
    name: str,
) -> tuple[
    str,
    str,
    str,
    subprocess.CompletedProcess[str],
    subprocess.CompletedProcess[str],
]:
    if not SAFE_NAME.fullmatch(name):
        raise GateError("name must match [a-z][a-z0-9_]{2,63}")
    workflow = workflow_record()
    if workflow.get("state") not in {"tests_authoring", "tests_validated"}:
        raise GateError("evaluator validation requires a completed investigation and validated plan")
    if workflow.get("name") != name:
        raise GateError("staged evaluator name does not match the durable workflow")
    if not PLAN_BODY.is_file() or file_digest(PLAN_BODY) != workflow.get("plan_body_hash"):
        raise GateError("implementation plan bytes do not match the controller-recorded plan hash")
    if parse_plan(PLAN_BODY.read_text(encoding="utf-8"), workflow) != workflow.get("planned_files"):
        raise GateError("implementation plan file manifest does not match the controller record")
    acceptance_path = STAGING / "acceptance.txt"
    regression_stage = STAGING / "regression.py"
    e2e_stage = STAGING / "e2e.py"
    for path in (acceptance_path, regression_stage, e2e_stage):
        if not path.is_file() or path.is_symlink():
            raise GateError(f"missing safe staged artifact: {path.name}")
    acceptance = acceptance_path.read_text(encoding="utf-8").strip()
    regression_content = regression_stage.read_text(encoding="utf-8")
    e2e_content = e2e_stage.read_text(encoding="utf-8")
    errors: list[str] = []
    regression_tree = None
    e2e_tree = None
    if len(acceptance) < 40 or len(acceptance) > 8_000:
        errors.append("acceptance criteria must be 40-8000 characters")
    for value, label in (
        (acceptance, "acceptance criteria"),
        (regression_content, "regression test"),
        (e2e_content, "E2E test"),
    ):
        try:
            reject_incomplete_artifact(value, label)
        except GateError as exc:
            errors.append(str(exc))
    try:
        acceptance_criteria(acceptance)
        reject_nonbehavioral_acceptance(acceptance)
        validate_acceptance_retains_explicit_markers(
            workflow.get("objective", "") + "\n" + PLAN_BODY.read_text(encoding="utf-8"),
            acceptance,
        )
    except GateError as exc:
        errors.append(str(exc))
    try:
        regression_tree = validate_python_test(regression_content, "regression")
        validate_regression_observes_behavior(regression_tree)
        validate_evaluator_scratch(regression_tree, "regression")
        validate_no_swallowed_execution_failures(regression_tree, "regression")
        validate_tests_assert_desired_outcomes(regression_tree, "regression")
        validate_registered_tool_transport(
            regression_content, PLAN_BODY.read_text(encoding="utf-8"), "regression"
        )
        validate_explicit_objective_evidence(
            workflow.get("objective", "") + "\n" + PLAN_BODY.read_text(encoding="utf-8"),
            regression_content,
            regression_tree,
            "regression",
        )
    except GateError as exc:
        errors.append(str(exc))
    try:
        e2e_tree = validate_python_test(e2e_content, "e2e")
        validate_evaluator_scratch(e2e_tree, "E2E")
        validate_no_swallowed_execution_failures(e2e_tree, "E2E")
        validate_tests_assert_desired_outcomes(e2e_tree, "E2E")
        validate_registered_tool_transport(
            e2e_content, PLAN_BODY.read_text(encoding="utf-8"), "E2E"
        )
        validate_e2e_matches_plan(
            e2e_content,
            PLAN_BODY.read_text(encoding="utf-8"),
            workflow.get("planned_files", []),
        )
        validate_explicit_marker_coverage(
            acceptance + "\n" + PLAN_BODY.read_text(encoding="utf-8"), e2e_content
        )
        validate_explicit_objective_evidence(
            workflow.get("objective", "") + "\n" + PLAN_BODY.read_text(encoding="utf-8"),
            e2e_content,
            e2e_tree,
            "E2E",
        )
    except GateError as exc:
        errors.append(str(exc))
    if regression_tree is not None and e2e_tree is not None:
        try:
            validate_acceptance_coverage(acceptance, regression_tree, e2e_tree)
        except GateError as exc:
            errors.append(str(exc))
        try:
            validate_no_test_owned_evidence(e2e_tree)
        except GateError as exc:
            errors.append(str(exc))
    baseline = subprocess.CompletedProcess([], 1, "not run because static validation failed")
    e2e_baseline = subprocess.CompletedProcess([], 1, "not run because static validation failed")
    registered_surface = registered_tool_surface(PLAN_BODY.read_text(encoding="utf-8"))
    if regression_tree is not None:
        baseline = run_python(regression_stage)
        if baseline.returncode == 0:
            errors.append("candidate regression already passes unchanged source; no causal pre-change failure was proved")
        elif "AssertionError" not in baseline.stdout or any(
            marker in baseline.stdout
            for marker in (
                "ModuleNotFoundError",
                "FileNotFoundError",
                "PermissionError",
                "ImportError",
                "SyntaxError",
                "CalledProcessError",
                "command not found",
                "No such file or directory",
            )
        ):
            errors.append(
                "candidate regression failed before reaching its behavioral assertion; "
                "pre-change evidence must be an AssertionError caused by the missing behavior, "
                "not a permission, path, syntax, import, timeout, or evaluator-runtime failure"
            )
        elif registered_surface and not registered_tool_boundary_reached(baseline.stdout, registered_surface):
            errors.append(
                "candidate regression did not reach the registered production-tool boundary; "
                "a fixture or evaluator assertion failed before the missing behavior was invoked"
            )
    if e2e_tree is not None:
        e2e_baseline = run_python(e2e_stage)
        if e2e_baseline.returncode == 0:
            errors.append("candidate E2E already passes unchanged source; no causal pre-change failure was proved")
        elif "AssertionError" not in e2e_baseline.stdout or any(
            marker in e2e_baseline.stdout
            for marker in (
                "ModuleNotFoundError",
                "FileNotFoundError",
                "PermissionError",
                "ImportError",
                "SyntaxError",
                "NameError",
                "AttributeError",
                "ConnectionRefusedError",
                "TimeoutError",
                "socket.timeout",
                "CalledProcessError",
                "command not found",
                "No such file or directory",
            )
        ):
            errors.append(
                "candidate E2E failed before reaching its behavioral assertion; "
                "pre-change evidence must be an AssertionError caused by the missing behavior, "
                "not a permission, path, syntax, import, connection, timeout, or evaluator-runtime failure"
            )
        elif registered_surface and not registered_tool_boundary_reached(e2e_baseline.stdout, registered_surface):
            errors.append(
                "candidate E2E did not reach the registered production-tool boundary; "
                "a fixture or evaluator assertion failed before the missing behavior was invoked"
            )
    if errors:
        unique_errors = list(dict.fromkeys(errors))
        raise GateError(
            f"staging validation found {len(unique_errors)} issue(s):\n- " + "\n- ".join(unique_errors)
        )
    return acceptance, regression_content, e2e_content, baseline, e2e_baseline


def staged_hashes() -> dict[str, str]:
    values: dict[str, str] = {}
    for name in ("acceptance.txt", "regression.py", "e2e.py", "plan_body.md"):
        path = STAGING / name
        values[name] = file_digest(path) if path.is_file() and not path.is_symlink() else "missing"
    return values


def persist_validation_failure(name: str, error: str) -> tuple[int, int]:
    record = workflow_record()
    hashes = staged_hashes()
    fingerprint = digest(json.dumps({"hashes": hashes, "error": error}, sort_keys=True).encode())
    attempts = record.setdefault("validation_attempts", [])
    if not isinstance(attempts, list):
        raise GateError("validation attempt ledger is malformed")
    repeat = 1
    if attempts and isinstance(attempts[-1], dict) and attempts[-1].get("fingerprint") == fingerprint:
        repeat = int(attempts[-1].get("repeat", 1)) + 1
    receipt = {
        "version": 2,
        "status": "failed",
        "name": name,
        "artifact_hashes": hashes,
        "diagnostic": error,
        "fingerprint": fingerprint,
        "repeat": repeat,
        "attempt": len(attempts) + 1,
        "validated_at": int(time.time()),
    }
    attempts.append(receipt)
    record["last_validation"] = receipt
    atomic_json(WORKFLOW, record)
    atomic_json(STAGING / "validation.json", receipt)
    refresh_plan_document(record)
    return repeat, len(attempts)


def lint_staged(kind: str) -> None:
    if kind not in {"acceptance", "regression", "e2e"}:
        raise GateError("lint kind must be acceptance, regression, or e2e")
    record = workflow_record()
    if record.get("state") != "tests_authoring":
        raise GateError("evaluator writes are legal only in the tests_authoring phase")
    path = STAGING / ("acceptance.txt" if kind == "acceptance" else f"{kind}.py")
    if not path.is_file() or path.is_symlink():
        raise GateError(f"staged {kind} artifact is missing")
    content = path.read_text(encoding="utf-8")
    try:
        reject_incomplete_artifact(content, f"{kind} artifact")
        if kind == "acceptance":
            acceptance_criteria(content)
            reject_nonbehavioral_acceptance(content)
            validate_acceptance_retains_explicit_markers(
                record.get("objective", "") + "\n" + PLAN_BODY.read_text(encoding="utf-8"),
                content,
            )
        else:
            tree = validate_python_test(content, kind)
            validate_evaluator_scratch(tree, kind)
            validate_no_swallowed_execution_failures(tree, kind)
            validate_tests_assert_desired_outcomes(tree, kind)
            if kind == "regression":
                validate_regression_observes_behavior(tree)
                validate_explicit_objective_evidence(
                    record.get("objective", "") + "\n" + PLAN_BODY.read_text(encoding="utf-8"),
                    content,
                    tree,
                    "regression",
                )
            else:
                validate_no_test_owned_evidence(tree)
                validate_e2e_matches_plan(
                    content,
                    PLAN_BODY.read_text(encoding="utf-8"),
                    record.get("planned_files", []),
                )
                validate_explicit_marker_coverage(
                    record.get("objective", "") + "\n" + PLAN_BODY.read_text(encoding="utf-8"),
                    content,
                )
                validate_explicit_objective_evidence(
                    record.get("objective", "") + "\n" + PLAN_BODY.read_text(encoding="utf-8"),
                    content,
                    tree,
                    "E2E",
                )
            validate_registered_tool_transport(
                content, PLAN_BODY.read_text(encoding="utf-8"), kind
            )
    except GateError as exc:
        receipt = {
            "version": 2,
            "status": "failed",
            "kind": kind,
            "sha256": file_digest(path),
            "diagnostic": str(exc),
            "linted_at": int(time.time()),
        }
        atomic_json(STAGING / "lint.json", receipt)
        raise GateError(f"{kind} artifact retained but failed immediate lint: {exc}") from exc
    receipt = {
        "version": 2,
        "status": "passed",
        "kind": kind,
        "sha256": file_digest(path),
        "linted_at": int(time.time()),
    }
    atomic_json(STAGING / "lint.json", receipt)
    print(f"IMPROVEMENT_ARTIFACT_LINT_OK kind={kind} hash={receipt['sha256']}")


def write_artifact(kind: str, content_b64: str) -> None:
    if kind not in {"acceptance", "regression", "e2e"}:
        raise GateError("artifact kind must be acceptance, regression, or e2e")
    limit = 8_000 if kind == "acceptance" else MAX_TEST_BYTES
    content = decode_text(content_b64, f"{kind} artifact", limit)
    workflow = workflow_record()
    path = STAGING / ("acceptance.txt" if kind == "acceptance" else f"{kind}.py")
    validation = STAGING / "validation.json"
    # Candidate writes are transactional. A bad correction must never destroy the
    # last retained artifact/receipt set and strand a previously recoverable run.
    protected_paths = (path, WORKFLOW, validation, TRANSPORT_TEMPLATE_RECEIPT)
    previous = {
        protected: protected.read_bytes() if protected.is_file() and not protected.is_symlink() else None
        for protected in protected_paths
    }
    if kind == "acceptance":
        TRANSPORT_TEMPLATE_RECEIPT.unlink(missing_ok=True)
    transport_installed = False
    if kind in {"regression", "e2e"} and PLAN_BODY.is_file():
        plan_content = PLAN_BODY.read_text(encoding="utf-8")
        surface = registered_tool_surface(plan_content)
        if surface:
            receipt = load_record(TRANSPORT_TEMPLATE_RECEIPT) if TRANSPORT_TEMPLATE_RECEIPT.exists() else {}
            if (
                receipt.get("plan_hash") != workflow.get("plan_body_hash")
                or receipt.get("surface") != surface
            ):
                raise GateError(
                    "registered-tool evaluators are locked until improvement_test_transport_template([]) "
                    "records the current plan-bound transport contract; call it now, then submit only the named desired-outcome test functions"
                )
        content, transport_installed = install_registered_tool_transport(
            content, plan_content, kind
        )
    if workflow.get("state") == "tests_validated":
        workflow["state"] = "tests_authoring"
        workflow.pop("last_validation", None)
        atomic_json(WORKFLOW, workflow)
        refresh_plan_document(workflow)
    path.write_text(content + ("\n" if not content.endswith("\n") else ""), encoding="utf-8")
    if validation.exists() and validation.is_file() and not validation.is_symlink():
        validation.unlink()
    try:
        lint_staged(kind)
    except GateError as exc:
        for protected, old_bytes in previous.items():
            if old_bytes is None:
                protected.unlink(missing_ok=True)
            else:
                protected.parent.mkdir(parents=True, exist_ok=True)
                protected.write_bytes(old_bytes)
        raise GateError(
            f"{kind} candidate rejected; previous staged artifact and controller receipts were restored: {exc}"
        ) from exc
    if transport_installed:
        print(
            f"IMPROVEMENT_TRANSPORT_CANONICALIZED kind={kind} "
            "source=controller runner=controller behavior=model_authored"
        )


def validate(name: str) -> None:
    try:
        acceptance, regression_content, e2e_content, baseline, e2e_baseline = validate_staging(name)
    except GateError as exc:
        repeat, total = persist_validation_failure(name, str(exc))
        suffix = (
            f"\nVALIDATION_RECEIPT_WRITTEN repeated={repeat} total={total}; staged bytes retained. "
            "There is no retry or turn cap: change the diagnosed artifact bytes before validating again."
        )
        raise GateError(str(exc) + suffix) from exc
    receipt = {
        "version": 2,
        "status": "passed",
        "name": name,
        "acceptance_hash": digest(acceptance.encode()),
        "regression_hash": digest(regression_content.encode()),
        "e2e_hash": digest(e2e_content.encode()),
        "baseline_failure_hash": digest(baseline.stdout.encode()),
        "e2e_baseline_failure_hash": digest(e2e_baseline.stdout.encode()),
        "validated_at": int(time.time()),
    }
    atomic_json(STAGING / "validation.json", receipt)
    workflow = workflow_record()
    workflow["state"] = "tests_validated"
    workflow["last_validation"] = receipt
    atomic_json(WORKFLOW, workflow)
    refresh_plan_document(workflow)
    print(
        "STAGING_VALIDATION_OK"
        f" name={name} criteria={len(acceptance_criteria(acceptance))}"
        f" regression_hash={receipt['regression_hash']}"
        f" e2e_hash={receipt['e2e_hash']} prechange=both_failed_as_required"
    )


def sandbox_profile() -> str:
    return """(version 1)
(deny default)
(allow process*)
(allow file-read*)
(allow file-write* (subpath \"/private/tmp\") (subpath \"/tmp\"))
(allow network-outbound (remote ip \"localhost:*\"))
(allow network-inbound (local ip \"localhost:*\"))
"""


def run_python(path: Path, timeout: int = 300) -> subprocess.CompletedProcess[str]:
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": os.environ.get("HOME", ""),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "ERNOS_SOURCE_ROOT": str(ROOT),
        "ERNOS_NODE_URL": "http://127.0.0.1:5000",
        "ERNOS_WEB_URL": "http://127.0.0.1:8088",
    }
    command = [sys.executable, "-I", str(path)]
    sandbox = shutil.which("sandbox-exec")
    if sandbox:
        command = [sandbox, "-p", sandbox_profile(), *command]
    try:
        return subprocess.run(
            command,
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or "") + "\nTEST TIMEOUT"
        return subprocess.CompletedProcess(command, 124, output)


def verify_frozen_bytes(
    record: dict, *, enforce_dependency_hashes: bool = True
) -> tuple[Path, Path]:
    for field in ("id", "name", "acceptance_hash", "regression_hash", "e2e_hash", "regression_path", "e2e_path", "plan_path", "plan_hash"):
        if not isinstance(record.get(field), str) or not record[field]:
            raise GateError(f"record missing {field}")
    for field in ("acceptance_hash", "regression_hash", "e2e_hash", "plan_hash"):
        if not HASH.fullmatch(record[field]):
            raise GateError(f"record has malformed {field}")
    regression = ROOT / record["regression_path"]
    e2e = ROOT / record["e2e_path"]
    plan = ROOT / record["plan_path"]
    if regression.is_symlink() or e2e.is_symlink() or plan.is_symlink() or not regression.is_file() or not e2e.is_file() or not plan.is_file():
        raise GateError("frozen test is missing or replaced by a symlink")
    if file_digest(regression) != record["regression_hash"]:
        raise GateError(f"frozen regression hash mismatch for {record['id']}")
    if file_digest(e2e) != record["e2e_hash"]:
        raise GateError(f"frozen E2E hash mismatch for {record['id']}")
    if file_digest(plan) != record["plan_hash"]:
        raise GateError(f"frozen implementation-plan hash mismatch for {record['id']}")
    dependency_hashes = record.get("plan_dependency_hashes", {})
    if not isinstance(dependency_hashes, dict):
        raise GateError("frozen plan dependency manifest is malformed")
    for relative, expected_hash in dependency_hashes.items():
        if not isinstance(relative, str) or not isinstance(expected_hash, str) or not HASH.fullmatch(expected_hash):
            raise GateError("frozen plan dependency manifest contains malformed data")
        _, dependency = safe_relative_path(relative, must_exist=True)
        actual_hash = file_digest(dependency)
        if enforce_dependency_hashes and actual_hash != expected_hash:
            raise GateError(
                f"frozen plan dependency changed after investigation: {relative}; "
                f"expected={expected_hash} actual={actual_hash}",
                code="PLAN_SCOPE_MISSING",
            )
    return regression, e2e


def run_record(record: dict, live: bool) -> list[str]:
    completed = record.get("state") == "completed"
    regression, e2e = verify_frozen_bytes(
        record, enforce_dependency_hashes=not completed
    )
    outputs: list[str] = []
    regression_result = run_python(regression)
    outputs.append(regression_result.stdout[-4000:])
    if regression_result.returncode != 0:
        raise GateError(f"regression failed for {record['id']}:\n{regression_result.stdout[-4000:]}")
    if live:
        e2e_result = run_python(e2e)
        outputs.append(e2e_result.stdout[-4000:])
        if e2e_result.returncode != 0:
            raise GateError(f"live E2E failed for {record['id']}:\n{e2e_result.stdout[-4000:]}")
    # Recheck after execution even under the OS sandbox. A test may never rewrite its
    # evaluator to manufacture a pass.
    verify_frozen_bytes(record, enforce_dependency_hashes=not completed)
    return outputs


def cleanup_staging() -> None:
    for name in ("name.txt", "acceptance.txt", "regression.py", "e2e.py", "validation.json", "lint.json", "abort_reason.txt"):
        path = STAGING / name
        if path.exists() and path.is_file() and not path.is_symlink():
            path.unlink()


def freeze(name: str) -> None:
    if ACTIVE.exists():
        raise GateError("an improvement test transaction is already active")
    acceptance_path = STAGING / "acceptance.txt"
    regression_stage = STAGING / "regression.py"
    e2e_stage = STAGING / "e2e.py"
    workflow = workflow_record()
    if workflow.get("state") != "tests_validated":
        raise GateError("freeze requires a successful retained validation receipt")
    validation = load_record(STAGING / "validation.json")
    if validation.get("status") != "passed":
        raise GateError("freeze requires the latest validation receipt to be successful")
    acceptance, regression_content, e2e_content, baseline, e2e_baseline = validate_staging(name)
    stamp = str(time.time_ns())
    transaction_id = digest(
        (name + "\n" + digest(acceptance.encode()) + "\n" + digest(regression_content.encode()) + "\n" + stamp).encode()
    )
    FROZEN.mkdir(parents=True, exist_ok=True)
    acceptance_frozen = FROZEN / f"{transaction_id}.acceptance.txt"
    regression_frozen = FROZEN / f"{transaction_id}.regression.py"
    e2e_frozen = FROZEN / f"{transaction_id}.e2e.py"
    plan_frozen = FROZEN / f"{transaction_id}.plan.md"
    os.replace(acceptance_path, acceptance_frozen)
    os.replace(regression_stage, regression_frozen)
    os.replace(e2e_stage, e2e_frozen)
    shutil.copy2(PLAN_BODY, plan_frozen)
    for staged_name in ("name.txt", "validation.json"):
        staged_path = STAGING / staged_name
        if staged_path.exists() and staged_path.is_file() and not staged_path.is_symlink():
            staged_path.unlink()
    implementation_baseline_hashes: dict[str, str] = {}
    for relative in workflow["planned_files"]:
        planned_path = (ROOT / relative).resolve()
        implementation_baseline_hashes[relative] = (
            file_digest(planned_path)
            if planned_path.is_file() and not planned_path.is_symlink()
            else "absent"
        )
    discovery_by_path = {
        entry.get("path"): entry
        for entry in workflow.get("discovery", [])
        if isinstance(entry, dict)
    }
    plan_dependency_hashes = {
        relative: discovery_by_path[relative]["sha256"]
        for relative in workflow.get("plan_discovery_paths", [])
        if relative not in workflow["planned_files"]
        and relative in discovery_by_path
        and isinstance(discovery_by_path[relative].get("sha256"), str)
    }
    record = {
        "version": 1,
        "id": transaction_id,
        "name": name,
        "state": "frozen",
        "acceptance_path": str(acceptance_frozen.relative_to(ROOT)),
        "acceptance_hash": file_digest(acceptance_frozen),
        "regression_path": str(regression_frozen.relative_to(ROOT)),
        "regression_hash": file_digest(regression_frozen),
        "e2e_path": str(e2e_frozen.relative_to(ROOT)),
        "e2e_hash": file_digest(e2e_frozen),
        "plan_path": str(plan_frozen.relative_to(ROOT)),
        "plan_hash": file_digest(plan_frozen),
        "planned_files": workflow["planned_files"],
        "implementation_baseline_hashes": implementation_baseline_hashes,
        "plan_dependency_hashes": plan_dependency_hashes,
        "planned_surfaces": workflow.get("planned_surfaces", plan_callable_surfaces(PLAN_BODY.read_text(encoding="utf-8"))),
        "discovery_hash": workflow.get("discovery_hash", ""),
        "baseline_failure_hash": digest(baseline.stdout.encode()),
        "baseline_failure_tail": baseline.stdout[-2000:],
        "e2e_baseline_failure_hash": digest(e2e_baseline.stdout.encode()),
        "e2e_baseline_failure_tail": e2e_baseline.stdout[-2000:],
        "frozen_at": int(time.time()),
    }
    atomic_json(ACTIVE, record)
    workflow["state"] = "frozen"
    workflow["transaction_id"] = transaction_id
    atomic_json(WORKFLOW, workflow)
    refresh_plan_document(workflow, record)
    print(
        "FREEZE_OK"
        f" id={transaction_id}"
        f" regression_hash={record['regression_hash']}"
        f" e2e_hash={record['e2e_hash']}"
        " prechange=both_failed_as_required"
    )


def transition(expected: tuple[str, ...], new_state: str) -> dict:
    record = load_record(ACTIVE)
    if record.get("state") not in expected:
        raise GateError(f"active transaction state {record.get('state')!r} is not one of {expected}")
    verify_frozen_bytes(record)
    record["state"] = new_state
    record[f"{new_state}_at"] = int(time.time())
    atomic_json(ACTIVE, record)
    if WORKFLOW.exists():
        workflow = workflow_record()
        workflow["state"] = new_state
        atomic_json(WORKFLOW, workflow)
        refresh_plan_document(workflow, record)
    return record


def start_implementation() -> None:
    record = load_record(ACTIVE)
    if record.get("state") not in {"frozen", "implementing", "repair_required"}:
        raise GateError("implementation may start only from a frozen or failed-live repair transaction")
    verify_frozen_bytes(record)
    print(
        f"IMPLEMENTATION_READY id={record['id']} tests=immutable "
        "state changes only after the first verified production write"
    )


def safe_planned_implementation_path(encoded: str) -> Path:
    try:
        decoded = base64.b64decode(encoded, validate=True).decode("utf-8")
    except (ValueError, UnicodeDecodeError) as exc:
        raise GateError("implementation path encoding is invalid") from exc
    relative = Path(decoded)
    if not decoded or relative.is_absolute() or ".." in relative.parts:
        raise GateError("implementation path must be a safe repository-relative path")
    resolved = (ROOT / relative).resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise GateError("implementation path escapes the repository") from exc
    return resolved


def safe_implementation_path(encoded: str) -> Path:
    resolved = safe_planned_implementation_path(encoded)
    if not resolved.is_file() or resolved.is_symlink():
        raise GateError(f"implementation path is not a regular file: {resolved.relative_to(ROOT)}")
    return resolved


def implementation_candidate_path(record: dict, target: Path) -> Path:
    transaction_id = record.get("id")
    if not isinstance(transaction_id, str) or not HASH.fullmatch(transaction_id):
        raise GateError("active transaction id is malformed")
    return target.parent / f".ernos-candidate-{transaction_id[:16]}-{target.name}"


def candidate_record(record: dict, relative: str) -> dict | None:
    candidates = record.get("implementation_candidates", {})
    if not isinstance(candidates, dict):
        raise GateError("implementation candidate manifest is malformed")
    value = candidates.get(relative)
    if value is None:
        return None
    if not isinstance(value, dict):
        raise GateError(f"implementation candidate receipt is malformed: {relative}")
    return value


def split_top_level_arguments(content: str) -> list[str]:
    """Split a model-default comma call without touching strings/nested calls."""
    parts: list[str] = []
    start = 0
    depth = 0
    quote = ""
    escaped = False
    for index, char in enumerate(content):
        if escaped:
            escaped = False
            continue
        if quote:
            if char == "\\":
                escaped = True
            elif char == quote:
                quote = ""
            continue
        if char in {'"', "'"}:
            quote = char
        elif char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
        elif char == "," and depth == 0:
            parts.append(content[start:index].strip())
            start = index + 1
    parts.append(content[start:].strip())
    return parts


def split_top_level_ernos_arguments(content: str) -> list[str]:
    """Split ErnosPlain's `left and right` call arguments outside nested syntax."""
    parts: list[str] = []
    start = 0
    depth = 0
    quote = ""
    escaped = False
    index = 0
    while index < len(content):
        char = content[index]
        if escaped:
            escaped = False
        elif quote:
            if char == "\\":
                escaped = True
            elif char == quote:
                quote = ""
        elif char in {'"', "'"}:
            quote = char
        elif char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
        elif depth == 0 and content.startswith(" and ", index):
            parts.append(content[start:index].strip())
            index += 4
            start = index + 1
        index += 1
    parts.append(content[start:].strip())
    return parts


def normalize_multi_argument_concat(text: str) -> tuple[str, int]:
    """Canonicalize unambiguous Python-style concat(a,b,...) to ErnosPlain."""
    changes = 0
    while True:
        replacement: tuple[int, int, str] | None = None
        for match in reversed(list(re.finditer(r"\bconcat\(", text))):
            start = match.end()
            depth = 1
            quote = ""
            escaped = False
            index = start
            while index < len(text):
                char = text[index]
                if escaped:
                    escaped = False
                elif quote:
                    if char == "\\":
                        escaped = True
                    elif char == quote:
                        quote = ""
                elif char in {'"', "'"}:
                    quote = char
                elif char == "(":
                    depth += 1
                elif char == ")":
                    depth -= 1
                    if depth == 0:
                        comma_args = split_top_level_arguments(text[start:index])
                        args = comma_args
                        should_normalize = len(comma_args) > 1
                        if len(comma_args) == 1:
                            args = split_top_level_ernos_arguments(text[start:index])
                            should_normalize = len(args) > 2
                        if should_normalize and all(args):
                            nested = args[-1]
                            for arg in reversed(args[:-1]):
                                nested = f"concat({arg} and {nested})"
                            replacement = (match.start(), index + 1, nested)
                        break
                index += 1
            if replacement is not None:
                break
        if replacement is None:
            return text, changes
        begin, end, value = replacement
        text = text[:begin] + value + text[end:]
        changes += 1


def normalize_bare_string_concat_assignments(text: str) -> tuple[str, int]:
    """Wrap an otherwise invalid top-level string `a and b and c` assignment."""
    lines = text.splitlines(keepends=True)
    changes = 0
    for index, line in enumerate(lines):
        newline = "\n" if line.endswith("\n") else ""
        body = line[:-1] if newline else line
        match = re.match(
            r'^(\s*set\s+[A-Za-z_][A-Za-z0-9_]*\s+to\s+)(.+)$', body
        )
        if not match:
            continue
        expression = match.group(2)
        if " and also " in expression or " or else " in expression:
            continue
        parts = split_top_level_ernos_arguments(expression)
        if len(parts) < 2 or not all(parts):
            continue
        if not any(re.search(r'(^|[^\\])["\']', part) for part in parts):
            continue
        nested = parts[-1]
        for part in reversed(parts[:-1]):
            nested = f"concat({part} and {nested})"
        lines[index] = match.group(1) + nested + newline
        changes += 1
    return "".join(lines), changes


def top_level_function_block(text: str, name: str) -> tuple[int, int, str]:
    """Return one complete top-level ErnosPlain function block."""
    match = re.search(rf"(?m)^define\s+{re.escape(name)}\b[^\n]*\n", text)
    if not match:
        return -1, -1, ""
    next_define = re.search(r"(?m)^define\s+", text[match.end():])
    end = match.end() + next_define.start() if next_define else len(text)
    return match.start(), end, text[match.start():end]


def additive_schema_entries(block: str) -> list[tuple[str, str]]:
    """Split a schema function into named entry blocks in source order."""
    lines = block.splitlines(keepends=True)
    starts: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        match = re.search(
            r'set\s+schemas\s+to\s+(?:concat\(schemas\s+and\s+)?"-\s*'
            r'([A-Za-z_][A-Za-z0-9_]*)\(',
            line,
        )
        if match:
            starts.append((index, match.group(1)))
    entries: list[tuple[str, str]] = []
    for position, (start, name) in enumerate(starts):
        end = starts[position + 1][0] if position + 1 < len(starts) else len(lines)
        for line_index in range(start + 1, end):
            if lines[line_index].lstrip().startswith("return schemas"):
                end = line_index
                break
        entries.append((name, "".join(lines[start:end])))
    return entries


def merge_additive_registry_function(
    baseline: str,
    candidate: str,
    function_name: str,
    entry_pattern: str,
    return_marker: str,
    allowed_additions: set[str] | None = None,
) -> tuple[str, list[str]]:
    """Preserve an existing registry function and append only genuinely new entries."""
    base_start, base_end, base_block = top_level_function_block(baseline, function_name)
    cand_start, cand_end, cand_block = top_level_function_block(candidate, function_name)
    if base_start < 0 or cand_start < 0:
        return candidate, []

    if function_name == "self_extensions_schema":
        base_entries = additive_schema_entries(base_block)
        candidate_entries = additive_schema_entries(cand_block)
    else:
        def known_entries(block: str) -> list[tuple[str, str]]:
            matches = list(re.finditer(entry_pattern, block, flags=re.MULTILINE))
            result: list[tuple[str, str]] = []
            for index, match in enumerate(matches):
                end = matches[index + 1].start() if index + 1 < len(matches) else block.find(return_marker, match.end())
                if end < 0:
                    end = len(block)
                result.append((match.group(1), block[match.start():end]))
            return result
        base_entries = known_entries(base_block)
        candidate_entries = known_entries(cand_block)

    existing = {name for name, _ in base_entries}
    additions = [
        (name, body)
        for name, body in candidate_entries
        if name not in existing and (allowed_additions is None or name in allowed_additions)
    ]
    merged = base_block
    insertion = merged.rfind(return_marker)
    if insertion < 0:
        return candidate, []
    addition_bytes = "".join(body for _, body in additions)
    merged = merged[:insertion] + addition_bytes + merged[insertion:]
    if merged == cand_block:
        return candidate, []
    return candidate[:cand_start] + merged + candidate[cand_end:], [name for name, _ in additions]


def normalize_candidate_dialect(
    record: dict, candidate: Path, target: Path | None = None
) -> list[str]:
    """Normalize only exact, semantics-preserving local-model source dialects."""
    if candidate.suffix != ".ep":
        return []
    text = candidate.read_text(encoding="utf-8")
    original = text
    rules: list[str] = []

    # Provider-constrained JSON can still leak only its closing transport bytes into
    # a large string argument. Remove the two observed suffix forms only when they
    # occur after a complete final ErnosPlain return string at end-of-file.
    cleaned = re.sub(r'(?m)(^\s*return\s+"[^"\n]*")"\]\}?\s*$', r"\1\n", text)
    cleaned = re.sub(r"\s*\]\}\s*$", "\n", cleaned)
    if cleaned != text:
        text = cleaned
        rules.append("transport_suffix")

    plan_path_value = record.get("plan_path")
    plan_text = ""
    if isinstance(plan_path_value, str):
        plan_path = ROOT / plan_path_value
        if plan_path.is_file() and not plan_path.is_symlink():
            plan_text = plan_path.read_text(encoding="utf-8", errors="replace")
    planned_files = record.get("planned_files", [])
    extension_target = (
        isinstance(planned_files, list)
        and "decent_agent/self_extensions.ep" in planned_files
    )
    if extension_target and '"storage_db"' in plan_text and "map_get_val" in plan_text:
        storage_aliases = (
            "tools_storage_get_db()",
            "storage_get_api_db()",
            "storage_get_db()",
        )
        for alias in storage_aliases:
            if alias in text:
                text = text.replace(alias, 'map_get_val(ctx and "storage_db")')
                rules.append("extension_storage_context")
        if 'import "../storage"\n' in text:
            text = text.replace('import "../storage"\n', "")
            rules.append("extension_storage_import_removed")
        if 'import "../decent_agent/tools"\n' in text:
            text = text.replace('import "../decent_agent/tools"\n', "")
            rules.append("extension_controller_import_removed")

    # When the frozen, hash-verified plan proves both the exact module import and a
    # working call site, a candidate that already calls that function but omitted the
    # import has one unambiguous repair. Add only those exact proven imports; never
    # invent an API or use a guessed module path.
    required_imports: list[tuple[str, tuple[str, ...], str]] = [
        (
            'import "../decent_net/bridge_rpc"',
            ("bridge_enqueue(", "bridge_wait_result("),
            "bridge_rpc_import_missing",
        ),
    ]
    missing_imports: list[str] = []
    for import_line, call_markers, rule in required_imports:
        if (
            import_line in plan_text
            and import_line not in text
            and any(marker in text for marker in call_markers)
        ):
            missing_imports.append(import_line)
            rules.append(rule)
    if missing_imports:
        imports = list(re.finditer(r'(?m)^import\s+"[^"]+"\s*$', text))
        if imports:
            insert_at = imports[-1].end()
            text = text[:insert_at] + "\n" + "\n".join(missing_imports) + text[insert_at:]
        else:
            text = "\n".join(missing_imports) + "\n" + text

    # Gemma's stable assignment dialect is unambiguous at a complete ErnosPlain
    # `set <identifier> = <expression>` statement. Normalize the operator only; the
    # compiler remains authoritative for the expression and surrounding structure.
    text, set_assignment_changes = re.subn(
        r"(?m)^(\s*set\s+[A-Za-z_][A-Za-z0-9_]*\s*)=(\s*.+)$",
        r"\1to\2",
        text,
    )
    if set_assignment_changes:
        rules.append(f"set_assignment:{set_assignment_changes}")

    text, concat_changes = normalize_multi_argument_concat(text)
    if concat_changes:
        rules.append(f"concat_binary:{concat_changes}")

    text, bare_concat_changes = normalize_bare_string_concat_assignments(text)
    if bare_concat_changes:
        rules.append(f"bare_string_concat:{bare_concat_changes}")

    if extension_target and target is not None:
        baseline = target.read_text(encoding="utf-8", errors="replace")
        # Additive registered-tool work is authorised to extend the registry and its
        # one dispatch branch, not to rewrite shared helpers. Preserve every existing
        # top-level helper byte-exactly before any branch-level normalization. This
        # closes the gap where a candidate inverted self_extensions_distill_kind while
        # all registered action branches still appeared unchanged.
        protected_registry_functions = {
            "self_extensions_schema",
            "self_extensions_action_known",
            "self_extensions_execute",
        }
        for helper_name in sorted(top_level_define_names(baseline) - protected_registry_functions):
            baseline_helper = top_level_function_block(baseline, helper_name)[2]
            candidate_helper = top_level_function_block(text, helper_name)[2]
            if baseline_helper and candidate_helper and baseline_helper != candidate_helper:
                text = text.replace(candidate_helper, baseline_helper, 1)
                rules.append(f"existing_helper_preserved:{helper_name}")
        baseline_execute = top_level_function_block(baseline, "self_extensions_execute")[2]
        candidate_execute = top_level_function_block(text, "self_extensions_execute")[2]
        baseline_known = top_level_function_block(baseline, "self_extensions_action_known")[2]
        candidate_known = top_level_function_block(text, "self_extensions_action_known")[2]
        baseline_actions = set(re.findall(r'if action_name equals "([A-Za-z_][A-Za-z0-9_]*)"', baseline_execute))
        candidate_dispatch_actions = set(re.findall(r'if action_name equals "([A-Za-z_][A-Za-z0-9_]*)"', candidate_execute))
        candidate_known_actions = set(re.findall(r'if action_name equals "([A-Za-z_][A-Za-z0-9_]*)"', candidate_known))
        required_surface = str(record.get("required_surface", "")).strip()
        if not required_surface:
            planned_surfaces = record.get("planned_surfaces", [])
            if isinstance(planned_surfaces, list) and planned_surfaces:
                required_surface = str(planned_surfaces[0]).strip()
        allowed_new_actions = set()
        if (
            required_surface
            and required_surface in candidate_dispatch_actions
            and required_surface in candidate_known_actions
            and required_surface not in baseline_actions
        ):
            allowed_new_actions.add(required_surface)
        original_schema_block = top_level_function_block(text, "self_extensions_schema")[2]
        text, schema_additions = merge_additive_registry_function(
            baseline,
            text,
            "self_extensions_schema",
            "",
            "    return schemas",
            allowed_new_actions,
        )
        if top_level_function_block(text, "self_extensions_schema")[2] != original_schema_block:
            rule = "existing_schema_preserved"
            if schema_additions:
                rule += ":add=" + ",".join(schema_additions)
            rules.append(rule)

        original_known_block = top_level_function_block(text, "self_extensions_action_known")[2]
        text, known_additions = merge_additive_registry_function(
            baseline,
            text,
            "self_extensions_action_known",
            r'^    if action_name equals "([A-Za-z_][A-Za-z0-9_]*)":\n(?:        .*\n)+?',
            "    return 0",
            allowed_new_actions,
        )
        if top_level_function_block(text, "self_extensions_action_known")[2] != original_known_block:
            rule = "existing_action_registry_preserved"
            if known_additions:
                rule += ":add=" + ",".join(known_additions)
            rules.append(rule)

        execute_at = baseline.find("define self_extensions_execute")
        existing_actions = re.findall(
            r'(?m)^    if action_name equals "([A-Za-z_][A-Za-z0-9_]*)":',
            baseline[execute_at:] if execute_at >= 0 else "",
        )
        for action_name in existing_actions:
            # A failed live deployment is repaired against the already-promoted
            # source, so the active surface is necessarily present in `target`.
            # It is the one branch this transaction is authorised to change;
            # treating it as unrelated pre-existing behavior silently erased every
            # causal repair and produced a byte-identical candidate loop.
            if action_name == required_surface:
                continue
            baseline_branch = self_extension_dispatch_branch(baseline, action_name)
            candidate_branch = self_extension_dispatch_branch(text, action_name)
            if not baseline_branch:
                continue
            if candidate_branch and baseline_branch != candidate_branch:
                text = text.replace(candidate_branch, baseline_branch, 1)
                rules.append(f"existing_action_preserved:{action_name}")
                continue
            if not candidate_branch:
                candidate_execute = top_level_function_block(text, "self_extensions_execute")[2]
                terminal = '    return "Error: self-extension dispatch received an unregistered action."'
                insertion = candidate_execute.rfind(terminal)
                if insertion < 0:
                    continue
                repaired_execute = (
                    candidate_execute[:insertion]
                    + baseline_branch
                    + "\n"
                    + candidate_execute[insertion:]
                )
                text = text.replace(candidate_execute, repaired_execute, 1)
                rules.append(f"existing_action_restored:{action_name}")

        # A path-like identifier means a slash anywhere in the identifier, not only
        # the one-character strings "/" or "\\". Gemma repeatedly emits that exact
        # equality form while otherwise implementing the frozen session-transcript
        # contract correctly. Canonicalize only the complete three-clause guard in
        # the transaction-authorized branch; arbitrary conditions and other actions
        # remain untouched and the objective validator still proves both substrings.
        if required_surface:
            active_branch = self_extension_dispatch_branch(text, required_surface)
            if active_branch:
                fixed_branch, path_guard_changes = re.subn(
                    r'(?m)^(\s*)if\s+string_length\(session_id\)\s*==\s*0\s+'
                    r'or(?:\s+else)?\s+session_id\s+(?:==|equals)\s*"/"\s+'
                    r'or(?:\s+else)?\s+session_id\s+(?:==|equals)\s*"\\\\"\s*:\s*$',
                    r'\1if string_length(session_id) == 0 or else '
                    r'string_index_of(session_id and "/") >= 0 or else '
                    r'string_index_of(session_id and "\\\\") >= 0:',
                    active_branch,
                )
                if path_guard_changes:
                    text = text.replace(active_branch, fixed_branch, 1)
                    rules.append(f"pathlike_session_id_guard:{path_guard_changes}")

        # memory_store follows the repository-wide C-style status contract: zero is
        # success. Provider-authored branches repeatedly invert only the immediate
        # error guard (`if ok == 0: return Error`) even after correctly diagnosing
        # the interface. Canonicalize that exact contradictory shape inside the one
        # transaction-authorized surface; successful zero-status handling in every
        # unrelated branch remains byte-exact above.
        if required_surface:
            active_branch = self_extension_dispatch_branch(text, required_surface)
            if active_branch:
                escaped_surface = re.escape(required_surface)
                fixed_branch, status_changes = re.subn(
                    rf'(?m)^(\s*)set\s+([A-Za-z_][A-Za-z0-9_]*)\s+to\s+'
                    rf'memory_store\(memory_mgr and 2 and "{escaped_surface}" and '
                    rf'([A-Za-z_][A-Za-z0-9_]*)\)\s*\n'
                    rf'\1if\s+\2\s*==\s*0\s*:\s*\n'
                    rf'(\s*)return\s+"Error:',
                    rf'\1set \2 to memory_store(memory_mgr and 2 and "{required_surface}" and \3)\n'
                    rf'\1if \2 != 0:\n\4return "Error:',
                    active_branch,
                )
                if status_changes:
                    text = text.replace(active_branch, fixed_branch, 1)
                    rules.append(f"memory_store_zero_success_guard:{status_changes}")

        # The bridge is a proven imported module, not a value injected into ctx.
        # Gemma has repeatedly invented this exact dead guard even though the next
        # call uses the imported functions directly. Remove only that exact pattern.
        text, bridge_context_changes = re.subn(
            r'(?m)^        set bridge_rpc to map_get_val\(ctx and "bridge_rpc"\)\n'
            r'        if bridge_rpc == 0:\n'
            r'            return "Error: bridge_rpc not available in context\."\n',
            "",
            text,
        )
        if bridge_context_changes:
            rules.append(f"invented_bridge_context_removed:{bridge_context_changes}")

    if text != original:
        candidate.write_text(text, encoding="utf-8")
    return rules


def self_extension_dispatch_branch(text: str, action_name: str) -> str:
    """Return one exact registered dispatch branch from self_extensions_execute."""
    execute_at = text.find("define self_extensions_execute")
    if execute_at < 0:
        return ""
    section = text[execute_at:]
    marker = f'    if action_name equals "{action_name}":'
    start = section.find(marker)
    if start < 0:
        return ""
    tail = section[start:]
    boundaries = [
        pos for pos in (
            tail.find("\n    if action_name equals ", len(marker)),
            tail.find("\n    return \"Error: self-extension dispatch", len(marker)),
        )
        if pos >= 0
    ]
    end = min(boundaries) if boundaries else len(tail)
    return tail[:end].rstrip()


def validate_additive_extension_preservation(
    record: dict, target: Path, candidate: Path
) -> None:
    """Fail closed unless an additive extension retains every prior surface."""
    relative = str(target.resolve().relative_to(ROOT.resolve()))
    if relative != "decent_agent/self_extensions.ep":
        return
    baseline = target.read_text(encoding="utf-8", errors="replace")
    proposed = candidate.read_text(encoding="utf-8", errors="replace")
    required_surface = str(record.get("required_surface", "")).strip()
    if not required_surface:
        planned_surfaces = record.get("planned_surfaces", [])
        if isinstance(planned_surfaces, list) and planned_surfaces:
            required_surface = str(planned_surfaces[0]).strip()

    execute_at = baseline.find("define self_extensions_execute")
    existing_actions = re.findall(
        r'(?m)^    if action_name equals "([A-Za-z_][A-Za-z0-9_]*)":',
        baseline[execute_at:] if execute_at >= 0 else "",
    )
    protected_actions = [name for name in existing_actions if name != required_surface]
    changed_actions = [
        name
        for name in protected_actions
        if not self_extension_dispatch_branch(proposed, name)
        or self_extension_dispatch_branch(baseline, name)
        != self_extension_dispatch_branch(proposed, name)
    ]
    protected_registry_functions = {
        "self_extensions_schema",
        "self_extensions_action_known",
        "self_extensions_execute",
    }
    changed_helpers = [
        name
        for name in sorted(top_level_define_names(baseline) - protected_registry_functions)
        if not top_level_function_block(proposed, name)[2]
        or top_level_function_block(baseline, name)[2]
        != top_level_function_block(proposed, name)[2]
    ]
    changed_schema = []
    for name in protected_actions:
        baseline_lines = [
            line.strip()
            for line in baseline.splitlines()
            if "set schemas to" in line and name in line
        ]
        if any(line not in proposed for line in baseline_lines):
            changed_schema.append(name)
    proposed_known = top_level_function_block(
        proposed, "self_extensions_action_known"
    )[2]
    missing_registry = [
        name
        for name in protected_actions
        if f'if action_name equals "{name}":' not in proposed_known
    ]
    required_missing = []
    if required_surface:
        if not self_extension_dispatch_branch(proposed, required_surface):
            required_missing.append("dispatch")
        if f'if action_name equals "{required_surface}":' not in proposed_known:
            required_missing.append("registry")
        if not any(
            "set schemas to" in line and required_surface in line
            for line in proposed.splitlines()
        ):
            required_missing.append("schema")
    if changed_actions or changed_helpers or changed_schema or missing_registry or required_missing:
        raise GateError(
            "CANDIDATE_BASELINE_INCOMPLETE "
            f"target={relative} "
            f"changed_existing_actions={','.join(changed_actions) or 'none'} "
            f"changed_existing_helpers={','.join(changed_helpers) or 'none'} "
            f"changed_existing_schema={','.join(changed_schema) or 'none'} "
            f"missing_registry={','.join(missing_registry) or 'none'} "
            f"required_surface_missing={','.join(required_missing) or 'none'} "
            "message=Every prior registered capability must remain byte-exact and the "
            "one plan-authorized surface must have schema, registry, and dispatch entries.",
            code="CANDIDATE_REPAIR_REQUIRED",
        )


def validate_candidate_objective_contract(record: dict, target: Path, candidate: Path) -> None:
    """Reject a compile-valid candidate that contradicts its immutable live contract."""
    objective = str(record.get("objective", ""))
    if not objective:
        workflow = workflow_record()
        if (
            workflow.get("transaction_id") != record.get("id")
            or workflow.get("plan_body_hash") != record.get("plan_hash")
        ):
            raise GateError(
                "active candidate is not bound to the current durable workflow objective",
                code="CANDIDATE_REPAIR_REQUIRED",
            )
        objective = str(workflow.get("objective", ""))
        if not objective:
            raise GateError(
                "current durable workflow has no immutable objective",
                code="CANDIDATE_REPAIR_REQUIRED",
            )
    discord_contract = objective_requires_discord_retrieval(objective)
    session_lookup_contract = objective_requires_session_lookup(objective)
    session_label_contract = objective_requires_session_label(objective)
    session_metadata_contract = objective_requires_session_metadata_lookup(objective)
    session_contract = objective_requires_session_transcript(objective) and not session_metadata_contract
    session_validation_contract = objective_requires_session_validation(objective) and not session_metadata_contract
    relative = str(target.resolve().relative_to(ROOT.resolve()))
    if relative != "decent_agent/self_extensions.ep":
        return
    baseline = target.read_text(encoding="utf-8", errors="replace")
    proposed = candidate.read_text(encoding="utf-8", errors="replace")
    required_surface = str(record.get("required_surface", "")).strip()
    if not required_surface:
        planned_surfaces = record.get("planned_surfaces", [])
        if isinstance(planned_surfaces, list) and planned_surfaces:
            required_surface = str(planned_surfaces[0]).strip()
    existing_actions = re.findall(
        r'(?m)^    if action_name equals "([A-Za-z_][A-Za-z0-9_]*)":',
        baseline[baseline.find("define self_extensions_execute"):],
    )
    protected_existing_actions = [name for name in existing_actions if name != required_surface]
    changed_existing = [
        name for name in protected_existing_actions
        if self_extension_dispatch_branch(baseline, name)
        != self_extension_dispatch_branch(proposed, name)
    ]
    protected_registry_functions = {
        "self_extensions_schema", "self_extensions_action_known", "self_extensions_execute",
    }
    changed_existing_helpers = [
        name for name in sorted(top_level_define_names(baseline) - protected_registry_functions)
        if top_level_function_block(baseline, name)[2]
        != top_level_function_block(proposed, name)[2]
    ]
    changed_existing_schema = []
    for name in protected_existing_actions:
        baseline_lines = [
            line.strip() for line in baseline.splitlines()
            if "set schemas to" in line and name in line
        ]
        if any(line not in proposed for line in baseline_lines):
            changed_existing_schema.append(name)
    if (
        (changed_existing or changed_existing_helpers or changed_existing_schema)
        and not discord_contract
        and not session_lookup_contract
        and not session_contract
        and not session_label_contract
        and not session_metadata_contract
        and not session_validation_contract
    ):
        raise GateError(
            "additive extension candidate changed unrelated production behavior: "
            f"changed_existing_actions={','.join(changed_existing) or 'none'} "
            f"changed_existing_helpers={','.join(changed_existing_helpers) or 'none'} "
            f"changed_existing_schema={','.join(changed_existing_schema) or 'none'}. "
            "Preserve every pre-existing action, helper, and schema entry byte-exactly.",
            code="CANDIDATE_REPAIR_REQUIRED",
        )
    if not discord_contract and not session_lookup_contract and not session_contract and not session_label_contract and not session_metadata_contract and not session_validation_contract:
        return
    surfaces = objective_callable_surfaces(objective)
    if not surfaces:
        raise GateError(
            "self-extension objective lost its exact registered surface",
            code="CANDIDATE_REPAIR_REQUIRED",
        )
    surface = surfaces[0]
    if discord_contract:
        required_fragments = (
            f'- {surface}([channel_id]) -> Str',
            f'if action_name equals "{surface}":',
            "if length_list(args_list) != 1:",
            "set channel_id to get_list(args_list and 0)",
            'bridge_enqueue(ddb and "discord" and "read_channel" and channel_id)',
        )
        forbidden_candidates = (
            f'- {surface}([]) -> Str',
            "bridge_rpc_get_config(",
            "map_get_val(ddb and",
            'map_get_val(ctx and "bridge_rpc")',
            "configured_discord_channel(",
        )
    elif session_lookup_contract:
        required_fragments = (
            f'- {surface}([title_query]) -> Str',
            f'if action_name equals "{surface}":',
            "if length_list(args_list) != 1:",
            "set title_query to get_list(args_list and 0)",
            'set sessions_mgr to map_get_val(ctx and "sessions")',
            "set resolved_id to session_manager_resolve_id(sessions_mgr and title_query)",
            f'memory_store(memory_mgr and 2 and "{surface}" and',
            f'"{surface}:ok,session_id:"',
            '",query:"',
        )
        forbidden_candidates = (
            f'- {surface}([]) -> Str',
            'map_get_val(ctx and "sessions_dir")',
            "session_load(",
            "active_session_id(",
        )
    elif session_label_contract:
        required_fragments = (
            f'- {surface}([session_id, label]) -> Str',
            f'if action_name equals "{surface}":',
            "if length_list(args_list) != 2:",
            "set session_id to get_list(args_list and 0)",
            "set label to get_list(args_list and 1)",
            f'memory_store(memory_mgr and 2 and "{surface}" and',
            f'"{surface}:ok,session_id:"',
            '",label:"',
        )
        forbidden_candidates = (
            f'- {surface}([]) -> Str',
            f'- {surface}([session_id]) -> Str',
            'map_get_val(ctx and "sessions_dir")',
            "session_load(",
            "active_session_id(",
            "codex-e2e-checkpoint-label",
        )
    elif session_metadata_contract:
        required_fragments = (
            f'- {surface}([session_id]) -> Str',
            f'if action_name equals "{surface}":',
            "if length_list(args_list) != 1:",
            "set session_id to get_list(args_list and 0)",
            'set sessions_mgr to map_get_val(ctx and "sessions")',
            'set sessions_map to map_get_val(sessions_mgr and "sessions")',
            "map_contains(sessions_map and session_id)",
            f'memory_store(memory_mgr and 2 and "{surface}" and',
            f'"{surface}:ok,session_id:"',
            f'"{surface}:not_found,session_id:"',
        )
        forbidden_candidates = (
            f'- {surface}([]) -> Str',
            'map_get_val(ctx and "sessions_dir")',
            "session_load(",
            "active_session_id(",
            '",exists:true"',
            '",exists:false"',
        )
    elif session_validation_contract:
        required_fragments = (
            f'- {surface}([session_id]) -> Str',
            f'if action_name equals "{surface}":',
            "if length_list(args_list) != 1:",
            "set session_id to get_list(args_list and 0)",
            'set sessions_mgr to map_get_val(ctx and "sessions")',
            'set sessions_map to map_get_val(sessions_mgr and "sessions")',
            "map_contains(sessions_map and session_id)",
            f'memory_store(memory_mgr and 2 and "{surface}" and',
            f'"{surface}:ok,session_id:"',
        )
        forbidden_candidates = (
            f'- {surface}([]) -> Str',
            'map_get_val(ctx and "sessions_dir")',
            "session_load(",
            "active_session_id(",
        )
    else:
        required_fragments = (
            f'- {surface}([session_id]) -> Str',
            f'if action_name equals "{surface}":',
            "if length_list(args_list) != 1:",
            "set session_id to get_list(args_list and 0)",
            f'memory_store(memory_mgr and 2 and "{surface}" and',
            f'"{surface}:ok,session_id:"',
        )
        forbidden_candidates = (
            f'- {surface}([]) -> Str',
            'map_get_val(ctx and "sessions_dir")',
            "session_load(",
            'map_get_val(msg_map and "text")',
            "decision_count + task_count",
            "task_count + decision_count",
            "active_session_id(",
        )
    missing = [fragment for fragment in required_fragments if fragment not in proposed]
    if session_lookup_contract:
        surface_branch = self_extension_dispatch_branch(proposed, surface)
        empty_query_rejected = bool(
            re.search(r'string_length\(title_query\)\s*==\s*0', surface_branch)
            or re.search(r'title_query\s*(?:==|equals)\s*""', surface_branch)
        )
        empty_result_rejected = bool(
            re.search(r'string_length\(resolved_id\)\s*==\s*0', surface_branch)
            or re.search(r'resolved_id\s*(?:==|equals)\s*""', surface_branch)
        )
        persistence_match = re.search(
            rf'(?m)^\s*set\s+([A-Za-z_][A-Za-z0-9_]*)\s+to\s+'
            rf'memory_store\(memory_mgr and 2 and "{re.escape(surface)}" and '
            rf'([A-Za-z_][A-Za-z0-9_]*)\)\s*$',
            surface_branch,
        )
        persistence_status_var = persistence_match.group(1) if persistence_match else ""
        persistence_value_var = persistence_match.group(2) if persistence_match else ""
        persistence_assignments = "\n".join(re.findall(
            rf'(?m)^\s*set\s+{re.escape(persistence_value_var)}\s+to\s+(.+)$'
            if persistence_value_var else r'(?!x)x',
            surface_branch,
        ))
        persistence_success_guard = bool(persistence_status_var) and bool(re.search(
            rf'(?m)^\s*if\s+{re.escape(persistence_status_var)}\s*!=\s*0\s*:\s*$',
            surface_branch,
        ))
        lookup_requirements = (
            ("empty title_query rejection", empty_query_rejected),
            ("unknown or ambiguous title rejection", empty_result_rejected),
            ("exact title query in persisted value", "title_query" in persistence_assignments),
            ("exact resolved ID in persisted value", "resolved_id" in persistence_assignments),
            ("memory_store success/failure contract", persistence_success_guard),
        )
        missing.extend(label for label, present in lookup_requirements if not present)
    if session_contract or session_label_contract or session_metadata_contract or session_validation_contract:
        surface_branch = self_extension_dispatch_branch(proposed, surface)
        manager_match = re.search(
            r'(?m)^\s*set\s+([A-Za-z_][A-Za-z0-9_]*)\s+to\s+map_get_val\(ctx and "sessions"\)\s*$',
            surface_branch,
        )
        sessions_var = manager_match.group(1) if manager_match else ""
        map_match = re.search(
            rf'(?m)^\s*set\s+([A-Za-z_][A-Za-z0-9_]*)\s+to\s+map_get_val\({re.escape(sessions_var)} and "sessions"\)\s*$'
            if sessions_var else r'(?!x)x',
            surface_branch,
        )
        sessions_map_var = map_match.group(1) if map_match else ""
        session_match = re.search(
            rf'(?m)^\s*set\s+([A-Za-z_][A-Za-z0-9_]*)\s+to\s+map_get_val\({re.escape(sessions_map_var)} and session_id\)\s*$'
            if sessions_map_var else r'(?!x)x',
            surface_branch,
        )
        session_var = session_match.group(1) if session_match else ""
        messages_match = re.search(
            rf'(?m)^\s*set\s+([A-Za-z_][A-Za-z0-9_]*)\s+to\s+map_get_val\({re.escape(session_var)} and "messages"\)\s*$'
            if session_var else r'(?!x)x',
            surface_branch,
        )
        messages_var = messages_match.group(1) if messages_match else ""
        count_match = re.search(
            rf'(?m)^\s*set\s+([A-Za-z_][A-Za-z0-9_]*)\s+to\s+length_list\({re.escape(messages_var)}\)\s*$'
            if messages_var else r'(?!x)x',
            surface_branch,
        )
        persistence_match = re.search(
            rf'(?m)^\s*set\s+([A-Za-z_][A-Za-z0-9_]*)\s+to\s+'
            rf'memory_store\(memory_mgr and 2 and "{re.escape(surface)}" and '
            rf'([A-Za-z_][A-Za-z0-9_]*)\)\s*$',
            surface_branch,
        )
        persistence_status_var = persistence_match.group(1) if persistence_match else ""
        persistence_success_guard = bool(persistence_status_var) and bool(
            re.search(
                rf'(?m)^\s*if\s+{re.escape(persistence_status_var)}\s*!=\s*0\s*:\s*$',
                surface_branch,
            )
        )
        empty_id_rejected = bool(
            re.search(r'string_length\(session_id\)\s*==\s*0', surface_branch)
            or re.search(r'session_id\s*(?:==|equals)\s*""', surface_branch)
        )
        slash_rejected = bool(re.search(
            r'(?:string_index_of|string_contains)\(session_id and "/"\)', surface_branch
        ))
        backslash_rejected = bool(re.search(
            r'(?:string_index_of|string_contains)\(session_id and "\\\\"\)', surface_branch
        ))
        pathlike_id_rejected = slash_rejected and backslash_rejected
        common_session_requirements = (
            ("empty session_id rejection", empty_id_rejected),
            ("path-like session_id rejection", pathlike_id_rejected),
            ("ctx.sessions manager assignment", bool(manager_match)),
            ("sessions map assignment from that manager", bool(map_match)),
            (
                "session_id membership check on that sessions map",
                bool(sessions_map_var)
                and f"map_contains({sessions_map_var} and session_id)" in surface_branch,
            ),
            ("memory_store success/failure contract", persistence_success_guard),
        )
        if session_label_contract:
            empty_label_rejected = bool(
                re.search(r'string_length\(label\)\s*==\s*0', surface_branch)
                or re.search(r'label\s*(?:==|equals)\s*""', surface_branch)
            )
            persisted_value_assignments = ""
            if persistence_match:
                persisted_value_var = persistence_match.group(2)
                persisted_value_assignments = "\n".join(re.findall(
                    rf'(?m)^\s*set\s+{re.escape(persisted_value_var)}\s+to\s+(.+)$',
                    surface_branch,
                ))
            session_dataflow_requirements = common_session_requirements + (
                ("explicit label assignment", "set label to get_list(args_list and 1)" in surface_branch),
                ("empty label rejection", empty_label_rejected),
                ("exact session_id in persisted value", "session_id" in persisted_value_assignments),
                ("exact label in persisted value", "label" in persisted_value_assignments),
            )
        elif session_metadata_contract:
            metadata_value_assignments = ""
            if persistence_match:
                metadata_value_var = persistence_match.group(2)
                metadata_value_assignments = "\n".join(re.findall(
                    rf'(?m)^\s*set\s+{re.escape(metadata_value_var)}\s+to\s+(.+)$',
                    surface_branch,
                ))
            session_dataflow_requirements = common_session_requirements + (
                ("session assignment from that sessions map", bool(session_match)),
                ("messages assignment from that session", bool(messages_match)),
                ("complete message-list count", bool(count_match)),
                (
                    "real title field",
                    bool(session_var) and f'map_get_val({session_var} and "title")' in surface_branch,
                ),
                (
                    "real model field",
                    bool(session_var) and f'map_get_val({session_var} and "model")' in surface_branch,
                ),
                ("exact session_id in persisted metadata", "session_id" in metadata_value_assignments),
                ("exact title in persisted metadata", "title" in metadata_value_assignments),
                ("exact model in persisted metadata", "model" in metadata_value_assignments),
                ("exact records count in persisted metadata", "record" in metadata_value_assignments),
            )
        elif session_validation_contract:
            persisted_value_assignments = ""
            if persistence_match:
                persisted_value_var = persistence_match.group(2)
                persisted_value_assignments = "\n".join(re.findall(
                    rf'(?m)^\s*set\s+{re.escape(persisted_value_var)}\s+to\s+(.+)$',
                    surface_branch,
                ))
            session_dataflow_requirements = common_session_requirements + (
                ("exact session_id in persisted value", "session_id" in persisted_value_assignments),
                ("boolean existence in persisted value", "exists" in persisted_value_assignments),
            )
        else:
            session_dataflow_requirements = common_session_requirements + (
                ("session assignment from that sessions map", bool(session_match)),
                ("messages assignment from that session", bool(messages_match)),
                ("complete message-list count", bool(count_match)),
                (
                    "real message content field",
                    bool(re.search(
                        r'map_get_val\([A-Za-z_][A-Za-z0-9_]* and "content"\)', surface_branch
                    )),
                ),
            )
        missing.extend(label for label, present in session_dataflow_requirements if not present)
    forbidden = [
        fragment for fragment in (
            forbidden_candidates
        )
        if fragment in proposed
    ]
    existing_actions = re.findall(
        r'(?m)^    if action_name equals "([A-Za-z_][A-Za-z0-9_]*)":',
        baseline[baseline.find("define self_extensions_execute"):],
    )
    required_surface = str(record.get("required_surface", "")).strip()
    if not required_surface:
        planned_surfaces = record.get("planned_surfaces", [])
        if isinstance(planned_surfaces, list) and planned_surfaces:
            required_surface = str(planned_surfaces[0]).strip()
    protected_existing_actions = [
        name for name in existing_actions if name != required_surface
    ]
    protected_registry_functions = {
        "self_extensions_schema",
        "self_extensions_action_known",
        "self_extensions_execute",
    }
    changed_existing_helpers = [
        name for name in sorted(top_level_define_names(baseline) - protected_registry_functions)
        if top_level_function_block(baseline, name)[2]
        != top_level_function_block(proposed, name)[2]
    ]
    changed_existing = [
        name for name in protected_existing_actions
        if self_extension_dispatch_branch(baseline, name)
        != self_extension_dispatch_branch(proposed, name)
    ]
    changed_existing_schema = []
    for name in protected_existing_actions:
        baseline_lines = [
            line.strip()
            for line in baseline.splitlines()
            if "set schemas to" in line and name in line
        ]
        if any(line not in proposed for line in baseline_lines):
            changed_existing_schema.append(name)
    if missing or forbidden or changed_existing or changed_existing_schema or changed_existing_helpers:
        contract_name = (
            "Discord" if discord_contract else
            ("session-title-lookup" if session_lookup_contract else
             ("session-label" if session_label_contract else
              ("session-metadata" if session_metadata_contract else
               ("session-validation" if session_validation_contract else "session-transcript"))))
        )
        if discord_contract:
            repair = (
                "Accept exactly one evaluator-supplied channel_id via args_list, use the "
                "proven bridge call, and preserve every pre-existing registered action byte-exactly."
            )
        elif session_lookup_contract:
            repair = (
                "Accept the exact evaluator-supplied title query, resolve it only through "
                "session_manager_resolve_id(ctx.sessions), reject unknown or ambiguous results, "
                "persist both query and resolved ID, and preserve every existing action byte-exactly."
            )
        elif session_label_contract:
            repair = (
                "Accept the exact evaluator-supplied session_id and label as two arguments, verify "
                "the session through ctx.sessions, persist both exact values with four-argument "
                "memory_store, and preserve every pre-existing registered action byte-exactly."
            )
        elif session_metadata_contract:
            repair = (
                "Accept the exact evaluator-supplied session_id, load only its real ctx.sessions entry, "
                "return and persist its exact title, model, and message count, return the exact not_found "
                "code for a missing ID, and preserve every pre-existing registered action byte-exactly."
            )
        elif session_validation_contract:
            repair = (
                "Accept the exact evaluator-supplied session_id, determine existence only through "
                "ctx.sessions, return and persist the exact ID with exists:true or exists:false, and "
                "preserve every pre-existing registered action byte-exactly."
            )
        else:
            repair = (
                "Resolve the exact evaluator-supplied session_id through ctx.sessions, read each "
                "message content field, count the complete messages list, use memory_store with four "
                "arguments, and preserve every pre-existing registered action byte-exactly."
            )
        raise GateError(
            f"{contract_name} extension candidate contradicts the frozen production contract: "
            f"missing={','.join(missing) or 'none'} "
            f"forbidden={','.join(forbidden) or 'none'} "
            f"changed_existing_actions={','.join(changed_existing) or 'none'}. "
            f"changed_existing_helpers={','.join(changed_existing_helpers) or 'none'}. "
            f"changed_existing_schema={','.join(changed_existing_schema) or 'none'}. "
            + repair,
            code="CANDIDATE_REPAIR_REQUIRED",
        )


def top_level_define_names(text: str) -> set[str]:
    """Return production definitions whose removal would break an additive edit."""
    return set(
        re.findall(
            r"(?m)^(?:async\s+)?define\s+([A-Za-z_][A-Za-z0-9_]*)\b",
            text,
        )
    )


def missing_additive_baseline_definitions(target: Path, candidate: Path) -> list[str]:
    baseline = top_level_define_names(target.read_text(encoding="utf-8", errors="replace"))
    proposed = top_level_define_names(candidate.read_text(encoding="utf-8", errors="replace"))
    return sorted(baseline - proposed)


def cleanup_implementation_candidates(record: dict) -> None:
    candidates = record.get("implementation_candidates", {})
    if not isinstance(candidates, dict):
        return
    planned = record.get("planned_files", [])
    if not isinstance(planned, list):
        return
    for relative in planned:
        if not isinstance(relative, str):
            continue
        try:
            target = safe_planned_implementation_path(
                base64.b64encode(relative.encode("utf-8")).decode("ascii")
            )
            candidate = implementation_candidate_path(record, target)
        except GateError:
            continue
        if candidate.is_file() and not candidate.is_symlink():
            candidate.unlink()


def preflight_write(path_b64: str) -> None:
    record = load_record(ACTIVE)
    if record.get("state") not in {"frozen", "implementing", "repair_required"}:
        raise GateError("implementation writes may be preflighted only in the frozen, implementing, or failed-live repair state")
    verify_frozen_bytes(record)
    path = safe_planned_implementation_path(path_b64)
    relative = str(path.relative_to(ROOT))
    planned = record.get("planned_files")
    if not isinstance(planned, list) or relative not in planned:
        planned_text = ", ".join(planned) if isinstance(planned, list) else "<malformed>"
        raise GateError(
            f"implementation path was not declared in the validated plan: {relative}; "
            f"planned={planned_text}. Implement only a declared file. If the design needs another file, "
            "abandon before the first successful write, investigate it, and create a new plan.",
            code="PLAN_SCOPE_MISSING",
        )
    print(f"IMPLEMENTATION_PREFLIGHT_OK path={relative}")


def check_candidate(path_b64: str) -> None:
    record = load_record(ACTIVE)
    if record.get("state") not in {"frozen", "implementing", "repair_required"}:
        raise GateError("implementation candidates may be checked only in an active frozen repair transaction")
    verify_frozen_bytes(record)
    preflight_write(path_b64)
    target = safe_planned_implementation_path(path_b64)
    relative = str(target.relative_to(ROOT))
    candidate = implementation_candidate_path(record, target)
    if not candidate.is_file() or candidate.is_symlink():
        raise GateError(f"retained implementation candidate is missing or unsafe: {candidate.relative_to(ROOT)}")

    normalization_rules = normalize_candidate_dialect(record, candidate, target)

    candidates = record.get("implementation_candidates", {})
    if not isinstance(candidates, dict):
        raise GateError("implementation candidate manifest is malformed")
    receipt = {
        "target": relative,
        "sha256": file_digest(candidate),
        "status": "checking",
        "checked_at": int(time.time()),
    }
    if normalization_rules:
        receipt["dialect_normalizations"] = normalization_rules
    candidates[relative] = receipt
    record["implementation_candidates"] = candidates
    atomic_json(ACTIVE, record)

    try:
        missing_definitions = missing_additive_baseline_definitions(target, candidate)
        if missing_definitions:
            preview = ",".join(missing_definitions[:24])
            raise GateError(
                "CANDIDATE_BASELINE_INCOMPLETE "
                f"target={relative} missing_definitions={preview} "+
                "message=An additive whole-file candidate removed existing production definitions. "
                "The live source is unchanged; reset this candidate, reread the exact production "
                "path, and preserve every existing definition in the next complete candidate.",
                code="CANDIDATE_REPAIR_REQUIRED",
            )
        validate_additive_extension_preservation(record, target, candidate)
        # The immutable regression and live E2E artifacts are the behavioral
        # authority. Do not independently reinterpret their objective by matching
        # source-code fragments here: overlapping prose classifiers can impose a
        # second, contradictory contract. Candidate admission proves only bounded
        # scope/baseline preservation and real compiler acceptance; behavior is
        # proved by the frozen evaluators during verification and replacement.
        check_implementation_path(candidate)
    except GateError as exc:
        diagnostic = str(exc)
        diagnostic = diagnostic.replace(str(candidate.relative_to(ROOT)), relative)
        diagnostic = diagnostic.replace(str(candidate), relative)
        diagnostic = diagnostic.replace(str(candidate.resolve()), str(target.resolve()))
        receipt["status"] = "rejected"
        receipt["diagnostic"] = diagnostic[-3000:]
        receipt["rejected_at"] = int(time.time())
        candidates[relative] = receipt
        record["implementation_candidates"] = candidates
        atomic_json(ACTIVE, record)
        raise GateError(
            f"{diagnostic}\nCANDIDATE_REPAIR_REQUIRED target={relative} "
            f"candidate_hash={receipt['sha256']} next=read_production_path_then_replace_production_path",
            code="CANDIDATE_REPAIR_REQUIRED",
        ) from exc

    receipt["status"] = "compiled"
    receipt["compiled_at"] = int(time.time())
    receipt.pop("diagnostic", None)
    candidates[relative] = receipt
    record["implementation_candidates"] = candidates
    atomic_json(ACTIVE, record)
    if normalization_rules:
        print("CANDIDATE_DIALECT_NORMALIZED rules=" + ",".join(normalization_rules))
    print(
        f"IMPLEMENTATION_CANDIDATE_OK target={relative} "
        f"candidate_hash={receipt['sha256']} live_source_unchanged=yes"
    )


def reset_incomplete_candidate() -> None:
    """Archive a rejected candidate and reopen the same frozen contract from source.

    A retained candidate is deliberately mutable only through exact replacement.  If
    that repair itself stalls (for example, the provider repeats a byte-identical
    replacement), keeping the candidate as the only legal address creates a permanent
    controller loop.  Resetting here is not a production rollback: rejected bytes were
    never live.  The attempt and its compiler diagnostic remain durable provenance and
    the immutable plan/evaluators remain in force for the next complete candidate.
    """
    record = load_record(ACTIVE)
    if record.get("state") not in {"frozen", "repair_required"}:
        raise GateError(
            "candidate reset is legal only before the first accepted implementation write "
            "or while repairing a rejected live deployment"
        )
    verify_frozen_bytes(record)
    candidates = record.get("implementation_candidates", {})
    if not isinstance(candidates, dict):
        raise GateError("implementation candidate manifest is malformed")
    rejected = [
        (relative, receipt)
        for relative, receipt in candidates.items()
        if isinstance(relative, str)
        and isinstance(receipt, dict)
        and receipt.get("status") == "rejected"
    ]
    if len(rejected) != 1:
        raise GateError(
            f"candidate reset requires exactly one rejected candidate; found={len(rejected)}",
            code="CANDIDATE_REPAIR_REQUIRED",
        )
    relative, receipt = rejected[0]
    target = safe_planned_implementation_path(
        base64.b64encode(relative.encode("utf-8")).decode("ascii")
    )
    candidate = implementation_candidate_path(record, target)
    if not candidate.is_file() or candidate.is_symlink():
        raise GateError("rejected candidate is unavailable for structural reset", code="CANDIDATE_REPAIR_REQUIRED")
    missing = missing_additive_baseline_definitions(target, candidate)
    transaction_id = str(record.get("id", ""))
    archive_dir = ROOT / "config" / "improvements" / "candidate-attempts" / transaction_id
    archive_dir.mkdir(parents=True, exist_ok=True)
    candidate_hash = file_digest(candidate)
    archive = archive_dir / f"{Path(relative).name}.{candidate_hash[:16]}.rejected"
    if archive.exists():
        if archive.read_bytes() != candidate.read_bytes():
            raise GateError("candidate provenance archive hash collision")
    else:
        archive.write_bytes(candidate.read_bytes())
    attempts = record.get("implementation_candidate_attempts", [])
    if not isinstance(attempts, list):
        raise GateError("candidate attempt provenance is malformed")
    reason = "CANDIDATE_BASELINE_INCOMPLETE" if missing else "CANDIDATE_REPAIR_STALLED"
    attempt = {
        "target": relative,
        "sha256": candidate_hash,
        "archived_path": str(archive.relative_to(ROOT)),
        "reason": reason,
        "diagnostic": str(receipt.get("diagnostic", "")),
        "reset_at": int(time.time()),
    }
    if missing:
        attempt["missing_definitions"] = missing
    attempts.append(attempt)
    record["implementation_candidate_attempts"] = attempts
    candidates.pop(relative, None)
    record["implementation_candidates"] = candidates
    candidate.unlink()
    atomic_json(ACTIVE, record)
    print(
        f"IMPLEMENTATION_CANDIDATE_RESET_OK target={relative} archived_hash={candidate_hash} "
        f"reason={reason} missing_definitions={len(missing)} next=read_exact_production_path"
    )


def normalize_active_candidate() -> None:
    """Controller transition for a rejected candidate with known source dialects."""
    record = load_record(ACTIVE)
    candidates = record.get("implementation_candidates", {})
    if not isinstance(candidates, dict):
        raise GateError("active implementation candidate manifest is malformed")
    rejected = [
        relative for relative, receipt in candidates.items()
        if isinstance(relative, str)
        and isinstance(receipt, dict)
        and receipt.get("status") == "rejected"
    ]
    if len(rejected) != 1:
        raise GateError(
            f"candidate normalization requires exactly one rejected candidate; found={len(rejected)}",
            code="CANDIDATE_REPAIR_REQUIRED",
        )
    encoded = base64.b64encode(rejected[0].encode("utf-8")).decode("ascii")
    check_candidate(encoded)


def check_implementation_path(path: Path) -> str:
    relative = str(path.relative_to(ROOT))
    command: list[str] | None = None
    if path.suffix == ".ep":
        compiler = shutil.which("ernos")
        if not compiler:
            raise GateError("ernos compiler is unavailable for changed .ep verification")
        command = [compiler, "check", relative]
    elif path.suffix == ".py":
        command = [sys.executable, "-m", "py_compile", relative]
    elif path.suffix == ".js":
        node = shutil.which("node")
        if not node:
            raise GateError("node is unavailable for changed .js verification")
        command = [node, "--check", relative]
    elif path.suffix == ".sh":
        command = ["/bin/bash", "-n", relative]
    if command is not None:
        result = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=300,
            check=False,
        )
        if result.returncode != 0:
            raise GateError(
                f"changed implementation failed syntax/compile verification: {relative}\n{result.stdout[-3000:]}"
            )
    return relative


def record_write(path_b64: str) -> None:
    record = load_record(ACTIVE)
    if record.get("state") not in {"frozen", "implementing", "repair_required"}:
        raise GateError("implementation writes may be recorded only in the frozen, implementing, or failed-live repair state")
    verify_frozen_bytes(record)
    preflight_write(path_b64)
    relative = check_implementation_path(safe_implementation_path(path_b64))
    planned = record.get("planned_files")
    if not isinstance(planned, list) or relative not in planned:
        raise GateError(
            f"implementation path was not declared in the validated plan: {relative}; "
            "plan amendments are legal only before evaluator freeze"
        )
    retained = candidate_record(record, relative)
    if retained is not None:
        if retained.get("status") != "compiled":
            raise GateError(f"retained implementation candidate has not compiled successfully: {relative}")
        candidate = implementation_candidate_path(record, ROOT / relative)
        retained_hash = retained.get("sha256")
        if not isinstance(retained_hash, str) or not HASH.fullmatch(retained_hash):
            raise GateError(f"retained implementation candidate hash is malformed: {relative}")
        if not candidate.is_file() or candidate.is_symlink() or file_digest(candidate) != retained_hash:
            raise GateError(f"retained implementation candidate bytes changed after compilation: {relative}")
        if file_digest(ROOT / relative) != retained_hash:
            raise GateError(f"promoted source does not match the compiled retained candidate: {relative}")
    baseline_hashes = record.get("implementation_baseline_hashes", {})
    if isinstance(baseline_hashes, dict):
        baseline_hash = baseline_hashes.get(relative)
        if isinstance(baseline_hash, str) and baseline_hash != "absent" and file_digest(ROOT / relative) == baseline_hash:
            raise GateError(
                f"implementation write made no production change to {relative}; its bytes equal the frozen pre-change baseline"
            )
    paths = record.get("implementation_paths", [])
    if not isinstance(paths, list) or any(not isinstance(value, str) for value in paths):
        raise GateError("implementation path manifest is malformed")
    if relative not in paths:
        paths.append(relative)
    record["state"] = "implementing"
    record.setdefault("implementing_at", int(time.time()))
    record["implementation_paths"] = sorted(paths)
    record["implementation_manifest_hash"] = digest("\n".join(sorted(paths)).encode())
    if retained is not None:
        retained["status"] = "promoted"
        retained["promoted_at"] = int(time.time())
        record["implementation_candidates"][relative] = retained
    atomic_json(ACTIVE, record)
    if retained is not None:
        candidate = implementation_candidate_path(record, ROOT / relative)
        if candidate.is_file() and not candidate.is_symlink():
            candidate.unlink()
    if WORKFLOW.exists():
        workflow = workflow_record()
        workflow["state"] = "implementing"
        atomic_json(WORKFLOW, workflow)
        refresh_plan_document(workflow, record)
    print(f"IMPLEMENTATION_WRITE_OK path={relative}")


def verify_implementation_paths(record: dict) -> None:
    paths = record.get("implementation_paths")
    if not isinstance(paths, list) or not paths:
        raise GateError("active improvement has no recorded, verified implementation paths")
    checked = [check_implementation_path((ROOT / value).resolve()) for value in paths]
    expected = digest("\n".join(sorted(checked)).encode())
    if record.get("implementation_manifest_hash") != expected:
        raise GateError("implementation path manifest hash mismatch")
    planned = record.get("planned_files")
    if not isinstance(planned, list) or set(checked) != set(planned):
        missing = sorted(set(planned or []) - set(checked))
        extra = sorted(set(checked) - set(planned or []))
        raise GateError(f"implementation does not match validated plan; missing={missing} extra={extra}")


def implementation_content_hash(record: dict) -> str:
    paths = record.get("implementation_paths", [])
    if not isinstance(paths, list) or not paths:
        return digest(b"")
    values: list[str] = []
    for relative in sorted(paths):
        if not isinstance(relative, str):
            raise GateError("implementation path manifest is malformed")
        path = (ROOT / relative).resolve()
        if not path.is_file() or path.is_symlink():
            values.append(f"{relative}\tmissing")
        else:
            values.append(f"{relative}\t{file_digest(path)}")
    return digest("\n".join(values).encode())


def persist_live_failure(error: str) -> dict | None:
    if not ACTIVE.exists():
        return None
    record = load_record(ACTIVE)
    verify_frozen_bytes(record)
    source_hash = implementation_content_hash(record)
    failure_hash = digest(error.encode())
    fingerprint = digest((failure_hash + "\n" + source_hash).encode())
    prior = record.get("live_failures", [])
    if not isinstance(prior, list):
        raise GateError("live failure ledger is malformed")
    repeat = 1
    if prior and isinstance(prior[-1], dict) and prior[-1].get("fingerprint") == fingerprint:
        repeat = int(prior[-1].get("repeat", 1)) + 1
    receipt = {
        "attempt": len(prior) + 1,
        "repeat": repeat,
        "failure_hash": failure_hash,
        "failure_tail": error[-4000:],
        "source_hash": source_hash,
        "fingerprint": fingerprint,
        "failed_at": int(time.time()),
    }
    prior.append(receipt)
    record["live_failures"] = prior
    record["state"] = "repair_required"
    record["live_failure_hash"] = failure_hash
    record["live_failure_tail"] = error[-4000:]
    record["live_failure_source_hash"] = source_hash
    record["live_failure_fingerprint"] = fingerprint
    record["live_failure_attempt"] = receipt["attempt"]
    record["live_failure_repeat"] = repeat
    record["repair_required_at"] = int(time.time())
    atomic_json(ACTIVE, record)
    if WORKFLOW.exists():
        workflow = workflow_record()
        workflow["state"] = "repair_required"
        workflow["last_live_failure"] = receipt
        atomic_json(WORKFLOW, workflow)
        refresh_plan_document(workflow, record)
    return record


def verify() -> None:
    completed = all_completed()
    for record in completed:
        # Completed improvements retain immutable plan/evaluator bytes, but their
        # investigated dependencies are expected to evolve through later authorized
        # upgrades. Their permanent behavioral regressions—not stale dependency
        # hashes—decide whether the new source preserves the completed capability.
        verify_frozen_bytes(record, enforce_dependency_hashes=False)
    active_count = 0
    if ACTIVE.exists():
        active = load_record(ACTIVE)
        state = active.get("state")
        if state == "frozen":
            raise GateError("active improvement is frozen but implementation has not started")
        if state not in ("implementing", "verified", "live_passed", "repair_required"):
            raise GateError(f"unsupported active improvement state: {state}")
        verify_frozen_bytes(active)
        verify_implementation_paths(active)
        if state == "repair_required":
            current_hash = implementation_content_hash(active)
            if current_hash == active.get("live_failure_source_hash"):
                raise GateError(
                    "the rolled-back candidate has not received a causal source change since its last live failure; "
                    "inspect the retained failure receipt, repair the implementation, and retry with different verified bytes"
                )
        active_count = 1
    print(
        f"IMPROVEMENT_VERIFY_OK completed={len(completed)} active={active_count} "
        "runtime=deferred_to_replacement"
    )


def mark_verified() -> None:
    verify()
    record = load_record(ACTIVE)
    if record.get("state") == "verified":
        print(f"VERIFIED_OK id={record['id']}")
        return
    record = transition(("implementing",), "verified")
    print(f"VERIFIED_OK id={record['id']}")


def live() -> None:
    completed = all_completed()
    try:
        for completed_record in completed:
            run_record(completed_record, live=True)
        if not ACTIVE.exists():
            print(f"IMPROVEMENT_LIVE_OK completed={len(completed)} active=0")
            return
        record = load_record(ACTIVE)
        if record.get("state") not in ("verified", "live_passed"):
            raise GateError("active improvement must be verified before live E2E")
        outputs = run_record(record, live=True)
    except GateError as exc:
        failed = persist_live_failure(str(exc))
        if failed is not None:
            raise GateError(
                f"{exc}\nLIVE_REPAIR_REQUIRED id={failed['id']} "
                f"failure_hash={failed['live_failure_hash']} "
                f"source_hash={failed['live_failure_source_hash']} "
                f"attempt={failed['live_failure_attempt']}"
            ) from exc
        raise
    record["state"] = "live_passed"
    record["live_passed_at"] = int(time.time())
    record["live_output_hash"] = digest("\n".join(outputs).encode())
    atomic_json(ACTIVE, record)
    if WORKFLOW.exists():
        workflow = workflow_record()
        workflow["state"] = "live_passed"
        atomic_json(WORKFLOW, workflow)
        refresh_plan_document(workflow, record)
    print(f"IMPROVEMENT_LIVE_OK completed={len(completed)} active=1 id={record['id']}")


def complete() -> None:
    record = load_record(ACTIVE)
    if record.get("state") != "live_passed":
        raise GateError("active improvement has no successful live-E2E receipt")
    verify_frozen_bytes(record)
    record["state"] = "completed"
    record["completed_at"] = int(time.time())
    COMPLETED.mkdir(parents=True, exist_ok=True)
    destination = COMPLETED / f"{record['id']}.json"
    if destination.exists():
        raise GateError("completed transaction id already exists")
    atomic_json(destination, record)
    if WORKFLOW.exists():
        workflow = workflow_record()
        workflow["state"] = "completed"
        workflow["completed_at"] = int(time.time())
        atomic_json(WORKFLOW, workflow)
        refresh_plan_document(workflow, record)
        shutil.copy2(PLAN_DOCUMENT, COMPLETED / f"{record['id']}.plan.md")
    cleanup_implementation_candidates(record)
    ACTIVE.unlink()
    print(f"IMPROVEMENT_COMPLETE_OK id={record['id']} permanent_regression=enabled")


def record_failure(detail: str) -> None:
    if not detail or len(detail) > 4000:
        raise GateError("failure detail must be 1-4000 characters")
    if ACTIVE.exists():
        existing = load_record(ACTIVE)
        if (
            existing.get("state") == "repair_required"
            and isinstance(existing.get("live_failure_hash"), str)
            and HASH.fullmatch(existing["live_failure_hash"])
            and isinstance(existing.get("live_failure_source_hash"), str)
            and HASH.fullmatch(existing["live_failure_source_hash"])
            and isinstance(existing.get("live_failure_fingerprint"), str)
            and HASH.fullmatch(existing["live_failure_fingerprint"])
            and isinstance(existing.get("live_failure_attempt"), int)
            and existing["live_failure_attempt"] > 0
        ):
            print(
                f"IMPROVEMENT_FAILURE_RECORDED id={existing['id']} state=repair_required "
                f"failure_hash={existing['live_failure_hash']} "
                f"source_hash={existing['live_failure_source_hash']} already_complete=yes"
            )
            return
    record = persist_live_failure(detail)
    if record is None:
        print("IMPROVEMENT_FAILURE_RECORDED active=none")
        return
    print(
        f"IMPROVEMENT_FAILURE_RECORDED id={record['id']} state=repair_required "
        f"failure_hash={record['live_failure_hash']} source_hash={record['live_failure_source_hash']}"
    )


def abort() -> None:
    record = load_record(ACTIVE)
    paths = record.get("implementation_paths", [])
    if record.get("state") not in {"frozen", "implementing"} or paths:
        raise GateError("a test may be abandoned only before the first verified implementation write")
    reason_path = STAGING / "abort_reason.txt"
    if not reason_path.is_file() or reason_path.is_symlink():
        raise GateError("abort reason is missing")
    reason = reason_path.read_text(encoding="utf-8").strip()
    if len(reason) < 40 or len(reason) > 4000:
        raise GateError("abort reason must be 40-4000 characters")
    record["state"] = "aborted"
    record["abort_reason"] = reason
    record["aborted_at"] = int(time.time())
    ABORTED.mkdir(parents=True, exist_ok=True)
    atomic_json(ABORTED / f"{record['id']}.json", record)
    cleanup_implementation_candidates(record)
    ACTIVE.unlink()
    reason_path.unlink()
    if WORKFLOW.exists():
        workflow = workflow_record()
        workflow["state"] = "aborted"
        workflow["abort_reason"] = reason
        atomic_json(WORKFLOW, workflow)
        refresh_plan_document(workflow, record)
    print(f"IMPROVEMENT_ABORT_OK id={record['id']} implementation_started=no")


def quarantine_active(reason_b64: str) -> None:
    """Operator-only migration for an immutable contract accepted by an older faulty gate."""
    record = load_record(ACTIVE)
    verify_frozen_bytes(record)
    reason = decode_text(reason_b64, "quarantine reason", 8_000).strip()
    if len(reason) < 80:
        raise GateError("quarantine reason must contain at least 80 characters of concrete evidence")
    record["state"] = "invalidated"
    record["invalidation_reason"] = reason
    record["invalidated_at"] = int(time.time())
    record["invalidated_by"] = "operator_controller_migration"
    ABORTED.mkdir(parents=True, exist_ok=True)
    destination = ABORTED / f"{record['id']}.json"
    if destination.exists():
        raise GateError("an archival receipt already exists for this transaction")
    atomic_json(destination, record)
    if WORKFLOW.exists():
        workflow = workflow_record()
        workflow["state"] = "aborted"
        workflow["abort_reason"] = reason
        workflow["aborted_at"] = int(time.time())
        workflow["invalid_transaction_id"] = record["id"]
        atomic_json(WORKFLOW, workflow)
        refresh_plan_document(workflow, record)
        if PLAN_DOCUMENT.is_file():
            shutil.copy2(PLAN_DOCUMENT, ABORTED / f"{record['id']}.plan.md")
    cleanup_implementation_candidates(record)
    ACTIVE.unlink()
    print(
        f"IMPROVEMENT_QUARANTINE_OK id={record['id']} frozen_evidence=preserved "
        "active=none"
    )


def restart_staging(reason_b64: str) -> None:
    if ACTIVE.exists():
        raise GateError("a frozen improvement is active; use the frozen pre-write abandonment path")
    workflow = workflow_record()
    if workflow.get("state") not in {"investigating", "planned", "tests_authoring", "tests_validated"}:
        raise GateError("only an investigating, planned, or evaluator-authoring workflow can be restarted before freeze")
    reason = decode_text(reason_b64, "workflow restart reason", 4_000).strip()
    if len(reason) < 40:
        raise GateError("workflow restart reason must be at least 40 characters")
    stamp = str(time.time_ns())
    restart_id = digest((json.dumps(workflow, sort_keys=True) + "\n" + reason + "\n" + stamp).encode())
    ABORTED.mkdir(parents=True, exist_ok=True)
    archived_files: list[str] = []
    for source in sorted(STAGING.iterdir()):
        if source.is_file() and not source.is_symlink():
            destination = ABORTED / f"{restart_id}.{source.name}"
            shutil.copy2(source, destination)
            archived_files.append(str(destination.relative_to(ROOT)))
    workflow["state"] = "aborted"
    workflow["abort_reason"] = reason
    workflow["aborted_at"] = int(time.time())
    workflow["abort_id"] = restart_id
    workflow["archived_files"] = archived_files
    atomic_json(ABORTED / f"{restart_id}.json", workflow)
    atomic_json(WORKFLOW, workflow)
    refresh_plan_document(workflow)
    print(
        f"IMPROVEMENT_STAGING_RESTART_OK id={restart_id} archived={len(archived_files)} "
        "implementation_started=no next=improvement_investigation_begin"
    )


def status() -> None:
    if not ACTIVE.exists():
        if WORKFLOW.exists():
            workflow = workflow_record()
            refresh_plan_document(workflow)
            print(
                f"IMPROVEMENT_STATUS active=none staging={workflow.get('state')} "
                f"source_reads={len(discovery_source_paths(workflow))} "
                f"plan_version={workflow.get('plan_version', 0)} completed={len(all_completed())} "
                f"superseded={len(superseded_ids())} plan={PLAN_DOCUMENT.relative_to(ROOT)}"
            )
            return
        print(
            f"IMPROVEMENT_STATUS active=none completed={len(all_completed())}"
            f" superseded={len(superseded_ids())}"
        )
        return
    record = load_record(ACTIVE)
    verify_frozen_bytes(record)
    workflow = workflow_record() if WORKFLOW.exists() else {}
    if workflow:
        refresh_plan_document(workflow, record)
    failure = ""
    if record.get("state") == "repair_required":
        failure = (
            f" failure_hash={record.get('live_failure_hash', '')}"
            f" source_hash={record.get('live_failure_source_hash', '')}"
            f" attempt={record.get('live_failure_attempt', 0)}"
            f" diagnostic={json.dumps(record.get('live_failure_tail', ''))}"
        )
    print(
        f"IMPROVEMENT_STATUS active={record['id']} state={record['state']}"
        f" name={record['name']} regression_hash={record['regression_hash']} e2e_hash={record['e2e_hash']}"
        f" plan={PLAN_DOCUMENT.relative_to(ROOT)}{failure}"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    freeze_parser = sub.add_parser("freeze")
    freeze_parser.add_argument("--name", required=True)
    validate_parser = sub.add_parser("validate")
    validate_parser.add_argument("--name", required=True)
    investigation_parser = sub.add_parser("investigate-begin")
    investigation_parser.add_argument("--objective-b64", required=True)
    discovery_parser = sub.add_parser("record-discovery")
    discovery_parser.add_argument("--path-b64", required=True)
    discovery_parser.add_argument("--mode", required=True)
    evidence_parser = sub.add_parser("record-investigation-evidence")
    evidence_parser.add_argument("--kind", required=True)
    evidence_parser.add_argument("--query-b64", required=True)
    plan_parser = sub.add_parser("plan-write")
    plan_parser.add_argument("--content-b64", required=True)
    scaffold_parser = sub.add_parser("plan-scaffold")
    scaffold_parser.add_argument("--surface-b64", required=True)
    scaffold_parser.add_argument("--production-path-b64", required=True, action="append")
    begin_parser = sub.add_parser("begin")
    begin_parser.add_argument("--name", required=True)
    begin_parser.add_argument("--acceptance-b64", required=True)
    resolve_surface_parser = sub.add_parser("resolve-surface")
    resolve_surface_parser.add_argument("--surface-b64", required=True)
    artifact_parser = sub.add_parser("write-artifact")
    artifact_parser.add_argument("--kind", required=True)
    artifact_parser.add_argument("--content-b64", required=True)
    lint_parser = sub.add_parser("lint")
    lint_parser.add_argument("--kind", required=True)
    record_parser = sub.add_parser("record-write")
    record_parser.add_argument("--path-b64", required=True)
    preflight_parser = sub.add_parser("preflight-write")
    preflight_parser.add_argument("--path-b64", required=True)
    candidate_parser = sub.add_parser("check-candidate")
    candidate_parser.add_argument("--path-b64", required=True)
    restart_parser = sub.add_parser("restart-staging")
    restart_parser.add_argument("--reason-b64", required=True)
    failure_parser = sub.add_parser("record-failure")
    failure_parser.add_argument("--detail", required=True)
    quarantine_parser = sub.add_parser("quarantine-active")
    quarantine_parser.add_argument("--reason-b64", required=True)
    for command in ("plan-read", "transport-template", "scaffold-evaluators", "normalize-candidate", "reset-incomplete-candidate", "start-implementation", "verify", "mark-verified", "live", "complete", "abort", "status"):
        sub.add_parser(command)
    args = parser.parse_args()
    try:
        if args.command == "freeze":
            freeze(args.name)
        elif args.command == "validate":
            validate(args.name)
        elif args.command == "investigate-begin":
            investigate_begin(args.objective_b64)
        elif args.command == "record-discovery":
            record_discovery(args.path_b64, args.mode)
        elif args.command == "record-investigation-evidence":
            record_investigation_evidence(args.kind, args.query_b64)
        elif args.command == "plan-write":
            plan_write(args.content_b64)
        elif args.command == "plan-scaffold":
            plan_scaffold(args.surface_b64, args.production_path_b64)
        elif args.command == "plan-read":
            read_plan()
        elif args.command == "transport-template":
            transport_template()
        elif args.command == "scaffold-evaluators":
            scaffold_evaluators()
        elif args.command == "begin":
            begin_stage(args.name, args.acceptance_b64)
        elif args.command == "resolve-surface":
            resolve_surface(args.surface_b64)
        elif args.command == "write-artifact":
            write_artifact(args.kind, args.content_b64)
        elif args.command == "lint":
            lint_staged(args.kind)
        elif args.command == "start-implementation":
            start_implementation()
        elif args.command == "preflight-write":
            preflight_write(args.path_b64)
        elif args.command == "check-candidate":
            check_candidate(args.path_b64)
        elif args.command == "normalize-candidate":
            normalize_active_candidate()
        elif args.command == "reset-incomplete-candidate":
            reset_incomplete_candidate()
        elif args.command == "record-write":
            record_write(args.path_b64)
        elif args.command == "restart-staging":
            restart_staging(args.reason_b64)
        elif args.command == "record-failure":
            record_failure(args.detail)
        elif args.command == "quarantine-active":
            quarantine_active(args.reason_b64)
        elif args.command == "verify":
            verify()
        elif args.command == "mark-verified":
            mark_verified()
        elif args.command == "live":
            live()
        elif args.command == "complete":
            complete()
        elif args.command == "abort":
            abort()
        else:
            status()
        return 0
    except GateError as exc:
        print(f"IMPROVEMENT_GATE_FAILED code={exc.code} message={exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
