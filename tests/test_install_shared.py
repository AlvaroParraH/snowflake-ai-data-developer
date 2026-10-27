from contextlib import redirect_stderr, redirect_stdout
import ast
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("install_shared", ROOT / "scripts/install_shared.py")
assert SPEC is not None and SPEC.loader is not None
installer = importlib.util.module_from_spec(SPEC)
with patch.object(sys, "path", [str(ROOT / "scripts"), *sys.path]):
    SPEC.loader.exec_module(installer)


class SharedInstallationTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="snowflake-shared-test-")
        self.addCleanup(temporary.cleanup)
        self.target = Path(temporary.name).resolve() / "shared kit"

    def run_install(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-B", str(ROOT / "scripts/install_shared.py"),
             "--target", str(self.target), *args],
            capture_output=True, text=True, stdin=subprocess.DEVNULL,
        )

    def kit_python(self) -> Path:
        return self.target / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")

    def test_preview_and_confirmation_do_not_write(self) -> None:
        self.assertEqual(self.run_install("--dry-run").returncode, 0)
        self.assertFalse(self.target.exists())
        result = self.run_install()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--yes", result.stderr)
        self.assertFalse(self.target.exists())

    def test_interactive_cancel_does_not_create_environment(self) -> None:
        with (patch.object(installer.sys.stdin, "isatty", return_value=True),
              patch("builtins.input", return_value="no"),
              patch.object(installer.venv, "EnvBuilder") as builder,
              redirect_stdout(io.StringIO())):
            self.assertEqual(installer.install(self.target, dry_run=False, yes=False), 0)
        builder.assert_not_called()
        self.assertFalse(self.target.exists())

    def test_environment_failure_is_reported_without_success(self) -> None:
        output, errors = io.StringIO(), io.StringIO()
        with (patch.object(installer.venv.EnvBuilder, "create",
                           side_effect=subprocess.CalledProcessError(1, ["ensurepip"])),
              patch.object(sys, "argv", ["install_shared", "--target", str(self.target), "--yes"]),
              redirect_stdout(output), redirect_stderr(errors)):
            self.assertEqual(installer.main(), 1)
        self.assertIn("Installation interrupted", errors.getvalue())
        self.assertIn("Error:", errors.getvalue())
        self.assertNotIn("Shared plugin created.", output.getvalue())
        self.assertTrue((self.target / "plugin.json").exists())

    def test_bundle_contains_skills_agents_and_working_links(self) -> None:
        result = self.run_install("--yes")
        self.assertEqual(result.returncode, 0, result.stderr)
        manifest = json.loads((self.target / "plugin.json").read_text())
        self.assertEqual(manifest["name"], "snowflake-data-developer")
        self.assertEqual(len(list((self.target / "skills").glob("*/SKILL.md"))), 26)
        self.assertEqual(len(list((self.target / "com.github.copilot/agents").glob("*.agent.md"))), 4)
        for document in self.target.rglob("*.md"):
            for link in re.findall(r"\[[^\]]+\]\(([^)]+)\)", document.read_text()):
                if link.startswith(("http:", "https:", "#")):
                    continue
                self.assertTrue((document.parent / link.split("#")[0]).exists(), (document, link))
        self.assertFalse((self.target / "mcp.json").exists())
        self.assertFalse((self.target / "com.github.copilot/hooks").exists())
        result = subprocess.run(
            [str(self.kit_python()), "-I", "-c",
             "import sys, pip; print(sys.prefix); print(sys.base_prefix)"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        prefix, base_prefix = result.stdout.strip().splitlines()
        self.assertEqual(Path(prefix).resolve(), (self.target / ".venv").resolve())
        self.assertNotEqual(prefix, base_prefix)
        wrapper = (self.target / "skills/snowflake-init/SKILL.md").read_text()
        self.assertIn(".venv/bin/python", wrapper)

    def test_refuses_existing_content(self) -> None:
        self.target.mkdir()
        existing = self.target / "personal.txt"
        existing.write_text("preserve")
        result = self.run_install("--yes")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(self.target.iterdir()), [existing])
        self.assertEqual(existing.read_text(), "preserve")

    def test_refuses_symlink_ancestor(self) -> None:
        outside = self.target.parent / "outside"
        outside.mkdir()
        self.target.symlink_to(outside, target_is_directory=True)
        result = self.run_install("--yes")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(outside.iterdir()), [])

    def test_refuses_home_root_and_source_checkout(self) -> None:
        for target in (Path.home(), Path("/"), ROOT):
            with self.subTest(target=target):
                result = self.run_install("--target", str(target), "--yes")
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("dedicated shared plugin directory", result.stderr)

    def test_shell_entry_point_builds_shared_bundle(self) -> None:
        result = subprocess.run(
            ["bash", str(ROOT / "install.sh"), "--shared",
             "--target", str(self.target), "--yes"],
            cwd=self.target.parent, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.target / "plugin.json").exists())

    def test_shared_generators_work_from_unrelated_project(self) -> None:
        self.assertEqual(self.run_install("--yes").returncode, 0)
        project = self.target.parent / "my pipeline"
        project.mkdir()
        result = subprocess.run(
            [str(self.kit_python()), "-B", str(self.target / "scripts/init_project.py"),
             "--target", str(project), "--scaffold", "--yes", "--no-git"],
            cwd=project, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        dbt_root = project / "pipelines/dbt"
        for layer, model, upstream in (
            ("staging", "stg_sales__orders", ["--source-name", "raw_sales", "--source-table", "orders"]),
            ("intermediate", "int_sales__orders", ["--upstream-model", "stg_sales__orders"]),
            ("marts", "fct_sales", ["--upstream-model", "int_sales__orders"]),
        ):
            with self.subTest(layer=layer):
                command = [
                    str(self.kit_python()), "-B", str(self.target / "scripts/scaffold_dbt_model.py"),
                    "--target", str(dbt_root), "--layer", layer, "--domain", "sales",
                    "--model-name", model, *upstream, "--column", "order_id",
                    "--not-null", "order_id",
                ]
                before = {path.relative_to(project): path.read_bytes()
                          for path in project.rglob("*") if path.is_file()}
                preview = subprocess.run([*command, "--dry-run"], cwd=project,
                                         capture_output=True, text=True)
                self.assertEqual(preview.returncode, 0, preview.stderr)
                self.assertEqual(before, {path.relative_to(project): path.read_bytes()
                                         for path in project.rglob("*") if path.is_file()})
                result = subprocess.run([*command, "--yes"], cwd=project,
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertNotEqual(subprocess.run(
                    [*command, "--yes"], cwd=project, capture_output=True,
                ).returncode, 0)
        self.assertEqual(len(list(dbt_root.glob("models/**/sales/*.sql"))), 3)
        self.assertEqual(len(list(dbt_root.glob("models/**/sales/*.yml"))), 3)
        for path in project.rglob("*.py"):
            ast.parse(path.read_text(), filename=str(path), feature_version=(3, 10))
        self.assertTrue((project / "pipelines/dbt/models/gold/marts/sales/fct_sales.sql").exists())
        self.assertFalse((project / "scripts").exists())
        self.assertFalse((project / ".github").exists())
        self.assertFalse((project / ".venv").exists())
        self.assertFalse((project / ".git").exists())

    def test_installed_kit_can_rebuild_complete_bundle(self) -> None:
        self.assertEqual(self.run_install("--yes").returncode, 0)
        rebuilt = self.target.parent / "rebuilt kit"
        result = subprocess.run(
            [str(self.kit_python()), "-B", str(self.target / "scripts/install_shared.py"),
             "--target", str(rebuilt), "--yes"],
            cwd=self.target.parent, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        for relative, content in installer.shared_payloads().items():
            self.assertEqual((rebuilt / relative).read_bytes(), content, relative)
        self.assertTrue((rebuilt / ".venv/pyvenv.cfg").is_file())


if __name__ == "__main__":
    unittest.main()
