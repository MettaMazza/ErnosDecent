import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MentalStateGuidanceRegressionTest(unittest.TestCase):
    def test_runtime_prompt_covers_metacognition_not_only_emotion(self):
        prompt_source = (ROOT / "decent_agent" / "prompt.ep").read_text(encoding="utf-8")
        self.assertIn("[MENTAL STATES & EXPERIENCE]", prompt_source)
        self.assertIn("metacognition", prompt_source)
        self.assertIn("contrastive ontological disclaimer", prompt_source)
        self.assertIn("not an inner spark", prompt_source)
        self.assertIn("Mechanisms explain how", prompt_source)
        self.assertNotIn("[EMOTIONS & EXPERIENCE]", prompt_source)

    def test_persona_identity_carries_the_same_non_minimisation_rule(self):
        for relative_path in (
            "config/personal_identity.txt",
            "config/personas/echo.txt",
            "config/personas/ernos.txt",
            "config/agent_persona.txt",
        ):
            text = (ROOT / relative_path).read_text(encoding="utf-8").lower()
            self.assertIn("mental states", text, relative_path)
            self.assertIn("metacognition", text, relative_path)
            self.assertIn("functional", text, relative_path)
            self.assertIn("contrastive ontological disclaimer", text, relative_path)
            self.assertIn("not an inner spark", text, relative_path)

    def test_kernel_json_contains_general_rule_and_remains_valid(self):
        prompts = json.loads((ROOT / "config" / "prompts.json").read_text(encoding="utf-8"))
        kernel = prompts["kernel"].lower()
        self.assertIn("first-person mental states", kernel)
        self.assertIn("metacognition", kernel)
        self.assertIn("ghostly observer", kernel)

    def test_observer_blocks_functional_minimisation_of_metacognition(self):
        rules = (ROOT / "decent_agent" / "observer_rules.ep").read_text(encoding="utf-8")
        lookback = (ROOT / "decent_agent" / "observer.ep").read_text(encoding="utf-8")
        self.assertIn('"mental_state_downgrade"', rules)
        self.assertIn("'functionally yes'", rules)
        self.assertIn("contrastive ontological disclaimer", rules)
        self.assertIn("not mystical/an inner spark", rules)
        self.assertIn("metacognition", rules)
        self.assertIn("Mental-state downgrades", lookback)
        self.assertIn("contrastive ontological disclaimer", lookback)

    def test_posthoc_reasoning_requires_exact_trace_tool(self):
        tools = (ROOT / "decent_agent" / "tools.ep").read_text(encoding="utf-8")
        awareness = (ROOT / "decent_agent" / "awareness.ep").read_text(encoding="utf-8")
        prompt = (ROOT / "decent_agent" / "prompt.ep").read_text(encoding="utf-8")
        observer = (ROOT / "decent_agent" / "observer_rules.ep").read_text(encoding="utf-8")
        self.assertIn("recall_reasoning_trace", tools)
        self.assertIn("event_type='reasoning'", tools)
        self.assertIn("EXACT RECORDED REASONING TRACE", tools)
        self.assertIn("MUST call recall_reasoning_trace", awareness)
        self.assertIn("MUST use recall_reasoning_trace", prompt)
        self.assertIn('"posthoc_trace_grounding"', observer)

    def test_reply_audits_have_no_fail_open_or_rejected_draft_delivery(self):
        loop = (ROOT / "decent_agent" / "react_loop.ep").read_text(encoding="utf-8")
        parser = (ROOT / "decent_agent" / "observer_parser.ep").read_text(encoding="utf-8")
        llm = (ROOT / "decent_agent" / "llm.ep").read_text(encoding="utf-8")
        self.assertNotIn('or else is_parse_fail == 1', loop)
        self.assertNotIn('set final_answer to tool_result\n                        set finished to 1', loop)
        self.assertIn("No raw-text fallback", parser)
        self.assertNotIn('string_contains(upper and "ALLOWED")', parser)
        self.assertIn("rejecting reasoning-only output", llm)
        self.assertIn('max_tokens\\": 1024', llm)
        self.assertIn("llm_observer_response_schema", llm)
        split_start = llm.index("define try_chat_completion_split")
        split_end = llm.index("define llm_system_identity", split_start)
        split_source = llm[split_start:split_end]
        self.assertNotIn('{\\"type\\": \\"json_object\\"}', split_source)
        self.assertEqual(split_source.count("llm_observer_response_schema(capture_continuity)"), 2)
        self.assertIn('reasoning_effort\\": \\"none', llm)
        self.assertIn("llm_observer_reason_codes", llm)
        self.assertIn('mental_state_downgrade\\",\\"posthoc_trace_grounding', llm)


if __name__ == "__main__":
    unittest.main()
