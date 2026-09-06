import ast
import asyncio
import os
from pathlib import Path
import re
import stat
import tempfile
import unittest
from unittest import mock


BRIDGE_PATH = Path(__file__).resolve().parents[1] / "decent_net" / "discord_bridge.py"
TOKEN = "0123456789abcdef0123456789abcdef0123456789abcdef"


def load_ipc_namespace():
    tree = ast.parse(BRIDGE_PATH.read_text(encoding="utf-8"), filename=str(BRIDGE_PATH))
    wanted = {"_read_ipc_token", "_send_daemon_ipc_inner", "send_daemon_ipc"}
    functions = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name in wanted
    ]
    namespace = {
        "asyncio": asyncio,
        "os": os,
        "re": re,
        "stat": stat,
        "IPC_DAEMON_PORT": 0,
        "IPC_MAX_REQUEST_BYTES": 65536,
        "IPC_MAX_RESPONSE_BYTES": 67108864,
        "IPC_CONNECT_TIMEOUT_SECONDS": 1.0,
        "IPC_SEND_TIMEOUT_SECONDS": 1.0,
        "IPC_RESPONSE_TIMEOUT_SECONDS": 1.0,
        "IPC_CLOSE_TIMEOUT_SECONDS": 1.0,
    }
    exec(
        compile(ast.Module(body=functions, type_ignores=[]), str(BRIDGE_PATH), "exec"),
        namespace,
    )
    return namespace


class DiscordIpcTokenTests(unittest.TestCase):
    def setUp(self):
        self.namespace = load_ipc_namespace()
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.home = Path(self.tempdir.name)
        self.token_dir = self.home / ".ernosdecent"
        self.token_dir.mkdir()
        self.token_path = self.token_dir / "ipc-token"

    def read_token(self):
        with mock.patch.dict(os.environ, {"HOME": str(self.home)}):
            return self.namespace["_read_ipc_token"]()

    def write_token(self, content=TOKEN, mode=0o600):
        self.token_path.write_text(content, encoding="ascii")
        self.token_path.chmod(mode)

    def test_exact_owner_only_regular_token_is_accepted(self):
        self.write_token()
        self.assertEqual(self.read_token(), TOKEN)

    def test_token_whitespace_is_not_normalized(self):
        self.write_token(TOKEN + "\n")
        self.assertEqual(self.read_token(), "")

    def test_symlink_token_is_rejected(self):
        target = self.token_dir / "actual-token"
        target.write_text(TOKEN, encoding="ascii")
        target.chmod(0o600)
        self.token_path.symlink_to(target)
        self.assertEqual(self.read_token(), "")

    def test_group_readable_token_is_rejected(self):
        self.write_token(mode=0o640)
        self.assertEqual(self.read_token(), "")

    def test_hardlinked_token_is_rejected(self):
        self.write_token()
        os.link(self.token_path, self.token_dir / "second-link")
        self.assertEqual(self.read_token(), "")

    def test_token_close_failure_invalidates_success(self):
        self.write_token()
        real_close = os.close

        def close_then_fail(fd):
            real_close(fd)
            raise OSError("injected close failure")

        with mock.patch.dict(os.environ, {"HOME": str(self.home)}), mock.patch.object(
            os, "close", side_effect=close_then_fail
        ):
            self.assertEqual(self.namespace["_read_ipc_token"](), "")


class DiscordIpcWireTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.namespace = load_ipc_namespace()
        self.namespace["_read_ipc_token"] = lambda: TOKEN

    async def run_server(self, response_parts, command="AI INFER café", hold=0.0):
        loop = asyncio.get_running_loop()
        received = loop.create_future()
        handler_finished = asyncio.Event()

        async def handler(reader, writer):
            try:
                header = await reader.readuntil(b"\n")
                match = re.fullmatch(rb"ERNOS_IPC/1 ([1-9][0-9]*)\n", header)
                if match is None:
                    received.set_exception(AssertionError(f"invalid header: {header!r}"))
                    return
                payload_length = int(match.group(1))
                payload = await reader.readexactly(payload_length)
                received.set_result((header, payload))
                if hold:
                    await asyncio.sleep(hold)
                for part in response_parts:
                    writer.write(part)
                    await writer.drain()
                    await asyncio.sleep(0.005)
            finally:
                writer.close()
                await writer.wait_closed()
                handler_finished.set()

        server = await asyncio.start_server(handler, "127.0.0.1", 0)
        self.namespace["IPC_DAEMON_PORT"] = server.sockets[0].getsockname()[1]
        try:
            result = await self.namespace["_send_daemon_ipc_inner"](command)
            wire = await asyncio.wait_for(received, timeout=1.0)
            await asyncio.wait_for(handler_finished.wait(), timeout=1.0)
            return result, wire
        finally:
            server.close()
            await server.wait_closed()

    async def test_exact_utf8_byte_length_and_fragmented_response(self):
        result, (header, payload) = await self.run_server(
            [b"reply caf", "é complete".encode("utf-8")]
        )
        expected = ("AUTH " + TOKEN + " AI INFER café").encode("utf-8")
        self.assertEqual(header, f"ERNOS_IPC/1 {len(expected)}\n".encode("ascii"))
        self.assertEqual(payload, expected)
        self.assertEqual(result, "reply café complete")

    async def test_nul_command_fails_before_connect(self):
        with mock.patch.object(
            asyncio, "open_connection", new=mock.AsyncMock()
        ) as open_connection:
            result = await self.namespace["_send_daemon_ipc_inner"]("STATUS\x00STOP")
        self.assertEqual(result, "error:ipc_command_invalid")
        open_connection.assert_not_awaited()

    async def test_request_limit_includes_authentication_prefix(self):
        command = "x" * 65536
        with mock.patch.object(
            asyncio, "open_connection", new=mock.AsyncMock()
        ) as open_connection:
            result = await self.namespace["_send_daemon_ipc_inner"](command)
        self.assertEqual(result, "error:ipc_request_size")
        open_connection.assert_not_awaited()

    async def test_absolute_response_timeout_is_visible(self):
        self.namespace["IPC_RESPONSE_TIMEOUT_SECONDS"] = 0.02
        result, _ = await self.run_server([], command="STATUS", hold=0.05)
        self.assertEqual(result, "error:ipc_timeout")

    async def test_response_byte_limit_is_enforced(self):
        self.namespace["IPC_MAX_RESPONSE_BYTES"] = 5
        result, _ = await self.run_server([b"123456"], command="STATUS")
        self.assertEqual(result, "error:ipc_response_oversized")

    async def test_invalid_utf8_response_is_rejected(self):
        result, _ = await self.run_server([b"\xed\xa0\x80"], command="STATUS")
        self.assertEqual(result, "error:ipc_response_encoding")

    async def test_checked_close_failure_overrides_success(self):
        class FakeReader:
            def __init__(self):
                self.reads = [b"ok", b""]

            async def read(self, count):
                return self.reads.pop(0)

        class FakeWriter:
            def write(self, data):
                self.data = data

            async def drain(self):
                return None

            def close(self):
                return None

            async def wait_closed(self):
                raise OSError("injected close failure")

        async def fake_open_connection(host, port):
            return FakeReader(), FakeWriter()

        with mock.patch.object(asyncio, "open_connection", fake_open_connection):
            result = await self.namespace["_send_daemon_ipc_inner"]("STATUS")
        self.assertEqual(result, "error:ipc_close_failed")

    async def test_parent_cancellation_does_not_cancel_the_ipc_outcome(self):
        completed = asyncio.Event()

        async def controlled_inner(command):
            await asyncio.sleep(0.02)
            completed.set()
            return "status:active"

        self.namespace["_send_daemon_ipc_inner"] = controlled_inner
        wrapper = asyncio.create_task(self.namespace["send_daemon_ipc"]("STATUS"))
        await asyncio.sleep(0)
        wrapper.cancel()
        result = await wrapper
        self.assertEqual(result, "status:active")
        self.assertTrue(completed.is_set())


if __name__ == "__main__":
    unittest.main()
