import base64
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SOURCE_MANAGER = Path(__file__).resolve().parents[1] / "scripts" / "improvement_test_gate.py"


REGRESSION = '''from pathlib import Path
import os

def test_feature_marker_contract():
    root = Path(os.environ["ERNOS_SOURCE_ROOT"])
    value = (root / "feature.marker").read_text(encoding="utf-8") if (root / "feature.marker").exists() else ""
    assert value == "implemented", f"expected implemented marker, got {value!r}"

if __name__ == "__main__":
    test_feature_marker_contract()
    print("regression contract passed")
'''


E2E = '''import subprocess
from pathlib import Path
import os

def test_live_process_surface():
    marker = Path(os.environ["ERNOS_SOURCE_ROOT"]) / "feature.marker"
    result = subprocess.run(["/bin/cat", str(marker)], capture_output=True, text=True, check=False)
    assert result.returncode == 0
    assert result.stdout.strip() == "implemented"

if __name__ == "__main__":
    test_live_process_surface()
    print("live E2E passed")
'''


PLAN = '''## Objective
Add an externally observable feature-marker behavior and prove that the value is persisted and readable through an independent process boundary.

## Investigation Findings
`source_one.py` owns the marker value contract and `source_two.py` owns the independent reader boundary. Both files were read from current source and their exact hashes are retained by the controller.

## Exact Interface Evidence
- `source_one.py:1`: `MARKER = 'implemented'`
- `source_two.py:1`: `READER = '/bin/cat'`

## Production Surface
The production surface is the exact `feature_marker_read()` callable described by `source_one.py`, with the independent process invocation and returned value described by `source_two.py`.

## Implementation
Create the durable marker with the exact value required by the acceptance contract, then let the immutable regression and live-process evaluator observe it independently.

## Files
- feature.marker: Persist the exact production marker value consumed by both verified behavior surfaces.

## Tests
The regression invokes the `feature_marker_read()` contract against current repository state and fails before implementation. The E2E launches `/bin/cat` as an independent process and verifies the same `feature_marker_read()` production-created bytes.

## Risks and Rollback
An incorrect value or missing durable write fails both evaluators. Rollback removes the marker and restores the unchanged pre-feature repository state.
'''


REGISTERED_TOOL_PLAN = '''## Objective
Add a registered transcript-distillation behavior and prove both returned output and durable memory effects through the authenticated production IPC boundary.

## Investigation Findings
`source_one.py` owns extension registration and `source_two.py` owns durable memory retrieval. Both current files were read and hash-recorded before planning.

## Production Surface
The exact registered production surface is `aes_distill`, dispatched internally through `self_extensions_execute` in the interface identified in `source_one.py` and persisted through `source_two.py`.

## Implementation
Register the tool and implement complete transcript parsing plus durable memory writes through the investigated interfaces.

## Files
- feature.marker: Implement the complete registered transcript-distillation behavior used by the fixture.

## Tests
Both evaluators call `aes_distill` through AI EVAL_TOOL. They assert parsed output, and the live E2E independently reads durable memory through AGENT GET MEMORY.

## Risks and Rollback
Malformed parsing or incomplete persistence fails the frozen evaluators. Rollback restores the exact pre-change source bytes.
'''


class ImprovementGateFixture:
    def __init__(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "scripts").mkdir()
        shutil.copy2(SOURCE_MANAGER, self.root / "scripts" / "improvement_test_gate.py")
        self.manager = self.root / "scripts" / "improvement_test_gate.py"
        (self.root / "source_one.py").write_text("MARKER = 'implemented'\n", encoding="utf-8")
        (self.root / "source_two.py").write_text("READER = '/bin/cat'\n", encoding="utf-8")

    def close(self):
        self.temp.cleanup()

    def write_discord_interface_sources(self):
        fixtures = {
            "decent_agent/self_extensions.ep": "define self_extensions_action_known with action_name as Str returning Int:\n    return 0\ndefine self_extensions_execute with ctx as Map and action_name as Str and args_list as List returning Str:\n    set memory_mgr to map_get_val(ctx and \"memory_mgr\")\n    return \"unknown\"\n",
            "decent_agent/memory.ep": "define memory_store with memory_mgr as Map and tier as Int and key as Str and value as Str returning Int:\n    return 0\n",
            "decent_agent/tools.ep": "import \"../storage\"\nimport \"../decent_net/bridge_rpc\"\nset extension_db to storage_get_db()\nset ok to map_insert(ctx and \"storage_db\" and extension_db)\nset ddb to storage_get_db()\nset did to bridge_enqueue(ddb and \"discord\" and \"read_channel\" and channel_id)\nset result to bridge_wait_result(ddb and did and 200)\nif result equals \"error\" or else result equals \"timeout\":\n    return concat(\"count=\" and int_to_string(1))\n",
            "decent_net/bridge_rpc.ep": "define bridge_enqueue with db as Int and platform as Str and action as Str and args as Str returning Int:\n    return 1\ndefine bridge_wait_result with db as Int and id as Int and max_tries as Int returning Str:\n    return \"done\"\n",
            "decent_net/discord_bridge.py": "async def read_channel(channel_id):\n    return []\n",
        }
        for relative, content in fixtures.items():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

    def write_session_interface_sources(self):
        fixtures = {
            "decent_agent/self_extensions.ep": (
                'import "session"\nimport "memory"\n'
                "define self_extensions_execute with ctx as Map and action_name as Str and args_list as List returning Str:\n"
                '    set memory_mgr to map_get_val(ctx and "memory_mgr")\n'
                '    set sessions_mgr to map_get_val(ctx and "sessions")\n'
                '    set channel_id to get_list(args_list and 0)\n'
                '    set did to bridge_enqueue(ddb and "discord" and "read_channel" and channel_id)\n'
                '    set diagnostic to concat("session:" and action_name)\n'
                "    return \"unknown\"\n"
            ),
            "decent_agent/session.ep": (
                "define session_load with path as Str returning Map:\n"
                "    return create_map()\n"
                "define session_manager_resolve_id with mgr as Map and ref as Str returning Str:\n"
                "    if string_length(ref) == 0:\n"
                "        return \"\"\n"
                "    set sessions_map to map_get_val(mgr and \"sessions\")\n"
                "    set keys to map_keys(sessions_map)\n"
                "    return ref\n"
                "define session_serialize_json_string with sess as Map returning Str:\n"
                "    return \"{}\"\n"
                'set path to path_join("config/sessions" and "fixture.json")\n'
                'set messages to map_get_val(sess and "messages")\n'
                'set record_count to length_list(messages)\n'
                'set content to map_get_val(msg_map and "content")\n'
            ),
            "decent_agent/memory.ep": (
                "define memory_store with memory_mgr as Map and tier as Int and key as Str and value as Str returning Int:\n"
                "    return 0\n"
            ),
            "decent_agent/tools.ep": (
                'import "./session"\n'
                'set runtime_sessions to map_get_val(ctx and "sessions")\n'
                'set loaded_by_id to map_get_val(runtime_sessions and "sessions")\n'
                'set sess to map_get_val(loaded_by_id and session_id)\n'
            ),
        }
        for relative, content in fixtures.items():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

    def write_registered_interface_sources(self):
        fixtures = {
            "decent_agent/self_extensions.ep": (
                'import "memory"\n'
                "define self_extensions_schema returning Str:\n"
                '    return "registered extensions"\n'
                "define self_extensions_action_known with action_name as Str returning Int:\n"
                "    return 0\n"
                "define self_extensions_execute with ctx as Map and action_name as Str and args_list as List returning Str:\n"
                '    set memory_mgr to map_get_val(ctx and "memory_mgr")\n'
                "    return action_name\n"
            ),
            "decent_agent/memory.ep": (
                "define memory_store with memory_mgr as Map and tier as Int and key as Str and value as Str returning Int:\n"
                "    return 0\n"
            ),
        }
        for relative, content in fixtures.items():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

    def stage(self, regression=REGRESSION, e2e=E2E, acceptance=None, plan=PLAN, planned_files=None):
        staging = self.root / "config" / "improvements" / "staging"
        staging.mkdir(parents=True, exist_ok=True)
        acceptance_value = acceptance or "[feature_marker] The externally observable feature marker contains the exact implemented value.\n[live_process] A separate live process reads and returns that persisted marker value."
        (staging / "acceptance.txt").write_text(
            acceptance_value,
            encoding="utf-8",
        )
        (staging / "regression.py").write_text(regression, encoding="utf-8")
        (staging / "e2e.py").write_text(e2e, encoding="utf-8")
        (staging / "plan_body.md").write_text(plan, encoding="utf-8")
        discovery = []
        for source in ("source_one.py", "source_two.py"):
            path = self.root / source
            discovery.append(
                {
                    "path": source,
                    "mode": "read",
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "size": path.stat().st_size,
                    "recorded_at": 1,
                }
            )
        workflow = {
            "version": 2,
            "objective": "Implement and verify the complete externally observable persisted marker behavior.",
            "state": "tests_authoring",
            "name": "fixture",
            "discovery": discovery,
            "discovery_hash": hashlib.sha256(json.dumps(discovery, sort_keys=True).encode()).hexdigest(),
            "plan_discovery_paths": ["source_one.py", "source_two.py"],
            "plan_discovery_hash": hashlib.sha256(
                json.dumps(["source_one.py", "source_two.py"]).encode()
            ).hexdigest(),
            "planned_files": planned_files or ["feature.marker"],
            "plan_body_hash": hashlib.sha256(plan.encode()).hexdigest(),
            "plan_version": 1,
            "validation_attempts": [],
            "acceptance_hash": hashlib.sha256(acceptance_value.encode()).hexdigest(),
        }
        (staging / "workflow.json").write_text(json.dumps(workflow), encoding="utf-8")

    def run(self, *args):
        if args and args[0] in {"validate", "freeze"} and "--name" in args:
            workflow_path = self.root / "config" / "improvements" / "staging" / "workflow.json"
            if workflow_path.is_file():
                workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
                workflow["name"] = args[args.index("--name") + 1]
                workflow_path.write_text(json.dumps(workflow), encoding="utf-8")
        return subprocess.run(
            [sys.executable, str(self.manager), *args],
            cwd=self.root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )

    def record_write(self, relative: str):
        encoded = base64.b64encode(relative.encode("utf-8")).decode("ascii")
        return self.run("record-write", "--path-b64", encoded)

    def preflight_write(self, relative: str):
        encoded = base64.b64encode(relative.encode("utf-8")).decode("ascii")
        return self.run("preflight-write", "--path-b64", encoded)

    def check_candidate(self, relative: str):
        encoded = base64.b64encode(relative.encode("utf-8")).decode("ascii")
        return self.run("check-candidate", "--path-b64", encoded)

    def candidate_path(self, relative: str):
        active = json.loads(
            (self.root / "config" / "improvements" / "active.json").read_text(encoding="utf-8")
        )
        target = self.root / relative
        return target.parent / f".ernos-candidate-{active['id'][:16]}-{target.name}"

    def record_discovery(self, relative: str, mode: str = "read"):
        encoded = base64.b64encode(relative.encode("utf-8")).decode("ascii")
        return self.run("record-discovery", "--path-b64", encoded, "--mode", mode)

    def record_evidence(self, kind: str, query: str):
        encoded = base64.b64encode(query.encode("utf-8")).decode("ascii")
        return self.run(
            "record-investigation-evidence", "--kind", kind, "--query-b64", encoded
        )

    def freeze_valid(self, name: str):
        validated = self.run("validate", "--name", name)
        if validated.returncode != 0:
            return validated
        return self.run("freeze", "--name", name)


