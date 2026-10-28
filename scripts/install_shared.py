"""Build a shared, relocatable Snowflake agent plugin without changing projects."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import venv

from install_kit import ROOT, check_destination, invalid_json_constant, json_object, payloads, verify_environment
from setup_mcp import MCPPlan, add_mcp_arguments, check_config_path, plan_mcp
from installation_state import prepare_manifest, save_manifest, update as update_installation


MANIFEST = {
    "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
    "name": "snowflake-data-developer",
    "version": "1.0.0",
    "description": "Snowflake engineering skills and local project/model workflows.",
}


@dataclass(frozen=True)
class RegistrationPlan:
    path: Path
    before: bytes
    content: bytes
    locations: dict[str, bool]

    def preview(self) -> None:
        print(f"VS Code User Settings: {self.path}")
        print(json.dumps({"chat.pluginLocations": self.locations}, indent=2))
        print("Only chat.pluginLocations changes; unrelated settings and plugins are preserved.")

    def apply(self) -> None:
        check_config_path(self.path)
        if self.path.read_bytes() != self.before:
            raise ValueError(f"User Settings changed after preview: {self.path}")
        if self.before == self.content:
            print("Plugin registration already matches; unchanged.")
            return
        with tempfile.NamedTemporaryFile(dir=self.path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            try:
                stream.write(self.content)
                stream.flush()
                os.chmod(temporary, self.path.stat().st_mode & 0o777)
                check_config_path(self.path)
                if self.path.read_bytes() != self.before:
                    raise ValueError(f"User Settings changed after preview: {self.path}")
                os.replace(temporary, self.path)
            finally:
                temporary.unlink(missing_ok=True)
        print("Plugin location saved. Editor discovery is not yet verified.")


def discover_vscode_settings() -> list[Path]:
    home = Path.home()
    if sys.platform == "darwin":
        base = home / "Library/Application Support"
    elif sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if not appdata:
            raise ValueError("APPDATA is unset; supply --vscode-settings explicitly.")
        base = Path(appdata)
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or home / ".config")
    candidates: list[Path] = []
    for edition in ("Code", "Code - Insiders"):
        user = base / edition / "User"
        paths = [user / "settings.json", *sorted((user / "profiles").glob("*/settings.json"))]
        for path in paths:
            if path.is_file():
                check_config_path(path)
                candidates.append(path)
    return candidates


def select_vscode_settings(*, dry_run: bool) -> Path:
    candidates = discover_vscode_settings()
    print("Detected VS Code User Settings files (active profile is not inferred):")
    for number, path in enumerate(candidates, 1):
        print(f"  {number}. {path}")
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise ValueError("No saved VS Code User Settings found. Open Preferences: Open User "
                         "Settings (JSON), save the file, and supply --vscode-settings.")
    if dry_run or not sys.stdin.isatty():
        raise ValueError("Multiple VS Code profiles/editions found. Select one explicitly "
                         "with --vscode-settings, or run interactively without --dry-run.")
    choice = input("Choose the intended settings file number (blank cancels): ").strip()
    if not choice.isdigit() or not 1 <= int(choice) <= len(candidates):
        raise ValueError("No valid settings selection; nothing written.")
    return candidates[int(choice) - 1]


def plan_registration(path: Path, target: Path, disable: list[str], *,
                      enable: bool = True) -> RegistrationPlan:
    path = path.expanduser()
    if not path.is_absolute():
        raise ValueError("--vscode-settings must be an absolute User Settings file path.")
    check_config_path(path)
    if not path.is_file():
        raise ValueError("Open Preferences: Open User Settings (JSON), save the file, "
                         "and supply that exact path. No profile path is guessed.")
    before = path.read_bytes()
    try:
        config = json.loads(before, object_pairs_hook=json_object, parse_constant=invalid_json_constant)
    except (ValueError, UnicodeDecodeError) as error:
        raise ValueError("Automatic registration requires strict JSON User Settings. "
                         "For JSONC/comments/trailing commas, merge chat.pluginLocations manually; "
                         "the file has not been changed.") from error
    if not isinstance(config, dict):
        raise ValueError("User Settings must contain a JSON object.")
    if enable and config.get("chat.plugins.enabled") is False:
        raise ValueError("Agent plugins are disabled in User Settings; enable them explicitly first.")
    locations = config.setdefault("chat.pluginLocations", {})
    if not isinstance(locations, dict) or any(
        not isinstance(value, bool) for value in locations.values()
    ):
        raise ValueError("chat.pluginLocations must be an object with boolean values.")
    location = str(target.expanduser().absolute())
    if not enable and location not in locations:
        raise ValueError("Selected bundle is not registered in this User Settings file. "
                         "Disable its plugin manually in the interface used to install it.")
    for old in disable:
        old = str(Path(old).expanduser().absolute())
        if old == location or old not in locations:
            raise ValueError(f"Cannot disable missing or selected plugin location: {old}")
        locations[old] = False
    locations[location] = enable
    content = before if json.loads(before) == config else (json.dumps(config, indent=2) + "\n").encode()
    return RegistrationPlan(path, before, content, locations)


def install_personal_skills(target: Path, directory: Path, *, dry_run: bool, yes: bool,
                            registration: RegistrationPlan | None = None) -> int:
    for path in (target, directory):
        if not path.is_absolute():
            raise ValueError("Bundle and personal skills paths must be absolute.")
        check_config_path(path / "path-check")
    if directory == target or target in directory.parents or directory in target.parents:
        raise ValueError("Personal skills directory must be separate from the shared bundle.")
    manifest = target / "plugin.json"
    check_config_path(manifest)
    if not manifest.is_file() or json.loads(manifest.read_bytes()).get("name") != MANIFEST["name"]:
        raise ValueError("Select an existing Snowflake shared bundle with plugin.json.")
    verify_environment(target)
    sources = sorted((target / "skills").glob("*/SKILL.md"))
    if not sources:
        raise ValueError("Shared bundle contains no skills.")
    changes: list[tuple[Path, bytes]] = []
    snapshots: dict[Path, bytes | None] = {}
    source_snapshots: dict[Path, bytes] = {}
    for source in sources:
        check_config_path(source)
        original = source.read_bytes()
        source_snapshots[source] = original
        text = original.decode("utf-8")
        name = source.parent.name
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
            raise ValueError(f"Invalid skill name: {name}")
        if not text.startswith(f"---\nname: {name}\n") or len(text.split("---", 2)) != 3:
            raise ValueError(f"Invalid skill frontmatter: {source}")
        metadata = text.split("---", 2)[1]
        content = f"""---{metadata}---

