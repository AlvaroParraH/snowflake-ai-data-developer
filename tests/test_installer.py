from contextlib import ExitStack, redirect_stdout
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/install_kit.py"
SPEC = importlib.util.spec_from_file_location("install_kit", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)
PIPELINE_LEAVES = (
    "pipelines/ingestion/bronze",
    "pipelines/dbt/models/silver/staging",
    "pipelines/dbt/models/silver/intermediate",
    "pipelines/dbt/models/gold/marts",
    "pipelines/orchestration/airflow/dags",
)


class InstallerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="snowflake-kit-test-")
        self.addCleanup(self.temporary.cleanup)
        self.target = Path(self.temporary.name) / "project with spaces"
        self.target.mkdir()
        self.bin = Path(self.temporary.name) / "bin"
        self.bin.mkdir()
        uv = self.bin / "uv"
        uv.write_text(
            f"#!{sys.executable}\n"
            "import sys, venv\n"
            "if sys.argv[1:] == ['--version']:\n"
            "    print('uv 0.0-test')\n"
            "elif sys.argv[1] == 'venv':\n"
            "    venv.EnvBuilder(with_pip=False).create(sys.argv[-1])\n"
            "else:\n"
            "    raise SystemExit(2)\n"
        )
        uv.chmod(0o755)
        git = self.bin / "git"
        git.write_text(f"#!{sys.executable}\nimport sys\n"
                       "if sys.argv[1:] == ['--version']: print('git version test')\n"
                       "else: raise SystemExit(128)\n")
        git.chmod(0o755)
        snow = self.bin / "snow"
        snow.write_text(f"#!{sys.executable}\nimport sys\n"
                        "if sys.argv[1:] == ['--version']: print('Snowflake CLI 3.0-test')\n"
                        "else: raise SystemExit(2)\n")
        snow.chmod(0o755)
        self.environment = dict(os.environ, PATH=str(self.bin) + os.pathsep
                                + os.environ.get("PATH", ""))

    def run_installer(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--target", str(self.target), *arguments],
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
            env=self.environment,
            check=False,
        )

    def snapshot(self) -> dict[str, bytes]:
        return {
            str(file.relative_to(self.target)): file.read_bytes()
            for file in self.target.rglob("*")
            if file.is_file()
        }

    def test_fresh_install_links_and_idempotency(self) -> None:
        result = self.run_installer("--yes")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(list((self.target / ".github/skills").glob("*/SKILL.md"))), 15)
        self.assertTrue(
            (self.target / ".github/skills/snowflake-compute-tagging/SKILL.md").is_file()
        )
        self.assertTrue((self.target / ".github/skills/snowflake-tasks/SKILL.md").is_file())
        self.assertFalse((self.target / "skills").exists())
        self.assertEqual(
            len(list((self.target / ".github/agents").glob("*.agent.md"))), 4
        )
        self.assertTrue(
            (self.target / ".github/agents/snowflake-cost-investigator.agent.md").is_file()
        )
        for name in ("snowflake-query-optimizer", "snowflake-naming-auditor",
                     "snowflake-data-profiler"):
            self.assertTrue(
                (self.target / f".github/agents/{name}.agent.md").is_file()
            )
        for skill in (self.target / ".github/skills").glob("*/SKILL.md"):
            content = skill.read_text()
            self.assertIn(f"\nname: {skill.parent.name}\n", content)
            self.assertRegex(content, r'\A---\nname: [^\n]+\ndescription: "[^\n]+"\n---\n')
            self.assertGreater(len(content.splitlines()), 50, skill)
            self.assertNotIn("../../../skills/", content)
        self.assertEqual(len(list((self.target / ".github/prompts").glob("*.prompt.md"))), 11)
        self.assertTrue((self.target / ".github/prompts/snowflake-audit.prompt.md").is_file())
        self.assertTrue((self.target / ".github/prompts/snowflake-check.prompt.md").is_file())
        self.assertTrue(
            (self.target / ".github/prompts/snowflake-connection-setup.prompt.md").is_file()
        )
        self.assertTrue(
            (self.target / ".github/prompts/snowflake-kit-status.prompt.md").is_file()
        )
        self.assertTrue(
            (self.target / ".github/prompts/snowflake-kit-update.prompt.md").is_file()
        )
        self.assertTrue((self.target / ".github/prompts/snowflake-pipeline.prompt.md").is_file())
        self.assertTrue((self.target / ".github/prompts/snowflake-dbt-model.prompt.md").is_file())
        self.assertTrue((self.target / "scripts/init_project.py").is_file())
        self.assertTrue((self.target / "scripts/scaffold_snowflake_project.py").is_file())
        self.assertTrue((self.target / "scripts/scaffold_dbt_model.py").is_file())
        self.assertFalse((self.target / ".github/github-app.yml").exists())
        self.assertFalse((self.target / "pyproject.toml").exists())
        self.assertTrue((self.target / ".venv/pyvenv.cfg").is_file())
        self.assertFalse((self.target / "uv.lock").exists())
        self.assertFalse((self.target / "pipelines").exists())
        for file in self.target.rglob("*.md"):
            for link in re.findall(r"\[[^\]]+\]\(([^)]+)\)", file.read_text()):
                if not link.startswith(("https:", "http:", "#")):
                    self.assertTrue((file.parent / link.split("#")[0]).exists(), (file, link))
        before = self.snapshot()
        before_directories = sorted(p.relative_to(self.target) for p in self.target.rglob("*")
                                    if p.is_dir())
        result = self.run_installer("--yes")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(before, self.snapshot())
        self.assertEqual(before_directories,
                         sorted(p.relative_to(self.target) for p in self.target.rglob("*")
                                if p.is_dir()))
        self.assertIn("Already installed", result.stdout)

    def test_dry_run_does_not_write(self) -> None:
        result = self.run_installer("--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(list(self.target.iterdir()), [])
        self.assertIn("Run /snowflake-init", result.stdout)
        self.assertNotIn("MKDIR pipelines", result.stdout)

    def test_missing_uv_no_install_fails_without_writes(self) -> None:
        (self.bin / "uv").unlink()
        self.environment["PATH"] = str(self.bin)
        result = self.run_installer("--yes", "--no-install")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("uv is required but missing", result.stderr)
        self.assertEqual(list(self.target.iterdir()), [])

    def test_missing_uv_dry_run_no_install_only_reports(self) -> None:
        (self.bin / "uv").unlink()
        self.environment["PATH"] = str(self.bin)
        result = self.run_installer("--dry-run", "--no-install")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("uv missing", result.stdout)
        self.assertEqual(list(self.target.iterdir()), [])

    def test_repeat_install_still_requires_uv(self) -> None:
        self.assertEqual(self.run_installer("--yes").returncode, 0)
        before = self.snapshot()
        (self.bin / "uv").unlink()
        self.environment["PATH"] = str(self.bin)
        result = self.run_installer("--yes", "--no-install")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("uv is required but missing", result.stderr)
        self.assertEqual(before, self.snapshot())

    def test_broken_uv_fails_before_project_writes(self) -> None:
        (self.bin / "uv").write_text(f"#!{sys.executable}\nraise SystemExit(7)\n")
        result = self.run_installer("--yes")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("exit status 7", result.stderr)
        self.assertEqual(list(self.target.iterdir()), [])

    def test_missing_git_fails_without_writes(self) -> None:
        (self.bin / "git").unlink()
        self.environment["PATH"] = str(self.bin)
        result = self.run_installer("--yes")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Git is required", result.stderr)
        self.assertEqual(list(self.target.iterdir()), [])

    def test_broken_git_fails_without_writes(self) -> None:
        (self.bin / "git").write_text(f"#!{sys.executable}\nraise SystemExit(8)\n")
        result = self.run_installer("--yes")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("exit status 8", result.stderr)
        self.assertEqual(list(self.target.iterdir()), [])

    def test_missing_snowflake_cli_fails_without_writes(self) -> None:
        (self.bin / "snow").unlink()
        self.environment["PATH"] = str(self.bin)
        result = self.run_installer("--yes", "--no-install")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Snowflake CLI (snow) is required but missing", result.stderr)
        self.assertIn("--no-install", result.stderr)
        self.assertEqual(list(self.target.iterdir()), [])

    def test_missing_snowflake_cli_dry_run_only_reports(self) -> None:
        (self.bin / "snow").unlink()
        self.environment["PATH"] = str(self.bin)
        result = self.run_installer("--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Snowflake CLI (snow) missing", result.stdout)
        self.assertEqual(list(self.target.iterdir()), [])

    def test_missing_snowflake_cli_requires_confirmation_noninteractively(self) -> None:
        (self.bin / "snow").unlink()
        self.environment["PATH"] = str(self.bin)
        result = self.run_installer()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Non-interactive installation requires --yes", result.stderr)
        self.assertEqual(list(self.target.iterdir()), [])

    def test_approved_plan_installs_missing_snowflake_cli_before_project_writes(self) -> None:
        (self.bin / "snow").unlink()
        data_directory = Path(self.temporary.name) / "data"
        self.environment["XDG_DATA_HOME"] = str(data_directory)
        installer_script = (
            "#!/bin/sh\n"
            'mkdir -p "$XDG_DATA_HOME/snowflake-cli/bin"\n'
            "printf '%s\\n' '#!/bin/sh' "
            "'printf \"%s\\\\n\" \"Snowflake CLI test\"' "
            '> "$XDG_DATA_HOME/snowflake-cli/bin/snow"\n'
            'chmod +x "$XDG_DATA_HOME/snowflake-cli/bin/snow"\n'
        )
        curl = self.bin / "curl"
        curl.write_text(
            f"#!{sys.executable}\n"
            "import pathlib, sys\n"
            "output = pathlib.Path(sys.argv[sys.argv.index('--output') + 1])\n"
            f"output.write_text({installer_script!r})\n"
        )
        curl.chmod(0o755)
        result = self.run_installer("--yes", "--skip-hooks", "--skip-venv")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Prerequisite verified: Snowflake CLI test", result.stdout)
        self.assertTrue((data_directory / "snowflake-cli/bin/snow").is_file())
        self.assertTrue((self.target / ".github/copilot-instructions.md").is_file())

    def test_broken_snowflake_cli_fails_before_project_writes(self) -> None:
        (self.bin / "snow").write_text(f"#!{sys.executable}\nraise SystemExit(9)\n")
        result = self.run_installer("--yes")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("exit status 9", result.stderr)
        self.assertEqual(list(self.target.iterdir()), [])

    def test_skip_environment_preserves_manifests(self) -> None:
        (self.target / "pyproject.toml").write_text("[project]\nname = 'existing'\n")
        result = self.run_installer("--yes", "--skip-venv")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.target / ".venv").exists())
        self.assertEqual((self.target / "pyproject.toml").read_text(),
                         "[project]\nname = 'existing'\n")

    def test_invalid_environment_is_not_overwritten(self) -> None:
        (self.target / ".venv").mkdir()
        before = self.snapshot()
        result = self.run_installer("--yes")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not a recognizable virtual environment", result.stderr)
        self.assertEqual(before, self.snapshot())
        self.assertFalse((self.target / ".github").exists())

    def test_existing_environment_workflow_requires_skip(self) -> None:
        (self.target / "poetry.lock").write_text("# Existing dependency manager\n")
        result = self.run_installer("--yes")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--skip-venv", result.stderr)
        self.assertFalse((self.target / ".venv").exists())

    def test_environment_symlink_is_rejected(self) -> None:
        (self.target / ".venv").symlink_to(self.bin, target_is_directory=True)
        result = self.run_installer("--yes")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("symlink", result.stderr)
        self.assertFalse((self.target / ".github").exists())

    def test_environment_creation_failure_stops_before_assets(self) -> None:
        uv = self.bin / "uv"
        uv.write_text(f"#!{sys.executable}\nimport sys\n"
                      "if sys.argv[1] == '--version': print('uv test')\n"
                      "else: raise SystemExit(9)\n")
        result = self.run_installer("--yes")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(".venv may remain", result.stderr)
        self.assertFalse((self.target / ".github").exists())

    def mcp_arguments(self, authentication: str = "oauth") -> tuple[str, ...]:
        return ("--mcp-endpoint", "https://example.snowflakecomputing.com/approved/mcp",
                "--mcp-auth", authentication,
                *(("--mcp-oauth-client-id", "approved-public-client") if authentication == "oauth" else ()),
                "--mcp-approved")

    def test_mcp_oauth_configuration_and_idempotency(self) -> None:
        result = self.run_installer("--yes", *self.mcp_arguments())
        self.assertEqual(result.returncode, 0, result.stderr)
        config = json.loads((self.target / ".vscode/mcp.json").read_text())
        self.assertEqual(config["servers"]["snowflake"],
                         {"type": "http",
                          "url": "https://example.snowflakecomputing.com/approved/mcp",
                          "oauth": {"clientId": "approved-public-client"}})
        before = self.snapshot()
        result = self.run_installer("--yes", *self.mcp_arguments())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(before, self.snapshot())

    def test_mcp_bearer_uses_environment_reference_not_a_token(self) -> None:
        self.environment["SNOWFLAKE_MCP_TOKEN"] = "test-only-not-a-real-token"
        result = self.run_installer("--yes", *self.mcp_arguments("bearer"))
        self.assertEqual(result.returncode, 0, result.stderr)
        config = json.loads((self.target / ".vscode/mcp.json").read_text())
        self.assertEqual(config["servers"]["snowflake"]["headers"],
                         {"Authorization": "Bearer ${env:SNOWFLAKE_MCP_TOKEN}"})
        self.assertNotIn("inputs", config)
        self.assertNotIn("test-only-not-a-real-token",
                         (self.target / ".vscode/mcp.json").read_text() + result.stdout + result.stderr)

    def test_mcp_merges_unrelated_config(self) -> None:
        path = self.target / ".vscode/mcp.json"
        path.parent.mkdir()
        existing = {"servers": {"other": {"type": "http", "url": "https://example.com/mcp"}},
                    "inputs": [{"id": "other", "type": "promptString", "description": "Other"}]}
        path.write_text(json.dumps(existing))
        result = self.run_installer("--yes", *self.mcp_arguments("bearer"))
        self.assertEqual(result.returncode, 0, result.stderr)
        merged = json.loads(path.read_text())
        self.assertEqual(merged["servers"]["other"], existing["servers"]["other"])
        self.assertEqual(merged["inputs"][0], existing["inputs"][0])

    def test_mcp_dry_run_does_not_write(self) -> None:
        result = self.run_installer("--dry-run", *self.mcp_arguments("bearer"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(list(self.target.iterdir()), [])
        self.assertIn(".vscode/mcp.json", result.stdout)

    def test_mcp_requires_explicit_details_noninteractively(self) -> None:
        result = self.run_installer("--yes", "--setup-mcp")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Non-interactive MCP setup requires", result.stderr)
        self.assertEqual(list(self.target.iterdir()), [])

    def test_mcp_setup_dry_run_defers_prompts(self) -> None:
        result = self.run_installer("--dry-run", "--setup-mcp")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("MCP setup pending", result.stdout)
        self.assertEqual(list(self.target.iterdir()), [])

    def test_mcp_rejects_missing_approval_or_authentication(self) -> None:
        for arguments in (self.mcp_arguments()[:-1],
                          ("--mcp-endpoint", "https://example.com/mcp", "--mcp-approved")):
            result = self.run_installer("--yes", *arguments)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(list(self.target.iterdir()), [])

    def test_mcp_conflicts_and_jsonc_are_preserved(self) -> None:
        path = self.target / ".vscode/mcp.json"
        path.parent.mkdir()
        for existing in ('{"servers": {"snowflake": {"url": "https://other.example"}}}',
                         '{// JSONC comment\n"servers": {}}',
                         '{"servers": []}', '[]',
                         '{"servers": {}, "servers": {}}', '{"unsupported": NaN}'):
            with self.subTest(existing=existing):
                path.write_text(existing)
                result = self.run_installer("--yes", *self.mcp_arguments("bearer"))
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(path.read_text(), existing)
                self.assertFalse((self.target / ".venv").exists())

    def test_mcp_rejects_unsafe_endpoint_without_echoing_it(self) -> None:
        for endpoint in ("http://example.com/mcp", "https://user:secret@example.com/mcp",
                         "https://example.com/mcp?token=secret", "https://example.com/mcp#secret"):
            result = self.run_installer("--yes", "--mcp-endpoint", endpoint,
                                        "--mcp-auth", "oauth", "--mcp-approved")
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn("secret", result.stdout + result.stderr)
            self.assertEqual(list(self.target.iterdir()), [])

    def test_mcp_destination_symlink_rejected(self) -> None:
        (self.target / ".vscode").symlink_to(self.bin, target_is_directory=True)
        result = self.run_installer("--yes", *self.mcp_arguments())
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("symlink", result.stderr)
        self.assertFalse((self.bin / "mcp.json").exists())

    def test_mcp_interactive_setup_confirms_details(self) -> None:
        with patch.object(installer.sys, "argv", [
            str(SCRIPT), "--target", str(self.target), "--setup-mcp",
        ]), patch.object(installer.sys.stdin, "isatty", return_value=True), patch(
            "builtins.input", side_effect=[
                "https://approved.example/mcp", "oauth", "approved-public-client", "yes",
            ],
        ), patch.object(installer, "install", return_value=0) as install:
            self.assertEqual(installer.main(), 0)
        self.assertEqual(install.call_args.kwargs["mcp_endpoint"], "https://approved.example/mcp")
        self.assertEqual(install.call_args.kwargs["mcp_auth"], "oauth")
        self.assertTrue(install.call_args.kwargs["mcp_approved"])
        self.assertEqual(install.call_args.kwargs["mcp_oauth_client_id"], "approved-public-client")

    def test_oauth_requires_public_client_id(self) -> None:
        result = self.run_installer("--yes", "--mcp-endpoint", "https://approved.example/mcp",
                                    "--mcp-auth", "oauth", "--mcp-approved")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--mcp-oauth-client-id", result.stderr)
        self.assertEqual(list(self.target.iterdir()), [])

    def test_existing_pipeline_content_preserved(self) -> None:
        model = self.target / "pipelines/dbt/models/silver/staging/custom.sql"
        model.parent.mkdir(parents=True)
        model.write_bytes(b"select 1 as existing_model;\n")
        result = self.run_installer("--yes")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(model.read_bytes(), b"select 1 as existing_model;\n")
        self.assertFalse((self.target / "pipelines/ingestion").exists())

    def test_installed_initializer_creates_folders_only_when_run(self) -> None:
        self.assertEqual(self.run_installer("--yes").returncode, 0)
        self.assertFalse((self.target / "pipelines").exists())
        before = self.snapshot()
        initialized = subprocess.run(
            [sys.executable, str(self.target / "scripts/init_project.py"),
             "--target", str(self.target), "--yes"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(initialized.returncode, 0, initialized.stderr)
        for directory in PIPELINE_LEAVES:
            self.assertTrue((self.target / directory).is_dir(), directory)
        self.assertTrue((self.target / ".git").is_dir())
        after_initialization = self.snapshot()
        self.assertEqual(before, {
            path: content for path, content in after_initialization.items()
            if not path.startswith(".git/")
        })
        missing = self.target / PIPELINE_LEAVES[0]
        missing.rmdir()
        (self.bin / "git").rename(self.bin / "git-disabled")
        result = self.run_installer("--yes")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(missing.exists())
        after_reinstall = self.snapshot()
        self.assertEqual(before, {
            path: content for path, content in after_reinstall.items()
            if not path.startswith(".git/")
        })

    def test_installer_leaves_pipeline_file_untouched(self) -> None:
        conflict = self.target / "pipelines"
        conflict.write_text("Existing file\n")
        result = self.run_installer("--yes")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(conflict.read_text(), "Existing file\n")

    def test_installer_does_not_follow_pipeline_symlinks(self) -> None:
        outside = Path(self.temporary.name) / "outside"
        outside.mkdir()
        pipelines = self.target / "pipelines"
        pipelines.mkdir()
        (pipelines / "dbt").symlink_to(outside, target_is_directory=True)
        result = self.run_installer("--yes")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(list(outside.iterdir()), [])
        self.assertTrue((pipelines / "dbt").is_symlink())

    def test_preserves_existing_instructions_and_unrelated_files(self) -> None:
        github = self.target / ".github"
        github.mkdir()
        original = b"# Project rules\r\nKeep these rules.\r\n"
        instructions = github / "copilot-instructions.md"
        instructions.write_bytes(original)
        (github / "github-app.yml").write_text("instructions: Keep app configuration\n")
        result = self.run_installer("--yes")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(instructions.read_bytes().startswith(original))
        self.assertEqual((github / "github-app.yml").read_text(),
                         "instructions: Keep app configuration\n")
        self.assertNotIn("## Editing this kit", instructions.read_text())

    def test_conflict_aborts_before_any_write(self) -> None:
        conflict = self.target / ".github/prompts/snowflake-sql-check.prompt.md"
        conflict.parent.mkdir(parents=True)
        conflict.write_text("My custom prompt\n")
        before = self.snapshot()
        result = self.run_installer("--yes")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Conflicts found", result.stderr)
        self.assertEqual(before, self.snapshot())
        self.assertFalse((self.target / "pipelines").exists())

    def test_agent_conflict_aborts_before_any_write(self) -> None:
        conflict = self.target / ".github/agents/snowflake-cost-investigator.agent.md"
        conflict.parent.mkdir(parents=True)
        conflict.write_text("My custom agent\n")
        before = self.snapshot()
        result = self.run_installer("--yes", "--skip-venv")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Conflicts found", result.stderr)
        self.assertEqual(before, self.snapshot())
        self.assertFalse((self.target / ".github/skills").exists())

    def test_modified_managed_instructions_are_not_replaced(self) -> None:
        self.assertEqual(self.run_installer("--yes").returncode, 0)
        file = self.target / ".github/copilot-instructions.md"
        file.write_text(file.read_text().replace("## Skill guidance", "## Custom guidance"))
        before = self.snapshot()
        result = self.run_installer("--yes")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(before, self.snapshot())

    def test_symlink_destination_rejected(self) -> None:
        outside = Path(self.temporary.name) / "outside"
        outside.mkdir()
        (self.target / ".github").symlink_to(outside, target_is_directory=True)
        result = self.run_installer("--yes")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("symlink", result.stderr)
        self.assertEqual(list(outside.iterdir()), [])

    def test_noninteractive_requires_confirmation(self) -> None:
        result = self.run_installer()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--yes", result.stderr)
        self.assertEqual(list(self.target.iterdir()), [])

    def test_duplicate_skill_discovery_root_rejected(self) -> None:
        alternate = self.target / ".claude/skills/snowflake-data-governance"
        alternate.mkdir(parents=True)
        (alternate / "SKILL.md").write_text("Existing skill\n")
        before = self.snapshot()
        result = self.run_installer("--yes")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("duplicate skill discovery root", result.stderr)
        self.assertEqual(before, self.snapshot())

    def test_source_and_missing_target_rejected(self) -> None:
        for target in (ROOT, self.target / "missing"):
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--target", str(target), "--yes"],
                capture_output=True, text=True, check=False,
            )
            self.assertNotEqual(result.returncode, 0)

    def test_shell_entrypoint(self) -> None:
        result = subprocess.run(
            ["bash", str(ROOT / "install.sh"), "--target", str(self.target), "--dry-run"],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(list(self.target.iterdir()), [])


class UvPrerequisiteTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="snowflake-uv-test-")
        self.addCleanup(temporary.cleanup)
        self.target = Path(temporary.name)
        self.output = io.StringIO()
        stack = ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(redirect_stdout(self.output))
        stack.enter_context(patch.object(installer.sys, "platform", "darwin"))
        stack.enter_context(patch.object(installer, "verify_git"))
        stack.enter_context(patch.object(installer, "hook_destination", return_value=None))
        stack.enter_context(patch.object(installer, "needs_environment", return_value=False))
        stack.enter_context(patch.object(installer, "verify_environment"))
        self.which = stack.enter_context(patch.object(
            installer.shutil, "which",
            side_effect=lambda name: None if name == "uv" else f"/tools/{name}",
        ))
        self.run = stack.enter_context(patch.object(
            installer.subprocess, "run",
            return_value=subprocess.CompletedProcess([], 0, "uv 0.0-test\n", ""),
        ))

    def test_dry_run_does_not_execute_or_install_uv(self) -> None:
        self.assertEqual(installer.install(self.target, True, True), 0)
        self.assertIn("brew install uv", self.output.getvalue())
        self.run.assert_not_called()
        self.assertEqual(list(self.target.iterdir()), [])

    def test_missing_uv_requires_confirmation(self) -> None:
        with patch.object(installer.sys.stdin, "isatty", return_value=False):
            with self.assertRaisesRegex(ValueError, "--yes"):
                installer.install(self.target, False, False)
        self.run.assert_not_called()
        self.assertEqual(list(self.target.iterdir()), [])

    def test_declining_plan_does_not_install_or_write(self) -> None:
        with patch.object(installer.sys.stdin, "isatty", return_value=True):
            with patch("builtins.input", return_value="n"):
                self.assertEqual(installer.install(self.target, False, False), 0)
        self.run.assert_not_called()
        self.assertEqual(list(self.target.iterdir()), [])

    def test_mac_install_verifies_before_project_writes(self) -> None:
        available = False

        def find(name: str) -> str | None:
            return "/tools/uv" if name == "uv" and available else (
                None if name == "uv" else f"/tools/{name}"
            )

        def execute(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            nonlocal available
            self.assertEqual(list(self.target.iterdir()), [])
            if command == ["brew", "install", "uv"]:
                available = True
            return subprocess.CompletedProcess(command, 0, "uv 0.0-test\n", "")

        self.which.side_effect = find
        self.run.side_effect = execute
        self.assertEqual(installer.install(self.target, False, True), 0)
        self.assertEqual([call.args[0] for call in self.run.call_args_list],
                         [["/tools/snow", "--version"],
                          ["brew", "install", "uv"], ["/tools/uv", "--version"]])
        self.assertFalse((self.target / "pipelines").exists())

    def test_uv_install_failure_aborts_before_writes(self) -> None:
        self.run.side_effect = subprocess.CalledProcessError(1, ["brew", "install", "uv"])
        with self.assertRaises(subprocess.CalledProcessError):
            installer.install(self.target, False, True)
        self.assertEqual(list(self.target.iterdir()), [])

    def test_uv_not_found_after_install_is_an_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "executable was not found"):
            installer.install(self.target, False, True)
        self.assertEqual(list(self.target.iterdir()), [])

    def test_invalid_uv_version_is_an_error(self) -> None:
        self.which.side_effect = lambda name: f"/tools/{name}"
        self.run.return_value.stdout = "not uv"
        with self.assertRaisesRegex(ValueError, "Unexpected uv --version"):
            installer.install(self.target, False, True)
        self.assertEqual(list(self.target.iterdir()), [])

    def test_existing_uv_is_verified_without_installing(self) -> None:
        self.which.side_effect = lambda name: f"/tools/{name}"
        self.assertEqual(installer.install(self.target, False, True, no_install=True), 0)
        self.assertEqual(
            [call.args[0] for call in self.run.call_args_list],
            [["/tools/snow", "--version"], ["/tools/uv", "--version"]],
        )

    def test_conflicts_prevent_uv_installation(self) -> None:
        (self.target / ".github").write_text("Conflict\n")
        with self.assertRaisesRegex(ValueError, "not a directory"):
            installer.install(self.target, False, True)
        self.run.assert_not_called()

    def test_mac_missing_homebrew_reports_manual_install(self) -> None:
        self.which.side_effect = lambda name: (
            f"/tools/{name}" if name in {"git", "snow"} else None
        )
        with self.assertRaisesRegex(ValueError, "Install Homebrew or install uv manually"):
            installer.install(self.target, False, True)
        self.run.assert_not_called()

    def test_snowflake_cli_install_uses_official_script_without_profile_changes(self) -> None:
        data_directory = self.target / "data"

        def execute(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            if command[0] == "sh":
                executable = data_directory / "snowflake-cli/bin/snow"
                executable.parent.mkdir(parents=True)
                executable.write_text("#!/bin/sh\nprintf '%s\\n' 'Snowflake CLI test'\n")
                executable.chmod(0o755)
            return subprocess.CompletedProcess(command, 0, "", "")

        self.run.side_effect = execute
        with patch.dict(os.environ, {"XDG_DATA_HOME": str(data_directory)}):
            with patch.object(installer.sys, "platform", "linux"):
                executable = installer.install_snowflake_cli()
        calls = self.run.call_args_list
        self.assertEqual(calls[0].args[0][0], "curl")
        self.assertEqual(calls[0].args[0][-1],
                         "https://sfc-repo.snowflakecomputing.com/snowflake-cli/install.sh")
        self.assertEqual(calls[1].args[0][0], "sh")
        self.assertEqual(calls[1].kwargs["env"]["NON_INTERACTIVE"], "1")
        self.assertEqual(calls[1].kwargs["env"]["SKIP_PATH_PROMPT"], "1")
        self.assertTrue(Path(executable).is_file())
        self.assertFalse(Path(calls[1].args[0][1]).parent.exists())

    def test_snowflake_cli_install_failure_stops(self) -> None:
        self.run.side_effect = subprocess.CalledProcessError(22, ["curl"])
        with patch.object(installer.sys, "platform", "linux"):
            with self.assertRaises(subprocess.CalledProcessError):
                installer.install_snowflake_cli()

    def test_linux_uses_official_installer_without_profile_changes(self) -> None:
        with patch.object(installer.sys, "platform", "linux"):
            executable = installer.install_uv()
        commands = [call.args[0] for call in self.run.call_args_list]
        self.assertEqual(commands[0][0], "curl")
        self.assertEqual(commands[0][-1], "https://astral.sh/uv/install.sh")
        self.assertEqual(commands[1][0], "sh")
        environment = self.run.call_args_list[1].kwargs["env"]
        self.assertEqual(environment["UV_NO_MODIFY_PATH"], "1")
        self.assertEqual(environment["UV_INSTALL_DIR"], str(Path.home() / ".local/bin"))
        self.assertNotIn("UV_UNMANAGED_INSTALL", environment)
        self.assertFalse(Path(commands[1][1]).parent.exists())
        self.assertEqual(executable, f"/tools/{Path.home() / '.local/bin/uv'}")

    def test_linux_download_failure_never_runs_script(self) -> None:
        self.run.side_effect = subprocess.CalledProcessError(22, ["curl"])
        with patch.object(installer.sys, "platform", "linux"):
            with self.assertRaises(subprocess.CalledProcessError):
                installer.install_uv()
        self.assertEqual(self.run.call_count, 1)
        command = self.run.call_args.args[0]
        self.assertFalse(Path(command[command.index("--output") + 1]).parent.exists())

    def test_linux_script_failure_cleans_up_and_stops(self) -> None:
        self.run.side_effect = [
            subprocess.CompletedProcess(["snow"], 0, "Snowflake CLI 3.0\n", ""),
            subprocess.CompletedProcess(["curl"], 0),
            subprocess.CalledProcessError(1, ["sh"]),
        ]
        with patch.object(installer.sys, "platform", "linux"):
            with self.assertRaises(subprocess.CalledProcessError):
                installer.install(self.target, False, True)
        self.assertEqual(list(self.target.iterdir()), [])
        script = Path(self.run.call_args.args[0][1])
        self.assertFalse(script.parent.exists())

    def test_linux_missing_curl_produces_manual_guidance(self) -> None:
        self.which.side_effect = lambda name: None if name in {"uv", "curl"} else f"/tools/{name}"
        with patch.object(installer.sys, "platform", "linux"):
            with self.assertRaisesRegex(ValueError, "requires curl and sh"):
                installer.install(self.target, False, True)
        self.run.assert_not_called()

    def test_unsupported_platform_reports_manual_install(self) -> None:
        with patch.object(installer.sys, "platform", "win32"):
            with self.assertRaisesRegex(ValueError, "Install uv manually"):
                installer.install(self.target, False, True)
        self.run.assert_not_called()


@unittest.skipUnless(shutil.which("uv") and shutil.which("git"), "Requires existing uv and Git")
class RealUvTests(unittest.TestCase):
    def test_offline_environment_creation_and_reuse(self) -> None:
        with tempfile.TemporaryDirectory(prefix="snowflake-real-uv-test-") as directory:
            target = Path(directory)
            fake_bin = target / "bin"
            fake_bin.mkdir()
            snow = fake_bin / "snow"
            snow.write_text("#!/bin/sh\nprintf '%s\\n' 'Snowflake CLI test'\n")
            snow.chmod(0o755)
            environment = dict(os.environ, PATH=str(fake_bin) + os.pathsep
                               + os.environ.get("PATH", ""))
            with patch.dict(os.environ, environment), redirect_stdout(io.StringIO()):
                self.assertEqual(installer.install(target, False, True, no_install=True), 0)
                python = installer.environment_python(target)
                result = subprocess.run(
                    [str(python), "-I", "-c",
                     "import importlib.util; assert importlib.util.find_spec('pip') is None"],
                    check=False, capture_output=True, text=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                configuration = (target / ".venv/pyvenv.cfg").read_bytes()
                self.assertEqual(installer.install(target, False, True, no_install=True), 0)
                self.assertEqual((target / ".venv/pyvenv.cfg").read_bytes(), configuration)
            self.assertFalse((target / "pyproject.toml").exists())
            self.assertFalse((target / "uv.lock").exists())
            self.assertFalse((target / ".vscode/mcp.json").exists())


if __name__ == "__main__":
    unittest.main()
