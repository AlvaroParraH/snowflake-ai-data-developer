from contextlib import redirect_stdout
import importlib.util
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/init_project.py"
SPEC = importlib.util.spec_from_file_location("init_project", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
initializer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(initializer)


class InitializationTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="snowflake-init-test-")
        self.addCleanup(temporary.cleanup)
        self.target = Path(temporary.name) / "project with spaces"
        self.target.mkdir()

    def run_init(self, *arguments: str, no_git: bool = True) -> subprocess.CompletedProcess[str]:
        if no_git and "--no-git" not in arguments:
            arguments = (*arguments, "--no-git")
        return subprocess.run(
            [sys.executable, "-B", str(SCRIPT), "--target", str(self.target), *arguments],
            stdin=subprocess.DEVNULL, capture_output=True, text=True, check=False,
        )

    def test_exact_folders_only_and_idempotency(self) -> None:
        result = self.run_init("--yes")
        self.assertEqual(result.returncode, 0, result.stderr)
        actual = {path.relative_to(self.target) for path in self.target.rglob("*")}
        self.assertEqual(actual, set(initializer.PIPELINE_DIRECTORIES))
        self.assertTrue(all(path.is_dir() for path in self.target.rglob("*")))
        result = self.run_init("--yes")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Already initialized", result.stdout)

    def test_greenfield_initializes_git_after_approval(self) -> None:
        preview = self.run_init("--dry-run", no_git=False)
        self.assertEqual(preview.returncode, 0, preview.stderr)
        self.assertIn("GIT INIT", preview.stdout)
        self.assertFalse((self.target / ".git").exists())
        result = self.run_init("--yes", no_git=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        root = subprocess.run(
            ["git", "-C", str(self.target), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        )
        self.assertEqual(Path(root.stdout.strip()).resolve(), self.target.resolve())
        commits = subprocess.run(
            ["git", "-C", str(self.target), "rev-list", "--count", "HEAD"],
            capture_output=True, text=True, check=False,
        )
        self.assertNotEqual(commits.returncode, 0)
        self.assertTrue((self.target / "pipelines/ingestion/bronze").is_dir())
        self.assertTrue(self.run_init("--yes", no_git=False).returncode == 0)

    def test_existing_git_repository_is_never_reinitialized(self) -> None:
        subprocess.run(["git", "-C", str(self.target), "init", "-q"], check=True)
        result = self.run_init("--yes", no_git=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("already a Git repository", result.stdout)
        self.assertNotIn("GIT INIT", result.stdout)
        self.assertTrue((self.target / ".git").is_dir())

    def test_nested_parent_repository_is_not_created(self) -> None:
        subprocess.run(["git", "-C", str(self.target), "init", "-q"], check=True)
        nested = self.target / "nested-project"
        nested.mkdir()
        result = subprocess.run(
            [sys.executable, "-B", str(SCRIPT), "--target", str(nested), "--yes"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("inside parent repository", result.stdout)
        self.assertFalse((nested / ".git").exists())

    def test_no_git_opt_out(self) -> None:
        result = self.run_init("--yes")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--no-git", result.stdout)
        self.assertFalse((self.target / ".git").exists())

    def test_existing_untracked_project_requires_approval_for_git_init(self) -> None:
        (self.target / "snowflake.yml").write_text("existing project\n")
        result = self.run_init("--yes", no_git=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--allow-existing", result.stderr)
        self.assertFalse((self.target / ".git").exists())
        result = self.run_init("--yes", "--allow-existing", no_git=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.target / ".git").exists())

    def test_declining_confirmation_does_not_initialize_git(self) -> None:
        with patch.object(initializer.shutil, "which", return_value="/usr/bin/git"), patch.object(
            initializer, "git_repository", return_value=None,
        ), patch.object(initializer.sys.stdin, "isatty", return_value=True), patch(
            "builtins.input", return_value="n",
        ), patch.object(initializer.subprocess, "run") as run, redirect_stdout(io.StringIO()):
            self.assertEqual(initializer.initialize(self.target, False, False), 0)
        run.assert_not_called()
        self.assertFalse((self.target / ".git").exists())

    def test_dry_run_and_confirmation_required(self) -> None:
        result = self.run_init("--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        for directory in initializer.PIPELINE_DIRECTORIES:
            self.assertIn(f"MKDIR {directory}", result.stdout)
        self.assertEqual(list(self.target.iterdir()), [])
        result = self.run_init()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--yes", result.stderr)
        self.assertEqual(list(self.target.iterdir()), [])

    def test_preserves_existing_content_and_restores_missing_folder(self) -> None:
        model = self.target / "pipelines/dbt/models/gold/marts/custom.sql"
        model.parent.mkdir(parents=True)
        model.write_bytes(b"Existing implementation\r\n")
        self.assertEqual(self.run_init("--yes", "--allow-existing").returncode, 0)
        missing = self.target / "pipelines/ingestion/bronze"
        missing.rmdir()
        self.assertEqual(self.run_init("--yes", "--allow-existing").returncode, 0)
        self.assertTrue(missing.is_dir())
        self.assertEqual(model.read_bytes(), b"Existing implementation\r\n")

    def test_conflict_is_detected_before_any_creation(self) -> None:
        conflict = self.target / "pipelines/orchestration/airflow"
        conflict.parent.mkdir(parents=True)
        conflict.write_text("Preserve\n")
        before = list(self.target.rglob("*"))
        result = self.run_init("--yes")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(self.target.rglob("*")), before)
        self.assertEqual(conflict.read_text(), "Preserve\n")

    def test_symlink_is_rejected_without_external_changes(self) -> None:
        outside = self.target.parent / "outside"
        outside.mkdir()
        (self.target / "pipelines").symlink_to(outside, target_is_directory=True)
        result = self.run_init("--yes")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("symlink", result.stderr)
        self.assertEqual(list(outside.iterdir()), [])

    def test_home_root_kit_and_missing_targets_rejected(self) -> None:
        for target in (Path.home(), Path("/"), ROOT, self.target / "missing"):
            result = subprocess.run(
                [sys.executable, "-B", str(SCRIPT), "--target", str(target), "--yes"],
                capture_output=True, text=True, check=False,
            )
            self.assertNotEqual(result.returncode, 0, target)

    def test_declining_confirmation_creates_nothing(self) -> None:
        with patch.object(initializer.sys.stdin, "isatty", return_value=True), patch(
            "builtins.input", return_value="n",
        ), redirect_stdout(io.StringIO()):
            self.assertEqual(initializer.initialize(self.target, False, False), 0)
        self.assertEqual(list(self.target.iterdir()), [])

    def test_partial_failure_is_reported(self) -> None:
        mkdir = Path.mkdir
        calls = 0

        def failing_mkdir(path: Path, *args: object, **kwargs: object) -> None:
            nonlocal calls
            calls += 1
            if calls == 2:
                raise PermissionError("Test denial")
            mkdir(path, *args, **kwargs)

        errors = io.StringIO()
        from contextlib import redirect_stderr
        with patch.object(Path, "mkdir", failing_mkdir), redirect_stdout(io.StringIO()), \
                redirect_stderr(errors), self.assertRaises(PermissionError):
            initializer.initialize(self.target, False, True)
        self.assertIn("1 directory operations", errors.getvalue())

    def test_installed_assets_do_not_count_as_existing_project(self) -> None:
        for relative in (".github/skills/example", ".venv", "scripts", "docs"):
            (self.target / relative).mkdir(parents=True)
        (self.target / "scripts/init_project.py").write_text("Installed helper\n")
        (self.target / "docs/copilot-setup.md").write_text("Installed docs\n")
        (self.target / "README.md").write_text("Readme\n")
        result = self.run_init("--detect-only")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("greenfield", result.stdout)
        self.assertFalse((self.target / "pipelines").exists())

    def test_snowflake_and_dbt_configuration_signals(self) -> None:
        for relative in ("snowflake.yml", "snowflake.yaml", "dbt_project.yml",
                         "pipelines/dbt/dbt_project.yml", "docs/project-profile.md"):
            with self.subTest(relative=relative):
                path = self.target / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("Do not read config values\n")
                result = self.run_init("--detect-only")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("brownfield", result.stdout)
                self.assertIn(f"SIGNAL {relative}", result.stdout)
                self.assertNotIn("Do not read config values", result.stdout)
                path.unlink()

    def test_populated_code_directories_are_signals_but_empty_ones_are_not(self) -> None:
        for directory in ("src", "pipelines", "models", "dags", "bronze", "silver", "gold"):
            path = self.target / directory
            path.mkdir()
            self.assertEqual(initializer.detect_project(self.target)["signals"], [])
            file = path / "implementation.sql"
            file.write_text("Existing code\n")
            self.assertIn(f"{directory}/ contains files",
                          initializer.detect_project(self.target)["signals"])
            file.unlink()

    def test_brownfield_requires_explicit_additive_approval(self) -> None:
        path = self.target / "snowflake.yml"
        path.write_text("Existing project\n")
        detected = self.run_init("--detect-only")
        self.assertEqual(detected.returncode, 0)
        preview = self.run_init("--dry-run")
        self.assertEqual(preview.returncode, 0)
        blocked = self.run_init("--yes")
        self.assertNotEqual(blocked.returncode, 0)
        self.assertIn("--allow-existing", blocked.stderr)
        self.assertFalse((self.target / "pipelines").exists())
        approved = self.run_init("--yes", "--allow-existing")
        self.assertEqual(approved.returncode, 0, approved.stderr)
        self.assertEqual(path.read_text(), "Existing project\n")


if __name__ == "__main__":
    unittest.main()
