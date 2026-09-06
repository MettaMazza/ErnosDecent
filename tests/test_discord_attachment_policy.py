import ast
import asyncio
import os
import tempfile
import unittest
from pathlib import Path


BRIDGE_PATH = Path(__file__).resolve().parents[1] / "decent_net" / "discord_bridge.py"
POLICY_NAMES = {
    "_ATTACH_DENY_MARKERS",
    "_ATTACH_DENY_BASENAMES",
    "_ATTACH_DENY_SUFFIXES",
    "_ATTACH_PRIVATE_KEY_NAMES",
    "_ATTACH_MAX_BYTES",
    "_attachment_path_denied",
    "_attachment_safe_canonical",
    "post_attachment",
    "build_discord_files",
}


def load_policy():
    """Load only the bridge's pure path policy, without starting Discord."""
    tree = ast.parse(BRIDGE_PATH.read_text(encoding="utf-8"), filename=str(BRIDGE_PATH))
    selected = []
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(target, ast.Name) and target.id in POLICY_NAMES for target in targets):
                selected.append(node)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in POLICY_NAMES:
            selected.append(node)
    namespace = {"os": os}
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(BRIDGE_PATH), "exec"), namespace)
    return namespace


class FakeFile:
    def __init__(self, path, filename=None):
        self.path = path
        self.filename = filename


class FakeDiscord:
    File = FakeFile


class FakeMessage:
    def __init__(self, message_id):
        self.id = message_id


class FakeChannel:
    def __init__(self):
        self.calls = []

    async def send(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return FakeMessage(len(self.calls))


class DiscordAttachmentPolicyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = load_policy()
        cls.denied = staticmethod(cls.policy["_attachment_path_denied"])
        cls.canonical = staticmethod(cls.policy["_attachment_safe_canonical"])

    def test_product_credentials_and_node_database_sidecars_are_denied(self):
        for path in (
            "config/platforms.json",
            r"C:\repo\config\platforms.json",
            "~/.ernosdecent/node.db",
            "~/.ernosdecent/node.db-wal",
            "~/.ernosdecent/node.db-shm",
            "~/.ernosdecent/node.db-journal",
            "~/.ernosdecent/keys/identity.key",
            "~/.ernosdecent/ipc-token",
        ):
            with self.subTest(path=path):
                self.assertTrue(self.denied(path))

    def test_package_vcs_and_cloud_credentials_are_denied(self):
        for path in (
            "~/.npmrc",
            "~/.pypirc",
            "~/.git-credentials",
            "~/.aws/credentials",
            "~/.config/gcloud/application_default_credentials.json",
            "/run/secrets/service-account.json",
            "/run/secrets/credentials.yaml",
        ):
            with self.subTest(path=path):
                self.assertTrue(self.denied(path))

    def test_private_key_formats_and_names_are_denied(self):
        for path in (
            "client.pem",
            "client.key",
            "client.p12",
            "client.pfx",
            "~/.ssh/id_rsa",
            "keys/id_ed25519.backup",
            "~/Library/Keychains/login.keychain-db",
        ):
            with self.subTest(path=path):
                self.assertTrue(self.denied(path))

    def test_dotenv_matching_does_not_deny_ordinary_similar_names(self):
        self.assertTrue(self.denied("/project/.env"))
        self.assertTrue(self.denied("/project/.env.production"))
        self.assertFalse(self.denied("/project/.environment.md"))

    def test_ordinary_documents_are_not_denied(self):
        for path in (
            "/project/report.pdf",
            "/project/client.pem.txt",
            "/project/config/platforms.json.example",
            "/project/docs/node.db-guide.md",
            "/project/credentials.md",
        ):
            with self.subTest(path=path):
                self.assertFalse(self.denied(path))

    def test_safe_looking_symlink_to_secret_is_refused_by_send_path(self):
        with tempfile.TemporaryDirectory(prefix="ernos-attach-symlink-") as tmp:
            secret = Path(tmp) / ".env"
            secret.write_text("TOKEN=must-not-leave", encoding="utf-8")
            alias = Path(tmp) / "report.txt"
            alias.symlink_to(secret)
            self.assertFalse(self.denied(str(alias)))
            self.assertEqual(self.canonical(str(alias)), "")

            namespace = load_policy()
            namespace["discord"] = FakeDiscord
            channel = FakeChannel()
            sent_ids = asyncio.run(namespace["post_attachment"](channel, str(alias)))
            self.assertEqual(sent_ids, [1])
            self.assertEqual(len(channel.calls), 1)
            self.assertNotIn("file", channel.calls[0][1])

    def test_bundled_symlink_to_secret_releases_exact_claim(self):
        with tempfile.TemporaryDirectory(prefix="ernos-attach-bundle-") as tmp:
            secret = Path(tmp) / "client.pem"
            secret.write_text("private", encoding="utf-8")
            alias = Path(tmp) / "chart.txt"
            alias.symlink_to(secret)
            namespace = load_policy()
            namespace["discord"] = FakeDiscord
            released = []

            async def release(claim, reason):
                released.append((claim, reason))
                return True

            namespace["db_release_trace_event"] = release
            claim = {"id": 17, "claim_token": "exact-token"}
            files, live_claims = asyncio.run(
                namespace["build_discord_files"]([str(alias)], [claim])
            )
            self.assertEqual(files, [])
            self.assertEqual(live_claims, [])
            self.assertEqual(released, [(claim, "attachment_requires_policy_notice")])


if __name__ == "__main__":
    unittest.main()
