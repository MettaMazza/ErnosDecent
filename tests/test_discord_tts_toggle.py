import ast
import asyncio
import os
import tempfile
import types
import unittest
from pathlib import Path


BRIDGE_PATH = Path(__file__).resolve().parents[1] / "decent_net" / "discord_bridge.py"


class FakeView:
    def __init__(self, timeout=None):
        self.timeout = timeout


class FakeButton:
    def __init__(self):
        self.label = "Speak"
        self.emoji = "🔊"
        self.disabled = False


class FakeFile:
    def __init__(self, path, filename=None):
        self.path = path
        self.filename = filename


class FakeNotFound(Exception):
    pass


def fake_button_decorator(**_kwargs):
    return lambda function: function


FAKE_DISCORD = types.SimpleNamespace(
    ui=types.SimpleNamespace(
        View=FakeView,
        Button=FakeButton,
        button=fake_button_decorator,
    ),
    ButtonStyle=types.SimpleNamespace(secondary=2),
    Interaction=object,
    File=FakeFile,
    NotFound=FakeNotFound,
)


def load_speak_view(send_daemon_ipc):
    tree = ast.parse(BRIDGE_PATH.read_text(encoding="utf-8"), filename=str(BRIDGE_PATH))
    speak_view = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "SpeakView"
    )
    namespace = {
        "asyncio": asyncio,
        "discord": FAKE_DISCORD,
        "os": os,
        "send_daemon_ipc": send_daemon_ipc,
    }
    exec(
        compile(ast.Module(body=[speak_view], type_ignores=[]), str(BRIDGE_PATH), "exec"),
        namespace,
    )
    return namespace["SpeakView"]


def load_bridge_command(client):
    tree = ast.parse(BRIDGE_PATH.read_text(encoding="utf-8"), filename=str(BRIDGE_PATH))
    command = next(
        node for node in tree.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "_exec_bridge_command"
    )
    namespace = {"client": client}
    exec(
        compile(ast.Module(body=[command], type_ignores=[]), str(BRIDGE_PATH), "exec"),
        namespace,
    )
    return namespace["_exec_bridge_command"]


class FakeResponse:
    def __init__(self):
        self.defer_count = 0

    async def defer(self):
        self.defer_count += 1


class FakeDeliveredMessage:
    def __init__(self):
        self.delete_count = 0

    async def delete(self):
        self.delete_count += 1


class FakeFollowup:
    def __init__(self):
        self.calls = []
        self.deliveries = []

    async def send(self, content=None, **kwargs):
        self.calls.append((content, kwargs))
        if "file" in kwargs:
            delivered = FakeDeliveredMessage()
            self.deliveries.append(delivered)
            return delivered
        return None


class FakeSourceMessage:
    def __init__(self):
        self.edits = []

    async def edit(self, **kwargs):
        self.edits.append(kwargs)


class FakeInteraction:
    def __init__(self):
        self.response = FakeResponse()
        self.followup = FakeFollowup()
        self.message = FakeSourceMessage()


class DiscordTtsToggleTest(unittest.IsolatedAsyncioTestCase):
    async def test_generate_remove_and_replay_uses_one_synthesis(self):
        ipc_calls = []
        with tempfile.NamedTemporaryFile(suffix=".wav") as wav:
            async def send_daemon_ipc(command):
                ipc_calls.append(command)
                return f"tts:ok,path:{wav.name}"

            view = load_speak_view(send_daemon_ipc)("Hello from Echo")
            button = FakeButton()

            first = FakeInteraction()
            await view.speak(first, button)
            self.assertEqual(ipc_calls, ["TTS SPEAK Hello from Echo"])
            self.assertEqual(len(first.followup.deliveries), 1)
            first_delivery = first.followup.deliveries[0]
            self.assertEqual(button.label, "Remove voice")

            second = FakeInteraction()
            await view.speak(second, button)
            self.assertEqual(first_delivery.delete_count, 1)
            self.assertEqual(len(second.followup.deliveries), 0)
            self.assertEqual(button.label, "Replay voice")

            third = FakeInteraction()
            await view.speak(third, button)
            self.assertEqual(len(third.followup.deliveries), 1)
            self.assertEqual(ipc_calls, ["TTS SPEAK Hello from Echo"])
            self.assertEqual(button.label, "Remove voice")

    async def test_click_during_generation_is_coalesced(self):
        ipc_calls = []
        started = asyncio.Event()
        release = asyncio.Event()
        with tempfile.NamedTemporaryFile(suffix=".wav") as wav:
            async def send_daemon_ipc(command):
                ipc_calls.append(command)
                started.set()
                await release.wait()
                return f"tts:ok,path:{wav.name}"

            view = load_speak_view(send_daemon_ipc)("One flight")
            button = FakeButton()
            first = FakeInteraction()
            repeated = FakeInteraction()

            first_task = asyncio.create_task(view.speak(first, button))
            await started.wait()
            await view.speak(repeated, button)
            release.set()
            await first_task

            self.assertEqual(ipc_calls, ["TTS SPEAK One flight"])
            self.assertEqual(len(first.followup.deliveries), 1)
            self.assertEqual(len(repeated.followup.deliveries), 0)
            self.assertIn("already in progress", repeated.followup.calls[0][0])
            self.assertTrue(repeated.followup.calls[0][1]["ephemeral"])

    async def test_read_channel_keeps_durable_marker_inside_bounded_history(self):
        class Author:
            display_name = "tester"

        class Message:
            def __init__(self, content):
                self.author = Author()
                self.content = content

        class Channel:
            def __init__(self):
                self.requested_limit = 0

            def history(self, limit):
                self.requested_limit = limit

                async def records():
                    for index in range(limit):
                        content = "[LESSON: durable_marker | verified]" if index == 137 else f"message {index}"
                        yield Message(content)

                return records()

        channel = Channel()
        client = types.SimpleNamespace(get_channel=lambda channel_id: channel if channel_id == 123 else None)
        execute = load_bridge_command(client)
        result = await execute("read_channel", "123")
        self.assertEqual(channel.requested_limit, 200)
        self.assertIn("durable_marker", result)


if __name__ == "__main__":
    unittest.main()
