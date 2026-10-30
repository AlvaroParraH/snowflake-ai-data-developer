import argparse
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
with patch.object(sys, "path", [str(ROOT / "scripts"), *sys.path]):
    setup = importlib.import_module("setup_mcp")


class SharedMCPTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="snowflake-mcp-test-")
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name).resolve()
        self.bin = self.directory / "bin"
        self.bin.mkdir()
        snow = self.bin / "snow"
        snow.write_text(f"#!{sys.executable}\nimport sys\n"
                        "if sys.argv[1:] == ['--version']: print('Snowflake CLI 3.0-test')\n"
                        "else: raise SystemExit(2)\n")
        snow.chmod(0o755)
        path = patch.dict(os.environ, {"PATH": str(self.bin) + os.pathsep
                                       + os.environ.get("PATH", "")})
        path.start()
        self.addCleanup(path.stop)
        self.config = self.directory / "user profile/mcp.json"
        self.arguments = [
            "--mcp-config", str(self.config),
            "--mcp-endpoint", "https://example.com/approved-mcp",
            "--mcp-auth", "oauth", "--mcp-oauth-client-id", "public-client",
            "--mcp-approved",
        ]

    def run_setup(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-B", str(ROOT / "scripts/setup_mcp.py"), *args],
            capture_output=True, text=True, stdin=subprocess.DEVNULL,
        )

    def test_preview_and_missing_confirmation_do_not_write(self) -> None:
        result = self.run_setup(*self.arguments, "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(str(self.config), result.stdout)
        self.assertIn("public-client", result.stdout)
        self.assertFalse(self.config.parent.exists())
        self.assertNotEqual(self.run_setup(*self.arguments).returncode, 0)
        self.assertFalse(self.config.exists())

    def test_user_merge_preserves_other_servers_and_is_idempotent(self) -> None:
        self.config.parent.mkdir()
        original = {"servers": {"other": {"command": "existing-server"}}, "inputs": []}
        self.config.write_text(json.dumps(original))
        result = self.run_setup(*self.arguments, "--yes")
        self.assertEqual(result.returncode, 0, result.stderr)
        config = json.loads(self.config.read_text())
        self.assertEqual(config["servers"]["other"], original["servers"]["other"])
        self.assertEqual(config["inputs"], [])
        self.assertEqual(config["servers"]["snowflake"]["oauth"], {"clientId": "public-client"})
        before = self.config.read_bytes()
        self.assertEqual(self.run_setup(*self.arguments, "--yes").returncode, 0)
        self.assertEqual(self.config.read_bytes(), before)

    def test_explicit_admin_approval_required(self) -> None:
        result = self.run_setup(*self.arguments[:-1], "--yes")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--mcp-approved", result.stderr)
        self.assertFalse(self.config.exists())

    def test_invalid_or_conflicting_configuration_is_preserved(self) -> None:
        self.config.parent.mkdir()
        for existing in ('{// JSONC\n}', '{"servers": {}, "servers": {}}',
                         '{"servers": {"snowflake": {"url": "https://other.example"}}}'):
            with self.subTest(existing=existing):
                self.config.write_text(existing)
                result = self.run_setup(*self.arguments, "--yes")
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.config.read_text(), existing)

    def test_rejects_symlink_config(self) -> None:
        self.config.parent.mkdir()
        original = self.directory / "original.json"
        original.write_text("{}")
        self.config.symlink_to(original)
        self.assertNotEqual(self.run_setup(*self.arguments, "--yes").returncode, 0)
        self.assertEqual(original.read_text(), "{}")

    def test_rejects_symlink_parent_without_writing_outside(self) -> None:
        outside = self.directory / "outside"
        outside.mkdir()
        self.config.parent.symlink_to(outside, target_is_directory=True)
        result = self.run_setup(*self.arguments, "--yes")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(outside.iterdir()), [])

    def test_rejects_nondirectory_parent_before_write(self) -> None:
        self.config.parent.write_text("preserve")
        result = self.run_setup(*self.arguments, "--yes")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not a directory", result.stderr.lower())
        self.assertEqual(self.config.parent.read_text(), "preserve")

    def test_file_change_after_preview_is_preserved(self) -> None:
        parser = argparse.ArgumentParser()
        setup.add_mcp_arguments(parser)
        parser.add_argument("--dry-run", action="store_true")
        plan = setup.plan_mcp(parser.parse_args(self.arguments))
        self.assertIsNotNone(plan)
        assert plan is not None
        self.config.parent.mkdir()
        self.config.write_text('{"servers":{"new":{"command":"preserve"}}}')
        with self.assertRaisesRegex(ValueError, "changed after preview"):
            plan.apply()
        self.assertEqual(self.config.read_text(), '{"servers":{"new":{"command":"preserve"}}}')

    def test_parent_swapped_after_preview_is_rejected(self) -> None:
        parser = argparse.ArgumentParser()
        setup.add_mcp_arguments(parser)
        parser.add_argument("--dry-run", action="store_true")
        plan = setup.plan_mcp(parser.parse_args(self.arguments))
        assert plan is not None
        outside = self.directory / "outside"
        outside.mkdir()
        self.config.parent.symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symlink"):
            plan.apply()
        self.assertEqual(list(outside.iterdir()), [])

    def test_pending_preview_does_not_ignore_partial_arguments(self) -> None:
        for script in ("setup_mcp.py", "install_shared.py"):
            with self.subTest(script=script):
                extra = ["--target", str(self.directory / "shared-kit")] if script == "install_shared.py" else []
                result = subprocess.run(
                    [sys.executable, "-B", str(ROOT / "scripts" / script),
                     "--setup-mcp", "--dry-run", "--mcp-config", "relative.json", *extra],
                    capture_output=True, text=True, stdin=subprocess.DEVNULL,
                )
                self.assertNotEqual(result.returncode, 0)

    def test_rejects_mismatched_formats_and_nonobject_roots(self) -> None:
        self.config.parent.mkdir()
        for existing in ('[]', 'null', '{"servers": []}', '{"mcpServers": {}}'):
            with self.subTest(existing=existing):
                self.config.write_text(existing)
                result = self.run_setup(*self.arguments, "--yes")
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.config.read_text(), existing)

    def test_rejects_relative_path_and_credential_bearing_endpoint(self) -> None:
        for extra in (["--mcp-config", "relative.json"],
                      ["--mcp-endpoint", "https://example.com/mcp?token=<placeholder>"]):
            with self.subTest(extra=extra):
                self.assertNotEqual(self.run_setup(*self.arguments, *extra, "--yes").returncode, 0)
                self.assertFalse(self.config.exists())

    def test_bearer_uses_environment_reference(self) -> None:
        args = self.arguments[:4] + ["--mcp-auth", "bearer", "--mcp-approved", "--yes"]
        result = self.run_setup(*args)
        self.assertEqual(result.returncode, 0, result.stderr)
        entry = json.loads(self.config.read_text())["servers"]["snowflake"]
        self.assertEqual(entry["headers"]["Authorization"], "Bearer ${env:SNOWFLAKE_MCP_TOKEN}")
        self.assertNotIn("oauth", entry)

    def test_copilot_global_preserves_entries_and_uses_portable_format(self) -> None:
        self.config.parent.mkdir()
        self.config.write_text('{"mcpServers": {"other": {"command": "existing"}}}')
        result = self.run_setup(
            *self.arguments[:4], "--mcp-format", "copilot", "--mcp-auth", "bearer",
            "--mcp-tool", "approved_metadata", "--mcp-approved", "--yes",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        config = json.loads(self.config.read_text())
        self.assertNotIn("servers", config)
        entry = config["mcpServers"]["snowflake"]
        self.assertEqual(entry["headers"]["Authorization"], "Bearer ${SNOWFLAKE_MCP_TOKEN}")
        self.assertEqual(entry["tools"], ["approved_metadata"])
        self.assertEqual(config["mcpServers"]["other"], {"command": "existing"})

    def test_copilot_rejects_oauth_missing_tools_and_wildcards(self) -> None:
        for extra in ([], ["--mcp-auth", "bearer"],
                      ["--mcp-auth", "bearer", "--mcp-tool", "*"]):
            with self.subTest(extra=extra):
                result = self.run_setup(*self.arguments, "--mcp-format", "copilot", *extra, "--yes")
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self.config.exists())

    def test_shared_install_mcp_preview_is_nonmutating(self) -> None:
        target = self.directory / "shared-kit"
        result = subprocess.run(
            [sys.executable, "-B", str(ROOT / "scripts/install_shared.py"),
             "--target", str(target), *self.arguments, "--dry-run"],
            capture_output=True, text=True, stdin=subprocess.DEVNULL,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(str(self.config), result.stdout)
        self.assertFalse(target.exists())
        self.assertFalse(self.config.exists())

    def test_shared_install_writes_user_config_not_project_config(self) -> None:
        target = self.directory / "shared-kit"
        result = subprocess.run(
            [sys.executable, "-B", str(ROOT / "scripts/install_shared.py"),
             "--target", str(target), *self.arguments, "--yes"],
            capture_output=True, text=True, stdin=subprocess.DEVNULL,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.config.is_file())
        self.assertTrue((target / "scripts/setup_mcp.py").is_file())
        self.assertFalse((target / ".vscode/mcp.json").exists())
        self.assertFalse((target / "mcp.json").exists())


if __name__ == "__main__":
    unittest.main()