# Personal Snowflake skill: {name}

Read [the shared entry point]({source.as_uri()}) and follow its linked
canonical guidance and safety instructions before proceeding.

The shared kit root is `{target}`. When the linked entry point refers to
THIS skill's location, it means the linked file, not this personal shortcut.
Resolve kit scripts and documentation inside that shared root; the current
project remains the consumer root. Never copy the kit into the project.
Use the shared kit's `.venv` interpreter for kit helpers. Loading this skill
does not authorize connections, installations, account changes or deployment.
Do not modify editor/plugin caches. If the bundle moves, stop and reconfigure
this shortcut rather than guessing another kit.
""".encode()
        destination = directory / name / "SKILL.md"
        check_config_path(destination)
        before = destination.read_bytes() if destination.is_file() else None
        if destination.exists() and not destination.is_file():
            raise ValueError(f"Not a regular personal skill file: {destination}")
        if before is not None and before != content:
            raise ValueError(f"Existing personal skill differs; preserve/merge manually: {destination}")
        # A skill folder can contain user assets even if SKILL.md is absent.
        if before is None and destination.parent.exists() and any(destination.parent.iterdir()):
            raise ValueError(f"Existing nonempty personal skill directory: {destination.parent}")
        snapshots[destination] = before
        if before is None:
            changes.append((destination, content))
    print(f"Personal skills: {directory}; shared source: {target}")
    for destination, _ in changes:
        print(f"  CREATE {destination}")
    print(f"{len(sources)} short skill names; {len(changes)} files to create; no guidance copies.")
    print("Disable the shared plugin to avoid duplicate workflows. Its four custom agents "
          "will no longer be exposed by that plugin; personal skills do not install agents.")
    if registration is not None:
        registration.preview()
    else:
        print("Plugin settings unchanged; disable the old plugin in its owning interface manually.")
    if dry_run:
        print("Dry run complete; nothing written.")
        return 0
    if not yes:
        if not sys.stdin.isatty():
            raise ValueError("Non-interactive personal skill setup requires --yes; preview with --dry-run.")
        if input("Create these personal skills and apply listed settings changes? [y/N] ").strip().lower() not in {"y", "yes"}:
            print("Cancelled; nothing written.")
            return 0
    for source, before in source_snapshots.items():
        check_config_path(source)
        if source.read_bytes() != before:
            raise ValueError(f"Shared skill changed after preview: {source}")
    for destination, before in snapshots.items():
        check_config_path(destination)
        current = destination.read_bytes() if destination.exists() else None
        if current != before:
            raise ValueError(f"Personal skill changed after preview: {destination}")
    if registration is not None:
        check_config_path(registration.path)
        if registration.path.read_bytes() != registration.before:
            raise ValueError("User Settings changed after preview.")
    written = 0
    try:
        for destination, content in changes:
            check_config_path(destination)
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("xb") as stream:
                stream.write(content)
            written += 1
        if registration is not None:
            registration.apply()
    except (OSError, ValueError):
        print(f"Personal skill setup interrupted after {written} files; inspect {directory}. "
              "Existing skills were not overwritten.", file=sys.stderr)
        raise
    print("Personal skill files configured. Reload VS Code or start a new session, then check "
          "/snowflake-audit. Running-editor discovery is not yet verified.")
    return 0


def activation_steps(target: Path) -> None:
    print("\nVS Code activation steps:")
    print("1. Merge this into User Settings (JSON) if not registered automatically:")
    print(json.dumps({"chat.pluginLocations": {str(target): True}}, indent=2))
    print("2. Disable the old Snowflake plugin entry, if any; enable only one copy.")
    print("   Existing project-local copies also need separate review to avoid duplicates.")
    print("3. Run Developer: Reload Window.")
    print("4. Open Chat: Open Customizations and check /snowflake-init and /snowflake-dbt-model.")
    print("Agent plugins must be supported, enabled and permitted by organization policy.")
    print("MCP authentication and actual editor discovery are separate checks.")


def shared_payloads() -> dict[Path, bytes]:
    files = payloads()
    for relative in ("install.sh", "scripts/install_kit.py", "scripts/install_shared.py",
                     "README.md", "ARCHITECTURE.md", "AGENTS.md", "scripts/setup_mcp.py"):
        files[Path(relative)] = (ROOT / relative).read_bytes()
    files[Path(".github/copilot-instructions.md")] = (
        ROOT / ".github/copilot-instructions.md"
    ).read_bytes()
    files[Path("plugin.json")] = (json.dumps(MANIFEST, indent=2) + "\n").encode()
    for source, content in list(files.items()):
        is_skill = source.parts[:2] == (".github", "skills") and source.name == "SKILL.md"
        is_prompt = source.parts[:2] == (".github", "prompts") and source.name.endswith(".prompt.md")
        if not (is_skill or is_prompt):
            continue
        text = content.decode("utf-8")
        metadata = text.split("---", 2)[1]
        name_match = re.search(r"^name: (.+)$", metadata, re.MULTILINE)
        description_match = re.search(r'^description: (".*")$', metadata, re.MULTILINE)
        if name_match is None or description_match is None:
            raise ValueError(f"Missing name/quoted description in {source}")
        name = name_match.group(1).strip()
        description = description_match.group(1)
        wrapper = f"""---
