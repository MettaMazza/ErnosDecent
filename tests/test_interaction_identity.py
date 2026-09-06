import types
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from decent_net import discord_bridge as bridge


ROOT = Path(__file__).resolve().parents[1]


class InteractionIdentityContractTest(unittest.TestCase):
    def test_discord_envelope_preserves_account_and_location_identity(self):
        original_admins = bridge.ADMIN_IDS
        original_hosts = bridge.HOST_IDS
        original_host_name = bridge.HOST_NAME
        bridge.ADMIN_IDS = {101}
        bridge.HOST_IDS = {101}
        bridge.HOST_NAME = "Maria"
        try:
            author = types.SimpleNamespace(
                id=101,
                name="maria.account",
                global_name="Maria Smith",
                display_name="Maria [host]",
                bot=False,
                roles=[],
            )
            parent = types.SimpleNamespace(id=303, name="general")
            thread = types.SimpleNamespace(id=404, name="project thread", parent_id=303, parent=parent)
            guild = types.SimpleNamespace(id=202, name="ErnosDecent")
            message = types.SimpleNamespace(id=505, channel=thread, guild=guild)

            tags = bridge.build_discord_interaction_tags(author, message)

            self.assertIn("[ACTOR_ID:101]", tags)
            self.assertIn("[ACTOR_USERNAME:maria.account]", tags)
            self.assertIn("[ACTOR_GLOBAL:Maria Smith]", tags)
            self.assertIn("[ACTOR_DISPLAY:Maria (host)]", tags)
            self.assertIn("[ACTOR_IS_HOST:yes]", tags)
            self.assertIn("[HOST_NAME:Maria]", tags)
            self.assertIn("[GUILD_ID:202]", tags)
            self.assertIn("[GUILD_NAME:ErnosDecent]", tags)
            self.assertIn("[CHANNEL_NAME:general]", tags)
            self.assertIn("[THREAD_ID:404]", tags)
            self.assertIn("[THREAD_NAME:project thread]", tags)
        finally:
            bridge.ADMIN_IDS = original_admins
            bridge.HOST_IDS = original_hosts
            bridge.HOST_NAME = original_host_name

    def test_every_transport_field_reaches_the_turn_context_and_prompt(self):
        node = (ROOT / "node.ep").read_text(encoding="utf-8")
        prompt = (ROOT / "decent_agent" / "prompt.ep").read_text(encoding="utf-8")
        for key in (
            "actor_id",
            "actor_username",
            "actor_global_name",
            "actor_display_name",
            "actor_type",
            "actor_is_host",
            "host_name",
            "guild_id",
            "guild_name",
            "channel_name",
            "thread_id",
            "thread_name",
        ):
            self.assertIn(f'map_insert(tctx and "{key}"', node)
        self.assertIn("prompt_interaction_identity_block(ctx)", prompt)
        self.assertIn("prompt_user_knowledge_path(ctx)", prompt)
        self.assertIn("A role such as admin proves authorization, not personal identity", prompt)


if __name__ == "__main__":
    unittest.main()