class ImprovementTestGateTests(unittest.TestCase):
    def setUp(self):
        self.fx = ImprovementGateFixture()

    def tearDown(self):
        self.fx.close()

    def test_candidate_dialect_normalization_is_exact_and_plan_bound(self):
        plan_path = self.fx.root / "config" / "improvements" / "frozen" / "plan.md"
        plan_path.parent.mkdir(parents=True, exist_ok=True)
        plan_path.write_text(
            '## Exact Interface Evidence\n'
            '- `tools.ep:1`: `set ok to map_insert(ctx and "storage_db" and storage_get_db())`\n'
            '- `self_extensions.ep:1`: `set db to map_get_val(ctx and "storage_db")`\n'
            '- `tools.ep:3`: `import "../decent_net/bridge_rpc"`\n'
            '- `tools.ep:4`: `set id to bridge_enqueue(db and "discord" and "read_channel" and channel)`\n'
            '- `tools.ep:5`: `set result to bridge_wait_result(db and id and 200)`\n',
            encoding="utf-8",
        )
        candidate = self.fx.root / "candidate.ep"
        candidate.write_text(
            'import "../decent_agent/tools"\n'
            'import "../storage"\n'
            'set db to tools_storage_get_db()\n'
            'set api_db to storage_get_api_db()\n'
            'set command_id to bridge_enqueue(db and "discord" and "read_channel" and channel_id)\n'
            'set bridge_result to bridge_wait_result(db and command_id and 200)\n'
            'set result = memory_store(memory_mgr and 2 and key and value)\n'
            'set joined to concat("left" and value and "right")\n'
            'set summary_text to "prefix:" and value and ",count:" and int_to_string(2)\n'
            'return concat("a", int_to_string(1), ",b", int_to_string(2))\n]}',
            encoding="utf-8",
        )
        spec = importlib.util.spec_from_file_location("fixture_gate", self.fx.manager)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        rules = module.normalize_candidate_dialect(
            {
                "plan_path": "config/improvements/frozen/plan.md",
                "planned_files": ["decent_agent/self_extensions.ep"],
                "planned_surfaces": ["session_summary_generator"],
            },
            candidate,
        )
        normalized = candidate.read_text(encoding="utf-8")
        self.assertIn("transport_suffix", rules)
        self.assertIn("extension_storage_context", rules)
        self.assertIn("extension_storage_import_removed", rules)
        self.assertIn("extension_controller_import_removed", rules)
        self.assertIn("bridge_rpc_import_missing", rules)
        self.assertIn("set_assignment:1", rules)
        self.assertTrue(any(rule.startswith("concat_binary:") for rule in rules))
        self.assertNotIn('import "../storage"', normalized)
        self.assertNotIn('import "../decent_agent/tools"', normalized)
        self.assertIn('import "../decent_net/bridge_rpc"', normalized)
        self.assertIn('set db to map_get_val(ctx and "storage_db")', normalized)
        self.assertIn('set api_db to map_get_val(ctx and "storage_db")', normalized)
        self.assertIn("set result to memory_store(memory_mgr and 2 and key and value)", normalized)
        self.assertIn(
            'return concat("a" and concat(int_to_string(1) and concat(",b" and int_to_string(2))))',
            normalized,
        )
        self.assertIn(
            'set joined to concat("left" and concat(value and "right"))',
            normalized,
        )
        self.assertIn(
            'set summary_text to concat("prefix:" and concat(value and concat(",count:" and int_to_string(2))))',
            normalized,
        )
        self.assertNotIn("]}", normalized)

        quoted_suffix = self.fx.root / "quoted_suffix.ep"
        quoted_suffix.write_text(
            'define final_value returning Str:\n'
            '    return "complete"\"]',
            encoding="utf-8",
        )
        suffix_rules = module.normalize_candidate_dialect(
            {
                "plan_path": "config/improvements/frozen/plan.md",
                "planned_files": ["decent_agent/self_extensions.ep"],
            },
            quoted_suffix,
        )
        self.assertIn("transport_suffix", suffix_rules)
        self.assertEqual(
            quoted_suffix.read_text(encoding="utf-8"),
            'define final_value returning Str:\n    return "complete"\n',
        )

    def test_discord_extension_candidate_enforces_argument_contract_and_existing_behavior(self):
        self.fx.write_discord_interface_sources()
        target = self.fx.root / "decent_agent" / "self_extensions.ep"
        target.write_text(
            'define self_extensions_schema returning Str:\n'
            '    set schemas to "- aes_distill([transcript]) -> Str\\n"\n'
            '    set schemas to concat(schemas and "  Example: Action: aes_distill([\\\"text\\\"])\\n")\n'
            '    return schemas\n'
            'define self_extensions_execute with ctx as Map and action_name as Str and args_list as List returning Str:\n'
            '    if action_name equals "aes_distill":\n'
            '        return "processed"\n'
            '    return "Error: self-extension dispatch received an unregistered action."\n',
            encoding="utf-8",
        )
        good = self.fx.root / "good.ep"
        good.write_text(
            'set schemas to concat(schemas and "- scavenger_sweep([channel_id]) -> Str\\n")\n'
            + target.read_text(encoding="utf-8").replace(
                '    return "Error: self-extension dispatch received an unregistered action."',
                '    if action_name equals "scavenger_sweep":\n'
                '        if length_list(args_list) != 1:\n'
                '            return "Error: channel required."\n'
                '        set channel_id to get_list(args_list and 0)\n'
                '        set ddb to map_get_val(ctx and "storage_db")\n'
                '        set did to bridge_enqueue(ddb and "discord" and "read_channel" and channel_id)\n'
                '        return "scavenger_sweep:ok"\n'
                '    return "Error: self-extension dispatch received an unregistered action."',
            ),
            encoding="utf-8",
        )
        spec = importlib.util.spec_from_file_location("fixture_contract_gate", self.fx.manager)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        record = {
            "objective": "Implement exactly `scavenger_sweep` with real Discord channel retrieval."
        }
        module.validate_candidate_objective_contract(record, target, good)

        staging = self.fx.root / "config" / "improvements" / "staging"
        staging.mkdir(parents=True, exist_ok=True)
        active_record = {"id": "frozen-test-id", "plan_hash": "plan-test-hash"}
        (staging / "workflow.json").write_text(
            json.dumps(
                {
                    "transaction_id": active_record["id"],
                    "plan_body_hash": active_record["plan_hash"],
                    "objective": record["objective"],
                }
            ),
            encoding="utf-8",
        )
        module.validate_candidate_objective_contract(active_record, target, good)

        repairable = self.fx.root / "repairable.ep"
        repairable.write_text(
            good.read_text(encoding="utf-8")
            .replace('return "processed"', 'return "processed,changed"')
            .replace(
                '        set ddb to map_get_val(ctx and "storage_db")',
                '        set bridge_rpc to map_get_val(ctx and "bridge_rpc")\n'
                '        if bridge_rpc == 0:\n'
                '            return "Error: bridge_rpc not available in context."\n'
                '        set ddb to map_get_val(ctx and "storage_db")',
            ),
            encoding="utf-8",
        )
        active_record["planned_files"] = ["decent_agent/self_extensions.ep"]
        rules = module.normalize_candidate_dialect(active_record, repairable, target)
        self.assertIn("existing_action_preserved:aes_distill", rules)
        self.assertIn("invented_bridge_context_removed:1", rules)
        module.validate_candidate_objective_contract(active_record, target, repairable)

        wrong = self.fx.root / "wrong.ep"
        wrong.write_text(
            good.read_text(encoding="utf-8")
            .replace("scavenger_sweep([channel_id])", "scavenger_sweep([])")
            .replace("length_list(args_list) != 1", "length_list(args_list) != 0")
            .replace(
                "set channel_id to get_list(args_list and 0)",
                'set channel_id to map_get_val(ddb and "discord" and "channel_id")',
            )
            .replace('return "processed"', 'return "processed,changed"')
            .replace("aes_distill([transcript])", "aes_distill_typo([transcript])"),
            encoding="utf-8",
        )
        with self.assertRaises(module.GateError) as caught:
            module.validate_candidate_objective_contract(active_record, target, wrong)
        detail = str(caught.exception)
        self.assertIn("channel_id", detail)
        self.assertIn("changed_existing_actions=aes_distill", detail)
        self.assertIn("changed_existing_schema=aes_distill", detail)

    def test_candidate_normalization_preserves_existing_registry_and_appends_only_new_surface(self):
        target = self.fx.root / "decent_agent" / "self_extensions.ep"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            'define self_extensions_schema returning Str:\n'
            '    set schemas to "- aes_distill([transcript]) -> Str\\n"\n'
            '    set schemas to concat(schemas and "  Description: existing exact schema.\\n")\n'
            '    return schemas\n\n'
            'define self_extensions_action_known with action_name as Str returning Int:\n'
            '    if action_name equals "aes_distill":\n'
            '        return 1\n'
            '    return 0\n\n'
            'define self_extensions_execute with ctx as Map and action_name as Str and args_list as List returning Str:\n'
            '    if action_name equals "aes_distill":\n'
            '        return "processed"\n'
            '    return "Error"\n',
            encoding="utf-8",
        )
        candidate = self.fx.root / "candidate_registry.ep"
        candidate.write_text(
            target.read_text(encoding="utf-8")
            .replace("aes_distill([transcript])", "aes_distil_typo([transcript])")
            .replace(
                '    return schemas\n',
                '    set schemas to concat(schemas and "- session_summary_generator([session_id]) -> Str\\n")\n'
                '    set schemas to concat(schemas and "  Description: summarize a live session.\\n")\n'
                '    return schemas\n',
                1,
            )
            .replace(
                '    if action_name equals "aes_distill":\n        return 1\n',
                '    if action_name and action_name equals "aes_distill":\n        return 1\n'
                '    if action_name equals "session_summary_generator":\n        return 1\n',
                1,
            )
            .replace(
                '    return "Error"\n',
                '    if action_name equals "session_summary_generator":\n'
                '        return "session_summary_generator:ok"\n'
                '    return "Error"\n',
            ),
            encoding="utf-8",
        )
        spec = importlib.util.spec_from_file_location("fixture_registry_gate", self.fx.manager)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        rules = module.normalize_candidate_dialect(
            {
                "plan_path": "config/improvements/frozen/plan.md",
                "planned_files": ["decent_agent/self_extensions.ep"],
                "planned_surfaces": ["session_summary_generator"],
            },
            candidate,
            target,
        )
        normalized = candidate.read_text(encoding="utf-8")
        self.assertTrue(any(rule.startswith("existing_schema_preserved") for rule in rules))
        self.assertTrue(any(rule.startswith("existing_action_registry_preserved") for rule in rules))
        self.assertIn('aes_distill([transcript])', normalized)
        self.assertNotIn('aes_distil_typo', normalized)
        self.assertIn('if action_name equals "aes_distill":', normalized)
        self.assertNotIn('if action_name and action_name equals "aes_distill":', normalized)
        self.assertEqual(normalized.count('session_summary_generator([session_id])'), 1)
        self.assertEqual(normalized.count('if action_name equals "session_summary_generator":'), 2)

    def test_candidate_normalization_restores_an_omitted_existing_dispatch_branch(self):
        target = self.fx.root / "decent_agent" / "self_extensions.ep"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            'define self_extensions_schema returning Str:\n'
            '    set schemas to "- retained_action([]) -> Str\\n"\n'
            '    return schemas\n\n'
            'define self_extensions_action_known with action_name as Str returning Int:\n'
            '    if action_name equals "retained_action":\n'
            '        return 1\n'
            '    return 0\n\n'
            'define self_extensions_execute with ctx as Map and action_name as Str and args_list as List returning Str:\n'
            '    if action_name equals "retained_action":\n'
            '        return "retained_action:ok"\n'
            '    return "Error: self-extension dispatch received an unregistered action."\n',
            encoding="utf-8",
        )
        candidate = self.fx.root / "candidate_omitted_branch.ep"
        candidate.write_text(
            'define self_extensions_schema returning Str:\n'
            '    set schemas to "- retained_action([]) -> Str\\n"\n'
            '    set schemas to concat(schemas and "- new_action([]) -> Str\\n")\n'
            '    return schemas\n\n'
            'define self_extensions_action_known with action_name as Str returning Int:\n'
            '    if action_name equals "retained_action":\n'
            '        return 1\n'
            '    if action_name equals "new_action":\n'
            '        return 1\n'
            '    return 0\n\n'
            'define self_extensions_execute with ctx as Map and action_name as Str and args_list as List returning Str:\n'
            '    if action_name equals "new_action":\n'
            '        return "new_action:ok"\n'
            '    return "Error: self-extension dispatch received an unregistered action."\n',
            encoding="utf-8",
        )
        spec = importlib.util.spec_from_file_location("fixture_omitted_action_gate", self.fx.manager)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        record = {
            "plan_path": "config/improvements/frozen/plan.md",
            "planned_files": ["decent_agent/self_extensions.ep"],
            "planned_surfaces": ["new_action"],
        }
        rules = module.normalize_candidate_dialect(record, candidate, target)
        normalized = candidate.read_text(encoding="utf-8")
        self.assertIn("existing_action_restored:retained_action", rules)
        self.assertIn('return "retained_action:ok"', normalized)
        self.assertIn('return "new_action:ok"', normalized)
        module.validate_additive_extension_preservation(record, target, candidate)

    def test_live_repair_preserves_other_actions_but_keeps_active_surface_change(self):
        target = self.fx.root / "decent_agent" / "self_extensions.ep"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            'define self_extensions_schema returning Str:\n'
            '    set schemas to "- aes_distill([]) -> Str\\n"\n'
            '    set schemas to concat(schemas and "- session_summary_generator([session_id]) -> Str\\n")\n'
            '    return schemas\n\n'
            'define self_extensions_action_known with action_name as Str returning Int:\n'
            '    if action_name equals "aes_distill":\n'
            '        return 1\n'
            '    if action_name equals "session_summary_generator":\n'
            '        return 1\n'
            '    return 0\n\n'
            'define self_extensions_execute with ctx as Map and action_name as Str and args_list as List returning Str:\n'
            '    if action_name equals "aes_distill":\n'
            '        return "existing"\n'
            '    if action_name equals "session_summary_generator":\n'
            '        return "old active behavior"\n'
            '    return "Error"\n',
            encoding="utf-8",
        )
        candidate = self.fx.root / "candidate_live_repair.ep"
        candidate.write_text(
            target.read_text(encoding="utf-8")
            .replace('return "existing"', 'return "damaged unrelated action"')
            .replace('return "old active behavior"', 'return "repaired active behavior"'),
            encoding="utf-8",
        )
        spec = importlib.util.spec_from_file_location("fixture_live_repair_gate", self.fx.manager)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        rules = module.normalize_candidate_dialect(
            {
                "plan_path": "config/improvements/frozen/plan.md",
                "planned_files": ["decent_agent/self_extensions.ep"],
                # Frozen active records retain planned_surfaces, while the richer
                # workflow record owns required_surface. Candidate repair must derive
                # the active surface from the frozen shape used in production.
                "planned_surfaces": ["session_summary_generator"],
            },
            candidate,
            target,
        )
        normalized = candidate.read_text(encoding="utf-8")
        self.assertIn("existing_action_preserved:aes_distill", rules)
        self.assertIn('return "existing"', normalized)
        self.assertNotIn("damaged unrelated action", normalized)
        self.assertIn('return "repaired active behavior"', normalized)
        self.assertNotIn("existing_action_preserved:session_summary_generator", rules)

    def test_session_extension_rejects_reversed_memory_store_status(self):
        spec = importlib.util.spec_from_file_location("fixture_persistence_gate", self.fx.manager)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        source = '''define self_extensions_schema returning Str:
    set schemas to "- session_summary_generator([session_id]) -> Str\\n"
    return schemas

define self_extensions_action_known with action_name as Str returning Int:
    if action_name equals "session_summary_generator":
        return 1
    return 0

define self_extensions_execute with ctx as Map and action_name as Str and args_list as List returning Str:
    if action_name equals "session_summary_generator":
        if length_list(args_list) != 1:
            return "Error"
        set session_id to get_list(args_list and 0)
        if string_length(session_id) == 0 or else string_index_of(session_id and "/") >= 0 or else string_index_of(session_id and "\\\\") >= 0:
            return "Error"
        set memory_mgr to map_get_val(ctx and "memory_mgr")
        set sessions_mgr to map_get_val(ctx and "sessions")
        set sessions_map to map_get_val(sessions_mgr and "sessions")
        if map_contains(sessions_map and session_id) == 0:
            return "Error"
        set sess to map_get_val(sessions_map and session_id)
        set messages_list to map_get_val(sess and "messages")
        set msg_count to length_list(messages_list)
        set msg to get_list(messages_list and 0)
        set content to map_get_val(msg and "content")
        set summary_value to concat(session_id and content)
        set ok to memory_store(memory_mgr and 2 and "session_summary_generator" and summary_value)
        if ok == 0:
            return "Error: failed to persist summary."
        return "session_summary_generator:ok,session_id:"
    return "Error"
'''
        target = self.fx.root / "decent_agent" / "self_extensions.ep"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source, encoding="utf-8")
        candidate = self.fx.root / "candidate.ep"
        candidate.write_text(source, encoding="utf-8")
        workflow = {
            "objective": "Implement a registered tool named `session_summary_generator` that takes a session ID and retrieves the full transcript.",
            "required_surface": "session_summary_generator",
        }
        with self.assertRaisesRegex(module.GateError, "memory_store success/failure contract"):
            module.validate_candidate_objective_contract(workflow, target, candidate)

        rules = module.normalize_candidate_dialect(
            {
                "planned_files": ["decent_agent/self_extensions.ep"],
                "planned_surfaces": ["session_summary_generator"],
            },
            candidate,
            target,
        )
        self.assertIn("memory_store_zero_success_guard:1", rules)
        normalized = candidate.read_text(encoding="utf-8")
        self.assertIn("if ok != 0:", normalized)
        self.assertIn('if ok == 0:', target.read_text(encoding="utf-8"))
        module.validate_candidate_objective_contract(workflow, target, candidate)

    def test_session_extension_normalizes_exact_path_equality_guard(self):
        spec = importlib.util.spec_from_file_location("fixture_path_guard_gate", self.fx.manager)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        source = '''define self_extensions_schema returning Str:
    set schemas to "- session_summary_generator([session_id]) -> Str\\n"
    return schemas

define self_extensions_action_known with action_name as Str returning Int:
    if action_name equals "session_summary_generator":
        return 1
    return 0

define self_extensions_execute with ctx as Map and action_name as Str and args_list as List returning Str:
    if action_name equals "session_summary_generator":
        if length_list(args_list) != 1:
            return "Error"
        set session_id to get_list(args_list and 0)
        if string_length(session_id) == 0 or session_id equals "/" or session_id equals "\\\\":
            return "Error"
        set memory_mgr to map_get_val(ctx and "memory_mgr")
        set sessions_mgr to map_get_val(ctx and "sessions")
        set sessions_map to map_get_val(sessions_mgr and "sessions")
        if map_contains(sessions_map and session_id) == 0:
            return "Error"
        set sess to map_get_val(sessions_map and session_id)
        set messages_list to map_get_val(sess and "messages")
        set msg_count to length_list(messages_list)
        set msg to get_list(messages_list and 0)
        set content to map_get_val(msg and "content")
        set summary_value to concat(session_id and content)
        set ok to memory_store(memory_mgr and 2 and "session_summary_generator" and summary_value)
        if ok != 0:
            return "Error: failed to persist summary."
        return "session_summary_generator:ok,session_id:"
    return "Error"
'''
        target = self.fx.root / "decent_agent" / "self_extensions.ep"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source, encoding="utf-8")
        candidate = self.fx.root / "candidate.ep"
        candidate.write_text(source, encoding="utf-8")
        workflow = {
            "objective": "Implement a registered tool named `session_summary_generator` that takes a session ID and retrieves the full transcript.",
            "required_surface": "session_summary_generator",
        }
        with self.assertRaisesRegex(module.GateError, "path-like session_id rejection"):
            module.validate_candidate_objective_contract(workflow, target, candidate)

        rules = module.normalize_candidate_dialect(
            {
                "planned_files": ["decent_agent/self_extensions.ep"],
                "planned_surfaces": ["session_summary_generator"],
            },
            candidate,
            target,
        )
        self.assertIn("pathlike_session_id_guard:1", rules)
        normalized = candidate.read_text(encoding="utf-8")
        self.assertIn('string_index_of(session_id and "/") >= 0', normalized)
        self.assertIn('string_index_of(session_id and "\\\\") >= 0', normalized)
        self.assertIn('session_id equals "/"', target.read_text(encoding="utf-8"))
        module.validate_candidate_objective_contract(workflow, target, candidate)

    @staticmethod
    def b64(value: str) -> str:
        return base64.b64encode(value.encode("utf-8")).decode("ascii")

    def test_generic_request_cannot_promote_prose_and_concrete_selection_is_retained(self):
        spec = importlib.util.spec_from_file_location("fixture_surface_gate", self.fx.manager)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        generic = (
            "Choose one useful feature that does not already exist. Inspect production code, "
            "create and maintain an implementation plan, implement the real feature, test it, "
            "recompile, restart, and verify it live."
        )
        selected = (
            "Implement a registered tool named `session_summary_generator` that returns a "
            "structured summary and persists it through the existing durable memory interface."
        )
        combined = (
            "[IMMUTABLE USER REQUEST]\n" + generic + "\n[/IMMUTABLE USER REQUEST]\n\n"
            "[CONCRETE FEATURE SELECTED BY ECHO]\n" + selected
            + "\n[/CONCRETE FEATURE SELECTED BY ECHO]"
        )
        self.assertEqual(module.objective_callable_surfaces(generic), [])
        self.assertEqual(
            module.objective_callable_surfaces(combined),
            ["session_summary_generator"],
        )
        self.assertEqual(
            module.explicit_marker_families(combined),
            set(),
            "structural immutable-request wrappers are not colon-form data markers",
        )
        transport_wrapped = (
            "[SESSION:sess_1] [SENDER:Maria] [ROLE:owner] [ACTOR_ID:123] "
            "[ACTOR_DISPLAY_NAME:Maria] [ACTOR_IS_HOST:1] [PLATFORM:discord] "
            "Implement aes_distill for [LESSON: key | value] and [CORRECTION: key | value]."
        )
        self.assertEqual(
            module.explicit_marker_families(transport_wrapped),
            {"LESSON", "CORRECTION"},
            "authenticated transport metadata must not become feature acceptance markers",
        )

        begun = self.fx.run(
            "investigate-begin", "--objective-b64", self.b64(combined)
        )
        self.assertEqual(begun.returncode, 0, begun.stdout)
        workflow = json.loads(
            (self.fx.root / "config" / "improvements" / "staging" / "workflow.json").read_text()
        )
        self.assertEqual(workflow["required_surface"], "session_summary_generator")
        self.assertNotEqual(workflow["required_surface"], "and")

    def test_controller_enforces_investigation_plan_and_behavioral_acceptance_order(self):
        begun = self.fx.run(
            "investigate-begin",
            "--objective-b64",
            self.b64("Implement a complete persisted marker capability through the verified production process surface."),
        )
        self.assertEqual(begun.returncode, 0, begun.stdout)
        pending_plan = self.fx.run("plan-read")
        self.assertEqual(pending_plan.returncode, 0, pending_plan.stdout)
        self.assertIn("IMPROVEMENT_PLAN_PENDING", pending_plan.stdout)
        self.assertIn("next=improvement_plan_write", pending_plan.stdout)
        blocked_plan = self.fx.run("plan-write", "--content-b64", self.b64(PLAN))
        self.assertNotEqual(blocked_plan.returncode, 0)
        self.assertIn("requires reads of at least 2", blocked_plan.stdout)

        for source in ("source_one.py", "source_two.py"):
            discovered = self.fx.run(
                "record-discovery",
                "--path-b64",
                self.b64(source),
                "--mode",
                "read",
            )
            self.assertEqual(discovered.returncode, 0, discovered.stdout)
        planned = self.fx.run("plan-write", "--content-b64", self.b64(PLAN))
        self.assertEqual(planned.returncode, 0, planned.stdout)
        self.assertIn("IMPROVEMENT_PLAN_OK", planned.stdout)
        plan_document = (
            self.fx.root / "config" / "improvements" / "staging" / "implementation_plan.md"
        ).read_text(encoding="utf-8")
        self.assertIn("- [x] Deep source investigation recorded", plan_document)
        self.assertIn("- [x] Implementation plan validated", plan_document)
        workflow = json.loads(
            (self.fx.root / "config" / "improvements" / "staging" / "workflow.json").read_text()
        )
        self.assertEqual(workflow["plan_discovery_paths"], ["source_one.py", "source_two.py"])
        self.assertEqual(workflow["planned_surfaces"], ["feature_marker_read"])

        nonbehavioral = (
            "[module_presence] The requested production module exists in the source tree after implementation.\n"
            "[tests_pass] The complete test command succeeds after the requested source update."
        )
        rejected = self.fx.run(
            "begin", "--name", "ordered_workflow", "--acceptance-b64", self.b64(nonbehavioral)
        )
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("test mechanics or artifact presence", rejected.stdout)
        self.assertFalse(
            (self.fx.root / "config" / "improvements" / "staging" / "name.txt").exists()
        )

        accepted = self.fx.run(
            "begin",
            "--name",
            "ordered_workflow",
            "--acceptance-b64",
            self.b64(
                "[feature_marker] The externally observable feature marker contains the exact implemented value.\n"
                "[live_process] A separate live process reads and returns that persisted marker value."
            ),
        )
        self.assertEqual(accepted.returncode, 0, accepted.stdout)

    def test_structured_plan_scaffold_uses_exact_durable_discovery(self):
        begun = self.fx.run(
            "investigate-begin",
            "--objective-b64",
            self.b64("Implement aes_distill as a complete registered production tool with an independently observable durable effect."),
        )
        self.assertEqual(begun.returncode, 0, begun.stdout)
        self.fx.write_registered_interface_sources()
        for source in (
            "decent_agent/self_extensions.ep", "decent_agent/memory.ep", "source_two.py"
        ):
            discovered = self.fx.run(
                "record-discovery", "--path-b64", self.b64(source), "--mode", "read"
            )
            self.assertEqual(discovered.returncode, 0, discovered.stdout)
        scaffolded = self.fx.run(
            "plan-scaffold",
            "--surface-b64",
            self.b64("aes_distill"),
            "--production-path-b64",
            self.b64("decent_agent/self_extensions.ep"),
        )
        self.assertEqual(scaffolded.returncode, 0, scaffolded.stdout)
        self.assertIn("IMPROVEMENT_PLAN_OK", scaffolded.stdout)
        body = (self.fx.root / "config" / "improvements" / "staging" / "plan_body.md").read_text()
        self.assertIn("`decent_agent/self_extensions.ep`", body)
        self.assertIn("`decent_agent/memory.ep`", body)
        self.assertIn("`source_two.py`", body)
        self.assertIn("`aes_distill`", body)
        self.assertIn("## Exact Interface Evidence", body)
        self.assertIn("`decent_agent/self_extensions.ep:1`", body)
        self.assertIn("`source_two.py:1`", body)
        self.assertNotIn("test_aes", body)
        workflow = json.loads(
            (self.fx.root / "config" / "improvements" / "staging" / "workflow.json").read_text()
        )
        self.assertEqual(workflow["planned_files"], ["decent_agent/self_extensions.ep"])
        self.assertEqual(workflow["planned_surfaces"][0], "aes_distill")

    def test_discord_objective_requires_exact_cross_component_discovery(self):
        objective = (
            "Implement exactly `scavenger_sweep` using real Discord channel retrieval "
            "and independently verified durable memory through current production interfaces."
        )
        begun = self.fx.run(
            "investigate-begin", "--objective-b64", self.b64(objective)
        )
        self.assertEqual(begun.returncode, 0, begun.stdout)
        for source in ("source_one.py", "source_two.py"):
            self.assertEqual(self.fx.record_discovery(source).returncode, 0)
        args = (
            "plan-scaffold", "--surface-b64", self.b64("scavenger_sweep"),
            "--production-path-b64", self.b64("decent_agent/self_extensions.ep"),
        )
        rejected = self.fx.run(*args)
        self.assertNotEqual(rejected.returncode, 0, rejected.stdout)
        self.assertIn("decent_agent/memory.ep", rejected.stdout)
        self.assertIn("decent_agent/tools.ep", rejected.stdout)
        self.assertIn("decent_net/bridge_rpc.ep", rejected.stdout)
        self.assertIn("decent_net/discord_bridge.py", rejected.stdout)

        self.fx.write_discord_interface_sources()
        required = (
            "decent_agent/self_extensions.ep",
            "decent_agent/memory.ep",
            "decent_agent/tools.ep",
            "decent_net/bridge_rpc.ep",
            "decent_net/discord_bridge.py",
        )
        for relative in required:
            receipt = self.fx.record_discovery(relative)
            self.assertEqual(receipt.returncode, 0, receipt.stdout)
        planned = self.fx.run(*args)
        self.assertEqual(planned.returncode, 0, planned.stdout)
        body = (
            self.fx.root / "config" / "improvements" / "staging" / "plan_body.md"
        ).read_text(encoding="utf-8")
        self.assertIn('map_insert(ctx and "storage_db" and extension_db)', body)
        self.assertIn('bridge_enqueue(ddb and "discord" and "read_channel"', body)
        self.assertIn('bridge_wait_result(ddb and did and 200)', body)
        self.assertIn('or else', body)
        self.assertIn('int_to_string', body)

    def test_plan_scaffold_supports_multiple_investigated_production_paths(self):
        begun = self.fx.run(
            "investigate-begin",
            "--objective-b64",
            self.b64("Implement a complete registered production tool across both declared source owners."),
        )
        self.assertEqual(begun.returncode, 0, begun.stdout)
        for source in ("source_one.py", "source_two.py"):
            self.assertEqual(self.fx.record_discovery(source).returncode, 0)
        planned = self.fx.run(
            "plan-scaffold",
            "--surface-b64", self.b64("aes_distill"),
            "--production-path-b64", self.b64("source_one.py"),
            "--production-path-b64", self.b64("source_two.py"),
        )
        self.assertEqual(planned.returncode, 0, planned.stdout)
        workflow = json.loads(
            (self.fx.root / "config" / "improvements" / "staging" / "workflow.json").read_text()
        )
        self.assertEqual(workflow["planned_files"], ["source_one.py", "source_two.py"])
        self.assertEqual(workflow["planned_surfaces"], ["aes_distill"])

    def test_explicit_primitive_and_callsite_investigation_is_structural(self):
        objective = (
            "Implement `aes_distill` after investigating exact string primitives and working call sites "
            "for every context, registry, and persistence interface used by the production implementation."
        )
        begun = self.fx.run("investigate-begin", "--objective-b64", self.b64(objective))
        self.assertEqual(begun.returncode, 0, begun.stdout)
        self.fx.write_registered_interface_sources()
        for source in (
            "source_one.py", "source_two.py",
            "decent_agent/self_extensions.ep", "decent_agent/memory.ep",
        ):
            discovered = self.fx.run(
                "record-discovery", "--path-b64", self.b64(source), "--mode", "read"
            )
            self.assertEqual(discovered.returncode, 0, discovered.stdout)
        args = (
            "plan-scaffold", "--surface-b64", self.b64("aes_distill"),
            "--production-path-b64", self.b64("decent_agent/self_extensions.ep"),
        )
        missing_reference = self.fx.run(*args)
        self.assertNotEqual(missing_reference.returncode, 0)
        self.assertIn("lookup_ernos", missing_reference.stdout)
        self.assertEqual(self.fx.record_evidence("language_reference", "string_index_of").returncode, 0)
        missing_callsites = self.fx.run(*args)
        self.assertNotEqual(missing_callsites.returncode, 0)
        self.assertIn("at least 3 distinct successful codebase_search", missing_callsites.stdout)
        for query in ("MARKER", "implemented", "READER"):
            receipt = self.fx.record_evidence("callsite_search", query)
            self.assertEqual(receipt.returncode, 0, receipt.stdout)
        planned = self.fx.run(*args)
        self.assertEqual(planned.returncode, 0, planned.stdout)

    def test_exact_interface_categories_require_semantic_receipts(self):
        (self.fx.root / "source_one.py").write_text(
            "def self_extensions_execute(ctx):\n    memory_mgr = ctx['memory_mgr']\n    return memory_store(memory_mgr, 2, 'k', 'v')\n",
            encoding="utf-8",
        )
        (self.fx.root / "source_two.py").write_text(
            "def parse(value):\n    return value.find('|')\n",
            encoding="utf-8",
        )
        objective = (
            "Implement `aes_distill` after investigating exact string primitives and working call sites "
            "for every context value, registry function, and persistence API used by production."
        )
        begun = self.fx.run("investigate-begin", "--objective-b64", self.b64(objective))
        self.assertEqual(begun.returncode, 0, begun.stdout)
        self.fx.write_registered_interface_sources()
        for source in (
            "source_one.py", "source_two.py",
            "decent_agent/self_extensions.ep", "decent_agent/memory.ep",
        ):
            discovered = self.fx.run(
                "record-discovery", "--path-b64", self.b64(source), "--mode", "read"
            )
            self.assertEqual(discovered.returncode, 0, discovered.stdout)
        args = (
            "plan-scaffold", "--surface-b64", self.b64("aes_distill"),
            "--production-path-b64", self.b64("decent_agent/self_extensions.ep"),
        )
        self.assertEqual(self.fx.record_evidence("language_reference", "string").returncode, 0)
        for query in ("self_extensions_execute", "memory_store", "memory_mgr"):
            receipt = self.fx.record_evidence("callsite_search", query)
            self.assertEqual(receipt.returncode, 0, receipt.stdout)
        vague_language = self.fx.run(*args)
        self.assertNotEqual(vague_language.returncode, 0)
        self.assertIn("exact string-primitive receipt", vague_language.stdout)
        self.assertEqual(self.fx.record_evidence("language_reference", "string_index_of").returncode, 0)
        planned = self.fx.run(*args)
        self.assertEqual(planned.returncode, 0, planned.stdout)

    def test_acceptance_must_retain_exact_marker_families_from_objective(self):
        objective = (
            "Implement aes_distill and extract every [LESSON: key | value] and "
            "[CORRECTION: key | value] marker through the registered production boundary."
        )
        begun = self.fx.run(
            "investigate-begin", "--objective-b64", self.b64(objective)
        )
        self.assertEqual(begun.returncode, 0, begun.stdout)
        self.fx.write_registered_interface_sources()
        for source in (
            "source_one.py", "source_two.py",
            "decent_agent/self_extensions.ep", "decent_agent/memory.ep",
        ):
            discovered = self.fx.run(
                "record-discovery", "--path-b64", self.b64(source), "--mode", "read"
            )
            self.assertEqual(discovered.returncode, 0, discovered.stdout)
        planned = self.fx.run(
            "plan-scaffold",
            "--surface-b64",
            self.b64("aes_distill"),
            "--production-path-b64",
            self.b64("decent_agent/self_extensions.ep"),
        )
        self.assertEqual(planned.returncode, 0, planned.stdout)

        misspelled = (
            "[transcript_parse] The input processes [LESSON: key | value] and [RECORRECTION: key | value] markers.\n"
            "[durable_memory] Every extracted value remains independently readable from durable memory."
        )
        rejected = self.fx.run(
            "begin", "--name", "aes_distill", "--acceptance-b64", self.b64(misspelled)
        )
        self.assertNotEqual(rejected.returncode, 0, rejected.stdout)
        self.assertIn("omit or misspell", rejected.stdout)
        self.assertIn("[CORRECTION]", rejected.stdout)

        exact = misspelled.replace("[RECORRECTION:", "[CORRECTION:")
        accepted = self.fx.run(
            "begin", "--name", "aes_distill", "--acceptance-b64", self.b64(exact)
        )
        self.assertEqual(accepted.returncode, 0, accepted.stdout)

    def test_structured_plan_scaffold_rejects_an_uninvestigated_path(self):
        begun = self.fx.run(
            "investigate-begin",
            "--objective-b64",
            self.b64("Implement a complete registered production tool only after exact source investigation."),
        )
        self.assertEqual(begun.returncode, 0, begun.stdout)
        for source in ("source_one.py", "source_two.py"):
            discovered = self.fx.run(
                "record-discovery", "--path-b64", self.b64(source), "--mode", "read"
            )
            self.assertEqual(discovered.returncode, 0, discovered.stdout)
        rejected = self.fx.run(
            "plan-scaffold",
            "--surface-b64",
            self.b64("aes_distill"),
            "--production-path-b64",
            self.b64("invented.py"),
        )
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("must be one exact investigated source path", rejected.stdout)

    def test_structured_plan_scaffold_rejects_surface_drift_from_objective(self):
        begun = self.fx.run(
            "investigate-begin",
            "--objective-b64",
            self.b64("Implement exactly `aes_distill` through the current registered extension interface."),
        )
        self.assertEqual(begun.returncode, 0, begun.stdout)
        self.fx.write_registered_interface_sources()
        for source in (
            "source_one.py", "source_two.py",
            "decent_agent/self_extensions.ep", "decent_agent/memory.ep",
        ):
            discovered = self.fx.run(
                "record-discovery", "--path-b64", self.b64(source), "--mode", "read"
            )
            self.assertEqual(discovered.returncode, 0, discovered.stdout)
        rejected = self.fx.run(
            "plan-scaffold",
            "--surface-b64",
            self.b64("aes_dist00"),
            "--production-path-b64",
            self.b64("decent_agent/self_extensions.ep"),
        )
        self.assertNotEqual(rejected.returncode, 0, rejected.stdout)
        self.assertIn("does not match the exact callable", rejected.stdout)
        self.assertIn("expected one of=aes_distill", rejected.stdout)
        self.assertFalse(
            (self.fx.root / "config" / "improvements" / "staging" / "plan_body.md").exists()
        )

    def test_scaffold_prefers_explicitly_named_tool_over_output_and_lifecycle_tokens(self):
        objective = (
            "Implement a new registered self-extension tool named e2e_echo_probe. "
            "It returns exactly e2e_probe: followed by the input, then completes "
            "system_verify and system_recompile."
        )
        begun = self.fx.run(
            "investigate-begin", "--objective-b64", self.b64(objective)
        )
        self.assertEqual(begun.returncode, 0, begun.stdout)
        self.fx.write_registered_interface_sources()
        for source in (
            "source_one.py", "source_two.py",
            "decent_agent/self_extensions.ep", "decent_agent/memory.ep",
        ):
            discovered = self.fx.run(
                "record-discovery", "--path-b64", self.b64(source), "--mode", "read"
            )
            self.assertEqual(discovered.returncode, 0, discovered.stdout)
        accepted = self.fx.run(
            "plan-scaffold",
            "--surface-b64",
            self.b64("e2e_echo_probe"),
            "--production-path-b64",
            self.b64("decent_agent/self_extensions.ep"),
        )
        self.assertEqual(accepted.returncode, 0, accepted.stdout)
        body = (
            self.fx.root / "config" / "improvements" / "staging" / "plan_body.md"
        ).read_text(encoding="utf-8")
        self.assertIn("`e2e_echo_probe`", body)
        self.assertNotIn("`e2e_probe`", body)

    def test_free_form_rejection_structurally_requires_scaffold_recovery(self):
        begun = self.fx.run(
            "investigate-begin",
            "--objective-b64",
            self.b64("Implement a complete registered production tool through investigated source interfaces."),
        )
        self.assertEqual(begun.returncode, 0, begun.stdout)
        for source in ("source_one.py", "source_two.py"):
            discovered = self.fx.run(
                "record-discovery", "--path-b64", self.b64(source), "--mode", "read"
            )
            self.assertEqual(discovered.returncode, 0, discovered.stdout)
        invalid = PLAN.replace(
            "- feature.marker: Persist the exact production marker value consumed by both verified behavior surfaces.",
            "- tests/test_feature_e2e.py: Implement an evaluator beside the production code.",
        )
        rejected = self.fx.run("plan-write", "--content-b64", self.b64(invalid))
        self.assertNotEqual(rejected.returncode, 0)
        locked = self.fx.run("plan-write", "--content-b64", self.b64(PLAN))
        self.assertNotEqual(locked.returncode, 0)
        self.assertIn("only legal plan-authoring route", locked.stdout)
        recovered = self.fx.run(
            "plan-scaffold",
            "--surface-b64",
            self.b64("feature_marker_read"),
            "--production-path-b64",
            self.b64("source_one.py"),
        )
        self.assertEqual(recovered.returncode, 0, recovered.stdout)
        self.assertFalse(
            (self.fx.root / "config" / "improvements" / "staging" / "plan_scaffold_required").exists()
        )

    def test_registered_extension_plan_requires_authenticated_eval_tool_transport(self):
        begun = self.fx.run(
            "investigate-begin",
            "--objective-b64",
            self.b64("Implement a registered transcript-distillation production tool."),
        )
        self.assertEqual(begun.returncode, 0, begun.stdout)
        for source in ("source_one.py", "source_two.py"):
            discovered = self.fx.run(
                "record-discovery", "--path-b64", self.b64(source), "--mode", "read"
            )
            self.assertEqual(discovered.returncode, 0, discovered.stdout)
        unbound = REGISTERED_TOOL_PLAN.replace(
            "AI EVAL_TOOL", "the authenticated production tool boundary"
        )
        rejected = self.fx.run("plan-write", "--content-b64", self.b64(unbound))
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("must bind Tests to authenticated AI EVAL TOOL", rejected.stdout)

    def test_durable_memory_plan_requires_current_memory_interface_discovery(self):
        begun = self.fx.run(
            "investigate-begin",
            "--objective-b64",
            self.b64("Implement a complete production tool with a durable memory effect."),
        )
        self.assertEqual(begun.returncode, 0, begun.stdout)
        for source in ("source_one.py", "source_two.py"):
            discovered = self.fx.run(
                "record-discovery", "--path-b64", self.b64(source), "--mode", "read"
            )
            self.assertEqual(discovered.returncode, 0, discovered.stdout)
        rejected = self.fx.run("plan-write", "--content-b64", self.b64(PLAN))
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("exact read of decent_agent/memory.ep", rejected.stdout)

    def test_plan_requires_exact_callable_surface_and_matching_test_strategy(self):
        self.fx.stage()
        staging = self.fx.root / "config" / "improvements" / "staging"
        vague = PLAN.replace("`feature_marker_read()` callable", "feature behavior")
        vague = vague.replace("`feature_marker_read()` contract", "feature contract")
        vague = vague.replace("`feature_marker_read()` production-created", "production-created")
        (staging / "plan_body.md").write_text(vague, encoding="utf-8")
        workflow_path = staging / "workflow.json"
        workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
        workflow["state"] = "investigating"
        workflow_path.write_text(json.dumps(workflow), encoding="utf-8")
        result = self.fx.run("plan-write", "--content-b64", self.b64(vague))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("exact backticked callable", result.stdout)

    def test_markdown_backticks_do_not_become_filesystem_path_bytes(self):
        self.fx.stage()
        staging = self.fx.root / "config" / "improvements" / "staging"
        quoted_plan = PLAN.replace("- feature.marker:", "- `feature.marker`:")
        workflow_path = staging / "workflow.json"
        workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
        workflow["state"] = "investigating"
        workflow_path.write_text(json.dumps(workflow), encoding="utf-8")
        result = self.fx.run("plan-write", "--content-b64", self.b64(quoted_plan))
        self.assertEqual(result.returncode, 0, result.stdout)
        updated = json.loads(workflow_path.read_text(encoding="utf-8"))
        self.assertEqual(updated["planned_files"], ["feature.marker"])

    def test_plan_rejects_sealed_controller_and_routes_tools_to_extension_registry(self):
        self.fx.stage()
        staging = self.fx.root / "config" / "improvements" / "staging"
        sealed_plan = PLAN.replace(
            "- feature.marker: Persist the exact production marker value consumed by both verified behavior surfaces.",
            "- decent_agent/tools.ep: Register the new production tool inside the central controller implementation.",
        )
        workflow_path = staging / "workflow.json"
        workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
        workflow["state"] = "investigating"
        workflow_path.write_text(json.dumps(workflow), encoding="utf-8")
        result = self.fx.run("plan-write", "--content-b64", self.b64(sealed_plan))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("operator-sealed deployment/controller path", result.stdout)
        self.assertIn("decent_agent/self_extensions.ep", result.stdout)

    def test_plan_rejects_invented_evaluator_path_with_exact_recovery_guidance(self):
        self.fx.stage()
        staging = self.fx.root / "config" / "improvements" / "staging"
        invalid_plan = PLAN.replace(
            "- feature.marker: Persist the exact production marker value consumed by both verified behavior surfaces.",
            "- tests/test_feature_e2e.py: Implement the evaluator used to prove the new production behavior.",
        )
        workflow_path = staging / "workflow.json"
        workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
        workflow["state"] = "investigating"
        workflow_path.write_text(json.dumps(workflow), encoding="utf-8")
        result = self.fx.run("plan-write", "--content-b64", self.b64(invalid_plan))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("operator-sealed test/gate path", result.stdout)
        self.assertIn("controller owns those artifacts", result.stdout)
        self.assertIn("describe only the desired behavior", result.stdout)

    def test_pre_freeze_workflow_restart_archives_evidence_and_allows_clean_reinvestigation(self):
        self.fx.stage()
        reason = "The accepted plan targets a newly sealed controller path and must be reinvestigated through the bounded extension registry."
        restarted = self.fx.run("restart-staging", "--reason-b64", self.b64(reason))
        self.assertEqual(restarted.returncode, 0, restarted.stdout)
        self.assertIn("IMPROVEMENT_STAGING_RESTART_OK", restarted.stdout)
        self.assertIn("implementation_started=no", restarted.stdout)
        aborted = [
            path
            for path in (self.fx.root / "config" / "improvements" / "aborted").glob("*.json")
            if path.name.count(".") == 1
        ]
        self.assertEqual(len(aborted), 1)
        archived = json.loads(aborted[0].read_text(encoding="utf-8"))
        self.assertEqual(archived["abort_reason"], reason)
        begun = self.fx.run(
            "investigate-begin",
            "--objective-b64",
            self.b64("Reinvestigate and implement the complete marker capability through a legal production extension surface."),
        )
        self.assertEqual(begun.returncode, 0, begun.stdout)

    def test_investigating_workflow_can_be_archived_before_a_plan_exists(self):
        staging = self.fx.root / "config" / "improvements" / "staging"
        objective = "Investigate a complete production capability before planning any implementation or evaluator bytes."
        begun = self.fx.run("investigate-begin", "--objective-b64", self.b64(objective))
        self.assertEqual(begun.returncode, 0, begun.stdout)
        reason = "The investigation exposed an incomplete architecture and must restart before any plan or source mutation."
        restarted = self.fx.run("restart-staging", "--reason-b64", self.b64(reason))
        self.assertEqual(restarted.returncode, 0, restarted.stdout)
        self.assertIn("IMPROVEMENT_STAGING_RESTART_OK", restarted.stdout)
        self.assertIn("implementation_started=no", restarted.stdout)
        archived = [
            path
            for path in (self.fx.root / "config" / "improvements" / "aborted").glob("*.json")
            if path.name.count(".") == 1
        ]
        self.assertEqual(len(archived), 1)
        record = json.loads(archived[0].read_text(encoding="utf-8"))
        self.assertEqual(record["abort_reason"], reason)
        self.assertIn("IMPROVEMENT_INVESTIGATION_OK", begun.stdout)

    def test_late_evaluator_discovery_is_supplemental_and_does_not_invalidate_plan(self):
        self.fx.stage()
        helper = self.fx.root / "production_runner.sh"
        helper.write_text("#!/usr/bin/env bash\nexec /bin/cat \"$@\"\n", encoding="utf-8")
        discovered = self.fx.run(
            "record-discovery",
            "--path-b64",
            self.b64("production_runner.sh"),
            "--mode",
            "read",
        )
        self.assertEqual(discovered.returncode, 0, discovered.stdout)
        self.assertIn("scope=supplemental", discovered.stdout)

        workflow_path = self.fx.root / "config" / "improvements" / "staging" / "workflow.json"
        workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
        self.assertIn("production_runner.sh", [item["path"] for item in workflow["discovery"]])
        self.assertEqual(workflow["plan_discovery_paths"], ["source_one.py", "source_two.py"])

        validated = self.fx.run("validate", "--name", "fixture")
        self.assertEqual(validated.returncode, 0, validated.stdout)
        self.assertIn("STAGING_VALIDATION_OK", validated.stdout)

    def test_legacy_plan_recovers_its_original_discovery_snapshot(self):
        self.fx.stage()
        workflow_path = self.fx.root / "config" / "improvements" / "staging" / "workflow.json"
        workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
        workflow.pop("plan_discovery_paths")
        workflow.pop("plan_discovery_hash")
        workflow_path.write_text(json.dumps(workflow), encoding="utf-8")

        helper = self.fx.root / "late_runner.sh"
        helper.write_text("#!/usr/bin/env bash\nexec /bin/cat \"$@\"\n", encoding="utf-8")
        discovered = self.fx.run(
            "record-discovery",
            "--path-b64",
            self.b64("late_runner.sh"),
            "--mode",
            "read",
        )
        self.assertEqual(discovered.returncode, 0, discovered.stdout)
        validated = self.fx.run("validate", "--name", "fixture")
        self.assertEqual(validated.returncode, 0, validated.stdout)

    def test_evaluator_write_lints_immediately_and_validation_retry_is_fingerprint_aware(self):
        self.fx.stage(regression='''from pathlib import Path
import os

def test_named_behavior():
    root = Path(os.environ["ERNOS_SOURCE_ROOT"])
    marker = root / "feature.marker"
    value = marker.read_text(encoding="utf-8") if marker.exists() else "missing"
    return value

if __name__ == "__main__":
    test_named_behavior()
''')
        invalid = self.fx.run("lint", "--kind", "regression")
        self.assertNotEqual(invalid.returncode, 0)
        self.assertIn("observable assert", invalid.stdout)
        lint_receipt = json.loads(
            (self.fx.root / "config" / "improvements" / "staging" / "lint.json").read_text()
        )
        self.assertEqual(lint_receipt["status"], "failed")

        first = self.fx.run("validate", "--name", "fingerprint_retry")
        second = self.fx.run("validate", "--name", "fingerprint_retry")
        self.assertNotEqual(first.returncode, 0)
        self.assertIn("repeated=1 total=1", first.stdout)
        self.assertIn("repeated=2 total=2", second.stdout)
        validation_receipt = json.loads(
            (self.fx.root / "config" / "improvements" / "staging" / "validation.json").read_text()
        )
        self.assertEqual(validation_receipt["repeat"], 2)

        latest = second
        for _ in range(19):
            latest = self.fx.run("validate", "--name", "fingerprint_retry")
        self.assertNotEqual(latest.returncode, 0)
        self.assertIn("repeated=21 total=21", latest.stdout)
        self.assertNotIn("STAGING_HALTED", latest.stdout)
        self.assertIn("no retry or turn cap", latest.stdout)

        staging = self.fx.root / "config" / "improvements" / "staging"
        (staging / "regression.py").write_text(REGRESSION, encoding="utf-8")
        changed = self.fx.run("validate", "--name", "fingerprint_retry")
        self.assertEqual(changed.returncode, 0, changed.stdout)

    def test_fail_freeze_fix_verify_live_complete_lifecycle(self):
        self.fx.stage()
        validated = self.fx.run("validate", "--name", "feature_marker")
        self.assertEqual(validated.returncode, 0, validated.stdout)
        self.assertIn("STAGING_VALIDATION_OK", validated.stdout)
        frozen = self.fx.run("freeze", "--name", "feature_marker")
        self.assertEqual(frozen.returncode, 0, frozen.stdout)
        self.assertIn("prechange=both_failed_as_required", frozen.stdout)
        active_path = self.fx.root / "config" / "improvements" / "active.json"
        active = json.loads(active_path.read_text(encoding="utf-8"))
        self.assertEqual(active["state"], "frozen")

        blocked = self.fx.run("verify")
        self.assertNotEqual(blocked.returncode, 0)
        self.assertIn("implementation has not started", blocked.stdout)

        (self.fx.root / "feature.marker").write_text("implemented", encoding="utf-8")
        self.assertEqual(self.fx.run("start-implementation").returncode, 0)
        self.assertEqual(self.fx.record_write("feature.marker").returncode, 0)
        verified = self.fx.run("mark-verified")
        self.assertEqual(verified.returncode, 0, verified.stdout)
        live = self.fx.run("live")
        self.assertEqual(live.returncode, 0, live.stdout)
        completed = self.fx.run("complete")
        self.assertEqual(completed.returncode, 0, completed.stdout)
        self.assertFalse(active_path.exists())
        self.assertEqual(self.fx.run("verify").returncode, 0)

        completed_path = next((self.fx.root / "config" / "improvements" / "completed").glob("*.json"))
        completed = json.loads(completed_path.read_text(encoding="utf-8"))
        superseded = self.fx.root / "config" / "improvements" / "superseded"
        superseded.mkdir()
        (superseded / f"{completed['id']}.json").write_text(
            json.dumps(
                {
                    "version": 1,
                    "transaction_id": completed["id"],
                    "acceptance_hash": completed["acceptance_hash"],
                    "regression_hash": completed["regression_hash"],
                    "e2e_hash": completed["e2e_hash"],
                    "reason": "Independent operator evidence proved that this immutable evaluator was non-causal; retain it for provenance but exclude it from promotion decisions.",
                }
            ),
            encoding="utf-8",
        )
        (self.fx.root / "feature.marker").unlink()
        superseded_verify = self.fx.run("verify")
        self.assertEqual(superseded_verify.returncode, 0, superseded_verify.stdout)
        self.assertIn("completed=0", superseded_verify.stdout)
        status = self.fx.run("status")
        self.assertIn("superseded=1", status.stdout)

    def test_completed_improvement_name_closes_duplicate_workflow(self):
        self.fx.stage()
        self.assertEqual(self.fx.freeze_valid("stable_capability").returncode, 0)
        (self.fx.root / "feature.marker").write_text("implemented", encoding="utf-8")
        self.assertEqual(self.fx.run("start-implementation").returncode, 0)
        self.assertEqual(self.fx.record_write("feature.marker").returncode, 0)
        self.assertEqual(self.fx.run("mark-verified").returncode, 0)
        self.assertEqual(self.fx.run("live").returncode, 0)
        self.assertEqual(self.fx.run("complete").returncode, 0)

        self.fx.stage()
        duplicate = self.fx.run(
            "begin",
            "--name",
            "stable_capability",
            "--acceptance-b64",
            self.b64(
                "[feature_marker] The externally observable feature marker contains the exact implemented value.\n"
                "[live_process] A separate live process reads and returns that persisted marker value."
            ),
        )
        self.assertEqual(duplicate.returncode, 0, duplicate.stdout)
        self.assertIn("IMPROVEMENT_ALREADY_COMPLETE", duplicate.stdout)
        self.assertIn("workflow=closed", duplicate.stdout)
        workflow = json.loads(
            (self.fx.root / "config" / "improvements" / "staging" / "workflow.json").read_text()
        )
        self.assertEqual(workflow["state"], "completed")
        self.assertEqual(workflow["resolution"], "already_complete")
        self.assertEqual(workflow["completed_name"], "stable_capability")
        self.assertFalse((self.fx.root / "config" / "improvements" / "active.json").exists())
        self.assertEqual(self.fx.run("verify").returncode, 0)

    def test_completed_public_surface_is_rejected_before_scaffold(self):
        self.fx.stage()
        self.assertEqual(self.fx.freeze_valid("stable_surface").returncode, 0)
        (self.fx.root / "feature.marker").write_text("implemented", encoding="utf-8")
        self.assertEqual(self.fx.run("start-implementation").returncode, 0)
        self.assertEqual(self.fx.record_write("feature.marker").returncode, 0)
        self.assertEqual(self.fx.run("mark-verified").returncode, 0)
        self.assertEqual(self.fx.run("live").returncode, 0)
        self.assertEqual(self.fx.run("complete").returncode, 0)
        completed_path = next(
            (self.fx.root / "config" / "improvements" / "completed").glob("*.json")
        )
        completed = json.loads(completed_path.read_text(encoding="utf-8"))
        completed["planned_surfaces"] = ["aes_distill"]
        completed_path.write_text(json.dumps(completed), encoding="utf-8")

        begun = self.fx.run(
            "investigate-begin",
            "--objective-b64",
            self.b64("Reimplement the exact existing `aes_distill` capability despite its permanent completion receipt."),
        )
        self.assertNotEqual(begun.returncode, 0, begun.stdout)
        self.assertIn("code=FEATURE_ALREADY_EXISTS", begun.stdout)
        workflow = json.loads(
            (self.fx.root / "config" / "improvements" / "staging" / "workflow.json").read_text()
        )
        self.assertEqual(workflow["state"], "completed")
        self.assertFalse((self.fx.root / "config" / "improvements" / "staging" / "plan_body.md").exists())

    def test_completed_surface_is_rejected_before_investigation(self):
        self.fx.stage()
        self.assertEqual(self.fx.freeze_valid("stable_surface").returncode, 0)
        (self.fx.root / "feature.marker").write_text("implemented", encoding="utf-8")
        self.assertEqual(self.fx.run("start-implementation").returncode, 0)
        self.assertEqual(self.fx.record_write("feature.marker").returncode, 0)
        self.assertEqual(self.fx.run("mark-verified").returncode, 0)
        self.assertEqual(self.fx.run("live").returncode, 0)
        self.assertEqual(self.fx.run("complete").returncode, 0)
        completed_path = next(
            (self.fx.root / "config" / "improvements" / "completed").glob("*.json")
        )
        completed = json.loads(completed_path.read_text(encoding="utf-8"))
        completed["planned_surfaces"] = ["already_installed_surface"]
        completed_path.write_text(json.dumps(completed), encoding="utf-8")

        rejected = self.fx.run(
            "investigate-begin",
            "--objective-b64",
            self.b64(
                "Implement a registered tool named `already_installed_surface` with observable output and durable state."
            ),
        )
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("code=FEATURE_ALREADY_EXISTS", rejected.stdout)
        workflow = json.loads(
            (self.fx.root / "config" / "improvements" / "staging" / "workflow.json").read_text()
        )
        self.assertEqual(workflow["state"], "completed")

    def test_completed_public_surface_closes_at_real_execution_boundary(self):
        self.fx.stage()
        self.assertEqual(self.fx.freeze_valid("stable_surface").returncode, 0)
        (self.fx.root / "feature.marker").write_text("implemented", encoding="utf-8")
        self.assertEqual(self.fx.run("start-implementation").returncode, 0)
        self.assertEqual(self.fx.record_write("feature.marker").returncode, 0)
        self.assertEqual(self.fx.run("mark-verified").returncode, 0)
        self.assertEqual(self.fx.run("live").returncode, 0)
        self.assertEqual(self.fx.run("complete").returncode, 0)
        completed_path = next(
            (self.fx.root / "config" / "improvements" / "completed").glob("*.json")
        )
        completed = json.loads(completed_path.read_text(encoding="utf-8"))
        completed["planned_surfaces"] = ["aes_distill"]
        completed_path.write_text(json.dumps(completed), encoding="utf-8")

        begun = self.fx.run(
            "investigate-begin",
            "--objective-b64",
            self.b64("Run a fresh implementation workflow for the already installed aes_distill capability."),
        )
        self.assertEqual(begun.returncode, 0, begun.stdout)
        resolved = self.fx.run(
            "resolve-surface", "--surface-b64", self.b64("aes_distill")
        )
        self.assertEqual(resolved.returncode, 0, resolved.stdout)
        self.assertIn("IMPROVEMENT_ALREADY_COMPLETE", resolved.stdout)
        self.assertIn("workflow=closed", resolved.stdout)
        workflow = json.loads(
            (self.fx.root / "config" / "improvements" / "staging" / "workflow.json").read_text()
        )
        self.assertEqual(workflow["state"], "completed")
        self.assertEqual(workflow["completed_surface"], "aes_distill")

    def test_byte_identical_implementation_write_does_not_advance(self):
        source_plan = PLAN.replace(
            "- feature.marker: Persist the exact production marker value consumed by both verified behavior surfaces.",
            "- source_one.py: Implement the production marker behavior consumed by both verified behavior surfaces.",
        )
        self.fx.stage(
            plan=source_plan,
            planned_files=["source_one.py"],
            e2e=E2E + "\n# production owner: source_one.py\n",
        )
        self.assertEqual(self.fx.freeze_valid("causal_write_only").returncode, 0)
        self.assertEqual(self.fx.run("start-implementation").returncode, 0)
        unchanged = self.fx.record_write("source_one.py")
        self.assertNotEqual(unchanged.returncode, 0)
        self.assertIn("made no production change", unchanged.stdout)
        active = json.loads(
            (self.fx.root / "config" / "improvements" / "active.json").read_text()
        )
        self.assertEqual(active["state"], "frozen")
        self.assertNotIn("implementation_paths", active)

    def test_operator_quarantine_preserves_invalid_frozen_contract(self):
        self.fx.stage()
        self.assertEqual(self.fx.freeze_valid("legacy_invalid_contract").returncode, 0)
        reason = (
            "The previous controller accepted a frozen evaluator that rewards an error sentinel "
            "instead of the desired production behavior; immutable evidence is retained while the active lock is removed."
        )
        quarantined = self.fx.run(
            "quarantine-active", "--reason-b64", self.b64(reason)
        )
        self.assertEqual(quarantined.returncode, 0, quarantined.stdout)
        self.assertIn("frozen_evidence=preserved", quarantined.stdout)
        self.assertFalse(
            (self.fx.root / "config" / "improvements" / "active.json").exists()
        )
        archived = list(
            (self.fx.root / "config" / "improvements" / "aborted").glob("*.json")
        )
        self.assertEqual(len(archived), 1)
        receipt = json.loads(archived[0].read_text())
        self.assertEqual(receipt["state"], "invalidated")
        self.assertEqual(receipt["invalidation_reason"], reason)

    def test_regression_cannot_reward_hack_by_branching_on_phase(self):
        cheating = REGRESSION.replace(
            "def test_feature_marker_contract():",
            'PHASE = os.environ.get("ERNOS_TEST_PHASE", "verify")\n\ndef test_feature_marker_contract():',
        )
        self.fx.stage(regression=cheating)
        result = self.fx.run("validate", "--name", "phase_cheat")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("may not branch on the gate phase", result.stdout)

    def test_regression_cannot_reward_missing_behavior_with_error_sentinel(self):
        cheating = REGRESSION.replace(
            'assert value == "implemented", f"expected implemented marker, got {value!r}"',
            "assert value == 'error_not_implemented'",
        )
        self.fx.stage(regression=cheating)
        result = self.fx.run("validate", "--name", "error_sentinel_cheat")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("asserts a missing/unknown/error state", result.stdout)

    def test_regression_cannot_use_repository_write_denial_as_prechange_evidence(self):
        permission_failure = '''from pathlib import Path

def test_feature_marker():
    with open("repository-owned-proof.tmp", "w", encoding="utf-8") as handle:
        handle.write("manufactured")
    observed = False
    assert observed, "feature behavior is absent"

def test_live_process():
    observed = False
    assert observed, "live behavior is absent"

if __name__ == "__main__":
    test_feature_marker()
'''
        self.fx.stage(regression=permission_failure)
        result = self.fx.run("validate", "--name", "permission_is_not_causality")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("writes scratch data without tempfile ownership", result.stdout)

    def test_tempfile_presence_cannot_hide_repository_or_durable_path_mutation(self):
        disguised_repository_write = '''import os
import tempfile

def test_feature_marker_contract():
    repository_target = "decent_agent/learning.ep"
    with tempfile.TemporaryDirectory() as tmpdir:
        os.remove(repository_target)
    observed = "missing"
    assert observed == "implemented", "feature behavior is absent"

if __name__ == "__main__":
    test_feature_marker_contract()
'''
        self.fx.stage(regression=disguised_repository_write)
        result = self.fx.run("validate", "--name", "tempfile_cannot_mask_repo_write")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("attempts to mutate repository/durable source path", result.stdout)

    def test_runtime_failure_cannot_be_embedded_inside_assertion_output(self):
        contaminated_assertion = '''import subprocess
import sys

def test_feature_marker_contract():
    result = subprocess.run(
        [sys.executable, "-m", "missing.production.surface"],
        capture_output=True,
        text=True,
        check=False,
    )
    observed = result.stdout + result.stderr
    assert "implemented" in observed, f"production output was absent: {observed}"

if __name__ == "__main__":
    test_feature_marker_contract()
'''
        self.fx.stage(regression=contaminated_assertion)
        result = self.fx.run("validate", "--name", "runtime_marker_not_causal")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("failed before reaching its behavioral assertion", result.stdout)

    def test_evaluator_cannot_swallow_production_execution_failure(self):
        swallowed = '''import subprocess

def test_feature_marker_contract():
    try:
        subprocess.run(["missing-production-command"], check=True)
        observed = "implemented"
    except (FileNotFoundError, subprocess.CalledProcessError):
        observed = "missing"
    assert observed == "implemented", "feature behavior is absent"

if __name__ == "__main__":
    test_feature_marker_contract()
'''
        self.fx.stage(regression=swallowed)
        result = self.fx.run("validate", "--name", "swallowed_failure_not_evidence")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("catches or swallows production execution failure", result.stdout)

    def test_prechange_failure_must_reach_behavioral_assertion(self):
        runtime_failure = REGRESSION.replace(
            'root = Path(os.environ["ERNOS_SOURCE_ROOT"])',
            'raise RuntimeError("evaluator broke before checking behavior")\n    root = Path(os.environ["ERNOS_SOURCE_ROOT"])',
        )
        self.fx.stage(regression=runtime_failure)
        result = self.fx.run("validate", "--name", "runtime_error_is_not_causality")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("failed before reaching its behavioral assertion", result.stdout)

    def test_prechange_e2e_runtime_failure_is_rejected_before_freeze(self):
        broken_e2e = E2E.replace(
            "result = subprocess.run",
            "result = missing_runtime_name",
            1,
        )
        self.fx.stage(e2e=broken_e2e)
        result = self.fx.run("validate", "--name", "broken_e2e_runtime")
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("candidate E2E failed before reaching its behavioral assertion", result.stdout)

    def test_acceptance_rejects_test_mechanics_and_mechanical_ids(self):
        mechanical = (
            "[regression] The regression test attempts the request and raises an AssertionError.\n"
            "[e2e] The E2E test verifies that the command succeeds after implementation."
        )
        self.fx.stage(acceptance=mechanical)
        result = self.fx.run("validate", "--name", "mechanical_acceptance")
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("names test machinery", result.stdout)

    def test_acceptance_rejects_unimplemented_state_as_an_outcome(self):
        mechanical = (
            "[tool_availability] The extension registry returns an error for the unregistered aes_distill action.\n"
            "[durable_learning] The supplied lesson is persisted and independently readable from memory."
        )
        self.fx.stage(acceptance=mechanical)
        result = self.fx.run("validate", "--name", "absence_is_not_acceptance")
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("test mechanics or artifact presence", result.stdout)

    def test_plan_rejects_missing_state_evidence_and_inexact_source_paths(self):
        self.fx.stage()
        staging = self.fx.root / "config" / "improvements" / "staging"
        workflow_path = staging / "workflow.json"
        workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
        workflow["state"] = "investigating"
        workflow_path.write_text(json.dumps(workflow), encoding="utf-8")
        negative = PLAN.replace(
            "The regression invokes the `feature_marker_read()` contract against current repository state and fails before implementation.",
            "The regression invokes `feature_marker_read()` and asserts an unknown-command error from current source.",
        )
        result = self.fx.run("plan-write", "--content-b64", self.b64(negative))
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("may not assert the current missing/unknown/error state", result.stdout)

        inexact = PLAN.replace(
            "Create the durable marker with the exact value required by the acceptance contract",
            "Create `missing/source.ep` and the durable marker with the exact value required by the acceptance contract",
        )
        result = self.fx.run("plan-write", "--content-b64", self.b64(inexact))
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("only legal plan-authoring route", result.stdout)

    def test_plan_rejects_inexact_source_paths_before_scaffold_lock(self):
        self.fx.stage()
        staging = self.fx.root / "config" / "improvements" / "staging"
        workflow_path = staging / "workflow.json"
        workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
        workflow["state"] = "investigating"
        workflow_path.write_text(json.dumps(workflow), encoding="utf-8")
        inexact = PLAN.replace(
            "Create the durable marker with the exact value required by the acceptance contract",
            "Create `missing/source.ep` and the durable marker with the exact value required by the acceptance contract",
        )
        result = self.fx.run("plan-write", "--content-b64", self.b64(inexact))
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("uninvestigated or non-planned backticked source path", result.stdout)

    def test_validated_evaluator_can_be_reopened_and_revalidated_before_freeze(self):
        self.fx.stage()
        first = self.fx.run("validate", "--name", "revisable_evaluators")
        self.assertEqual(first.returncode, 0, first.stdout)
        revised = E2E.replace("live E2E passed", "live E2E causal contract passed")
        written = self.fx.run(
            "write-artifact",
            "--kind",
            "e2e",
            "--content-b64",
            self.b64(revised),
        )
        self.assertEqual(written.returncode, 0, written.stdout)
        workflow = json.loads(
            (self.fx.root / "config" / "improvements" / "staging" / "workflow.json").read_text()
        )
        self.assertEqual(workflow["state"], "tests_authoring")
        second = self.fx.run("validate", "--name", "revisable_evaluators")
        self.assertEqual(second.returncode, 0, second.stdout)

    def test_failed_artifact_correction_restores_previous_controller_state(self):
        self.fx.stage()
        staging = self.fx.root / "config" / "improvements" / "staging"
        transport = staging / "transport_template.json"
        transport.write_text('{"surface":"retained"}\n', encoding="utf-8")
        validation = staging / "validation.json"
        validation.write_text('{"status":"retained"}\n', encoding="utf-8")
        before = {
            name: (staging / name).read_bytes()
            for name in ("acceptance.txt", "workflow.json", "validation.json", "transport_template.json")
        }
        rejected = self.fx.run(
            "write-artifact",
            "--kind",
            "acceptance",
            "--content-b64",
            self.b64("def test_wrong_artifact():\n    pass"),
        )
        self.assertNotEqual(rejected.returncode, 0, rejected.stdout)
        self.assertIn("previous staged artifact and controller receipts were restored", rejected.stdout)
        for name, expected in before.items():
            self.assertEqual((staging / name).read_bytes(), expected, name)

    def test_e2e_must_name_the_frozen_production_surface(self):
        unrelated = E2E.replace("feature.marker", "unrelated.marker")
        self.fx.stage(e2e=unrelated)
        result = self.fx.run("validate", "--name", "unrelated_surface")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("exact production surface frozen in the plan", result.stdout)

    def test_registered_tool_template_blocks_http_and_lints_canonical_raw_tcp(self):
        acceptance = (
            "[pattern_extraction] The supplied transcript marker is returned by the registered distillation tool.\n"
            "[durable_persistence] The extracted marker persists and is independently readable from durable memory."
        )
        http_evaluator = '''import requests

def test_pattern_extraction():
    response = requests.post("http://localhost:8080/execute", json={"action": "aes_distill"})
    assert "marker" in response.text

def test_durable_persistence():
    response = requests.post("http://localhost:8080/execute", json={"action": "memory"})
    assert "marker" in response.text
'''
        self.fx.stage(
            regression=http_evaluator,
            e2e=http_evaluator,
            acceptance=acceptance,
            plan=REGISTERED_TOOL_PLAN,
        )
        template = self.fx.run("transport-template")
        self.assertEqual(template.returncode, 0, template.stdout)
        self.assertIn("REGISTERED_TOOL_TRANSPORT_TEMPLATE surface=aes_distill", template.stdout)
        self.assertIn("socket.create_connection", template.stdout)
        self.assertIn("AGENT GET MEMORY", template.stdout)

        rejected = self.fx.run("lint", "--kind", "regression")
        self.assertNotEqual(rejected.returncode, 0, rejected.stdout)
        self.assertIn("substitutes HTTP/curl", rejected.stdout)
        self.assertIn("improvement_test_transport_template", rejected.stdout)

        canonical = '''import base64
import json
import os
import socket
from urllib.parse import urlparse

SURFACE = "aes_distill"
PREFIX = "eval_tool:ok,name:" + SURFACE + ",result_b64:"

def _endpoint():
    raw = os.environ.get("ERNOS_NODE_URL", "http://127.0.0.1:5000")
    parsed = urlparse(raw if "://" in raw else "//" + raw)
    return parsed.hostname or "127.0.0.1", parsed.port or 5000

def _ipc(command):
    with open(os.path.expanduser("~/.ernosdecent/ipc-token"), "r", encoding="utf-8") as handle:
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
    assert response.startswith(PREFIX), "authenticated tool result missing: " + response
    return base64.b64decode(response[len(PREFIX):]).decode("utf-8")

def get_memory():
    return _ipc("AGENT GET MEMORY")

def test_pattern_extraction():
    result = eval_planned_tool("lesson: fixture_marker")
    assert "fixture_marker" in result

def test_durable_persistence():
    eval_planned_tool("lesson: fixture_marker")
    assert "fixture_marker" in get_memory()

if __name__ == "__main__":
    test_pattern_extraction()
    test_durable_persistence()
'''
        regression = self.fx.run(
            "write-artifact", "--kind", "regression", "--content-b64", self.b64(canonical)
        )
        self.assertEqual(regression.returncode, 0, regression.stdout)
        self.assertIn("IMPROVEMENT_TRANSPORT_CANONICALIZED", regression.stdout)
        e2e = self.fx.run(
            "write-artifact", "--kind", "e2e", "--content-b64", self.b64(canonical)
        )
        self.assertEqual(e2e.returncode, 0, e2e.stdout)
        self.assertIn("IMPROVEMENT_TRANSPORT_CANONICALIZED", e2e.stdout)
        staged_regression = (
            self.fx.root / "config" / "improvements" / "staging" / "regression.py"
        ).read_text(encoding="utf-8")
        self.assertIn("SURFACE = 'aes_distill'", staged_regression)
        self.assertIn("chunk = connection.recv(65536)", staged_regression)
        self.assertNotIn("authenticated tool result missing", staged_regression)
        self.assertIn('if __name__ == "__main__":\n    test_pattern_extraction()', staged_regression)

    def test_controller_replaces_corrupted_registered_transport_before_lint(self):
        acceptance = (
            "[pattern_extraction] The supplied transcript marker is returned by the registered distillation tool.\n"
            "[durable_persistence] The extracted marker persists and is independently readable from durable memory."
        )
        corrupt = '''import socket
SURFACE = "aes_distint"

def broken_transport():
    return urlint("bad")

def test_pattern_extraction():
    result = eval_planned_tool("[LESSON: fixture_key | fixture_value]")
    assert "fixture_value" in result

def test_durable_persistence():
    eval_planned_tool("[LESSON: fixture_key | fixture_value]")
    assert "fixture_value" in get_memory()
'''
        self.fx.stage(
            regression=corrupt,
            e2e=corrupt,
            acceptance=acceptance,
            plan=REGISTERED_TOOL_PLAN,
        )
        template = self.fx.run("transport-template")
        self.assertEqual(template.returncode, 0, template.stdout)
        written = self.fx.run(
            "write-artifact", "--kind", "e2e", "--content-b64", self.b64(corrupt)
        )
        self.assertEqual(written.returncode, 0, written.stdout)
        staged = (
            self.fx.root / "config" / "improvements" / "staging" / "e2e.py"
        ).read_text(encoding="utf-8")
        self.assertTrue(staged.startswith("import base64\nimport json\nimport os\nimport socket\n"))
        self.assertIn("SURFACE = 'aes_distill'", staged)
        self.assertNotIn("aes_distint", staged)
        self.assertNotIn("urlint", staged)
        self.assertIn('if __name__ == "__main__":', staged)
        self.assertIn("    test_pattern_extraction()", staged)
        self.assertIn("    test_durable_persistence()", staged)

    def test_discord_retrieval_evaluator_preserves_real_channel_argument(self):
        discord_plan = REGISTERED_TOOL_PLAN.replace(
            "Add a registered transcript-distillation behavior and prove both returned output and durable memory effects through the authenticated production IPC boundary.",
            "Add scavenger_sweep with real Discord retrieval and independently verified durable memory through the authenticated production IPC boundary.",
        ).replace("aes_distill", "scavenger_sweep")
        acceptance = (
            "[channel_retrieval] The configured Discord channel is read through the live bridge and produces an observable sweep result.\n"
            "[durable_persistence] Retrieved knowledge remains independently readable from durable memory."
        )
        wrong = '''def test_channel_retrieval():
    result = eval_planned_tool("[LESSON: fixture_key | fixture_value]")
    assert "processed" in result

def test_durable_persistence():
    result = eval_planned_tool("123456789")
    assert "processed" in result
    assert "memory" in get_memory()
'''
        self.fx.stage(
            regression=wrong,
            e2e=wrong,
            acceptance=acceptance,
            plan=discord_plan,
        )
        workflow_path = self.fx.root / "config" / "improvements" / "staging" / "workflow.json"
        workflow = json.loads(workflow_path.read_text())
        workflow["objective"] = "Implement scavenger_sweep with real Discord retrieval and durable memory."
        workflow_path.write_text(json.dumps(workflow), encoding="utf-8")
        template = self.fx.run("transport-template")
        self.assertEqual(template.returncode, 0, template.stdout)
        self.assertIn("eval_planned_tool(configured_discord_channel())", template.stdout)
        rejected = self.fx.run(
            "write-artifact", "--kind", "e2e", "--content-b64", self.b64(wrong)
        )
        self.assertNotEqual(rejected.returncode, 0, rejected.stdout)
        self.assertIn("must call the real configured channel", rejected.stdout)

        correct = '''def test_channel_retrieval():
    result = eval_planned_tool(configured_discord_channel())
    assert "processed" in result

def test_durable_persistence():
    result = eval_planned_tool(configured_discord_channel())
    assert "processed" in result
    memory = get_memory()
    assert "memory" in memory
'''
        accepted = self.fx.run(
            "write-artifact", "--kind", "e2e", "--content-b64", self.b64(correct)
        )
        self.assertEqual(accepted.returncode, 0, accepted.stdout)
        staged = (
            self.fx.root / "config" / "improvements" / "staging" / "e2e.py"
        ).read_text()
        self.assertIn("def configured_discord_channel():", staged)
        self.assertIn("eval_planned_tool(configured_discord_channel())", staged)

    def test_discord_retrieval_accepts_single_assignment_configured_channel_alias(self):
        discord_plan = REGISTERED_TOOL_PLAN.replace(
            "Add a registered transcript-distillation behavior and prove both returned output and durable memory effects through the authenticated production IPC boundary.",
            "Add scavenger_sweep with real Discord retrieval and independently verified durable memory through the authenticated production IPC boundary.",
        ).replace("aes_distill", "scavenger_sweep")
        acceptance = (
            "[channel_retrieval] The configured Discord channel is read through the live bridge and produces an observable sweep result.\n"
            "[durable_persistence] Retrieved knowledge remains independently readable from durable memory."
        )
        aliased = '''def test_channel_retrieval():
    channel_id = configured_discord_channel()
    result = eval_planned_tool(channel_id)
    assert "processed" in result

def test_durable_persistence():
    channel_id = configured_discord_channel()
    result = eval_planned_tool(channel_id)
    assert "processed" in result
    memory = get_memory()
    assert "memory" in memory
'''
        self.fx.stage(regression=aliased, e2e=aliased, acceptance=acceptance, plan=discord_plan)
        workflow_path = self.fx.root / "config" / "improvements" / "staging" / "workflow.json"
        workflow = json.loads(workflow_path.read_text())
        workflow["objective"] = "Implement scavenger_sweep with real Discord retrieval and durable memory."
        workflow_path.write_text(json.dumps(workflow), encoding="utf-8")
        self.assertEqual(self.fx.run("transport-template").returncode, 0)
        accepted = self.fx.run(
            "write-artifact", "--kind", "e2e", "--content-b64", self.b64(aliased)
        )
        self.assertEqual(accepted.returncode, 0, accepted.stdout)
        staged = (self.fx.root / "config" / "improvements" / "staging" / "e2e.py").read_text()
        self.assertIn("result = eval_planned_tool(channel_id)", staged)

    def test_controller_scaffolds_real_discord_evaluators_from_plan_contract(self):
        objective = (
            "Implement exactly `scavenger_sweep` using real Discord channel retrieval, process "
            "[LESSON: manual_e2e_lesson | verified_value] and "
            "[CORRECTION: manual_e2e_correction | verified_value], and persist both to durable memory."
        )
        begun = self.fx.run("investigate-begin", "--objective-b64", self.b64(objective))
        self.assertEqual(begun.returncode, 0, begun.stdout)
        self.fx.write_discord_interface_sources()
        sources = (
            "source_one.py", "source_two.py", "decent_agent/self_extensions.ep", "decent_agent/memory.ep", "decent_agent/tools.ep",
            "decent_net/bridge_rpc.ep", "decent_net/discord_bridge.py",
        )
        for relative in sources:
            path = self.fx.root / relative
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("# current production interface\n", encoding="utf-8")
            self.assertEqual(self.fx.record_discovery(relative).returncode, 0)
        planned = self.fx.run(
            "plan-scaffold", "--surface-b64", self.b64("scavenger_sweep"),
            "--production-path-b64", self.b64("decent_agent/self_extensions.ep"),
        )
        self.assertEqual(planned.returncode, 0, planned.stdout)
        acceptance = (
            "[channel_retrieval] The configured Discord channel is retrieved through the real bridge.\n"
            "[marker_persistence] The [LESSON: manual_e2e_lesson | verified_value] and "
            "[CORRECTION: manual_e2e_correction | verified_value] values persist in durable memory."
        )
        started = self.fx.run(
            "begin", "--name", "scavenger_sweep", "--acceptance-b64", self.b64(acceptance)
        )
        self.assertEqual(started.returncode, 0, started.stdout)
        generated = self.fx.run("scaffold-evaluators")
        self.assertEqual(generated.returncode, 0, generated.stdout)
        self.assertIn("IMPROVEMENT_EVALUATORS_SCAFFOLDED", generated.stdout)
        for name in ("regression.py", "e2e.py"):
            content = (
                self.fx.root / "config" / "improvements" / "staging" / name
            ).read_text(encoding="utf-8")
            self.assertIn("channel_id = configured_discord_channel()", content)
            self.assertIn("result = eval_planned_tool(channel_id)", content)
            self.assertIn("assert 'scavenger_sweep:ok' in result", content)
            self.assertIn("assert 'manual_e2e_lesson' in memory", content)
            self.assertIn("assert 'manual_e2e_correction' in memory", content)

    def test_plan_scaffold_derives_required_acceptance_for_generic_surface(self):
        objective = (
            "Choose and implement a useful registered capability called novel_status with a real "
            "observable result and independently retrievable durable production effect."
        )
        self.assertEqual(
            self.fx.run("investigate-begin", "--objective-b64", self.b64(objective)).returncode,
            0,
        )
        self.fx.write_registered_interface_sources()
        for relative in ("decent_agent/self_extensions.ep", "decent_agent/memory.ep"):
            self.assertEqual(self.fx.record_discovery(relative).returncode, 0)
        planned = self.fx.run(
            "plan-scaffold", "--surface-b64", self.b64("novel_status"),
            "--production-path-b64", self.b64("decent_agent/self_extensions.ep"),
        )
        self.assertEqual(planned.returncode, 0, planned.stdout)
        workflow = json.loads(
            (self.fx.root / "config" / "improvements" / "staging" / "workflow.json").read_text()
        )
        self.assertEqual(workflow["required_surface"], "novel_status")
        self.assertEqual(workflow["invocation_fixture"], "no_arguments")
        self.assertIn("[observable_result]", workflow["required_acceptance"])
        self.assertIn("[durable_effect]", workflow["required_acceptance"])
        self.assertIn("novel_status:ok", workflow["required_acceptance"])

    def test_marker_transcript_scaffold_uses_one_real_text_argument_without_literal_examples(self):
        objective = (
            "Implement a registered tool named `session_importance_scorer` that analyzes a transcript "
            "for lessons and corrections, returns an observable importance score, and persists its result."
        )
        begun = self.fx.run("investigate-begin", "--objective-b64", self.b64(objective))
        self.assertEqual(begun.returncode, 0, begun.stdout)
        self.fx.write_registered_interface_sources()
        for relative in ("decent_agent/self_extensions.ep", "decent_agent/memory.ep"):
            self.assertEqual(self.fx.record_discovery(relative).returncode, 0)
        planned = self.fx.run(
            "plan-scaffold", "--surface-b64", self.b64("session_importance_scorer"),
            "--production-path-b64", self.b64("decent_agent/self_extensions.ep"),
        )
        self.assertEqual(planned.returncode, 0, planned.stdout)
        workflow_path = self.fx.root / "config" / "improvements" / "staging" / "workflow.json"
        workflow = json.loads(workflow_path.read_text())
        self.assertEqual(workflow["invocation_fixture"], "marker_transcript")
        started = self.fx.run(
            "begin", "--name", "session_importance_scorer",
            "--acceptance-b64", self.b64(workflow["required_acceptance"]),
        )
        self.assertEqual(started.returncode, 0, started.stdout)
        generated = self.fx.run("scaffold-evaluators")
        self.assertEqual(generated.returncode, 0, generated.stdout)
        for name in ("regression.py", "e2e.py"):
            content = (
                self.fx.root / "config" / "improvements" / "staging" / name
            ).read_text(encoding="utf-8")
            self.assertIn("eval_planned_tool('[LESSON: fixture_key | fixture_value]", content)
            self.assertIn("[CORRECTION: correction_key | correction_value]')", content)
            self.assertNotIn("result = eval_planned_tool()", content)

    def test_plan_scaffold_preserves_every_explicit_marker_family_before_persisting_planned_state(self):
        objective = (
            "Implement a registered tool named `session_importance_scorer_v2` that consumes "
            "([DECISION:], [LESSON:], [CORRECTION:]) markers, returns an observable importance "
            "score, and persists every marker family for independent durable retrieval."
        )
        begun = self.fx.run("investigate-begin", "--objective-b64", self.b64(objective))
        self.assertEqual(begun.returncode, 0, begun.stdout)
        self.fx.write_registered_interface_sources()
        for relative in ("decent_agent/self_extensions.ep", "decent_agent/memory.ep"):
            self.assertEqual(self.fx.record_discovery(relative).returncode, 0)
        planned = self.fx.run(
            "plan-scaffold", "--surface-b64", self.b64("session_importance_scorer_v2"),
            "--production-path-b64", self.b64("decent_agent/self_extensions.ep"),
        )
        self.assertEqual(planned.returncode, 0, planned.stdout)
        workflow_path = self.fx.root / "config" / "improvements" / "staging" / "workflow.json"
        workflow = json.loads(workflow_path.read_text())
        acceptance = workflow["required_acceptance"]
        for family in ("CORRECTION", "DECISION", "LESSON"):
            self.assertIn(f"[{family}:", acceptance)
        started = self.fx.run(
            "begin", "--name", "session_importance_scorer_v2",
            "--acceptance-b64", self.b64(acceptance),
        )
        self.assertEqual(started.returncode, 0, started.stdout)
        generated = self.fx.run("scaffold-evaluators")
        self.assertEqual(generated.returncode, 0, generated.stdout)
        for name in ("regression.py", "e2e.py"):
            content = (
                self.fx.root / "config" / "improvements" / "staging" / name
            ).read_text(encoding="utf-8")
            for family in ("CORRECTION", "DECISION", "LESSON"):
                self.assertIn(f"[{family}:", content)

    def test_session_title_lookup_has_owned_path_and_real_two_query_fixture(self):
        objective = (
            "Implement a registered tool named `session_id_lookup` that retrieves the exact session ID "
            "from either a session title or a unique part of its title and persists the result."
        )
        spec = importlib.util.spec_from_file_location("session_lookup_gate", self.fx.manager)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertTrue(module.objective_requires_session_lookup(objective))
        self.assertEqual(module.objective_invocation_fixture(objective), "active_session_title_queries")
        self.assertEqual(
            module.required_objective_production_paths(objective),
            ["decent_agent/self_extensions.ep"],
        )
        self.assertEqual(
            module.required_objective_discovery_paths(objective),
            [
                "decent_agent/self_extensions.ep",
                "decent_agent/memory.ep",
                "decent_agent/session.ep",
            ],
        )

        begun = self.fx.run("investigate-begin", "--objective-b64", self.b64(objective))
        self.assertEqual(begun.returncode, 0, begun.stdout)
        workflow_path = self.fx.root / "config" / "improvements" / "staging" / "workflow.json"
        investigating = json.loads(workflow_path.read_text())
        self.assertEqual(
            investigating["required_production_paths"],
            ["decent_agent/self_extensions.ep"],
        )
        self.fx.write_session_interface_sources()
        for relative in (
            "decent_agent/self_extensions.ep",
            "decent_agent/memory.ep",
            "decent_agent/session.ep",
        ):
            self.assertEqual(self.fx.record_discovery(relative).returncode, 0)
        planned = self.fx.run(
            "plan-scaffold", "--surface-b64", self.b64("session_id_lookup"),
            "--production-path-b64", self.b64("decent_agent/self_extensions.ep"),
        )
        self.assertEqual(planned.returncode, 0, planned.stdout)
        workflow = json.loads(workflow_path.read_text())
        self.assertEqual(workflow["invocation_fixture"], "active_session_title_queries")
        self.assertIn("exact title", workflow["required_acceptance"])
        self.assertIn("unique title substring", workflow["required_acceptance"])
        plan = (
            self.fx.root / "config" / "improvements" / "staging" / "plan_body.md"
        ).read_text()
        self.assertIn("session_manager_resolve_id(sessions_mgr and title_query)", plan)
        self.assertIn("exact active-session title", plan)
        started = self.fx.run(
            "begin", "--name", "session_id_lookup",
            "--acceptance-b64", self.b64(workflow["required_acceptance"]),
        )
        self.assertEqual(started.returncode, 0, started.stdout)
        generated = self.fx.run("scaffold-evaluators")
        self.assertEqual(generated.returncode, 0, generated.stdout)
        for name in ("regression.py", "e2e.py"):
            content = (
                self.fx.root / "config" / "improvements" / "staging" / name
            ).read_text()
            self.assertIn("active_session_title_queries()", content)
            self.assertIn("exact_result = eval_planned_tool(exact_title)", content)
            self.assertIn("result = eval_planned_tool(unique_title)", content)
            self.assertIn("assert session_id in exact_result", content)
            self.assertIn("assert session_id in result", content)
        e2e = (
            self.fx.root / "config" / "improvements" / "staging" / "e2e.py"
        ).read_text()
        self.assertIn("assert unique_title in memory", e2e)

        target = self.fx.root / "decent_agent" / "self_extensions.ep"
        candidate = self.fx.root / "session_lookup_candidate.ep"
        candidate.write_text('''import "session"
import "memory"
define self_extensions_schema returning Str:
    return "- session_id_lookup([title_query]) -> Str"
define self_extensions_action_known with action_name as Str returning Int:
    if action_name equals "session_id_lookup":
        return 1
    return 0
define self_extensions_execute with ctx as Map and action_name as Str and args_list as List returning Str:
    if action_name equals "session_id_lookup":
        if length_list(args_list) != 1:
            return "Error"
        set title_query to get_list(args_list and 0)
        if string_length(title_query) == 0:
            return "Error"
        set memory_mgr to map_get_val(ctx and "memory_mgr")
        set sessions_mgr to map_get_val(ctx and "sessions")
        set resolved_id to session_manager_resolve_id(sessions_mgr and title_query)
        if string_length(resolved_id) == 0:
            return "Error"
        set lookup_value to concat(title_query and concat(" " and resolved_id))
        set ok to memory_store(memory_mgr and 2 and "session_id_lookup" and lookup_value)
        if ok != 0:
            return "Error"
        return concat("session_id_lookup:ok,session_id:" and concat(resolved_id and concat(",query:" and title_query)))
    return "Error"
''', encoding="utf-8")
        module.validate_candidate_objective_contract(workflow, target, candidate)
        broken = self.fx.root / "session_lookup_broken.ep"
        broken.write_text(
            candidate.read_text().replace(
                "set resolved_id to session_manager_resolve_id(sessions_mgr and title_query)",
                'set resolved_id to "hardcoded"',
            ),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(module.GateError, "session-title-lookup"):
            module.validate_candidate_objective_contract(workflow, target, broken)

    def test_session_validator_uses_existing_and_missing_ids_with_durable_boolean_readback(self):
        objective = (
            "Implement a registered tool named `session_id_validator` that accepts an exact session_id "
            "string and returns whether it exists in the system registry, providing a durable integrity check."
        )
        spec = importlib.util.spec_from_file_location("session_validator_gate", self.fx.manager)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertTrue(module.objective_requires_session_validation(objective))
        self.assertEqual(
            module.objective_invocation_fixture(objective),
            "existing_and_missing_session_ids",
        )
        self.assertEqual(
            module.required_objective_discovery_paths(objective),
            [
                "decent_agent/self_extensions.ep",
                "decent_agent/memory.ep",
                "decent_agent/session.ep",
                "decent_agent/tools.ep",
            ],
        )
        begun = self.fx.run("investigate-begin", "--objective-b64", self.b64(objective))
        self.assertEqual(begun.returncode, 0, begun.stdout)
        self.fx.write_session_interface_sources()
        for relative in (
            "decent_agent/self_extensions.ep",
            "decent_agent/memory.ep",
            "decent_agent/session.ep",
            "decent_agent/tools.ep",
        ):
            self.assertEqual(self.fx.record_discovery(relative).returncode, 0)
        planned = self.fx.run(
            "plan-scaffold", "--surface-b64", self.b64("session_id_validator"),
            "--production-path-b64", self.b64("decent_agent/self_extensions.ep"),
        )
        self.assertEqual(planned.returncode, 0, planned.stdout)
        workflow_path = self.fx.root / "config" / "improvements" / "staging" / "workflow.json"
        workflow = json.loads(workflow_path.read_text())
        self.assertEqual(workflow["invocation_fixture"], "existing_and_missing_session_ids")
        self.assertIn("exists:true", workflow["required_acceptance"])
        self.assertIn("exists:false", workflow["required_acceptance"])
        started = self.fx.run(
            "begin", "--name", "session_id_validator",
            "--acceptance-b64", self.b64(workflow["required_acceptance"]),
        )
        self.assertEqual(started.returncode, 0, started.stdout)
        generated = self.fx.run("scaffold-evaluators")
        self.assertEqual(generated.returncode, 0, generated.stdout)
        for name in ("regression.py", "e2e.py"):
            content = (self.fx.root / "config" / "improvements" / "staging" / name).read_text()
            self.assertIn("existing_and_missing_session_ids()", content)
            self.assertIn("eval_planned_tool(existing_id)", content)
            self.assertIn("eval_planned_tool(missing_id)", content)
            self.assertIn("assert 'exists:true' in existing_result", content)
            self.assertIn("assert 'exists:false' in missing_result", content)
        e2e = (self.fx.root / "config" / "improvements" / "staging" / "e2e.py").read_text()
        self.assertIn("assert existing_id in memory", e2e)
        self.assertIn("assert 'exists:true' in memory", e2e)

        source = '''define self_extensions_schema returning Str:
    return "- session_id_validator([session_id]) -> Str"
define self_extensions_action_known with action_name as Str returning Int:
    if action_name equals "session_id_validator":
        return 1
    return 0
define self_extensions_execute with ctx as Map and action_name as Str and args_list as List returning Str:
    if action_name equals "session_id_validator":
        if length_list(args_list) != 1:
            return "Error"
        set session_id to get_list(args_list and 0)
        if string_length(session_id) == 0 or else string_index_of(session_id and "/") >= 0 or else string_index_of(session_id and "\\\\") >= 0:
            return "Error"
        set memory_mgr to map_get_val(ctx and "memory_mgr")
        set sessions_mgr to map_get_val(ctx and "sessions")
        set sessions_map to map_get_val(sessions_mgr and "sessions")
        set exists_flag to map_contains(sessions_map and session_id)
        set exists_text to "false"
        if exists_flag != 0:
            set exists_text to "true"
        set validation_value to concat(session_id and concat(",exists:" and exists_text))
        set result to concat("session_id_validator:ok,session_id:" and concat(session_id and concat(",exists:" and exists_text)))
        set ok to memory_store(memory_mgr and 2 and "session_id_validator" and validation_value)
        if ok != 0:
            return "Error"
        return result
    return "Error"
'''
        target = self.fx.root / "decent_agent" / "self_extensions.ep"
        target.write_text(source, encoding="utf-8")
        candidate = self.fx.root / "session_validator_candidate.ep"
        candidate.write_text(source, encoding="utf-8")
        module.validate_candidate_objective_contract(workflow, target, candidate)
        broken = self.fx.root / "session_validator_broken.ep"
        broken.write_text(source.replace("map_contains(sessions_map and session_id)", "1"), encoding="utf-8")
        with self.assertRaisesRegex(module.GateError, "session-validation"):
            module.validate_candidate_objective_contract(workflow, target, broken)

    def test_session_metadata_lookup_tests_real_fields_and_missing_id(self):
        objective = (
            "Implement a registered tool named `session_id_lookup` that verifies whether a specific "
            "session ID exists in the runtime registry and returns its metadata if found, or a clear error if not."
        )
        spec = importlib.util.spec_from_file_location("session_metadata_gate", self.fx.manager)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertTrue(module.objective_requires_session_metadata_lookup(objective))
        self.assertEqual(
            module.objective_invocation_fixture(objective),
            "existing_missing_session_metadata",
        )
        transport = module.registered_tool_transport_source("session_id_lookup")
        self.assertIn("complete = []", transport)
        self.assertIn("if item[0] == active", transport)
        self.assertIn("no persisted session has complete title/model/messages metadata", transport)
        self.assertIn('print("EVAL_BOUNDARY_OK name=" + SURFACE)', transport)
        self.assertTrue(
            module.registered_tool_boundary_reached(
                "EVAL_BOUNDARY_OK name=session_id_lookup\nAssertionError: desired result absent",
                "session_id_lookup",
            )
        )
        self.assertFalse(
            module.registered_tool_boundary_reached(
                "AssertionError: no persisted session has complete title/model/messages metadata",
                "session_id_lookup",
            )
        )
        begun = self.fx.run("investigate-begin", "--objective-b64", self.b64(objective))
        self.assertEqual(begun.returncode, 0, begun.stdout)
        self.fx.write_session_interface_sources()
        for relative in (
            "decent_agent/self_extensions.ep",
            "decent_agent/memory.ep",
            "decent_agent/session.ep",
            "decent_agent/tools.ep",
        ):
            self.assertEqual(self.fx.record_discovery(relative).returncode, 0)
        planned = self.fx.run(
            "plan-scaffold", "--surface-b64", self.b64("session_id_lookup"),
            "--production-path-b64", self.b64("decent_agent/self_extensions.ep"),
        )
        self.assertEqual(planned.returncode, 0, planned.stdout)
        workflow_path = self.fx.root / "config" / "improvements" / "staging" / "workflow.json"
        workflow = json.loads(workflow_path.read_text())
        self.assertEqual(workflow["invocation_fixture"], "existing_missing_session_metadata")
        self.assertIn("title", workflow["required_acceptance"])
        self.assertIn("model", workflow["required_acceptance"])
        self.assertIn("records count", workflow["required_acceptance"])
        self.assertIn("session_id_lookup:not_found", workflow["required_acceptance"])
        started = self.fx.run(
            "begin", "--name", "session_id_lookup",
            "--acceptance-b64", self.b64(workflow["required_acceptance"]),
        )
        self.assertEqual(started.returncode, 0, started.stdout)
        generated = self.fx.run("scaffold-evaluators")
        self.assertEqual(generated.returncode, 0, generated.stdout)
        for name in ("regression.py", "e2e.py"):
            content = (self.fx.root / "config" / "improvements" / "staging" / name).read_text()
            self.assertIn("existing_missing_session_metadata()", content)
            self.assertIn("assert title in existing_result", content)
            self.assertIn("assert model in existing_result", content)
            self.assertIn("assert ('records:' + str(records)) in existing_result", content)
            self.assertIn("assert 'session_id_lookup:not_found' in missing_result", content)
        e2e = (self.fx.root / "config" / "improvements" / "staging" / "e2e.py").read_text()
        self.assertIn("assert title in memory", e2e)
        self.assertIn("assert model in memory", e2e)

        source = '''define self_extensions_schema returning Str:
    return "- session_id_lookup([session_id]) -> Str"
define self_extensions_action_known with action_name as Str returning Int:
    if action_name equals "session_id_lookup":
        return 1
    return 0
define self_extensions_execute with ctx as Map and action_name as Str and args_list as List returning Str:
    if action_name equals "session_id_lookup":
        if length_list(args_list) != 1:
            return "Error"
        set session_id to get_list(args_list and 0)
        if string_length(session_id) == 0 or else string_index_of(session_id and "/") >= 0 or else string_index_of(session_id and "\\\\") >= 0:
            return "Error"
        set memory_mgr to map_get_val(ctx and "memory_mgr")
        set sessions_mgr to map_get_val(ctx and "sessions")
        set sessions_map to map_get_val(sessions_mgr and "sessions")
        if map_contains(sessions_map and session_id) == 0:
            return concat("session_id_lookup:not_found,session_id:" and session_id)
        set sess to map_get_val(sessions_map and session_id)
        set title to map_get_val(sess and "title")
        set model to map_get_val(sess and "model")
        set messages to map_get_val(sess and "messages")
        set record_count to length_list(messages)
        set metadata_value to concat(session_id and concat(title and concat(model and int_to_string(record_count))))
        set ok to memory_store(memory_mgr and 2 and "session_id_lookup" and metadata_value)
        if ok != 0:
            return "Error"
        return concat("session_id_lookup:ok,session_id:" and concat(session_id and concat(",title:" and concat(title and concat(",model:" and concat(model and concat(",records:" and int_to_string(record_count))))))))
    return "Error"
'''
        target = self.fx.root / "decent_agent" / "self_extensions.ep"
        target.write_text(source, encoding="utf-8")
        candidate = self.fx.root / "session_metadata_candidate.ep"
        candidate.write_text(source, encoding="utf-8")
        module.validate_candidate_objective_contract(workflow, target, candidate)
        broken = self.fx.root / "session_metadata_broken.ep"
        broken.write_text(source.replace('map_get_val(sess and "model")', '"hardcoded"'), encoding="utf-8")
        with self.assertRaisesRegex(module.GateError, "session-metadata"):
            module.validate_candidate_objective_contract(workflow, target, broken)

    def test_session_summary_contract_uses_live_session_and_independent_readback(self):
        objective = (
            "Implement exactly `session_summary_generator`: it takes a session ID, retrieves the full "
            "persisted transcript, creates a structured session summary, and persists it to durable memory."
        )
        begun = self.fx.run("investigate-begin", "--objective-b64", self.b64(objective))
        self.assertEqual(begun.returncode, 0, begun.stdout)
        self.fx.write_session_interface_sources()
        for relative in (
            "source_one.py",
            "source_two.py",
            "decent_agent/self_extensions.ep",
            "decent_agent/session.ep",
            "decent_agent/memory.ep",
            "decent_agent/tools.ep",
        ):
            self.assertEqual(self.fx.record_discovery(relative).returncode, 0)
        planned = self.fx.run(
            "plan-scaffold", "--surface-b64", self.b64("session_summary_generator"),
            "--production-path-b64", self.b64("decent_agent/self_extensions.ep"),
        )
        self.assertEqual(planned.returncode, 0, planned.stdout)
        workflow_path = self.fx.root / "config" / "improvements" / "staging" / "workflow.json"
        workflow = json.loads(workflow_path.read_text())
        self.assertEqual(workflow["invocation_fixture"], "active_session_id")
        self.assertIn("nonzero records count", workflow["required_acceptance"])
        started = self.fx.run(
            "begin", "--name", "session_summary_generator",
            "--acceptance-b64", self.b64(workflow["required_acceptance"]),
        )
        self.assertEqual(started.returncode, 0, started.stdout)
        generated = self.fx.run("scaffold-evaluators")
        self.assertEqual(generated.returncode, 0, generated.stdout)
        regression = (
            self.fx.root / "config" / "improvements" / "staging" / "regression.py"
        ).read_text()
        e2e = (
            self.fx.root / "config" / "improvements" / "staging" / "e2e.py"
        ).read_text()
        for content in (regression, e2e):
            self.assertIn("session_id = active_session_id()", content)
            self.assertIn("result = eval_planned_tool(session_id)", content)
            self.assertIn('assert "records:0" not in result', content)
        self.assertNotIn("memory = get_memory()", regression)
        self.assertIn("memory = get_memory()", e2e)
        self.assertIn("assert 'session_summary_generator' in memory", e2e)
        self.assertIn("assert session_id in memory", e2e)
        plan = (
            self.fx.root / "config" / "improvements" / "staging" / "plan_body.md"
        ).read_text()
        self.assertIn('set sessions_mgr to map_get_val(ctx and "sessions")', plan)
        self.assertIn('set record_count to length_list(messages)', plan)
        self.assertIn('map_get_val(msg_map and "content")', plan)
        self.assertIn(
            'memory_store(memory_mgr and 2 and "session_summary_generator" and summary_value)',
            plan,
        )

        spec = importlib.util.spec_from_file_location("session_contract_gate", self.fx.manager)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        target = self.fx.root / "decent_agent" / "self_extensions.ep"
        candidate = self.fx.root / "session_candidate.ep"
        candidate.write_text(
            'define self_extensions_schema returning Str:\n'
            '    return "- session_summary_generator([session_id]) -> Str"\n'
            'define self_extensions_execute with ctx as Map and action_name as Str and args_list as List returning Str:\n'
            '    if action_name equals "session_summary_generator":\n'
            '        if length_list(args_list) != 1:\n'
            '            return "Error"\n'
            '        set session_id to get_list(args_list and 0)\n'
            '        if string_length(session_id) == 0 or else string_index_of(session_id and "/") >= 0 or else string_index_of(session_id and "\\\\") >= 0:\n'
            '            return "Error"\n'
            '        set runtime_sessions to map_get_val(ctx and "sessions")\n'
            '        set loaded_by_id to map_get_val(runtime_sessions and "sessions")\n'
            '        if map_contains(loaded_by_id and session_id) == 0:\n'
            '            return "Error"\n'
            '        set session_record to map_get_val(loaded_by_id and session_id)\n'
            '        set transcript_items to map_get_val(session_record and "messages")\n'
            '        set total_records to length_list(transcript_items)\n'
            '        set turn to get_list(transcript_items and 0)\n'
            '        set content to map_get_val(turn and "content")\n'
            '        set summary_value to concat(session_id and content)\n'
            '        set ok to memory_store(memory_mgr and 2 and "session_summary_generator" and summary_value)\n'
            '        if ok != 0:\n'
            '            return "Error"\n'
            '        return concat("session_summary_generator:ok,session_id:" and session_id)\n'
            '    return "Error"\n',
            encoding="utf-8",
        )
        module.validate_candidate_objective_contract(
            {
                "objective": objective,
                "planned_files": ["decent_agent/self_extensions.ep"],
            },
            target,
            candidate,
        )
        wrong_candidate = self.fx.root / "wrong_session_candidate.ep"
        wrong_candidate.write_text(
            candidate.read_text(encoding="utf-8")
            .replace('set total_records to length_list(transcript_items)', 'set total_records to decision_count + task_count')
            .replace('map_get_val(turn and "content")', 'map_get_val(turn and "text")'),
            encoding="utf-8",
        )
        with self.assertRaises(module.GateError) as caught:
            module.validate_candidate_objective_contract(
                {
                    "objective": objective,
                    "planned_files": ["decent_agent/self_extensions.ep"],
                },
                target,
                wrong_candidate,
            )
        self.assertIn("session-transcript extension candidate", str(caught.exception))
        self.assertIn("decision_count + task_count", str(caught.exception))

    def test_selected_session_label_contract_ignores_excluded_summary_name(self):
        objective = '''[IMMUTABLE USER REQUEST]
Choose a fresh capability. Do not choose session_summary_generator.
[/IMMUTABLE USER REQUEST]

[CONCRETE FEATURE SELECTED BY ECHO]
Implement a registered tool named `session_checkpoint_labeler` that attaches and persists an explicit human-readable label to a specific session ID.
[/CONCRETE FEATURE SELECTED BY ECHO]'''
        spec = importlib.util.spec_from_file_location("session_label_gate", self.fx.manager)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertFalse(module.objective_requires_session_transcript(objective))
        self.assertTrue(module.objective_requires_session_label(objective))
        self.assertEqual(module.objective_callable_surfaces(objective), ["session_checkpoint_labeler"])

        begun = self.fx.run("investigate-begin", "--objective-b64", self.b64(objective))
        self.assertEqual(begun.returncode, 0, begun.stdout)
        self.fx.write_session_interface_sources()
        for relative in (
            "source_one.py", "source_two.py", "decent_agent/self_extensions.ep",
            "decent_agent/session.ep", "decent_agent/memory.ep", "decent_agent/tools.ep",
        ):
            self.assertEqual(self.fx.record_discovery(relative).returncode, 0)
        planned = self.fx.run(
            "plan-scaffold", "--surface-b64", self.b64("session_checkpoint_labeler"),
            "--production-path-b64", self.b64("decent_agent/self_extensions.ep"),
        )
        self.assertEqual(planned.returncode, 0, planned.stdout)
        workflow_path = self.fx.root / "config" / "improvements" / "staging" / "workflow.json"
        workflow = json.loads(workflow_path.read_text())
        self.assertEqual(workflow["invocation_fixture"], "active_session_id_and_label")
        self.assertIn("exact session ID and label", workflow["required_acceptance"])
        self.assertNotIn("records count", workflow["required_acceptance"])
        plan = (self.fx.root / "config" / "improvements" / "staging" / "plan_body.md").read_text()
        self.assertIn("exactly two arguments, `session_id` and `label`", plan)
        self.assertIn(
            'memory_store(memory_mgr and 2 and "session_checkpoint_labeler" and label_value)', plan
        )

        started = self.fx.run(
            "begin", "--name", "session_checkpoint_labeler",
            "--acceptance-b64", self.b64(workflow["required_acceptance"]),
        )
        self.assertEqual(started.returncode, 0, started.stdout)
        generated = self.fx.run("scaffold-evaluators")
        self.assertEqual(generated.returncode, 0, generated.stdout)
        for name in ("regression.py", "e2e.py"):
            content = (
                self.fx.root / "config" / "improvements" / "staging" / name
            ).read_text()
            self.assertIn('label = "codex-e2e-checkpoint-label"', content)
            self.assertIn("result = eval_planned_tool(session_id, label)", content)
            self.assertIn("assert session_id in result", content)
            self.assertIn("assert label in result", content)
        e2e = (
            self.fx.root / "config" / "improvements" / "staging" / "e2e.py"
        ).read_text()
        self.assertIn("assert session_id in memory", e2e)
        self.assertIn("assert label in memory", e2e)

        target = self.fx.root / "decent_agent" / "self_extensions.ep"
        target.write_text(
            'define shared_extension_helper returning Int:\n    return 0\n\n'
            + target.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        candidate = self.fx.root / "session_label_candidate.ep"
        candidate.write_text('''define shared_extension_helper returning Int:
    return 1

define self_extensions_schema returning Str:
    return "- session_checkpoint_labeler([session_id, label]) -> Str"
define self_extensions_action_known with action_name as Str returning Int:
    if action_name equals "session_checkpoint_labeler":
        return 1
    return 0
define self_extensions_execute with ctx as Map and action_name as Str and args_list as List returning Str:
    if action_name equals "session_checkpoint_labeler":
        if length_list(args_list) != 2:
            return "Error"
        set session_id to get_list(args_list and 0)
        set label to get_list(args_list and 1)
        if string_length(session_id) == 0 or else string_index_of(session_id and "/") >= 0 or else string_index_of(session_id and "\\\\") >= 0:
            return "Error"
        if string_length(label) == 0:
            return "Error"
        set memory_mgr to map_get_val(ctx and "memory_mgr")
        set sessions_mgr to map_get_val(ctx and "sessions")
        set sessions_map to map_get_val(sessions_mgr and "sessions")
        if map_contains(sessions_map and session_id) == 0:
            return "Error"
        set label_value to concat(session_id and label)
        set ok to memory_store(memory_mgr and 2 and "session_checkpoint_labeler" and label_value)
        if ok != 0:
            return "Error"
        return concat("session_checkpoint_labeler:ok,session_id:" and concat(session_id and concat(",label:" and label)))
    return "Error"
''', encoding="utf-8")
        with self.assertRaisesRegex(module.GateError, "changed_existing_helpers=shared_extension_helper"):
            module.validate_candidate_objective_contract(workflow, target, candidate)
        rules = module.normalize_candidate_dialect(workflow, candidate, target)
        self.assertIn("existing_helper_preserved:shared_extension_helper", rules)
        self.assertIn("return 0", candidate.read_text(encoding="utf-8"))
        module.validate_candidate_objective_contract(workflow, target, candidate)

    def test_registered_evaluator_rejects_unittest_methods_with_exact_repair(self):
        acceptance = (
            "[pattern_extraction] The supplied transcript marker is returned by the registered distillation tool.\n"
            "[durable_persistence] The extracted marker persists and is independently readable from durable memory."
        )
        class_wrapped = '''import unittest

class TestDistill(unittest.TestCase):
    def test_pattern_extraction(self):
        result = eval_planned_tool("aes_distill", ["[LESSON: fixture_key | fixture_value]"])
        self.assertIn("fixture_value", result)

    def test_durable_persistence(self):
        self.assertIn("fixture_value", get_memory())
'''
        self.fx.stage(
            regression=class_wrapped,
            e2e=class_wrapped,
            acceptance=acceptance,
            plan=REGISTERED_TOOL_PLAN,
        )
        template = self.fx.run("transport-template")
        self.assertEqual(template.returncode, 0, template.stdout)
        rejected = self.fx.run(
            "write-artifact", "--kind", "regression", "--content-b64", self.b64(class_wrapped)
        )
        self.assertNotEqual(rejected.returncode, 0, rejected.stdout)
        self.assertIn("standalone top-level functions", rejected.stdout)
        self.assertIn("unittest classes and nested test methods", rejected.stdout)
        self.assertIn('eval_planned_tool("[LESSON:', rejected.stdout)

    def test_registered_evaluator_rejects_repassing_bound_surface_or_list(self):
        acceptance = (
            "[pattern_extraction] The supplied transcript marker is returned by the registered distillation tool.\n"
            "[durable_persistence] The extracted marker persists and is independently readable from durable memory."
        )
        wrong_surface_arg = '''def test_pattern_extraction():
    result = eval_planned_tool("aes_distill", ["[LESSON: fixture_key | fixture_value]"])
    assert "fixture_value" in result

def test_durable_persistence():
    assert "fixture_value" in get_memory()
'''
        self.fx.stage(
            regression=wrong_surface_arg,
            e2e=wrong_surface_arg,
            acceptance=acceptance,
            plan=REGISTERED_TOOL_PLAN,
        )
        self.assertEqual(self.fx.run("transport-template").returncode, 0)
        rejected = self.fx.run(
            "write-artifact", "--kind", "regression", "--content-b64", self.b64(wrong_surface_arg)
        )
        self.assertNotEqual(rejected.returncode, 0, rejected.stdout)
        self.assertIn("passes the already-bound surface", rejected.stdout)

        wrong_list_arg = wrong_surface_arg.replace(
            'eval_planned_tool("aes_distill", ["[LESSON: fixture_key | fixture_value]"])',
            'eval_planned_tool(["[LESSON: fixture_key | fixture_value]"])',
        )
        rejected = self.fx.run(
            "write-artifact", "--kind", "regression", "--content-b64", self.b64(wrong_list_arg)
        )
        self.assertNotEqual(rejected.returncode, 0, rejected.stdout)
        self.assertIn("wraps registered-tool arguments in an extra list", rejected.stdout)

    def test_e2e_must_cover_every_explicit_acceptance_marker_family(self):
        acceptance = (
            "[transcript_parse] The supplied lesson and correction markers are both processed.\n"
            "[durable_memory] Every extracted marker value persists and is independently readable."
        )
        marker_plan = REGISTERED_TOOL_PLAN.replace(
            "Add a registered transcript-distillation behavior and prove both returned output and durable memory effects through the authenticated production IPC boundary.",
            "Extract every [LESSON: key | value] and [CORRECTION: key | value] marker and persist both through the authenticated production IPC boundary.",
        )
        regression = '''def test_transcript_parse():
    result = eval_planned_tool("[LESSON: lesson_key | lesson_value]")
    assert "processed" in result

def test_durable_memory():
    assert "lesson_value" in get_memory()
'''
        e2e_missing_correction = '''def test_transcript_parse():
    result = eval_planned_tool("[LESSON: lesson_key | lesson_value]")
    assert "processed" in result

def test_durable_memory():
    eval_planned_tool("[LESSON: durable_key | durable_value]")
    assert "durable_value" in get_memory()
'''
        self.fx.stage(
            regression=regression,
            e2e=e2e_missing_correction,
            acceptance=acceptance,
            plan=marker_plan,
        )
        self.assertEqual(self.fx.run("transport-template").returncode, 0)
        self.assertEqual(
            self.fx.run(
                "write-artifact", "--kind", "regression", "--content-b64", self.b64(regression)
            ).returncode,
            0,
        )
        rejected = self.fx.run(
            "write-artifact",
            "--kind",
            "e2e",
            "--content-b64",
            self.b64(e2e_missing_correction),
        )
        self.assertNotEqual(rejected.returncode, 0, rejected.stdout)
        self.assertIn("omits explicit input marker", rejected.stdout)
        self.assertIn("[CORRECTION: ...]", rejected.stdout)

    def test_e2e_binds_explicit_output_and_exact_marker_memory_evidence(self):
        acceptance = (
            "[extract_lesson] The [LESSON: key | value] marker is extracted and persisted durably.\n"
            "[extract_correction] The [CORRECTION: key | value] marker is extracted and persisted durably.\n"
            "[retrieval_verification] Every concrete marker key and value remains independently readable."
        )
        marker_plan = REGISTERED_TOOL_PLAN.replace(
            "Add a registered transcript-distillation behavior and prove both returned output and durable memory effects through the authenticated production IPC boundary.",
            "Extract [LESSON: lesson_probe | lesson_value] and [CORRECTION: correction_probe | correction_value], then assert desired `processed` output and durable memory evidence.",
        )
        missing_output = '''def test_extract_lesson():
    out = eval_planned_tool("[LESSON: lesson_probe | lesson_value] [CORRECTION: correction_probe | correction_value]")
    assert "lesson_probe" in out

def test_extract_correction():
    memory = get_memory()
    assert "lesson_probe" in memory and "lesson_value" in memory

def test_retrieval_verification():
    memory = get_memory()
    assert "correction_probe" in memory and "correction_value" in memory
'''
        self.fx.stage(e2e=missing_output, acceptance=acceptance, plan=marker_plan)
        workflow_path = self.fx.root / "config" / "improvements" / "staging" / "workflow.json"
        workflow = json.loads(workflow_path.read_text())
        workflow["objective"] = marker_plan.split("## Investigation Findings", 1)[0]
        workflow_path.write_text(json.dumps(workflow), encoding="utf-8")
        self.assertEqual(self.fx.run("transport-template").returncode, 0)
        rejected_output = self.fx.run(
            "write-artifact", "--kind", "e2e", "--content-b64", self.b64(missing_output)
        )
        self.assertNotEqual(rejected_output.returncode, 0, rejected_output.stdout)
        self.assertIn("explicit desired output", rejected_output.stdout)
        self.assertIn("processed", rejected_output.stdout)

        missing_values = missing_output.replace(
            'assert "lesson_probe" in out', 'assert "processed" in out'
        ).replace(
            'assert "lesson_probe" in memory and "lesson_value" in memory',
            'assert "lesson_probe" in memory',
        ).replace(
            'assert "correction_probe" in memory and "correction_value" in memory',
            'assert "correction_probe" in memory',
        )
        rejected_memory = self.fx.run(
            "write-artifact", "--kind", "e2e", "--content-b64", self.b64(missing_values)
        )
        self.assertNotEqual(rejected_memory.returncode, 0, rejected_memory.stdout)
        self.assertIn("against get_memory", rejected_memory.stdout)
        self.assertIn("LESSON:lesson_value", rejected_memory.stdout)
        self.assertIn("CORRECTION:correction_value", rejected_memory.stdout)

    def test_registered_evaluator_write_requires_current_transport_receipt(self):
        acceptance = (
            "[pattern_extraction] The supplied transcript marker is returned by the registered distillation tool.\n"
            "[durable_persistence] The extracted marker persists and is independently readable from durable memory."
        )
        behavior = '''def test_pattern_extraction():
    result = eval_planned_tool("[LESSON: fixture_key | fixture_value]")
    assert "fixture_value" in result

def test_durable_persistence():
    eval_planned_tool("[LESSON: fixture_key | fixture_value]")
    assert "fixture_value" in get_memory()
'''
        self.fx.stage(
            regression=behavior,
            e2e=behavior,
            acceptance=acceptance,
            plan=REGISTERED_TOOL_PLAN,
        )
        rejected = self.fx.run(
            "write-artifact", "--kind", "regression", "--content-b64", self.b64(behavior)
        )
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("locked until improvement_test_transport_template", rejected.stdout)

    def test_registered_evaluator_rejects_asserting_current_error_state(self):
        acceptance = (
            "[pattern_extraction] The supplied transcript marker is returned by the registered distillation tool.\n"
            "[durable_persistence] The extracted marker persists and is independently readable from durable memory."
        )
        wrong_outcome = '''def test_pattern_extraction():
    result = eval_planned_tool("[LESSON: fixture_key | fixture_value]")
    assert "unregistered" in result

def test_durable_persistence():
    result = eval_planned_tool("[LESSON: fixture_key | fixture_value]")
    assert "error:" in result
'''
        self.fx.stage(
            regression=wrong_outcome,
            e2e=wrong_outcome,
            acceptance=acceptance,
            plan=REGISTERED_TOOL_PLAN,
        )
        template = self.fx.run("transport-template")
        self.assertEqual(template.returncode, 0, template.stdout)
        rejected = self.fx.run(
            "write-artifact", "--kind", "regression", "--content-b64", self.b64(wrong_outcome)
        )
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("asserts a missing/unknown/error state", rejected.stdout)

    def test_semantically_empty_success_contract_is_rejected(self):
        shallow_regression = '''import importlib.util

def test_module_presence():
    module = importlib.util.find_spec("decent_agent.synthesis")
    assert module is not None, "synthesis module must exist"

if __name__ == "__main__":
    test_module_presence()
'''
        shallow_e2e = '''import subprocess
import sys

def test_process_reports_success():
    result = subprocess.run([sys.executable, "-c", "print('success')"], capture_output=True, text=True)
    assert result.returncode == 0
    assert result.stdout.strip() == "success"

if __name__ == "__main__":
    test_process_reports_success()
'''
        self.fx.stage(
            regression=shallow_regression,
            e2e=shallow_e2e,
            acceptance="[transcript_parse] The synthesis engine parses the supplied session transcript into structured events.\n[lesson_extract] It extracts the expected lesson from those events.\n[graph_edges] It creates the expected graph edges.\n[durable_store] It commits lessons and edges durably.",
        )
        result = self.fx.run("validate", "--name", "shallow_success")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("do not map every acceptance criterion", result.stdout)
        self.assertIn("transcript_parse", result.stdout)

    def test_literal_assertions_and_incomplete_artifacts_are_rejected(self):
        literal = REGRESSION.replace(
            'assert value == "implemented", f"expected implemented marker, got {value!r}"',
            "assert True, 'always green'",
        )
        self.fx.stage(regression=literal)
        result = self.fx.run("validate", "--name", "literal_assert")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("literal assert", result.stdout)

        self.fx.stage(acceptance="[synthesis_result] Implement a placeholder synthesis result exposed by the live process.\n[durable_result] Persist that result for later retrieval.")
        result = self.fx.run("validate", "--name", "placeholder_contract")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("prohibited incomplete-artifact language", result.stdout)

    def test_failed_validation_preserves_staged_artifacts_for_targeted_repair(self):
        invalid = REGRESSION.replace("assert value ==", "assert True or value ==")
        self.fx.stage(regression=invalid)
        result = self.fx.run("validate", "--name", "repairable_stage")
        self.assertNotEqual(result.returncode, 0)
        staging = self.fx.root / "config" / "improvements" / "staging"
        self.assertTrue((staging / "acceptance.txt").is_file())
        self.assertTrue((staging / "regression.py").is_file())
        self.assertTrue((staging / "e2e.py").is_file())

    def test_e2e_cannot_assert_a_value_manufactured_by_its_own_command(self):
        manufactured = '''import subprocess
import sys

def test_feature_marker():
    result = subprocess.run([sys.executable, "-c", "print('manufactured-proof')"], capture_output=True, text=True)
    assert result.stdout.strip() == "manufactured-proof"

def test_live_process():
    assert subprocess.run([sys.executable, "-c", "print('live-proof')"]).returncode == 0

if __name__ == "__main__":
    test_feature_marker()
    test_live_process()
'''
        self.fx.stage(e2e=manufactured)
        result = self.fx.run("validate", "--name", "manufactured_evidence")
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(
            "inline interpreter/shell code" in result.stdout
            or "embedded in its own subprocess command" in result.stdout,
            result.stdout,
        )

    def test_helper_variable_cannot_hide_inline_manufactured_evidence(self):
        bypass = '''import subprocess
import sys

def run_check(msg):
    cmd = [sys.executable, "-c", f'print("{msg}")']
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    assert msg in result.stdout

def test_feature_marker():
    run_check("feature")

def test_live_process():
    run_check("live")

if __name__ == "__main__":
    test_feature_marker()
    test_live_process()
'''
        self.fx.stage(e2e=bypass)
        result = self.fx.run("validate", "--name", "helper_bypass")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("inline interpreter/shell code", result.stdout)

    def test_presence_only_regression_is_not_behavioral_evidence(self):
        presence = '''from pathlib import Path
import os

def test_feature_marker():
    path = Path(os.environ["ERNOS_SOURCE_ROOT"]) / "feature.marker"
    assert path.exists(), "feature marker must exist"

if __name__ == "__main__":
    test_feature_marker()
'''
        self.fx.stage(regression=presence)
        result = self.fx.run("validate", "--name", "presence_only")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("proves only module/file presence", result.stdout)

    def test_every_recorded_ep_write_must_compile_before_verification(self):
        compile_plan = PLAN.replace(
            "- feature.marker: Persist the exact production marker value consumed by both verified behavior surfaces.",
            "- feature.marker: Persist the exact production marker value consumed by both verified behavior surfaces.\n"
            "- invalid.ep: Exercise the mandatory compiler check for every declared ErnosPlain production write.",
        )
        self.fx.stage(plan=compile_plan, planned_files=["feature.marker", "invalid.ep"])
        self.assertEqual(self.fx.freeze_valid("compile_each_write").returncode, 0)
        self.assertEqual(self.fx.run("start-implementation").returncode, 0)
        invalid = self.fx.root / "invalid.ep"
        invalid.write_text("import sys\n\ndef main():\n    print('not Ernos')\n", encoding="utf-8")
        encoded = base64.b64encode(b"invalid.ep").decode("ascii")
        result = self.fx.run("record-write", "--path-b64", encoded)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("failed syntax/compile verification", result.stdout)
        active = json.loads(
            (self.fx.root / "config" / "improvements" / "active.json").read_text(encoding="utf-8")
        )
        self.assertNotIn("implementation_paths", active)

    def test_failed_candidate_is_retained_without_mutating_live_source(self):
        candidate_plan = PLAN.replace("feature.marker", "candidate.py")
        candidate_regression = REGRESSION.replace("feature.marker", "candidate.py")
        candidate_e2e = E2E.replace("feature.marker", "candidate.py")
        live = self.fx.root / "candidate.py"
        live.write_text("VALUE = 'baseline'\n", encoding="utf-8")
        self.fx.stage(
            plan=candidate_plan,
            regression=candidate_regression,
            e2e=candidate_e2e,
            planned_files=["candidate.py"],
        )
        self.assertEqual(self.fx.freeze_valid("retain_candidate").returncode, 0)
        candidate = self.fx.candidate_path("candidate.py")
        candidate.write_text("VALUE = (\n", encoding="utf-8")

        rejected = self.fx.check_candidate("candidate.py")

        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("code=CANDIDATE_REPAIR_REQUIRED", rejected.stdout)
        self.assertIn("CANDIDATE_REPAIR_REQUIRED target=candidate.py", rejected.stdout)
        self.assertNotIn(".ernos-candidate-", rejected.stdout)
        self.assertEqual(live.read_text(encoding="utf-8"), "VALUE = 'baseline'\n")
        self.assertEqual(candidate.read_text(encoding="utf-8"), "VALUE = (\n")
        active = json.loads(
            (self.fx.root / "config" / "improvements" / "active.json").read_text(encoding="utf-8")
        )
        self.assertEqual(active["implementation_candidates"]["candidate.py"]["status"], "rejected")
        self.assertEqual(active["implementation_candidates"]["candidate.py"]["target"], "candidate.py")
        self.assertNotIn("path", active["implementation_candidates"]["candidate.py"])
        self.assertNotIn(".ernos-candidate-", active["implementation_candidates"]["candidate.py"]["diagnostic"])

        reset = self.fx.run("reset-incomplete-candidate")
        self.assertEqual(reset.returncode, 0, reset.stdout)
        self.assertIn("reason=CANDIDATE_REPAIR_STALLED", reset.stdout)
        self.assertFalse(candidate.exists())
        active = json.loads(
            (self.fx.root / "config" / "improvements" / "active.json").read_text(encoding="utf-8")
        )
        attempt = active["implementation_candidate_attempts"][-1]
        self.assertEqual(attempt["reason"], "CANDIDATE_REPAIR_STALLED")
        self.assertIn("failed syntax/compile verification", attempt["diagnostic"])
        self.assertTrue((self.fx.root / attempt["archived_path"]).is_file())

    def test_candidate_admission_does_not_reinterpret_frozen_behavior_from_source_shape(self):
        candidate_plan = PLAN.replace("feature.marker", "candidate.py")
        candidate_regression = REGRESSION.replace("feature.marker", "candidate.py")
        candidate_e2e = E2E.replace("feature.marker", "candidate.py")
        live = self.fx.root / "candidate.py"
        live.write_text("VALUE = 'baseline'\n", encoding="utf-8")
        self.fx.stage(
            plan=candidate_plan,
            regression=candidate_regression,
            e2e=candidate_e2e,
            planned_files=["candidate.py"],
        )
        self.assertEqual(self.fx.freeze_valid("compiler_is_candidate_authority").returncode, 0)
        candidate = self.fx.candidate_path("candidate.py")
        candidate.write_text("VALUE = 'compiled candidate'\n", encoding="utf-8")

        spec = importlib.util.spec_from_file_location("candidate_authority_gate", self.fx.manager)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        def forbidden_source_classifier(*_args, **_kwargs):
            raise AssertionError("candidate admission invoked the objective source-shape classifier")

        module.validate_candidate_objective_contract = forbidden_source_classifier
        module.check_candidate(base64.b64encode(b"candidate.py").decode("ascii"))

        active = json.loads(
            (self.fx.root / "config" / "improvements" / "active.json").read_text(encoding="utf-8")
        )
        self.assertEqual(active["implementation_candidates"]["candidate.py"]["status"], "compiled")
        self.assertEqual(live.read_text(encoding="utf-8"), "VALUE = 'baseline'\n")

    def test_additive_candidate_cannot_drop_baseline_definitions_and_can_reset(self):
        candidate_plan = PLAN.replace("feature.marker", "extension.ep")
        candidate_regression = REGRESSION.replace("feature.marker", "extension.ep")
        candidate_e2e = E2E.replace("feature.marker", "extension.ep")
        live = self.fx.root / "extension.ep"
        live.write_text(
            "define existing_schema returning Str:\n    return \"schema\"\n\n"
            "define existing_execute returning Str:\n    return \"execute\"\n",
            encoding="utf-8",
        )
        self.fx.stage(
            plan=candidate_plan,
            regression=candidate_regression,
            e2e=candidate_e2e,
            planned_files=["extension.ep"],
        )
        frozen = self.fx.freeze_valid("preserve_additive_baseline")
        self.assertEqual(frozen.returncode, 0, frozen.stdout)
        candidate = self.fx.candidate_path("extension.ep")
        candidate.write_text(
            "define new_surface returning Str:\n    return \"new\"\n",
            encoding="utf-8",
        )

        rejected = self.fx.check_candidate("extension.ep")
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("CANDIDATE_BASELINE_INCOMPLETE", rejected.stdout)
        self.assertIn("existing_schema", rejected.stdout)
        self.assertEqual(live.read_text(encoding="utf-8").splitlines()[0], "define existing_schema returning Str:")

        # A replacement-node failure returns the same immutable transaction to
        # repair_required. A malformed subsequent candidate was never live and must
        # remain resettable without abandoning the already accepted transaction.
        active_path = self.fx.root / "config" / "improvements" / "active.json"
        repair_active = json.loads(active_path.read_text(encoding="utf-8"))
        repair_active["state"] = "repair_required"
        active_path.write_text(json.dumps(repair_active), encoding="utf-8")

        reset = self.fx.run("reset-incomplete-candidate")
        self.assertEqual(reset.returncode, 0, reset.stdout)
        self.assertIn("IMPLEMENTATION_CANDIDATE_RESET_OK", reset.stdout)
        self.assertFalse(candidate.exists())
        active = json.loads(
            (self.fx.root / "config" / "improvements" / "active.json").read_text(encoding="utf-8")
        )
        self.assertNotIn("extension.ep", active["implementation_candidates"])
        attempt = active["implementation_candidate_attempts"][-1]
        self.assertEqual(attempt["reason"], "CANDIDATE_BASELINE_INCOMPLETE")
        self.assertTrue((self.fx.root / attempt["archived_path"]).is_file())

    def test_compiled_candidate_must_match_promoted_source_and_is_cleaned_after_record(self):
        candidate_plan = PLAN.replace("feature.marker", "candidate.py")
        candidate_regression = REGRESSION.replace("feature.marker", "candidate.py")
        candidate_e2e = E2E.replace("feature.marker", "candidate.py")
        live = self.fx.root / "candidate.py"
        live.write_text("VALUE = 'baseline'\n", encoding="utf-8")
        self.fx.stage(
            plan=candidate_plan,
            regression=candidate_regression,
            e2e=candidate_e2e,
            planned_files=["candidate.py"],
        )
        self.assertEqual(self.fx.freeze_valid("promote_candidate").returncode, 0)
        candidate = self.fx.candidate_path("candidate.py")
        candidate.write_text("VALUE = 'repaired'\n", encoding="utf-8")
        checked = self.fx.check_candidate("candidate.py")
        self.assertEqual(checked.returncode, 0, checked.stdout)
        self.assertIn("live_source_unchanged=yes", checked.stdout)
        self.assertEqual(live.read_text(encoding="utf-8"), "VALUE = 'baseline'\n")

        mismatched = self.fx.record_write("candidate.py")
        self.assertNotEqual(mismatched.returncode, 0)
        self.assertIn("does not match the compiled retained candidate", mismatched.stdout)

        live.write_bytes(candidate.read_bytes())
        promoted = self.fx.record_write("candidate.py")
        self.assertEqual(promoted.returncode, 0, promoted.stdout)
        self.assertIn("IMPLEMENTATION_WRITE_OK", promoted.stdout)
        self.assertFalse(candidate.exists())

    def test_write_preflight_rejects_undeclared_path_before_mutation(self):
        self.fx.stage()
        self.assertEqual(self.fx.freeze_valid("preflight_paths").returncode, 0)
        self.assertEqual(self.fx.run("start-implementation").returncode, 0)
        accepted = self.fx.preflight_write("feature.marker")
        self.assertEqual(accepted.returncode, 0, accepted.stdout)
        self.assertIn("IMPLEMENTATION_PREFLIGHT_OK", accepted.stdout)
        undeclared = self.fx.preflight_write("undeclared_new_file.ep")
        self.assertNotEqual(undeclared.returncode, 0)
        self.assertIn("code=PLAN_SCOPE_MISSING", undeclared.stdout)
        self.assertIn("was not declared in the validated plan", undeclared.stdout)
        self.assertIn("planned=feature.marker", undeclared.stdout)
        self.assertFalse((self.fx.root / "undeclared_new_file.ep").exists())

    def test_frozen_plan_rejects_changed_investigated_dependency(self):
        self.fx.stage()
        frozen = self.fx.freeze_valid("dependency_drift")
        self.assertEqual(frozen.returncode, 0, frozen.stdout)
        (self.fx.root / "source_two.py").write_text("READER = 'changed after freeze'\n", encoding="utf-8")
        rejected = self.fx.preflight_write("feature.marker")
        self.assertNotEqual(rejected.returncode, 0, rejected.stdout)
        self.assertIn("code=PLAN_SCOPE_MISSING", rejected.stdout)
        self.assertIn("frozen plan dependency changed after investigation", rejected.stdout)

    def test_completed_regression_survives_authorized_dependency_evolution(self):
        self.fx.stage()
        frozen = self.fx.freeze_valid("completed_dependency_evolution")
        self.assertEqual(frozen.returncode, 0, frozen.stdout)
        active_path = self.fx.root / "config" / "improvements" / "active.json"
        active = json.loads(active_path.read_text(encoding="utf-8"))
        active["state"] = "completed"
        completed_dir = self.fx.root / "config" / "improvements" / "completed"
        completed_dir.mkdir(parents=True, exist_ok=True)
        (completed_dir / f"{active['id']}.json").write_text(
            json.dumps(active), encoding="utf-8"
        )
        active_path.unlink()
        (self.fx.root / "source_two.py").write_text(
            "READER = '/bin/cat'\nEVOLVED = True\n", encoding="utf-8"
        )

        verified = self.fx.run("verify")
        self.assertEqual(verified.returncode, 0, verified.stdout)
        self.assertIn("IMPROVEMENT_VERIFY_OK completed=1 active=0", verified.stdout)

    def test_frozen_plan_allows_only_hash_verified_reread_of_declared_source(self):
        source_plan = PLAN.replace("feature.marker", "source_one.py")
        source_regression = REGRESSION.replace("feature.marker", "source_one.py")
        source_e2e = E2E.replace("feature.marker", "source_one.py")
        self.fx.stage(
            plan=source_plan,
            regression=source_regression,
            e2e=source_e2e,
            planned_files=["source_one.py"],
        )
        frozen = self.fx.freeze_valid("frozen_reread")
        self.assertEqual(frozen.returncode, 0, frozen.stdout)

        allowed = self.fx.record_discovery("source_one.py")
        self.assertEqual(allowed.returncode, 0, allowed.stdout)
        self.assertIn("IMPROVEMENT_REREAD_OK path=source_one.py", allowed.stdout)
        self.assertIn("scope=frozen-plan", allowed.stdout)

        unplanned = self.fx.record_discovery("source_two.py")
        self.assertNotEqual(unplanned.returncode, 0, unplanned.stdout)
        self.assertIn("code=PLAN_SCOPE_MISSING", unplanned.stdout)
        self.assertIn("limited to exact production paths declared in the frozen plan", unplanned.stdout)

        (self.fx.root / "source_one.py").write_text("MARKER = 'tampered'\n", encoding="utf-8")
        changed = self.fx.record_discovery("source_one.py")
        self.assertNotEqual(changed.returncode, 0, changed.stdout)
        self.assertIn("changed outside the protected implementation path", changed.stdout)

    def test_frozen_test_hash_cannot_be_weakened(self):
        self.fx.stage()
        self.assertEqual(self.fx.freeze_valid("immutable_test").returncode, 0)
        record = json.loads((self.fx.root / "config" / "improvements" / "active.json").read_text())
        regression = self.fx.root / record["regression_path"]
        regression.write_text(REGRESSION + "\n# weakened after freeze\n", encoding="utf-8")
        result = self.fx.run("start-implementation")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("hash mismatch", result.stdout)

    def test_abandon_is_allowed_only_before_implementation(self):
        self.fx.stage()
        self.assertEqual(self.fx.freeze_valid("abandon_before_write").returncode, 0)
        staging = self.fx.root / "config" / "improvements" / "staging"
        staging.mkdir(parents=True, exist_ok=True)
        (staging / "abort_reason.txt").write_text(
            "The acceptance test encoded the wrong public contract, so this transaction is abandoned before any implementation write.",
            encoding="utf-8",
        )
        aborted = self.fx.run("abort")
        self.assertEqual(aborted.returncode, 0, aborted.stdout)

        self.fx.stage()
        self.assertEqual(self.fx.freeze_valid("cannot_abandon_after_write").returncode, 0)
        self.assertEqual(self.fx.run("start-implementation").returncode, 0)
        (self.fx.root / "feature.marker").write_text("implemented", encoding="utf-8")
        self.assertEqual(self.fx.record_write("feature.marker").returncode, 0)
        (staging / "abort_reason.txt").write_text(
            "Attempted abandonment after implementation began must fail closed and preserve the frozen evaluator.",
            encoding="utf-8",
        )
        blocked = self.fx.run("abort")
        self.assertNotEqual(blocked.returncode, 0)
        self.assertIn("only before the first verified implementation write", blocked.stdout)

    def test_failed_first_write_leaves_frozen_transaction_abandonable(self):
        self.fx.stage()
        self.assertEqual(self.fx.freeze_valid("failed_write_abandonable").returncode, 0)
        self.assertEqual(self.fx.run("start-implementation").returncode, 0)
        invalid = self.fx.root / "invalid.ep"
        invalid.write_text("import sys\n\ndef main():\n    print('not Ernos')\n", encoding="utf-8")
        result = self.fx.record_write("invalid.ep")
        self.assertNotEqual(result.returncode, 0)
        active = json.loads(
            (self.fx.root / "config" / "improvements" / "active.json").read_text(encoding="utf-8")
        )
        self.assertEqual(active["state"], "frozen")
        staging = self.fx.root / "config" / "improvements" / "staging"
        (staging / "abort_reason.txt").write_text(
            "The first proposed implementation failed syntax verification and changed no production bytes, so the invalid contract remains safely abandonable.",
            encoding="utf-8",
        )
        abandoned = self.fx.run("abort")
        self.assertEqual(abandoned.returncode, 0, abandoned.stdout)

    def test_live_e2e_failure_cannot_be_promoted_after_green_regression(self):
        failing_e2e = E2E.replace(
            'assert result.stdout.strip() == "implemented"',
            'assert result.stdout.strip() == "a-different-required-surface"',
        )
        self.fx.stage(e2e=failing_e2e)
        self.assertEqual(self.fx.freeze_valid("live_failure_blocks_commit").returncode, 0)
        (self.fx.root / "feature.marker").write_text("implemented", encoding="utf-8")
        self.assertEqual(self.fx.run("start-implementation").returncode, 0)
        self.assertEqual(self.fx.record_write("feature.marker").returncode, 0)
        self.assertEqual(self.fx.run("mark-verified").returncode, 0)
        live = self.fx.run("live")
        self.assertNotEqual(live.returncode, 0)
        self.assertIn("live E2E failed", live.stdout)
        active = json.loads(
            (self.fx.root / "config" / "improvements" / "active.json").read_text(encoding="utf-8")
        )
        self.assertEqual(active["state"], "repair_required")
        self.assertEqual(len(active["live_failure_hash"]), 64)
        self.assertEqual(len(active["live_failure_source_hash"]), 64)
        self.assertEqual(len(active["live_failure_fingerprint"]), 64)
        unchanged = self.fx.run("verify")
        self.assertNotEqual(unchanged.returncode, 0)
        self.assertIn("has not received a causal source change", unchanged.stdout)
        (self.fx.root / "feature.marker").write_text(
            "a-different-required-surface", encoding="utf-8"
        )
        repaired = self.fx.record_write("feature.marker")
        self.assertEqual(repaired.returncode, 0, repaired.stdout)
        blocked = self.fx.run("complete")
        self.assertNotEqual(blocked.returncode, 0)
        self.assertIn("no successful live-E2E receipt", blocked.stdout)

    def test_active_runtime_regression_runs_after_activation_not_before_build(self):
        replacement_only_regression = REGRESSION.replace(
            'assert value == "implemented", f"expected implemented marker, got {value!r}"',
            'assert value == "replacement-runtime", f"expected replacement runtime, got {value!r}"',
        )
        self.fx.stage(regression=replacement_only_regression)
        self.assertEqual(self.fx.freeze_valid("replacement_runtime_order").returncode, 0)
        (self.fx.root / "feature.marker").write_text("implemented", encoding="utf-8")
        self.assertEqual(self.fx.run("start-implementation").returncode, 0)
        self.assertEqual(self.fx.record_write("feature.marker").returncode, 0)

        verified = self.fx.run("mark-verified")
        self.assertEqual(verified.returncode, 0, verified.stdout)
        self.assertIn("runtime=deferred_to_replacement", verified.stdout)

        live = self.fx.run("live")
        self.assertNotEqual(live.returncode, 0)
        self.assertIn("regression failed", live.stdout)
        active = json.loads(
            (self.fx.root / "config" / "improvements" / "active.json").read_text(encoding="utf-8")
        )
        self.assertEqual(active["state"], "repair_required")

    def test_completed_runtime_regressions_are_deferred_then_run_live(self):
        self.fx.stage()
        self.assertEqual(self.fx.freeze_valid("completed_runtime_order").returncode, 0)
        (self.fx.root / "feature.marker").write_text("implemented", encoding="utf-8")
        self.assertEqual(self.fx.run("start-implementation").returncode, 0)
        self.assertEqual(self.fx.record_write("feature.marker").returncode, 0)
        self.assertEqual(self.fx.run("mark-verified").returncode, 0)
        self.assertEqual(self.fx.run("live").returncode, 0)
        self.assertEqual(self.fx.run("complete").returncode, 0)

        (self.fx.root / "feature.marker").write_text("regressed", encoding="utf-8")
        verified = self.fx.run("verify")
        self.assertEqual(verified.returncode, 0, verified.stdout)
        self.assertIn("runtime=deferred_to_replacement", verified.stdout)

        live = self.fx.run("live")
        self.assertNotEqual(live.returncode, 0)
        self.assertIn("regression failed", live.stdout)

    def test_completed_runtime_failure_records_active_repair_receipt_once(self):
        self.fx.stage()
        self.assertEqual(self.fx.freeze_valid("completed_failure_receipt").returncode, 0)
        marker = self.fx.root / "feature.marker"
        marker.write_text("implemented", encoding="utf-8")
        self.assertEqual(self.fx.run("start-implementation").returncode, 0)
        self.assertEqual(self.fx.record_write("feature.marker").returncode, 0)
        self.assertEqual(self.fx.run("mark-verified").returncode, 0)
        self.assertEqual(self.fx.run("live").returncode, 0)
        self.assertEqual(self.fx.run("complete").returncode, 0)

        marker.write_text("regressed", encoding="utf-8")
        next_regression = REGRESSION.replace('"implemented"', '"next-implemented"')
        next_e2e = E2E.replace('"implemented"', '"next-implemented"')
        self.fx.stage(regression=next_regression, e2e=next_e2e)
        self.assertEqual(self.fx.freeze_valid("active_after_completed").returncode, 0)
        marker.write_text("next-implemented", encoding="utf-8")
        self.assertEqual(self.fx.run("start-implementation").returncode, 0)
        self.assertEqual(self.fx.record_write("feature.marker").returncode, 0)
        self.assertEqual(self.fx.run("mark-verified").returncode, 0)

        failed = self.fx.run("live")
        self.assertNotEqual(failed.returncode, 0)
        self.assertIn("LIVE_REPAIR_REQUIRED", failed.stdout)
        active_path = self.fx.root / "config" / "improvements" / "active.json"
        active = json.loads(active_path.read_text(encoding="utf-8"))
        self.assertEqual(active["state"], "repair_required")
        self.assertEqual(active["live_failure_attempt"], 1)
        for field in (
            "live_failure_hash",
            "live_failure_source_hash",
            "live_failure_fingerprint",
        ):
            self.assertEqual(len(active[field]), 64)

        repeated = self.fx.run(
            "record-failure", "--detail", "frozen_improvement_live_e2e_failed"
        )
        self.assertEqual(repeated.returncode, 0, repeated.stdout)
        self.assertIn("already_complete=yes", repeated.stdout)
        unchanged = json.loads(active_path.read_text(encoding="utf-8"))
        self.assertEqual(unchanged["live_failure_attempt"], 1)


if __name__ == "__main__":
    unittest.main()
