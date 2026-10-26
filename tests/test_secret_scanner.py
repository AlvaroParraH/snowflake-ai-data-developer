from contextlib import redirect_stdout
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from test_installer import ROOT, installer


@unittest.skipUnless(shutil.which("git"), "Requires Git")
class SecretScannerTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="snowflake-hook-test-")
        self.addCleanup(temporary.cleanup)
        self.target = Path(temporary.name).resolve()
        fake_bin = self.target / "bin"
        fake_bin.mkdir()
        snow = fake_bin / "snow"
        snow.write_text("#!/bin/sh\nprintf '%s\\n' 'Snowflake CLI test'\n")
        snow.chmod(0o755)
        path_patch = patch.dict(
            os.environ, PATH=str(fake_bin) + os.pathsep + os.environ.get("PATH", ""),
        )
        path_patch.start()
        self.addCleanup(path_patch.stop)
        self.git("init", "-q")
        self.git("config", "user.name", "Installer Test")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        (self.target / "scripts").mkdir()
        shutil.copyfile(ROOT / "scripts/scan_secrets.py", self.target / "scripts/scan_secrets.py")

    def git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["git", "-C", str(self.target), *args],
                              check=check, capture_output=True, text=True)

    def stage(self, content: str, name: str = "config.txt") -> Path:
        file = self.target / name
        file.write_text(content)
        self.git("add", "--", name)
        return file

    def scan(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, str(ROOT / "scripts/scan_secrets.py")],
                              cwd=self.target, capture_output=True, text=True, check=False)

    def enable(self) -> Path:
        with redirect_stdout(io.StringIO()):
            destination = installer.hook_destination(self.target, "git")
            self.assertIsNotNone(destination)
            installer.activate_hook(destination)
        return destination

    def test_empty_index_passes(self) -> None:
        self.assertEqual(self.scan().returncode, 0)

    def test_staged_secret_blocked_even_when_worktree_is_clean(self) -> None:
        secret = "unit" + "test-credential-value"
        file = self.stage('password = "' + secret + '"\n', "file with spaces\nand newline.txt")
        file.write_text("No credential in worktree\n")
        result = self.scan()
        self.assertEqual(result.returncode, 1)
        self.assertIn("credential assignment", result.stderr)
        self.assertNotIn(secret, result.stderr + result.stdout)
        self.assertIn("\\n", result.stderr)

    def test_unstaged_secret_does_not_block_clean_index(self) -> None:
        file = self.stage("Clean staged content\n")
        file.write_text('token = "' + "unit" + "test-token-value" + '"\n')
        self.assertEqual(self.scan().returncode, 0)

    def test_pathspec_characters_and_binary_content_are_scanned(self) -> None:
        file = self.target / "config[1]*.bin"
        file.write_bytes(b"\0password=" + b"x" * 20 + b"\0\n")
        self.git("add", "--", file.name)
        self.assertEqual(self.scan().returncode, 1)

    def test_credential_patterns_are_blocked_without_disclosure(self) -> None:
        examples = (
            "-----BEGIN " + "PRIVATE KEY-----",
            "-----BEGIN " + "ENCRYPTED PRIVATE KEY-----",
            "gh" + "p_" + "a" * 36,
            "AK" + "IA" + "A" * 16,
            "Authorization: " + "Bearer " + "a" * 40,
            "ey" + "J" + "a" * 10 + "." + "b" * 15 + "." + "c" * 15,
            'SNOWFLAKE_PASSWORD="' + "a" * 12 + '"',
            "client_secret: " + "a" * 12,
            "private_key_passphrase = " + "a" * 12,
        )
        for example in examples:
            with self.subTest(kind=example[:4]):
                self.stage(example + "\n")
                result = self.scan()
                self.assertEqual(result.returncode, 1)
                self.assertNotIn(example, result.stderr + result.stdout)

    def test_environment_references_and_oauth_client_ids_pass(self) -> None:
        self.stage('{"Authorization": "Bearer ${env:SNOWFLAKE_MCP_TOKEN}", '
                   '"oauth": {"clientId": "public-client-id"}}\n'
                   'password = ${SNOWFLAKE_PASSWORD}\n'
                   'password = "<your-password>"\n'
                   'password = os.environ["SNOWFLAKE_PASSWORD"]\n')
        self.assertEqual(self.scan().returncode, 0)

    def test_renamed_secret_is_scanned(self) -> None:
        self.stage("Clean\n", "old.txt")
        self.git("commit", "-qm", "Initial")
        self.git("mv", "old.txt", "new.txt")
        self.stage('token = "' + "a" * 15 + '"\n', "new.txt")
        self.assertEqual(self.scan().returncode, 1)

    def test_deleted_secret_is_not_scanned(self) -> None:
        self.stage('token = "' + "a" * 15 + '"\n')
        self.git("commit", "-qm", "Fixture before enabling hook")
        self.git("rm", "config.txt")
        self.assertEqual(self.scan().returncode, 0)

    def test_scan_failure_blocks_with_no_raw_git_errors(self) -> None:
        with tempfile.TemporaryDirectory(prefix="not-a-repo-") as directory:
            result = subprocess.run([sys.executable, str(ROOT / "scripts/scan_secrets.py")],
                                    cwd=directory, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Commit blocked", result.stderr)
        self.assertNotIn("fatal:", result.stderr)

    def test_hook_blocks_real_commit_and_is_idempotent(self) -> None:
        destination = self.enable()
        before = destination.read_bytes()
        self.enable()
        self.assertEqual(destination.read_bytes(), before)
        secret = "a" * 20
        self.stage('password = "' + secret + '"\n')
        result = self.git("commit", "-qm", "Should fail", check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Secret scan blocked", result.stderr)
        self.assertNotIn(secret, result.stderr)
        self.stage("Clean\n")
        self.assertEqual(self.git("commit", "-qm", "Should pass").returncode, 0)

    def test_existing_hook_is_preserved(self) -> None:
        hook = self.target / ".git/hooks/pre-commit"
        hook.write_text("#!/bin/sh\nexit 0\n")
        with self.assertRaisesRegex(ValueError, "existing pre-commit hook differs"):
            installer.hook_destination(self.target, "git")
        self.assertEqual(hook.read_text(), "#!/bin/sh\nexit 0\n")

    def test_existing_hookspath_and_other_hooks_preserved(self) -> None:
        self.git("config", "core.hooksPath", "custom-hooks")
        directory = self.target / "custom-hooks"
        directory.mkdir()
        (directory / "post-commit").write_text("Existing post-commit\n")
        destination = self.enable()
        self.assertEqual(destination, directory / "pre-commit")
        self.assertEqual(self.git("config", "--get", "core.hooksPath").stdout.strip(), "custom-hooks")
        self.assertEqual((directory / "post-commit").read_text(), "Existing post-commit\n")

    def test_symlink_hook_is_rejected(self) -> None:
        outside = self.target / "outside"
        outside.write_text("Preserve\n")
        (self.target / ".git/hooks/pre-commit").symlink_to(outside)
        with self.assertRaisesRegex(ValueError, "Symlink"):
            installer.hook_destination(self.target, "git")
        self.assertEqual(outside.read_text(), "Preserve\n")

    def test_parent_repository_is_not_modified(self) -> None:
        child = self.target / "child"
        child.mkdir()
        with self.assertRaisesRegex(ValueError, "parent Git repository"):
            installer.hook_destination(child, "git")
        self.assertFalse((self.target / ".git/hooks/pre-commit").exists())

    @unittest.skipUnless(shutil.which("uv"), "Requires existing uv")
    def test_installer_enables_hook_and_preserves_other_hooks(self) -> None:
        other = self.target / ".git/hooks/post-commit"
        other.write_text("Preserved post-commit\n")
        with redirect_stdout(io.StringIO()):
            self.assertEqual(installer.install(self.target, False, True, no_install=True,
                                               skip_venv=True), 0)
        self.assertTrue((self.target / ".git/hooks/pre-commit").stat().st_mode & 0o111)
        self.assertEqual(other.read_text(), "Preserved post-commit\n")
        self.stage('password = "' + "x" * 20 + '"\n')
        self.assertNotEqual(self.git("commit", "-qm", "Should fail", check=False).returncode, 0)

    @unittest.skipUnless(shutil.which("uv"), "Requires existing uv")
    def test_conflicting_hook_blocks_installer_before_assets(self) -> None:
        hook = self.target / ".git/hooks/pre-commit"
        hook.write_text("Preserve existing hook\n")
        with redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(ValueError, "existing pre-commit hook differs"):
                installer.install(self.target, False, True, no_install=True, skip_venv=True)
            self.assertFalse((self.target / ".github").exists())
            self.assertEqual(installer.install(self.target, False, True, no_install=True,
                                               skip_venv=True, skip_hooks=True), 0)
        self.assertEqual(hook.read_text(), "Preserve existing hook\n")


if __name__ == "__main__":
    unittest.main()
