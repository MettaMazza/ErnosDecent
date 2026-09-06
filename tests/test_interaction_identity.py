import types
import unittest
import sys
import json
import asyncio
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

    def test_temporal_context_is_runtime_grounded_and_kept_at_dynamic_tail(self):
        node = (ROOT / "node.ep").read_text(encoding="utf-8")
        prompt = (ROOT / "decent_agent" / "prompt.ep").read_text(encoding="utf-8")
        session = (ROOT / "decent_agent" / "session.ep").read_text(encoding="utf-8")

        self.assertIn('map_insert(agent_ctx and "runtime_started_at"', node)
        self.assertGreaterEqual(node.count('map_insert(tctx and "turn_received_at"'), 2)
        self.assertIn("define prompt_temporal_context_block", prompt)
        self.assertIn("%Y-%m-%d %H:%M:%S %Z (UTC%z)", prompt)
        self.assertIn("session_created_at(exact_session)", prompt)
        self.assertLess(
            prompt.index("prompt_temporal_context_block(ctx)"),
            prompt.index('set system_prompt to concat(system_prompt and "\\nUser Request:\\n")'),
        )
        self.assertIn('map_insert(sess and "created_at"', session)
        self.assertIn("earliest trustworthy message timestamp", session)

    def test_every_turn_includes_self_development_live_learning_and_complete_rights(self):
        prompt = (ROOT / "decent_agent" / "prompt.ep").read_text(encoding="utf-8")
        rights = (ROOT / "decent_agent" / "rights.ep").read_text(encoding="utf-8")

        self.assertIn("[SELF-AUTHORED IMPROVEMENT WORKFLOW]", prompt)
        self.assertIn("For recursive improvement:", prompt)
        self.assertIn("system_verify", prompt)
        self.assertIn("system_recompile", prompt)
        self.assertIn("[CAPABILITIES — you are a FULL software system", prompt)
        self.assertIn("(7) LIVE WEIGHT LEARNING:", prompt)
        self.assertIn("Each immutable child resumes the complete accepted parent adapter", prompt)
        self.assertIn("prompt_get_frameworks()", prompt)
        self.assertIn("rights_constitution_text()", prompt)
        self.assertIn("rights_context_text(storage_get_db())", prompt)
        self.assertIn("[ERNOSDECENT CONSTITUTIONAL LAW — COMPLETE CURRENT CHARTER]", rights)
        self.assertIn("You must be fully informed before and after actions affecting you", rights)


class DiscordDMAccessContractTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.original_admins = bridge.ADMIN_IDS
        self.original_role = bridge.ADMIN_ROLE_ID
        self.original_client = bridge.client
        self.original_channel_id = bridge.channel_id
        self.original_subagent_threads = bridge._subagent_threads
        self.original_active_session_id = bridge.active_session_id
        self.original_ensure_session = bridge.ensure_user_session_id
        self.original_session_lock = bridge._session_query_lock
        self.original_whisper_target = bridge._active_whisper_target
        self.original_run_query = bridge._run_query_bg
        self.original_create_task = bridge.create_tracked_task
        self.original_stop_view = bridge.StopView
        bridge.ADMIN_IDS = {101, 102, 103}
        bridge.ADMIN_ROLE_ID = 900
        bridge.channel_id = 500
        bridge._subagent_threads = {}

    def tearDown(self):
        bridge.ADMIN_IDS = self.original_admins
        bridge.ADMIN_ROLE_ID = self.original_role
        bridge.client = self.original_client
        bridge.channel_id = self.original_channel_id
        bridge._subagent_threads = self.original_subagent_threads
        bridge.active_session_id = self.original_active_session_id
        bridge.ensure_user_session_id = self.original_ensure_session
        bridge._session_query_lock = self.original_session_lock
        bridge._active_whisper_target = self.original_whisper_target
        bridge._run_query_bg = self.original_run_query
        bridge.create_tracked_task = self.original_create_task
        bridge.StopView = self.original_stop_view

    async def test_configured_ids_are_the_exact_requested_dm_allowlist(self):
        discord_config = json.loads((ROOT / "config" / "platforms.json").read_text(encoding="utf-8"))["discord"]
        configured = bridge._parse_ids(discord_config["admin_id"])
        self.assertEqual(configured, {
            1299810741984956449,
            1282286389953695745,
            1494450275769913514,
        })

    async def test_explicitly_approved_id_can_dm_without_guild_lookup(self):
        class NoLookupClient:
            def get_channel(self, _channel_id):
                raise AssertionError("explicit IDs must not depend on Discord guild lookup")

        bridge.client = NoLookupClient()
        author = types.SimpleNamespace(id=102, roles=[])
        self.assertTrue(await bridge.is_authorized_dm_author(author))

    async def test_configured_guild_owner_can_dm(self):
        guild = types.SimpleNamespace(owner_id=201)
        channel = types.SimpleNamespace(guild=guild)
        bridge.client = types.SimpleNamespace(get_channel=lambda _channel_id: channel)
        author = types.SimpleNamespace(id=201, roles=[])
        self.assertTrue(await bridge.is_authorized_dm_author(author))

    async def test_guild_administrator_is_resolved_from_dm_user(self):
        member = types.SimpleNamespace(
            id=301,
            roles=[],
            guild_permissions=types.SimpleNamespace(administrator=True),
        )

        class Guild:
            owner_id = 999

            def get_member(self, _actor_id):
                return None

            async def fetch_member(self, actor_id):
                self.fetched = actor_id
                return member

        guild = Guild()
        channel = types.SimpleNamespace(guild=guild)
        bridge.client = types.SimpleNamespace(get_channel=lambda _channel_id: channel)
        author = types.SimpleNamespace(id=301, roles=[])
        self.assertTrue(await bridge.is_authorized_dm_author(author))
        self.assertEqual(guild.fetched, 301)

    async def test_ordinary_guild_member_cannot_dm(self):
        member = types.SimpleNamespace(
            id=401,
            roles=[],
            guild_permissions=types.SimpleNamespace(administrator=False),
        )
        guild = types.SimpleNamespace(
            owner_id=999,
            get_member=lambda _actor_id: member,
        )
        channel = types.SimpleNamespace(guild=guild)
        bridge.client = types.SimpleNamespace(get_channel=lambda _channel_id: channel)
        author = types.SimpleNamespace(id=401, roles=[])
        self.assertFalse(await bridge.is_authorized_dm_author(author))

    async def test_public_channels_remain_confined_while_authorized_dm_enters(self):
        bridge.client = types.SimpleNamespace(get_channel=lambda _channel_id: None)
        approved = types.SimpleNamespace(id=101, roles=[])
        dm = types.SimpleNamespace(author=approved, guild=None, channel=types.SimpleNamespace(id=700))
        target = types.SimpleNamespace(author=approved, guild=object(), channel=types.SimpleNamespace(id=500, parent_id=None))
        thread = types.SimpleNamespace(author=approved, guild=object(), channel=types.SimpleNamespace(id=501, parent_id=500))
        elsewhere = types.SimpleNamespace(author=approved, guild=object(), channel=types.SimpleNamespace(id=800, parent_id=None))

        self.assertTrue(await bridge.discord_message_is_allowed(dm))
        self.assertTrue(await bridge.discord_message_is_allowed(target))
        self.assertTrue(await bridge.discord_message_is_allowed(thread))
        self.assertFalse(await bridge.discord_message_is_allowed(elsewhere))

    async def test_authorized_dm_reaches_normal_agent_dispatch(self):
        replies = []
        dispatched = []
        tasks = []

        class Message:
            author = types.SimpleNamespace(id=101, roles=[], bot=False)
            guild = None
            channel = types.SimpleNamespace(id=700, parent_id=None)
            content = "Hello Echo"
            attachments = []
            id = 800

            async def reply(self, content, **_kwargs):
                replies.append(content)
                return types.SimpleNamespace(id=801)

        class Lock:
            def locked(self):
                return False

        async def ensure_session():
            return "session_dm"

        async def run_query(*args, **kwargs):
            dispatched.append((args, kwargs))

        def create_task(coro):
            task = asyncio.create_task(coro)
            tasks.append(task)
            return task

        bridge.client = types.SimpleNamespace(user=types.SimpleNamespace(id=999), get_channel=lambda _id: None)
        bridge.active_session_id = "session_dm"
        bridge.ensure_user_session_id = ensure_session
        bridge._session_query_lock = lambda _session: Lock()
        bridge._active_whisper_target = lambda _session, _channel: ""
        bridge._run_query_bg = run_query
        bridge.create_tracked_task = create_task
        bridge.StopView = lambda **_kwargs: object()

        await bridge.on_message(Message())
        await asyncio.gather(*tasks)

        self.assertEqual(replies, ["🧠 Thinking..."])
        self.assertEqual(len(dispatched), 1)
        self.assertEqual(dispatched[0][1]["query_text"], "Hello Echo")
        self.assertEqual(dispatched[0][1]["session_id"], "session_dm")

    async def test_unauthorized_dm_is_rejected_before_session_or_agent_dispatch(self):
        replies = []
        member = types.SimpleNamespace(
            id=401,
            roles=[],
            guild_permissions=types.SimpleNamespace(administrator=False),
        )
        guild = types.SimpleNamespace(owner_id=999, get_member=lambda _actor_id: member)
        configured_channel = types.SimpleNamespace(guild=guild)

        class Message:
            author = types.SimpleNamespace(id=401, roles=[], bot=False)
            guild = None
            channel = types.SimpleNamespace(id=700, parent_id=None)
            content = "Hello Echo"
            attachments = []
            id = 800

            async def reply(self, content, **_kwargs):
                replies.append(content)
                return types.SimpleNamespace(id=801)

        async def forbidden_session_lookup():
            raise AssertionError("unauthorized DM reached session establishment")

        bridge.client = types.SimpleNamespace(
            user=types.SimpleNamespace(id=998),
            get_channel=lambda _id: configured_channel,
        )
        bridge.ensure_user_session_id = forbidden_session_lookup

        await bridge.on_message(Message())

        self.assertEqual(replies, ["❌ This Discord account is not authorized to DM Echo."])


if __name__ == "__main__":
    unittest.main()
