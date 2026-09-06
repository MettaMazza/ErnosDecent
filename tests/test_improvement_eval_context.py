#!/usr/bin/env python3
"""Guard the production evaluator seam's live service-context wiring."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ImprovementEvaluatorContextTests(unittest.TestCase):
    def test_live_sessions_manager_is_supplied_before_tool_execution(self):
        source = (ROOT / "node.ep").read_text(encoding="utf-8")
        start = source.index('if string_index_of(cmd_upper and "AI EVAL_TOOL ") == 0:')
        end = source.index('else if string_contains(cmd_upper and "AI INFER ") == 1:', start)
        evaluator = source[start:end]

        sessions_lookup = 'map_get_val(agent_ctx and "sessions")'
        sessions_insert = (
            'map_insert(eval_ctx and "sessions" and '
            'cast_borrow_to_map(eval_sessions))'
        )
        execute = (
            "tools_execute(cast_borrow_to_map(agent_tools) and eval_ctx and "
            "eval_name and eval_args)"
        )

        self.assertIn(sessions_lookup, evaluator)
        self.assertIn(sessions_insert, evaluator)
        self.assertIn(execute, evaluator)
        self.assertLess(evaluator.index(sessions_lookup), evaluator.index(sessions_insert))
        self.assertLess(evaluator.index(sessions_insert), evaluator.index(execute))


if __name__ == "__main__":
    unittest.main()
