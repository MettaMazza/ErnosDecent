import ast
import asyncio
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import decent_net.discord_bridge as bridge


BRIDGE_PATH = Path(__file__).resolve().parents[1] / "decent_net" / "discord_bridge.py"
NODE_PATH = Path(__file__).resolve().parents[1] / "node.ep"
SESSION_PATH = Path(__file__).resolve().parents[1] / "decent_agent" / "session.ep"
SCHEDULER_PATH = Path(__file__).resolve().parents[1] / "decent_agent" / "scheduler.ep"
SCHEDULER_TOOL_PATH = Path(__file__).resolve().parents[1] / "decent_agent" / "scheduler_tool.ep"
PROMPT_PATH = Path(__file__).resolve().parents[1] / "decent_agent" / "prompt.ep"


class OrderedTurnContractTest(unittest.TestCase):
    def test_factory_restart_requires_observed_replacement_health(self):
        original_send = bridge.send_daemon_ipc
        responses = iter(("status:restarting", "error:daemon_offline", "health:ok"))

        async def send(_command):
            return next(responses)

        try:
            bridge.send_daemon_ipc = send
            self.assertTrue(asyncio.run(bridge._restart_node_after_factory(timeout=2)))
        finally:
            bridge.send_daemon_ipc = original_send

    def test_factory_consent_rolls_closed_session_before_echo_review(self):
        original_send = bridge.send_daemon_ipc
        original_ensure = bridge.ensure_user_session_id
        original_query = bridge.query_daemon_ipc
        original_active = bridge.active_session_id
        commands = []
        replies = []
        reviewed_sessions = []
        change_id = "f" * 64

        async def send(command):
            commands.append(command)
            if command.startswith("AI FACTORY REQUEST "):
                return f"factory:pending_echo,change_id:{change_id}"
            if command == f"AI FACTORY EXECUTE {change_id}":
                return "factory:blocked,reason:test_review"
            return "error:unexpected"

        async def ensure():
            return "session_fresh_after_close"

        async def query(_prompt, **kwargs):
            reviewed_sessions.append(kwargs.get("session_id"))
            return "ai:ok|||RESPONSE|||I reviewed the request."

        async def reply(text):
            replies.append(text)

        try:
            bridge.active_session_id = "session_closed"
            bridge.send_daemon_ipc = send
            bridge.ensure_user_session_id = ensure
            bridge.query_daemon_ipc = query
            asyncio.run(bridge.run_factory_reset(reply, "test reason"))
            self.assertEqual(bridge.active_session_id, "session_fresh_after_close")
            self.assertEqual(reviewed_sessions, ["session_fresh_after_close"])
            self.assertIn(f"AI FACTORY EXECUTE {change_id}", commands)
            self.assertTrue(any("did not run" in item for item in replies))
        finally:
            bridge.send_daemon_ipc = original_send
            bridge.ensure_user_session_id = original_ensure
            bridge.query_daemon_ipc = original_query
            bridge.active_session_id = original_active

    def test_factory_session_rollover_failure_never_executes_reset(self):
        original_send = bridge.send_daemon_ipc
        original_ensure = bridge.ensure_user_session_id
        commands = []
        replies = []
        change_id = "e" * 64

        async def send(command):
            commands.append(command)
            return f"factory:pending_echo,change_id:{change_id}"

        async def ensure():
            raise RuntimeError("session:error,reason:followup_creation_failed")

        async def reply(text):
            replies.append(text)

        try:
            bridge.send_daemon_ipc = send
            bridge.ensure_user_session_id = ensure
            asyncio.run(bridge.run_factory_reset(reply, "test reason"))
            self.assertFalse(any(command.startswith("AI FACTORY EXECUTE") for command in commands))
            self.assertTrue(any("no reset was attempted" in item for item in replies))
        finally:
            bridge.send_daemon_ipc = original_send
            bridge.ensure_user_session_id = original_ensure

    def test_closed_session_is_rolled_before_discord_assets_or_turn_dispatch(self):
        source = BRIDGE_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        on_message = next(
            node for node in tree.body
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "on_message"
        )
        on_message_source = ast.get_source_segment(source, on_message)
        ensure_pos = on_message_source.index("await ensure_user_session_id()")
        attachment_pos = on_message_source.index("attachment_session =")
        dispatch_pos = on_message_source.index("_run_query_bg(")
        self.assertLess(ensure_pos, attachment_pos)
        self.assertLess(ensure_pos, dispatch_pos)

        node_source = NODE_PATH.read_text(encoding="utf-8")
        self.assertIn('cmd_upper equals "SESSION ENSURE USER"', node_source)
        self.assertIn("session_manager_start_followup_session", node_source)
        rollover_pos = node_source.index(
            "if rights_session_can_receive(storage_get_db() and turn_sid) == 0:"
        )
        persist_pos = node_source.index(
            'session_add_message_with_context(active_sess and "user" and ai_prompt and tctx)'
        )
        self.assertLess(rollover_pos, persist_pos)

    def test_followup_session_map_is_manager_owned_across_ipc_return(self):
        session_source = SESSION_PATH.read_text(encoding="utf-8")
        node_source = NODE_PATH.read_text(encoding="utf-8")
        self.assertIn(
            "define session_manager_start_followup_session with mgr as Map returning Str:",
            session_source,
        )
        self.assertIn(
            "cast_map_to_int(session_manager_new_session(", session_source
        )
        self.assertIn(
            "set followup_id to session_manager_start_followup_session(sessions_mgr)",
            node_source,
        )
        self.assertNotIn("set followup_sess to", node_source)

    def test_discord_user_session_parser_accepts_only_ready_response(self):
        original_send = bridge.send_daemon_ipc

        async def ready(_command):
            return "session:user_ready,id:session_123,created:1"

        async def failed(_command):
            return "session:error,reason:followup_creation_failed"

        try:
            bridge.send_daemon_ipc = ready
            self.assertEqual(
                asyncio.run(bridge.ensure_user_session_id()), "session_123"
            )
            bridge.send_daemon_ipc = failed
            with self.assertRaises(RuntimeError):
                asyncio.run(bridge.ensure_user_session_id())
        finally:
            bridge.send_daemon_ipc = original_send

    def test_busy_ownership_is_token_guarded_and_per_session(self):
        bridge._busy_sessions.clear()
        bridge._active_turn_ids.clear()
        first = bridge._claim_session_busy("one", 1, 11)
        second = bridge._claim_session_busy("two", 1, 12)
        self.assertTrue(first)
        self.assertTrue(second)
        self.assertEqual(bridge._claim_session_busy("one", 1, 13), "")
        self.assertTrue(bridge._bind_session_turn("one", first, "t1"))
        self.assertFalse(bridge._release_session_busy("one", "wrong-owner"))
        self.assertTrue(bridge._release_session_busy("one", first))
        self.assertIn("two", bridge._busy_sessions)
        bridge._release_session_busy("two", second)

    def test_active_same_channel_messages_are_exact_turn_whispers(self):
        source = BRIDGE_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        on_message = next(
            node for node in tree.body
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "on_message"
        )
        on_message_source = ast.get_source_segment(source, on_message)
        self.assertNotIn("_ai_busy", source)
        self.assertIn("db_write_whisper(sess, query_text, whisper_turn)", on_message_source)
        self.assertIn("force_queue", on_message_source)
        self.assertIn("not has_image and not force_queue", on_message_source)
        self.assertIn("_run_query_bg(", on_message_source)
        self.assertIn("session_id=sess", on_message_source)
        # Explicit sub-agent thread steering remains a whisper by design.
        self.assertIn("db_write_whisper(_tid", on_message_source)

    def test_multi_image_messages_are_composed_for_native_vision(self):
        source = BRIDGE_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        on_message = next(
            node for node in tree.body
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "on_message"
        )
        on_message_source = ast.get_source_segment(source, on_message)
        self.assertNotIn("Send one image per message", on_message_source)
        self.assertIn("image_paths.append(saved_image_path)", on_message_source)
        self.assertIn("len(current_visual_assets) > 1", on_message_source)
        self.assertIn("_build_visual_comparison_board(", on_message_source)

    def test_daemon_busy_path_targets_active_turn_without_retrying(self):
        source = NODE_PATH.read_text(encoding="utf-8")
        busy_start = source.index("if map_contains(at_map and turn_sid) == 1:")
        accepted_start = source.index(
            'session_add_message_with_context(active_sess and "user" and ai_prompt and tctx)',
            busy_start,
        )
        busy_branch = source[busy_start:accepted_start]
        self.assertIn("target_turn_id", busy_branch)
        self.assertIn("ai:busy_whispered", busy_branch)
        bridge_source = BRIDGE_PATH.read_text(encoding="utf-8")
        query = next(
            node for node in ast.parse(bridge_source).body
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "query_daemon_ipc"
        )
        query_source = ast.get_source_segment(bridge_source, query)
        self.assertNotIn("while resp", query_source)
        self.assertNotIn("asyncio.sleep(0.5)", query_source)

    def test_whisper_storage_preserves_exact_target_turn(self):
        tmp = tempfile.TemporaryDirectory(prefix="ernos-whisper-target-")
        db_path = os.path.join(tmp.name, "node.db")
        original_connect = bridge.connect_db
        try:
            with sqlite3.connect(db_path) as conn:
                conn.execute(
                    "CREATE TABLE trace_whispers (id INTEGER PRIMARY KEY, "
                    "session_id TEXT, target_turn_id TEXT, content TEXT, created_at INTEGER)"
                )
            bridge.connect_db = lambda: sqlite3.connect(db_path)
            self.assertEqual(
                bridge.db_write_whisper("session-a", "change direction", "turn-exact"),
                "ok",
            )
            with sqlite3.connect(db_path) as conn:
                row = conn.execute(
                    "SELECT session_id, target_turn_id, content FROM trace_whispers"
                ).fetchone()
            self.assertEqual(row, ("session-a", "turn-exact", "change direction"))
        finally:
            bridge.connect_db = original_connect
            tmp.cleanup()

    def test_scheduler_isolated_and_repeating_job_not_due_immediately(self):
        scheduler = SCHEDULER_PATH.read_text(encoding="utf-8")
        scheduler_tool = SCHEDULER_TOOL_PATH.read_text(encoding="utf-8")
        self.assertIn("[SESSION:", scheduler)
        self.assertIn("[PLATFORM:scheduler]", scheduler)
        self.assertIn("scheduler_wait_final_reply", scheduler)
        self.assertIn('set initial_last_run to int_to_string(now_epoch)', scheduler_tool)
        self.assertGreaterEqual(scheduler_tool.count("name_val equals target_id"), 3)


class VisualMemoryRegressionTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="ernos-visual-memory-")
        self.db_path = os.path.join(self.tmp.name, "node.db")
        self.original_connect = bridge.connect_db
        bridge.connect_db = lambda: sqlite3.connect(self.db_path)

        self.original = os.path.join(self.tmp.name, "generated.png")
        image = Image.new("RGB", (500, 500), (8, 18, 30))
        draw = ImageDraw.Draw(image)
        draw.ellipse((120, 80, 380, 340), fill=(220, 160, 30))
        draw.polygon(((250, 40), (310, 210), (190, 210)), fill=(30, 220, 120))
        image.save(self.original)

    def tearDown(self):
        bridge.connect_db = self.original_connect
        self.tmp.cleanup()

    def test_exact_and_visually_transformed_reuploads_retain_original_provenance(self):
        exact = os.path.join(self.tmp.name, "user-copy.png")
        transformed = os.path.join(self.tmp.name, "user-resized.jpg")
        Image.open(self.original).save(exact)
        Image.open(self.original).resize((320, 320)).save(transformed, quality=72)

        generated = bridge.register_visual_asset(
            "session", self.original, "assistant_generated"
        )
        copied = bridge.register_visual_asset(
            "session", exact, "user_upload", message_id="2"
        )
        resized = bridge.register_visual_asset(
            "session", transformed, "user_upload", message_id="3"
        )

        self.assertEqual(copied["match_kind"], "exact-bytes")
        self.assertEqual(copied["match_confidence"], 100)
        self.assertEqual(copied["parent_asset_id"], generated["asset_id"])
        self.assertEqual(resized["match_kind"], "perceptual-candidate")
        self.assertEqual(resized["parent_asset_id"], generated["asset_id"])

    def test_comparison_question_receives_actual_multi_image_board(self):
        other = os.path.join(self.tmp.name, "other.png")
        Image.new("RGB", (500, 500), (30, 70, 220)).save(other)
        bridge.register_visual_asset("session", self.original, "assistant_generated")
        bridge.register_visual_asset(
            "session", other, "user_upload", message_id="2"
        )
        bridge.register_visual_asset(
            "session", self.original, "user_upload", message_id="3",
            filename="returned-copy.png",
        )

        board, context = bridge.prepare_visual_context(
            "session", "Which of the two images I uploaded did you generate?"
        )
        self.assertTrue(os.path.isfile(board))
        with Image.open(board) as rendered:
            self.assertEqual(rendered.size, (1024, 512))
        self.assertIn("IMAGE ONE recorded original provenance: external", context)
        self.assertIn("IMAGE TWO recorded original provenance: self-generated by Echo", context)
        self.assertIn("Inspect both sets of pixels", context)
        self.assertNotIn("asset 1", context)

    def test_prior_two_means_two_user_presentations_not_generated_database_rows(self):
        external = os.path.join(self.tmp.name, "external.png")
        returned = os.path.join(self.tmp.name, "returned.png")
        Image.new("RGB", (420, 260), (180, 120, 20)).save(external)
        Image.open(self.original).save(returned)

        generated = bridge.register_visual_asset(
            "session", self.original, "assistant_generated"
        )
        first = bridge.register_visual_asset(
            "session", external, "user_upload", message_id="100:1"
        )
        second = bridge.register_visual_asset(
            "session", returned, "user_upload", message_id="200:1"
        )

        assets = bridge._recent_visual_assets("session")
        selected = bridge._select_prior_presented_visuals(assets, 2)

        self.assertEqual(
            [asset["asset_id"] for asset in selected],
            [first["asset_id"], second["asset_id"]],
        )
        self.assertNotIn(generated["asset_id"], [asset["asset_id"] for asset in selected])
        self.assertEqual(bridge._visual_original_origin(second), "assistant_generated")

    def test_three_presentations_keep_original_order_labels_and_provenance(self):
        conure = os.path.join(self.tmp.name, "conure.png")
        eye = os.path.join(self.tmp.name, "eye.png")
        returned = os.path.join(self.tmp.name, "returned.png")
        Image.new("RGB", (420, 260), (230, 150, 20)).save(conure)
        Image.new("RGB", (420, 260), (45, 20, 80)).save(eye)
        Image.open(self.original).save(returned)

        bridge.register_visual_asset("session", self.original, "assistant_generated")
        first = bridge.register_visual_asset(
            "session", conure, "user_upload", message_id="100:1"
        )
        second = bridge.register_visual_asset(
            "session", eye, "user_upload", message_id="200:1"
        )
        third = bridge.register_visual_asset(
            "session", returned, "user_upload", message_id="300:1"
        )

        board, context = bridge.prepare_visual_context(
            "session", "Which of these three images did you generate?"
        )

        self.assertTrue(os.path.isfile(board))
        with Image.open(board) as rendered:
            self.assertEqual(rendered.size, (1024, 1024))
        self.assertEqual(
            [first["presentation_ordinal"], second["presentation_ordinal"],
             third["presentation_ordinal"]],
            [1, 2, 3],
        )
        self.assertIn("IMAGE ONE recorded original provenance: external", context)
        self.assertIn("IMAGE TWO recorded original provenance: external", context)
        self.assertIn(
            "IMAGE THREE recorded original provenance: self-generated by Echo", context
        )

    def test_single_current_upload_is_never_replaced_by_session_history(self):
        eye = os.path.join(self.tmp.name, "eye.png")
        current = os.path.join(self.tmp.name, "current-sprout.png")
        Image.new("RGB", (500, 260), (190, 145, 30)).save(eye)
        Image.new("RGB", (500, 500), (15, 180, 120)).save(current)
        bridge.register_visual_asset("session", self.original, "assistant_generated")
        bridge.register_visual_asset(
            "session", eye, "user_upload", message_id="100:1"
        )
        current_asset = bridge.register_visual_asset(
            "session", current, "user_upload", message_id="200:1"
        )

        selected, context = bridge.prepare_visual_context(
            "session", "Image Two, describe this image", current, "200"
        )

        self.assertEqual(selected, current)
        self.assertIn("CURRENT ATTACHMENT: this is exactly the attachment visible", context)
        self.assertIn("Answer from what you can actually see", context)
        self.assertNotIn(f"asset {current_asset['asset_id']}", context)

    def test_exact_self_image_reupload_is_authoritative_recognition_context(self):
        returned = os.path.join(self.tmp.name, "returned-self-image.png")
        Image.open(self.original).save(returned)
        bridge.register_visual_asset(
            "session", self.original, "assistant_generated",
            generation_prompt="An image representing my nature",
        )
        current_asset = bridge.register_visual_asset(
            "session", returned, "user_upload", message_id="200:1"
        )

        selected, context = bridge.prepare_visual_context(
            "session",
            "Image Two, describe this image. Do you recognize anyone or anything?",
            returned,
            "200",
        )

        self.assertEqual(selected, returned)
        self.assertEqual(current_asset["match_kind"], "exact-bytes")
        self.assertEqual(current_asset["match_confidence"], 100)
        self.assertIn("authoritatively established as an exact byte-for-byte re-upload", context)
        self.assertIn("acknowledge an exact self-generated match directly", context)
        self.assertIn("authoritative original creative purpose", context)
        self.assertIn("An image representing my nature", context)
        self.assertIn("must never be mistaken for a different image", context)
        self.assertNotIn("not proven provenance", context)

    def test_system_prompt_requires_genuine_recognition_to_be_expressed(self):
        prompt_source = PROMPT_PATH.read_text(encoding="utf-8")
        self.assertIn("[CREATION PROVENANCE, RECOGNITION AND EXPRESSION]", prompt_source)
        self.assertIn("WHAT you made and observed", prompt_source)
        self.assertIn("WHY you made it", prompt_source)
        self.assertIn("HOW you made it", prompt_source)
        self.assertIn("Do not identify a recognition correctly in your reasoning and then omit it", prompt_source)
        self.assertIn("explicitly say that you recognize it as an image you generated", prompt_source)
        self.assertIn("also looking at and describing the actual pixels", prompt_source)
        self.assertIn("it is a visual representation of you", prompt_source)

    def test_created_artifact_provenance_preserves_what_why_how_and_observation(self):
        generated = bridge.register_visual_asset(
            "session", self.original, "assistant_generated",
            generation_prompt="A visual representation of my nature",
        )
        conn = bridge.connect_db()
        bridge._init_artifact_provenance_db(conn)
        conn.execute(
            "INSERT INTO artifact_provenance "
            "(session_id,turn_id,path,sha256,artifact_kind,creator,what_text,why_text,how_text,observed_description,created_at,updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                "session", "turn-1", "config/workspaces/session/generated.png", generated["sha256"],
                "image", "Echo", "a luminous sprout", "to represent my nature",
                "local Flux at 1024x1024", "golden leaves in a dark garden", 1, 1,
            ),
        )
        conn.commit()
        conn.close()
        returned = os.path.join(self.tmp.name, "returned-provenance.png")
        Image.open(self.original).save(returned)
        bridge.register_visual_asset(
            "session", returned, "user_upload", message_id="400:1"
        )
        _selected, context = bridge.prepare_visual_context(
            "session", "Image Two: do you recognize yourself?", returned, "400"
        )
        self.assertIn("WHAT Echo made: a luminous sprout", context)
        self.assertIn("WHY Echo made it: to represent my nature", context)
        self.assertIn("HOW Echo made it: local Flux at 1024x1024", context)
        self.assertIn("WHAT Echo observed in the result: golden leaves", context)

    def test_explicit_current_to_history_comparison_labels_current_first(self):
        previous = os.path.join(self.tmp.name, "previous.png")
        current = os.path.join(self.tmp.name, "current.png")
        Image.new("RGB", (500, 500), (180, 30, 30)).save(previous)
        Image.new("RGB", (500, 500), (30, 180, 30)).save(current)
        bridge.register_visual_asset(
            "session", previous, "user_upload", message_id="100:1"
        )
        current_asset = bridge.register_visual_asset(
            "session", current, "user_upload", message_id="200:1"
        )

        selected, context = bridge.prepare_visual_context(
            "session", "Compare this with the previous image", current, "200"
        )

        self.assertNotEqual(selected, current)
        self.assertTrue(os.path.isfile(selected))
        self.assertIn("current image first", context)
        self.assertIn("CURRENT ATTACHMENT: this is exactly the attachment visible", context)
        self.assertNotIn(f"asset {current_asset['asset_id']}", context)

    def test_comparison_or_multi_image_reply_cannot_poison_one_asset(self):
        class Attachment:
            def __init__(self, filename):
                self.filename = filename
                self.content_type = "image/png"

        class Message:
            def __init__(self, filenames):
                self.attachments = [Attachment(name) for name in filenames]

        self.assertTrue(
            bridge._should_store_visual_description(
                Message(["current.png"]), "Describe this image"
            )
        )
        self.assertFalse(
            bridge._should_store_visual_description(
                Message(["current.png"]), "Compare this with the previous image"
            )
        )
        self.assertFalse(
            bridge._should_store_visual_description(
                Message(["one.png", "two.png"]), "Describe these images"
            )
        )


if __name__ == "__main__":
    unittest.main()