name: {name}
description: {description}
---

# Shared Snowflake kit: {name}

This skill belongs to a shared plugin, not the current project.
Read [the full workflow/guidance](../../{source.as_posix()}) and
[Snowflake safety instructions](../../.github/copilot-instructions.md)
before proceeding. Preserve the current project's instructions and conventions.
Do not treat installing or loading this skill as authorization to connect,
install dependencies, modify account objects, or deploy.

## Shared installation path rules

- Resolve the kit root from THIS skill file's location: two directories above
  `skills/{name}/SKILL.md`. Do not assume it is the current working directory
  or a fixed home path; plugin managers may relocate the bundle.
- Every kit `scripts/`, `docs/`, `.github/`, `install.sh`, or hook reference in
  the linked workflow resolves inside that kit root. Use the kit's
  `.venv/bin/python` (`.venv/Scripts/python.exe` on Windows) to invoke Python
  helpers using their quoted absolute path, while passing the explicit PROJECT root
  (or project dbt root) as `--target`. Keep the working directory in the project.
  If the kit environment is missing or broken, report it rather than silently
  falling back to another interpreter. Project environments remain separate;
  initialization does not automatically create a project `.venv`.
- Never copy the kit into the project to make a command work. Project files
  are generated only after the workflow's preview and approval.
