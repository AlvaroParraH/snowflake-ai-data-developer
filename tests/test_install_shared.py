from contextlib import redirect_stderr, redirect_stdout
import ast
import hashlib
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
SPEC = importlib.util.spec_from_file_location("install_shared", ROOT / "scripts/install_shared.py")
assert SPEC is not None and SPEC.loader is not None
installer = importlib.util.module_from_spec(SPEC)
with (patch.object(sys, "path", [str(ROOT / "scripts"), *sys.path]),
      patch.dict(sys.modules, {SPEC.name: installer})):
    SPEC.loader.exec_module(installer)


class SharedInstallationTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="snowflake-shared-test-")
        self.addCleanup(temporary.cleanup)
        self.target = Path(temporary.name).resolve() / "shared kit"
        self.bin = Path(temporary.name).resolve() / "bin"
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

    def run_install(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-B", str(ROOT / "scripts/install_shared.py"),
             "--target", str(self.target), *args],
            capture_output=True, text=True, stdin=subprocess.DEVNULL,
        )

    def kit_python(self) -> Path:
        return self.target / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")

    def test_shell_entrypoint_default_requires_existing_shared_bundle(self) -> None:
        home = self.target.parent / "home"
        home.mkdir()
        environment = {**os.environ, "HOME": str(home), "USERPROFILE": str(home)}
        results = [
            subprocess.run(
                ["bash", str(ROOT / "install.sh"), *args],
                capture_output=True, text=True, stdin=subprocess.DEVNULL, env=environment,
            )
            for args in ((), ("--shared", "--yes", "--personal-skills"))
        ]
        for result in results:
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Select an existing Snowflake shared bundle", result.stderr)
        self.assertEqual(results[0].stdout, results[1].stdout)
        self.assertEqual(results[0].stderr, results[1].stderr)
        self.assertEqual(list(home.iterdir()), [])

    def test_shell_entrypoint_default_installs_personal_skills_without_confirmation(self) -> None:
        home = self.target.parent / "home"
        home.mkdir()
        environment = {**os.environ, "HOME": str(home), "USERPROFILE": str(home)}
        bundle = home / ".snowflake-ai-data-developer"
        result = self.run_install("--target", str(bundle), "--yes")
        self.assertEqual(result.returncode, 0, result.stderr)
        before = {path.relative_to(bundle): path.read_bytes()
                  for path in bundle.rglob("*") if path.is_file()}
        for args in ((), ("--shared", "--yes", "--personal-skills")):
            result = subprocess.run(
                ["bash", str(ROOT / "install.sh"), *args],
                capture_output=True, text=True, stdin=subprocess.DEVNULL, env=environment,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
        shortcuts = list((home / ".copilot/skills").glob("*/SKILL.md"))
        self.assertEqual(len(shortcuts), 26)
        self.assertIn((bundle / "skills/snowflake-init/SKILL.md").as_uri(),
                      (home / ".copilot/skills/snowflake-init/SKILL.md").read_text())
        self.assertEqual(before, {path.relative_to(bundle): path.read_bytes()
                                  for path in bundle.rglob("*") if path.is_file()})
        self.assertEqual({path.name for path in home.iterdir()},
                         {".snowflake-ai-data-developer", ".copilot"})

    def test_shell_entrypoint_preserves_explicit_shared_options(self) -> None:
        result = subprocess.run(
            ["bash", str(ROOT / "install.sh"), "--shared",
             "--target", str(self.target), "--dry-run"],
            capture_output=True, text=True, stdin=subprocess.DEVNULL,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"Shared plugin: {self.target}", result.stdout)
        self.assertIn("Dry run complete; nothing written.", result.stdout)
        self.assertFalse(self.target.exists())

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

    def test_cached_workflows_use_stable_runtime_without_cached_environment(self) -> None:
        self.assertEqual(self.run_install("--yes").returncode, 0)
        cache = self.target.parent / "editor cache"
        shutil.copytree(self.target, cache, ignore=shutil.ignore_patterns(".venv"))
        for source in (cache / "skills").glob("*/SKILL.md"):
            wrapper = source.read_text()
            self.assertIn(f"Stable runtime root: `{self.target}`", wrapper)
            self.assertIn("Do not execute Python or helpers from the cached copy", wrapper)
            self.assertNotIn("Resolve the kit root from THIS skill", wrapper)
        wrapper = (cache / "skills/snowflake-init/SKILL.md").read_text()
        match = re.search(r"Stable runtime root: `([^`]+)`", wrapper)
        self.assertIsNotNone(match)
        assert match is not None
        runtime = Path(match.group(1))
        python = runtime / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        project = self.target.parent / "consumer project"
        project.mkdir()
        command = [str(python), "-B", str(runtime / "scripts/init_project.py"),
                   "--target", str(project)]
        cached_python = cache / python.relative_to(runtime)
        for state in ("missing", "not executable"):
            if state == "not executable":
                cached_python.parent.mkdir(parents=True)
                cached_python.write_text("invalid cached interpreter\n")
                cached_python.chmod(0o644)
            for flag in ("--detect-only", "--dry-run"):
                with self.subTest(cache_environment=state, flag=flag):
                    result = subprocess.run([*command, flag], cwd=project,
                                            capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(list(project.iterdir()), [])
        self.assertEqual(cached_python.read_text(), "invalid cached interpreter\n")
        self.target.rename(self.target.parent / "moved runtime")
        with self.assertRaises(FileNotFoundError):
            subprocess.run([*command, "--detect-only"], cwd=project, check=True)
        self.assertEqual(list(project.iterdir()), [])

    def test_update_migrates_cached_runtime_rules_without_rebuilding_environment(self) -> None:
        self.assertEqual(self.run_install("--yes").returncode, 0)
        wrapper = self.target / "skills/snowflake-init/SKILL.md"
        wrapper.write_text("previous release: resolve Python relative to cached skill\n")
        manifest = self.target / ".snowflake-kit-manifest.json"
        records = json.loads(manifest.read_bytes())
        records["files"]["skills/snowflake-init/SKILL.md"] = hashlib.sha256(
            wrapper.read_bytes()
        ).hexdigest()
        manifest.write_text(json.dumps(records))
        environment = (self.target / ".venv/pyvenv.cfg").read_bytes()
        result = self.run_install("--update", "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("previous release", wrapper.read_text())
        result = self.run_install("--update", "--yes")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"Stable runtime root: `{self.target}`", wrapper.read_text())
        self.assertEqual((self.target / ".venv/pyvenv.cfg").read_bytes(), environment)

    def test_personal_shortcuts_preview_apply_and_repeat(self) -> None:
        self.assertEqual(self.run_install("--yes").returncode, 0)
        directory = self.target.parent / "personal skills"
        settings = self.target.parent / "settings.json"
        settings.write_text(json.dumps({
            "editor.fontSize": 14,
            "chat.pluginLocations": {str(self.target): True, "/other/plugin": True},
        }))
        before = settings.read_bytes()
        flags = ("--personal-skills", "--skills-dir", str(directory),
                 "--vscode-settings", str(settings))
        result = self.run_install(*flags, "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(directory.exists())
        self.assertEqual(settings.read_bytes(), before)
        result = self.run_install(*flags, "--yes")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(list(directory.glob("*/SKILL.md"))), 26)
        audit = (directory / "snowflake-audit/SKILL.md").read_text()
        self.assertIn("\nname: snowflake-audit\n", audit)
        self.assertIn((self.target / "skills/snowflake-audit/SKILL.md").as_uri(), audit)
        self.assertIn(f"The shared kit root is `{self.target}`", audit)
        config = json.loads(settings.read_bytes())
        self.assertIs(config["chat.pluginLocations"][str(self.target)], False)
        self.assertIs(config["chat.pluginLocations"]["/other/plugin"], True)
        self.assertEqual(config["editor.fontSize"], 14)
        snapshot = {p: p.read_bytes() for p in directory.glob("*/SKILL.md")}
        result = self.run_install(*flags, "--yes")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(snapshot, {p: p.read_bytes() for p in directory.glob("*/SKILL.md")})

    def test_personal_collision_aborts_before_any_writes(self) -> None:
        self.assertEqual(self.run_install("--yes").returncode, 0)
        directory = self.target.parent / "personal"
        collision = directory / "snowflake-audit/SKILL.md"
        collision.parent.mkdir(parents=True)
        collision.write_text("personal customizations")
        result = self.run_install("--personal-skills", "--skills-dir", str(directory), "--yes")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Existing personal skill differs", result.stderr)
        self.assertEqual(list(directory.glob("*/SKILL.md")), [collision])
        self.assertEqual(collision.read_text(), "personal customizations")

    def test_personal_symlink_and_incompatible_options_are_rejected(self) -> None:
        self.assertEqual(self.run_install("--yes").returncode, 0)
        external = self.target.parent / "external"
        external.mkdir()
        directory = self.target.parent / "personal"
        directory.symlink_to(external, target_is_directory=True)
        result = self.run_install("--personal-skills", "--skills-dir", str(directory), "--yes")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("symlink", result.stderr)
        self.assertEqual(list(external.iterdir()), [])
        for flags in (("--update",), ("--setup-mcp",)):
            result = self.run_install("--personal-skills", *flags, "--dry-run")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("separate from", result.stderr)
        result = self.run_install("--skills-dir", str(external), "--dry-run")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires --personal-skills", result.stderr)

    def test_personal_setup_without_confirmation_writes_nothing(self) -> None:
        self.assertEqual(self.run_install("--yes").returncode, 0)
        directory = self.target.parent / "personal"
        result = self.run_install("--personal-skills", "--skills-dir", str(directory))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires --yes", result.stderr)
        self.assertFalse(directory.exists())

    def test_update_cli_preserves_environment_and_rejects_configuration_changes(self) -> None:
        result = self.run_install("--yes")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.target / ".snowflake-kit-manifest.json").is_file())
        before = {p.relative_to(self.target): p.read_bytes()
                  for p in self.target.rglob("*") if p.is_file()}
        result = self.run_install("--update", "--yes")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Already up to date", result.stdout)
        self.assertEqual(before, {p.relative_to(self.target): p.read_bytes()
                                  for p in self.target.rglob("*") if p.is_file()})
        document = self.target / "docs/copilot-setup.md"
        original = document.read_bytes()
        document.write_bytes(b"previous release\n")
        manifest = self.target / ".snowflake-kit-manifest.json"
        records = json.loads(manifest.read_bytes())
        records["files"]["docs/copilot-setup.md"] = hashlib.sha256(document.read_bytes()).hexdigest()
        manifest.write_text(json.dumps(records))
        result = self.run_install("--update", "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(document.read_bytes(), b"previous release\n")
        result = self.run_install("--update", "--yes")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(document.read_bytes(), original)
        self.assertEqual((self.target / ".venv/pyvenv.cfg").read_bytes(),
                         before[Path(".venv/pyvenv.cfg")])
        for flags in (("--register-vscode",), ("--setup-mcp",),
                      ("--mcp-config", str(self.target.parent / "mcp.json"))):
            result = self.run_install("--update", "--dry-run", *flags)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("cannot change MCP or User Settings", result.stderr)

    def test_registration_preview_and_approval_preserve_settings(self) -> None:
        settings = self.target.parent / "settings.json"
        settings.write_text('{"editor.fontSize": 14}')
        before = settings.read_bytes()
        result = self.run_install("--vscode-settings", str(settings), "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Developer: Reload Window", result.stdout)
        self.assertIn(str(self.target), result.stdout)
        self.assertEqual(settings.read_bytes(), before)
        self.assertFalse(self.target.exists())
        result = self.run_install("--vscode-settings", str(settings))
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(settings.read_bytes(), before)

    def test_discovers_default_and_named_profiles_across_editions(self) -> None:
        home = self.target.parent
        expected = [
            home / "Library/Application Support/Code/User/settings.json",
            home / "Library/Application Support/Code/User/profiles/team/settings.json",
            home / "Library/Application Support/Code - Insiders/User/settings.json",
        ]
        for path in expected:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("{}")
        with patch.object(installer.Path, "home", return_value=home), patch.object(sys, "platform", "darwin"):
            self.assertEqual(installer.discover_vscode_settings(), expected)

    def test_discovers_linux_and_windows_settings(self) -> None:
        base = self.target.parent / "config"
        settings = base / "Code/User/settings.json"
        settings.parent.mkdir(parents=True)
        settings.write_text("{}")
        for platform, variable in (("linux", "XDG_CONFIG_HOME"), ("win32", "APPDATA")):
            with (self.subTest(platform=platform), patch.object(sys, "platform", platform),
                  patch.dict(os.environ, {variable: str(base)})):
                self.assertEqual(installer.discover_vscode_settings(), [settings])

    def test_single_candidate_is_selected_without_writing(self) -> None:
        settings = self.target.parent / "settings.json"
        settings.write_text("{}")
        with (patch.object(installer, "discover_vscode_settings", return_value=[settings]),
              redirect_stdout(io.StringIO()), patch("builtins.input") as prompt):
            self.assertEqual(installer.select_vscode_settings(dry_run=True), settings)
        prompt.assert_not_called()
        self.assertEqual(settings.read_text(), "{}")

    def test_multiple_candidates_require_selection(self) -> None:
        paths = [self.target.parent / "one.json", self.target.parent / "two.json"]
        with (patch.object(installer, "discover_vscode_settings", return_value=paths),
              redirect_stdout(io.StringIO()), patch.object(sys.stdin, "isatty", return_value=True),
              patch("builtins.input", return_value="2")):
            self.assertEqual(installer.select_vscode_settings(dry_run=False), paths[1])
            with self.assertRaisesRegex(ValueError, "Multiple"):
                installer.select_vscode_settings(dry_run=True)
        with (patch.object(installer, "discover_vscode_settings", return_value=paths),
              redirect_stdout(io.StringIO()), patch.object(sys.stdin, "isatty", return_value=False)):
            with self.assertRaisesRegex(ValueError, "Multiple"):
                installer.select_vscode_settings(dry_run=False)

    def test_missing_settings_are_not_created(self) -> None:
        with (patch.object(installer, "discover_vscode_settings", return_value=[]),
              redirect_stdout(io.StringIO())):
            with self.assertRaisesRegex(ValueError, "No saved"):
                installer.select_vscode_settings(dry_run=True)

    def test_activation_steps_show_plugin_namespaced_workflow_commands(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            installer.activation_steps(self.target)
        self.assertIn("/snowflake-data-developer:snowflake-init", output.getvalue())
        self.assertIn("/snowflake-data-developer:snowflake-dbt-model", output.getvalue())
        self.assertIn("Some clients expose unqualified names", output.getvalue())

    def test_detected_registration_still_requires_write_approval(self) -> None:
        settings = self.target.parent / "settings.json"
        settings.write_text("{}")
        with (patch.object(installer, "discover_vscode_settings", return_value=[settings]),
              patch.object(sys, "argv", ["install_shared", "--target", str(self.target),
                                        "--register-vscode"]),
              patch.object(sys.stdin, "isatty", return_value=False),
              redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO())):
            self.assertEqual(installer.main(), 1)
        self.assertFalse(self.target.exists())
        self.assertEqual(settings.read_text(), "{}")

    def test_interactive_install_offers_vscode_registration(self) -> None:
        settings = self.target.parent / "settings.json"
        settings.write_text('{"editor.fontSize": 14}')
        for flags in ([], ["--yes"]):
            with (self.subTest(flags=flags),
                  patch.object(sys, "argv", ["install_shared", "--target", str(self.target), *flags]),
                  patch.object(sys.stdin, "isatty", return_value=True),
                  patch("builtins.input", return_value="yes") as prompt,
                  patch.object(installer, "discover_vscode_settings", return_value=[settings]),
                  patch.object(installer, "install", return_value=0) as install,
                  redirect_stdout(io.StringIO())):
                self.assertEqual(installer.main(), 0)
                prompt.assert_called_once()
                self.assertIn("VS Code", prompt.call_args.args[0])
                plan = install.call_args.kwargs["registration"]
                self.assertIsInstance(plan, installer.RegistrationPlan)
                self.assertEqual(plan.path, settings)
                self.assertIs(plan.locations[str(self.target)], True)
                self.assertEqual(settings.read_text(), '{"editor.fontSize": 14}')

    def test_declining_vscode_offer_does_not_inspect_or_change_settings(self) -> None:
        for answer in ("", "no"):
            with (self.subTest(answer=answer),
                  patch.object(sys, "argv", ["install_shared", "--target", str(self.target)]),
                  patch.object(sys.stdin, "isatty", return_value=True),
                  patch("builtins.input", return_value=answer),
                  patch.object(installer, "discover_vscode_settings") as discover,
                  patch.object(installer, "install", return_value=0) as install,
                  redirect_stdout(io.StringIO())):
                self.assertEqual(installer.main(), 0)
                discover.assert_not_called()
                self.assertIsNone(install.call_args.kwargs["registration"])

    def test_vscode_offer_is_skipped_for_dry_run_and_unattended_installs(self) -> None:
        for tty, flags in ((True, ["--dry-run"]), (False, ["--yes"]), (False, [])):
            with (self.subTest(tty=tty, flags=flags),
                  patch.object(sys, "argv", ["install_shared", "--target", str(self.target), *flags]),
                  patch.object(sys.stdin, "isatty", return_value=tty),
                  patch("builtins.input") as prompt,
                  patch.object(installer, "discover_vscode_settings") as discover,
                  patch.object(installer, "install", return_value=0) as install,
                  redirect_stdout(io.StringIO())):
                self.assertEqual(installer.main(), 0)
                prompt.assert_not_called()
                discover.assert_not_called()
                self.assertIsNone(install.call_args.kwargs["registration"])

    def test_explicit_vscode_registration_skips_offer(self) -> None:
        settings = self.target.parent / "settings.json"
        settings.write_text("{}")
        for flags in (["--register-vscode"], ["--vscode-settings", str(settings)]):
            with (self.subTest(flags=flags),
                  patch.object(sys, "argv", ["install_shared", "--target", str(self.target), *flags]),
                  patch.object(sys.stdin, "isatty", return_value=True),
                  patch("builtins.input") as prompt,
                  patch.object(installer, "discover_vscode_settings", return_value=[settings]),
                  patch.object(installer, "install", return_value=0) as install,
                  redirect_stdout(io.StringIO())):
                self.assertEqual(installer.main(), 0)
                prompt.assert_not_called()
                self.assertEqual(install.call_args.kwargs["registration"].path, settings)

    def test_accepted_offer_still_requires_final_installation_approval(self) -> None:
        settings = self.target.parent / "settings.json"
        settings.write_text("{}")
        output = io.StringIO()
        with (patch.object(sys, "argv", ["install_shared", "--target", str(self.target)]),
              patch.object(sys.stdin, "isatty", return_value=True),
              patch("builtins.input", side_effect=["yes", "no"]),
              patch.object(installer, "discover_vscode_settings", return_value=[settings]),
              patch.object(installer.venv, "EnvBuilder") as builder,
              redirect_stdout(output)):
            self.assertEqual(installer.main(), 0)
        builder.assert_not_called()
        self.assertIn("VS Code User Settings:", output.getvalue())
        self.assertIn("Cancelled; nothing written.", output.getvalue())
        self.assertFalse(self.target.exists())
        self.assertEqual(settings.read_text(), "{}")

    def test_approved_interactive_offer_installs_and_registers_bundle(self) -> None:
        settings = self.target.parent / "settings.json"
        settings.write_text(json.dumps({
            "editor.fontSize": 14, "chat.pluginLocations": {"/other/plugin": False},
        }))
        with (patch.object(sys, "argv", ["install_shared", "--target", str(self.target)]),
              patch.object(sys.stdin, "isatty", return_value=True),
              patch("builtins.input", side_effect=["yes", "yes"]),
              patch.object(installer, "discover_vscode_settings", return_value=[settings]),
              redirect_stdout(io.StringIO())):
            self.assertEqual(installer.main(), 0)
        config = json.loads(settings.read_text())
        self.assertEqual(config["editor.fontSize"], 14)
        self.assertEqual(config["chat.pluginLocations"], {
            "/other/plugin": False, str(self.target): True,
        })
        self.assertTrue((self.target / "plugin.json").is_file())
        self.assertTrue(self.kit_python().is_file())

    def test_update_and_personal_skill_setup_do_not_offer_registration(self) -> None:
        for flag, entrypoint in (("--update", "install"),
                                 ("--personal-skills", "install_personal_skills")):
            with (self.subTest(flag=flag),
                  patch.object(sys, "argv", ["install_shared", "--target", str(self.target), flag]),
                  patch.object(sys.stdin, "isatty", return_value=True),
                  patch("builtins.input") as prompt,
                  patch.object(installer, "discover_vscode_settings") as discover,
                  patch.object(installer, entrypoint, return_value=0),
                  redirect_stdout(io.StringIO())):
                self.assertEqual(installer.main(), 0)
                prompt.assert_not_called()
                discover.assert_not_called()

    def test_accepted_offer_reports_invalid_settings_without_installing(self) -> None:
        settings = self.target.parent / "settings.json"
        settings.write_text('{// JSONC\n}')
        errors = io.StringIO()
        with (patch.object(sys, "argv", ["install_shared", "--target", str(self.target)]),
              patch.object(sys.stdin, "isatty", return_value=True),
              patch("builtins.input", return_value="yes"),
              patch.object(installer, "discover_vscode_settings", return_value=[settings]),
              redirect_stdout(io.StringIO()), redirect_stderr(errors)):
            self.assertEqual(installer.main(), 1)
        self.assertIn("strict JSON", errors.getvalue())
        self.assertFalse(self.target.exists())
        self.assertEqual(settings.read_text(), '{// JSONC\n}')

    def test_registration_preserves_settings_and_disables_only_selected_copy(self) -> None:
        settings = self.target.parent / "settings.json"
        old = str(self.target.parent / "old-kit")
        settings.write_text(json.dumps({
            "editor.fontSize": 14, "chat.pluginLocations": {old: True, "/other/plugin": True},
        }))
        result = self.run_install("--vscode-settings", str(settings),
                                  "--disable-plugin", old, "--yes")
        self.assertEqual(result.returncode, 0, result.stderr)
        config = json.loads(settings.read_text())
        self.assertEqual(config["editor.fontSize"], 14)
        self.assertEqual(config["chat.pluginLocations"], {
            old: False, "/other/plugin": True, str(self.target): True,
        })
        plan = installer.plan_registration(settings, self.target, [])
        self.assertEqual(plan.before, plan.content)

    def test_registration_refuses_jsonc_invalid_shapes_and_disabled_plugins(self) -> None:
        settings = self.target.parent / "settings.json"
        for content in ('{// comment\n}', '{"a":1,"a":2}', '[]',
                        '{"chat.pluginLocations": []}', '{"chat.pluginLocations":{"x":"true"}}',
                        '{"chat.plugins.enabled":false}'):
            with self.subTest(content=content):
                settings.write_text(content)
                result = self.run_install("--vscode-settings", str(settings), "--yes")
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(settings.read_text(), content)
                self.assertFalse(self.target.exists())

    def test_registration_rechecks_settings_after_preview(self) -> None:
        settings = self.target.parent / "settings.json"
        settings.write_text("{}")
        plan = installer.plan_registration(settings, self.target, [])
        settings.write_text('{"new":true}')
        with self.assertRaisesRegex(ValueError, "changed after preview"):
            plan.apply()
        self.assertEqual(settings.read_text(), '{"new":true}')

    def test_registration_refuses_symlink_and_missing_user_file(self) -> None:
        settings = self.target.parent / "settings.json"
        with self.assertRaises(ValueError):
            installer.plan_registration(settings, self.target, [])
        original = self.target.parent / "original.json"
        original.write_text("{}")
        settings.symlink_to(original)
        with self.assertRaisesRegex(ValueError, "symlink"):
            installer.plan_registration(settings, self.target, [])
        self.assertEqual(original.read_text(), "{}")

    def test_registration_not_written_if_environment_creation_fails(self) -> None:
        settings = self.target.parent / "settings.json"
        settings.write_text("{}")
        plan = installer.plan_registration(settings, self.target, [])
        with (patch.object(installer.venv.EnvBuilder, "create", side_effect=OSError("test failure")),
              redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO())):
            with self.assertRaises(OSError):
                installer.install(self.target, dry_run=False, yes=True, registration=plan)
        self.assertEqual(settings.read_text(), "{}")

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
        for relative, content in installer.shared_payloads(rebuilt).items():
            self.assertEqual((rebuilt / relative).read_bytes(), content, relative)
        self.assertTrue((rebuilt / ".venv/pyvenv.cfg").is_file())


    def test_missing_snowflake_cli_reports_without_blocking_bundle(self) -> None:
        (self.bin / "snow").unlink()
        with patch.dict(os.environ, {"PATH": str(self.bin)}):
            result = self.run_install("--dry-run")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Snowflake CLI (snow) missing", result.stdout)
            self.assertIn("works without Snowflake CLI", result.stdout)
            self.assertFalse(self.target.exists())
            result = self.run_install("--yes", "--no-install")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("automatic installation disabled", result.stdout)
        self.assertTrue((self.target / "plugin.json").is_file())

    def test_approved_plan_installs_missing_snowflake_cli_with_bundle(self) -> None:
        if os.name == "nt":
            self.skipTest("POSIX official-installer path")
        (self.bin / "snow").unlink()
        data_directory = self.target.parent / "data"
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
        with patch.dict(os.environ, {
            "PATH": os.pathsep.join([str(self.bin), "/usr/bin", "/bin"]),
            "XDG_DATA_HOME": str(data_directory),
        }):
            result = self.run_install("--yes")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("INSTALL", result.stdout)
        self.assertIn("Prerequisite verified: Snowflake CLI test", result.stdout)
        self.assertTrue((data_directory / "snowflake-cli/bin/snow").is_file())
        self.assertTrue((self.target / "plugin.json").is_file())

    def test_found_snowflake_cli_is_verified_during_install(self) -> None:
        result = self.run_install("--yes")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"Snowflake CLI found at {self.bin / 'snow'}", result.stdout)
        self.assertIn("Prerequisite verified: Snowflake CLI 3.0-test", result.stdout)


if __name__ == "__main__":
    unittest.main()
