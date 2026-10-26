"""Build a shared, relocatable Snowflake agent plugin without changing projects."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import venv

from install_kit import ROOT, check_destination, payloads, verify_environment
from setup_mcp import MCPPlan, add_mcp_arguments, plan_mcp


MANIFEST = {
    "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
    "name": "snowflake-data-developer",
    "version": "1.0.0",
    "description": "Snowflake engineering skills and local project/model workflows.",
}


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
- Kit updates are performed by the plugin manager or by rebuilding the shared
  bundle into a fresh directory. Do not run the project-local installer as an
  update, alter a plugin cache, or overwrite existing project customizations.
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


def install(target: Path, *, dry_run: bool, yes: bool, mcp: MCPPlan | None = None) -> int:
    if target.is_symlink():
        raise ValueError(f"Refusing symlink target: {target}")
    target = target.absolute()
    # Check every existing ancestor before resolving or creating anything.
    for ancestor in reversed((target, *target.parents)):
        if ancestor.is_symlink():
            raise ValueError(f"Refusing symlink ancestor: {ancestor}")
    if target == Path.home() or target == Path(target.anchor) or target == ROOT:
        raise ValueError("Choose a dedicated shared plugin directory, not home, root, or the kit checkout.")
    if target.exists() and not target.is_dir():
        raise ValueError(f"Not a directory: {target}")
    if target.is_dir() and any(target.iterdir()):
        raise ValueError("Shared plugin target must be empty; choose a fresh directory for updates.")
    if mcp is not None and (mcp.path == target or target in mcp.path.parents):
        raise ValueError("User MCP configuration must be outside the shared plugin directory.")
    files = shared_payloads()
    for relative in files:
        check_destination(target, relative)
    print(f"Shared plugin: {target}")
    print(f"Plan: {len(files)} files, 15 guidance skills and 10 workflow skills.")
    print(f"Create kit Python environment: {target / '.venv'} using {sys.executable}")
    print("Uses Python's bundled venv/pip; no downloads or third-party packages.")
    print("No project files, editor settings, credentials or hooks will be changed.")
    if mcp is None:
        print("MCP: deferred. Use --setup-mcp or the shared scripts/setup_mcp.py helper later.")
    else:
        mcp.preview()
    if dry_run:
        print("Dry run complete; nothing written.")
        return 0
    if not yes:
        if not sys.stdin.isatty():
            raise ValueError("Non-interactive installation requires --yes; preview with --dry-run.")
        if input("Create this shared plugin? [y/N] ").strip().lower() not in {"y", "yes"}:
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
    except (OSError, ValueError, subprocess.SubprocessError):
        print(f"Installation interrupted after {written} files; inspect {target} before retrying.",
              file=sys.stderr)
        raise
    print("Shared plugin created. Register this folder in VS Code to enable it.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, default=Path.home() / ".snowflake-ai-data-developer")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--yes", action="store_true")
    add_mcp_arguments(parser)
    args = parser.parse_args()
    try:
        mcp = plan_mcp(args)
        return install(args.target.expanduser(), dry_run=args.dry_run, yes=args.yes, mcp=mcp)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
