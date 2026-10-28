from contextlib import redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
with patch.object(sys, "path", [str(ROOT / "scripts"), *sys.path]):
    import installation_state as state


class InstallationUpdateTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="snowflake-update-test-")
        self.addCleanup(temporary.cleanup)
        self.target = Path(temporary.name).resolve() / "kit with spaces"
        self.target.mkdir()
        self.old = {
            Path("docs/guide.md"): b"old guidance\n",
            Path("docs/obsolete.md"): b"obsolete\n",
        }

    def install(self, mode: str = "project") -> None:
        for path, content in self.old.items():
            state.atomic_write(self.target, path, content, None)
        state.save_manifest(self.target, state.prepare_manifest(self.target, self.old, mode))

    def snapshot(self) -> dict[str, bytes]:
        return {p.relative_to(self.target).as_posix(): p.read_bytes()
                for p in self.target.rglob("*") if p.is_file()}

    def update(self, files: dict[Path, bytes], *, mode: str = "project",
               dry_run: bool = False, yes: bool = True) -> str:
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(state.update(self.target, files, mode, dry_run=dry_run, yes=yes), 0)
        return output.getvalue()

    def test_replace_create_remove_backup_and_idempotency_in_both_modes(self) -> None:
        for mode in ("project", "shared"):
            with self.subTest(mode=mode):
                self.target = self.target.parent / mode
                self.target.mkdir()
                self.install(mode)
                state.atomic_write(self.target, Path("personal.txt"), b"keep", None)
                state.atomic_write(self.target, Path(".vscode/mcp.json"), b"private config", None)
                state.atomic_write(self.target, Path(".venv/marker"), b"environment", None)
                old_manifest = (self.target / state.MANIFEST).read_bytes()
                files = {Path("docs/guide.md"): b"new guidance\n", Path("docs/new.md"): b"new\n"}
                before = self.snapshot()
                output = self.update(files, mode=mode, dry_run=True)
                self.assertIn("REPLACE docs/guide.md", output)
                self.assertIn("DELETE docs/obsolete.md", output)
                self.assertIn("CREATE docs/new.md", output)
                self.assertEqual(self.snapshot(), before)
                self.update(files, mode=mode)
                backups = list((self.target / state.BACKUPS).iterdir())
                self.assertEqual(len(backups), 1)
                self.assertEqual((backups[0] / "docs/guide.md").read_bytes(), self.old[Path("docs/guide.md")])
                self.assertEqual((backups[0] / "docs/obsolete.md").read_bytes(), b"obsolete\n")
                self.assertEqual((backups[0] / state.MANIFEST).read_bytes(), old_manifest)
                self.assertFalse((backups[0] / ".vscode").exists())
                self.assertFalse((self.target / "docs/obsolete.md").exists())
                self.assertEqual((self.target / "personal.txt").read_bytes(), b"keep")
                self.assertEqual((self.target / ".vscode/mcp.json").read_bytes(), b"private config")
                self.assertEqual((self.target / ".venv/marker").read_bytes(), b"environment")
                before = self.snapshot()
                self.assertIn("Already up to date", self.update(files, mode=mode))
                self.assertEqual(self.snapshot(), before)

    def test_modified_files_abort_entire_update_without_writes(self) -> None:
        self.install()
        for name in ("guide", "obsolete"):
            with self.subTest(name=name):
                path = Path(f"docs/{name}.md")
                (self.target / path).write_bytes(b"local edit")
                before = self.snapshot()
                with redirect_stdout(io.StringIO()), self.assertRaisesRegex(ValueError, "Locally modified"):
                    state.update(self.target, {Path("docs/guide.md"): b"new"}, "project",
                                 dry_run=False, yes=True)
                self.assertEqual(self.snapshot(), before)
                (self.target / path).write_bytes(self.old[path])

    def test_new_untracked_collision_and_directory_collision_are_rejected(self) -> None:
        self.install()
        new = Path("docs/new.md")
        (self.target / new).write_bytes(b"personal")
        with redirect_stdout(io.StringIO()), self.assertRaisesRegex(ValueError, "untracked"):
            state.update(self.target, {**self.old, new: b"kit"}, "project", dry_run=False, yes=True)
        (self.target / new).unlink()
        (self.target / new).mkdir()
        with self.assertRaisesRegex(ValueError, "Not a regular file"):
            self.update({**self.old, new: b"kit"})

    def test_missing_managed_file_is_restored(self) -> None:
        self.install()
        (self.target / "docs/guide.md").unlink()
        self.update(self.old)
        self.assertEqual((self.target / "docs/guide.md").read_bytes(), b"old guidance\n")

    def test_instruction_block_update_preserves_user_prefix_and_suffix(self) -> None:
        old_block = state.START + b"\nold\n" + state.END
        new_block = state.START + b"\nnew\n" + state.END
        self.old[state.INSTRUCTIONS] = b"user prefix\n" + old_block + b"\nuser suffix\n"
        self.install()
        # Users may edit their own instructions outside the tracked block.
        original = b"changed prefix\n" + old_block + b"\nchanged suffix\n"
        (self.target / state.INSTRUCTIONS).write_bytes(original)
        self.update({**self.old, state.INSTRUCTIONS: new_block + b"\n"})
        self.assertEqual((self.target / state.INSTRUCTIONS).read_bytes(),
                         b"changed prefix\n" + new_block + b"\nchanged suffix\n")
        backup = next((self.target / state.BACKUPS).iterdir())
        self.assertEqual((backup / state.INSTRUCTIONS).read_bytes(), original)

    def test_instruction_block_edit_is_not_overwritten(self) -> None:
        self.old[state.INSTRUCTIONS] = state.START + b"\nold\n" + state.END
        self.install()
        (self.target / state.INSTRUCTIONS).write_bytes(state.START + b"\ncustom\n" + state.END)
        before = self.snapshot()
        with redirect_stdout(io.StringIO()), self.assertRaisesRegex(ValueError, "Locally modified"):
            self.update(self.old)
        self.assertEqual(self.snapshot(), before)

    def test_legacy_installation_is_not_adopted_blindly(self) -> None:
        (self.target / "personal.txt").write_text("keep")
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, "older/untracked"):
            self.update(self.old)
        self.assertEqual(self.snapshot(), before)

    def test_manifest_validation_rejects_unsafe_paths_and_modes(self) -> None:
        for name in ("../outside.md", "/docs/outside.md", "docs/../../outside.md",
                     ".venv/secret.md", ".vscode/mcp.json", "scripts/personal.py",
                     ".git/config", ".envrc", "docs//guide.md"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                state.load_records(json.dumps({"version": 1, "mode": "project",
                                               "files": {name: "a" * 64}}).encode(), "project")
        with self.assertRaisesRegex(ValueError, "mode"):
            state.load_records(state.manifest_content(self.old, "shared"), "project")
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            state.load_records(b'{"version":1,"version":1}', "project")

    def test_symlink_asset_manifest_and_backup_directory_are_rejected(self) -> None:
        self.install()
        external = self.target.parent / "external"
        external.mkdir()
        for relative in (Path("docs/guide.md"), state.MANIFEST, state.BACKUPS):
            with self.subTest(relative=relative):
                path = self.target / relative
                before = path.read_bytes() if path.exists() else None
                if path.exists():
                    path.unlink()
                path.symlink_to(external, target_is_directory=True)
                with self.assertRaisesRegex(ValueError, "symlink"):
                    self.update({Path("docs/guide.md"): b"new"})
                path.unlink()
                if before is not None:
                    path.write_bytes(before)
                self.assertEqual(list(external.iterdir()), [])

    def test_noninteractive_requires_yes_and_cancel_is_noop(self) -> None:
        self.install()
        before = self.snapshot()
        with patch.object(state.sys.stdin, "isatty", return_value=False):
            with redirect_stdout(io.StringIO()), self.assertRaisesRegex(ValueError, "--yes"):
                self.update({Path("docs/guide.md"): b"new"}, yes=False)
        with (patch.object(state.sys.stdin, "isatty", return_value=True),
              patch("builtins.input", return_value="no")):
            self.update({Path("docs/guide.md"): b"new"}, yes=False)
        self.assertEqual(self.snapshot(), before)

    def test_edit_after_preview_is_not_overwritten(self) -> None:
        self.install()

        def consent(prompt: str) -> str:
            (self.target / "docs/guide.md").write_bytes(b"concurrent edit")
            return "yes"

        with (patch.object(state.sys.stdin, "isatty", return_value=True),
              patch("builtins.input", side_effect=consent),
              redirect_stdout(io.StringIO()),
              self.assertRaisesRegex(ValueError, "changed after preview")):
            self.update({Path("docs/guide.md"): b"new"}, yes=False)
        self.assertFalse((self.target / state.BACKUPS).exists())
        self.assertEqual((self.target / "docs/guide.md").read_bytes(), b"concurrent edit")

    def test_backup_failure_prevents_all_replacement(self) -> None:
        self.install()
        before = self.snapshot()
        with (patch.object(state, "atomic_write", side_effect=OSError("backup failed")),
              redirect_stdout(io.StringIO()), self.assertRaisesRegex(OSError, "backup failed")):
            self.update({Path("docs/guide.md"): b"new"})
        self.assertEqual(self.snapshot(), before)

    def test_partial_failure_is_explicit_and_retains_backups_and_old_manifest(self) -> None:
        self.install()
        original_write = state.atomic_write
        old_manifest = (self.target / state.MANIFEST).read_bytes()

        def fail_manifest(target: Path, relative: Path, content: bytes, before: bytes | None) -> None:
            if relative == state.MANIFEST:
                raise OSError("manifest write failed")
            original_write(target, relative, content, before)

        errors = io.StringIO()
        with (patch.object(state, "atomic_write", side_effect=fail_manifest),
              redirect_stderr(errors), redirect_stdout(io.StringIO()),
              self.assertRaisesRegex(OSError, "manifest write failed")):
            self.update({Path("docs/guide.md"): b"new"})
        self.assertIn("interrupted", errors.getvalue())
        self.assertEqual((self.target / state.MANIFEST).read_bytes(), old_manifest)
        backup = next((self.target / state.BACKUPS).iterdir())
        self.assertEqual((backup / "docs/guide.md").read_bytes(), b"old guidance\n")


if __name__ == "__main__":
    unittest.main()