- Kit health checks inspect assets in the shared kit, not missing copies in
  the project. Project environment, repository, MCP and pipeline checks still
  inspect the project. A missing project-local kit or `.venv` is not a shared
  plugin failure. Report absent CLI prerequisites without installing them.
- Kit updates use the plugin manager or an approved source checkout's
  `install.sh --shared --update --target "<registered-source-bundle>"`.
  Preview with `--dry-run`, then obtain approval before `--yes`. A tracking
  manifest is required; legacy untracked bundles need a fresh installation.
  Never target an editor/plugin-manager cache, run the project-local installer
  as a shared update, or overwrite customizations.
- MCP configuration, CLI authentication and staged Git hooks remain separate,
  explicit project/user actions. For shared remote MCP setup use
  `scripts/setup_mcp.py` with the kit interpreter and the VS Code user MCP path.
  Existing user-level MCP entries need not be duplicated in the project.
  No MCP server or hook is activated by loading this plugin. Do not install a
  project-local hook merely because kit assets exist.
"""
        files[Path("skills") / name / "SKILL.md"] = wrapper.encode()
    for source, content in list(files.items()):
        if source.parts[:2] == (".github", "agents") and source.name.endswith(".agent.md"):
            files[Path("com.github.copilot/agents") / source.name] = content.replace(
                b"](../skills/", b"](../../.github/skills/",
            )
    return files


def install(target: Path, *, dry_run: bool, yes: bool, mcp: MCPPlan | None = None,
            registration: RegistrationPlan | None = None, update: bool = False) -> int:
    if target.is_symlink():
        raise ValueError(f"Refusing symlink target: {target}")
    target = target.absolute()
    # Check every existing ancestor before resolving or creating anything.
    for ancestor in reversed((target, *target.parents)):
        if ancestor.is_symlink():
            raise ValueError(f"Refusing symlink ancestor: {ancestor}")
    if target == Path.home() or target == Path(target.anchor) or target == ROOT or ROOT in target.parents:
        raise ValueError("Choose a dedicated shared plugin directory, not home, root, or the kit checkout.")
    if target.exists() and not target.is_dir():
        raise ValueError(f"Not a directory: {target}")
    if update:
        if mcp is not None or registration is not None:
            raise ValueError("--update cannot change MCP or User Settings; configure them separately.")
        return update_installation(target, shared_payloads(), "shared", dry_run=dry_run, yes=yes)
    if target.is_dir() and any(target.iterdir()):
        raise ValueError("Shared plugin target must be empty; use --update for tracked installations "
                         "or choose a fresh directory for an untracked legacy copy.")
    if mcp is not None and (mcp.path == target or target in mcp.path.parents):
        raise ValueError("User MCP configuration must be outside the shared plugin directory.")
    if registration is not None:
        if registration.path == target or target in registration.path.parents:
            raise ValueError("User Settings must be outside the shared plugin directory.")
        if mcp is not None and registration.path == mcp.path:
            raise ValueError("User Settings and MCP configuration must be different files.")
    files = shared_payloads()
    tracking = prepare_manifest(target, files, "shared")
    for relative in files:
        check_destination(target, relative)
    print(f"Shared plugin: {target}")
    print(f"Plan: {len(files)} files, 15 guidance skills and 11 workflow skills.")
    print(f"Create kit Python environment: {target / '.venv'} using {sys.executable}")
    print("Uses Python's bundled venv/pip; no downloads or third-party packages.")
    print("No project files, credentials or hooks will be changed.")
    if registration is None:
        print("Editor settings: unchanged.")
    else:
        registration.preview()
    if mcp is None:
        print("MCP: deferred. Use --setup-mcp or the shared scripts/setup_mcp.py helper later.")
    else:
        mcp.preview()
    if dry_run:
        activation_steps(target)
        print("Dry run complete; nothing written.")
        return 0
    if not yes:
        if not sys.stdin.isatty():
            raise ValueError("Non-interactive installation requires --yes; preview with --dry-run.")
        if input("Apply this plan, including listed User Settings/MCP changes? [y/N] ").strip().lower() not in {"y", "yes"}:
            print("Cancelled; nothing written.")
            return 0
    written = 0
    try:
        for relative, content in files.items():
            check_destination(target, relative)
            destination = target / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("xb") as stream:
                stream.write(content)
            written += 1
        check_destination(target, Path(".venv"))
        venv.EnvBuilder(with_pip=True).create(target / ".venv")
        verify_environment(target)
        if mcp is not None:
            mcp.apply()
        if registration is not None:
            registration.apply()
        save_manifest(target, tracking)
    except (OSError, ValueError, subprocess.SubprocessError):
        print(f"Installation interrupted after {written} files; inspect {target} before retrying.",
              file=sys.stderr)
        raise
    print("Shared plugin created.")
    activation_steps(target)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, default=Path.home() / ".snowflake-ai-data-developer")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--update", action="store_true",
                        help="Back up and update unchanged manifest-owned kit assets only")
    parser.add_argument("--yes", action="store_true")
    parser.add_argument("--personal-skills", action="store_true",
                        help="Create short user-level skill entry points to an existing shared bundle")
    parser.add_argument("--skills-dir", type=Path,
                        help="Personal skills directory (default: ~/.copilot/skills); requires --personal-skills")
    parser.add_argument("--register-vscode", action="store_true",
                        help="Offer User Settings registration with preview and installation approval")
    parser.add_argument("--vscode-settings", type=Path,
                        help="Exact absolute file path from Preferences: Open User Settings (JSON)")
    parser.add_argument("--disable-plugin", action="append", default=[],
                        help="Explicit old plugin location to disable; repeat as needed")
    add_mcp_arguments(parser)
    args = parser.parse_args()
    try:
        if args.skills_dir is not None and not args.personal_skills:
            raise ValueError("--skills-dir requires --personal-skills.")
        if args.personal_skills:
            if (args.update or args.setup_mcp or args.mcp_endpoint or args.mcp_auth
                    or args.mcp_approved or args.mcp_oauth_client_id or args.mcp_config
                    or args.mcp_tool or args.mcp_format != "vscode"):
                raise ValueError("--personal-skills is separate from bundle updates and MCP setup.")
            if args.register_vscode and args.vscode_settings is None:
                args.vscode_settings = select_vscode_settings(dry_run=args.dry_run)
            if args.disable_plugin and args.vscode_settings is None:
                raise ValueError("--disable-plugin requires explicit VS Code registration settings.")
            target = args.target.expanduser()
            registration = (plan_registration(args.vscode_settings, target,
                                             args.disable_plugin, enable=False)
                            if args.vscode_settings is not None else None)
            directory = (args.skills_dir or Path.home() / ".copilot/skills").expanduser()
            return install_personal_skills(target, directory, dry_run=args.dry_run,
                                           yes=args.yes, registration=registration)
        if args.update:
            if (args.register_vscode or args.vscode_settings or args.disable_plugin
                    or args.setup_mcp or args.mcp_endpoint or args.mcp_auth
                    or args.mcp_approved or args.mcp_oauth_client_id or args.mcp_config
                    or args.mcp_tool or args.mcp_format != "vscode"):
                raise ValueError("--update cannot change MCP or User Settings; configure them separately.")
            return install(args.target.expanduser(), dry_run=args.dry_run, yes=args.yes, update=True)
        mcp = plan_mcp(args)
        if args.disable_plugin and not (args.register_vscode or args.vscode_settings):
            raise ValueError("--disable-plugin requires VS Code registration.")
        if args.register_vscode and args.vscode_settings is None:
            args.vscode_settings = select_vscode_settings(dry_run=args.dry_run)
        registration = (plan_registration(args.vscode_settings, args.target, args.disable_plugin)
                        if args.vscode_settings is not None else None)
        return install(args.target.expanduser(), dry_run=args.dry_run, yes=args.yes, mcp=mcp,
                       registration=registration)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
