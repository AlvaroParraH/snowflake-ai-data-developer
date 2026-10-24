"""Install project-local Copilot assets without replacing existing content."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
START = b"<!-- snowflake-ai-data-developer:start -->"
END = b"<!-- snowflake-ai-data-developer:end -->"
PIPELINE_DIRECTORIES = tuple(map(Path, (
    "pipelines",
    "pipelines/ingestion",
    "pipelines/ingestion/bronze",
    "pipelines/dbt",
    "pipelines/dbt/models",
    "pipelines/dbt/models/silver",
    "pipelines/dbt/models/silver/staging",
    "pipelines/dbt/models/silver/intermediate",
    "pipelines/dbt/models/gold",
    "pipelines/dbt/models/gold/marts",
    "pipelines/orchestration",
    "pipelines/orchestration/airflow",
    "pipelines/orchestration/airflow/dags",
)))


def uv_install_plan() -> str:
    if sys.platform == "darwin":
        if not shutil.which("brew"):
            raise ValueError("uv is required. Install Homebrew or install uv manually: "
                             "https://docs.astral.sh/uv/getting-started/installation/")
        return "brew install uv (machine-level Homebrew installation)"
    if sys.platform.startswith("linux"):
        if not shutil.which("curl") or not shutil.which("sh"):
            raise ValueError("Installing uv requires curl and sh. Install uv manually: "
                             "https://docs.astral.sh/uv/getting-started/installation/")
        return ("download and run https://astral.sh/uv/install.sh; "
                f"install to {Path.home() / '.local/bin'} without editing shell profiles")
    raise ValueError("Automatic uv installation supports macOS and Linux only. "
                     "Install uv manually and ensure it is on PATH: "
                     "https://docs.astral.sh/uv/getting-started/installation/")


def install_uv() -> str:
    uv_install_plan()
    if sys.platform == "darwin":
        subprocess.run(["brew", "install", "uv"], check=True, stdin=subprocess.DEVNULL)
        executable = shutil.which("uv")
    else:
        directory = Path.home() / ".local/bin"
        environment = dict(os.environ, UV_INSTALL_DIR=str(directory), UV_NO_MODIFY_PATH="1")
        environment.pop("UV_UNMANAGED_INSTALL", None)
        with tempfile.TemporaryDirectory(prefix="snowflake-uv-install-") as temporary:
            script = Path(temporary) / "install.sh"
            subprocess.run(
                ["curl", "--fail", "--location", "--silent", "--show-error",
                 "--proto", "=https", "--proto-redir", "=https",
                 "--connect-timeout", "15", "--max-time", "120",
                 "--output", str(script), "https://astral.sh/uv/install.sh"],
                check=True, stdin=subprocess.DEVNULL,
            )
            subprocess.run(["sh", str(script)], env=environment,
                           check=True, stdin=subprocess.DEVNULL)
        executable = shutil.which(str(directory / "uv"))
        print(f"Add {directory} to PATH in future shells if it is not already present.")
    if not executable:
        raise ValueError("uv installation finished but its executable was not found. "
                         "Check the installation and PATH before rerunning; no project files written.")
    return executable


def verify_uv(executable: str) -> None:
    result = subprocess.run([executable, "--version"], check=True, capture_output=True, text=True)
    version = result.stdout.strip()
    if not version.startswith("uv "):
        raise ValueError(f"Unexpected uv --version output from {executable}: {version!r}")
    print(f"Prerequisite verified: {version} ({executable})")


def payloads() -> dict[Path, bytes]:
    files: dict[Path, bytes] = {}
    for directory in (".github/skills", ".github/prompts", "docs"):
        source = ROOT / directory
        if not source.is_dir():
            raise ValueError(f"Missing kit directory: {source}")
        for file in sorted(source.rglob("*")):
            if file.is_symlink():
                raise ValueError(f"Symlink in kit assets: {file}")
            if file.is_file() and file.suffix in {".md", ".svg"}:
                files[file.relative_to(ROOT)] = file.read_bytes()
    skills = {
        p.parent.name
        for p in files
        if p.parts[:2] == (".github", "skills") and p.name == "SKILL.md"
    }
    if not skills:
        raise ValueError("No skills found under .github/skills/.")
    return files


def check_destination(target: Path, relative: Path) -> None:
    current = target
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            raise ValueError(f"Refusing symlink destination: {current}")
        if current.exists() and current != target / relative and not current.is_dir():
            raise ValueError(f"Destination parent is not a directory: {current}")


def instruction_content(existing: bytes) -> bytes:
    guidance = (ROOT / ".github/copilot-instructions.md").read_bytes()
    guidance = guidance.split(b"\n## Editing this kit", 1)[0].rstrip()
    block = START + b"\n" + guidance + b"\n" + END
    if START in existing or END in existing:
        if existing.count(START) != 1 or existing.count(END) != 1:
            raise ValueError("Malformed Snowflake instruction block; merge it manually.")
        start = existing.index(START)
        end = existing.index(END) + len(END)
        if existing[start:end] != block:
            raise ValueError("Existing Snowflake instruction block differs; merge it manually.")
        return existing
    if existing:
        return existing + (b"\n" if existing.endswith(b"\n") else b"\n\n") + block + b"\n"
    return block + b"\n"


def install(target: Path, dry_run: bool, assume_yes: bool, no_install: bool = False) -> int:
    if not target.is_dir():
        raise ValueError("Target must be an existing project directory.")
    target = target.resolve()
    if target == ROOT or ROOT in target.parents:
        raise ValueError("Choose a target outside the source kit.")

    files = payloads()
    instructions = Path(".github/copilot-instructions.md")
    check_destination(target, instructions)
    destination = target / instructions
    if destination.exists() and not destination.is_file():
        raise ValueError(f"Not a regular file: {destination}")
    original = destination.read_bytes() if destination.exists() else None
    files[instructions] = instruction_content(original or b"")

    changes: list[tuple[Path, bytes, bytes | None]] = []
    conflicts: list[str] = []
    directories: list[Path] = []
    for relative in PIPELINE_DIRECTORIES:
        check_destination(target, relative)
        destination = target / relative
        if destination.exists():
            if not destination.is_dir():
                conflicts.append(f"{relative}: not a directory")
        else:
            directories.append(relative)
    skill_names = {
        relative.parent.name
        for relative in files
        if relative.parts[:2] == (".github", "skills") and relative.name == "SKILL.md"
    }
    for directory in (".agents/skills", ".claude/skills"):
        for name in sorted(skill_names):
            alternate = target / directory / name
            if alternate.exists() or alternate.is_symlink():
                conflicts.append(f"{directory}/{name}: duplicate skill discovery root")
    unchanged = 0
    for relative, content in sorted(files.items()):
        check_destination(target, relative)
        destination = target / relative
        if destination.exists() and not destination.is_file():
            conflicts.append(f"{relative}: not a regular file")
            continue
        before = destination.read_bytes() if destination.exists() else None
        if before == content:
            unchanged += 1
        elif before is not None and relative != instructions:
            conflicts.append(f"{relative}: existing content differs")
        else:
            changes.append((relative, content, before))

    print(f"Target: {target}")
    for relative in directories:
        print(f"  MKDIR {relative}")
    for relative, _, before in changes:
        print(f"  {'APPEND' if before is not None else 'CREATE'} {relative}")
    print(f"Unchanged: {unchanged}; planned writes: {len(changes)}; "
          f"planned directories: {len(directories)}")
    if conflicts:
        raise ValueError(
            "Conflicts found; no files written. Review/merge these files manually, then rerun:\n  "
            + "\n  ".join(conflicts)
        )
    uv = shutil.which("uv")
    if uv:
        print(f"Prerequisite: uv found at {uv}; will verify with uv --version.")
    elif no_install:
        print("Prerequisite: uv missing; automatic installation disabled (--no-install).")
    else:
        print(f"Prerequisite: uv missing; INSTALL {uv_install_plan()}.")
    if dry_run:
        print("Dry run complete. No files written, commands executed or tools installed. "
              "uv is required for an actual installation.")
        return 0
    if not uv and no_install:
        raise ValueError("uv is required but missing. Install uv and add it to PATH, "
                         "or rerun without --no-install. No project files written.")
    if not assume_yes and (changes or directories or not uv):
        if not sys.stdin.isatty():
            raise ValueError("Non-interactive installation requires --yes; preview with --dry-run.")
        if input("Approve this plan, including uv installation if listed? [y/N] "
                 ).strip().lower() not in {"y", "yes"}:
            print("Cancelled. No files written.")
            return 0
    if not uv:
        uv = install_uv()
    verify_uv(uv)
    if not changes and not directories:
        print("Already installed; no files changed.")
        return 0

    written = 0
    created = 0
    try:
        for relative in directories:
            check_destination(target, relative)
            (target / relative).mkdir(exist_ok=True)
            created += 1
        for relative, content, before in changes:
            check_destination(target, relative)
            destination = target / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            if before is None:
                with destination.open("xb") as stream:
                    stream.write(content)
            else:
                if destination.read_bytes() != before:
                    raise ValueError(f"File changed after preview: {destination}")
                with destination.open("ab") as stream:
                    stream.write(content[len(before):])
            written += 1
    except (OSError, ValueError):
        print(f"Installation interrupted after {written} file writes and {created} directory "
              "operations; inspect the target before retrying.",
              file=sys.stderr)
        raise
    print(f"Installed {written} files; created {created} pipeline directories. "
          "uv prerequisite verified. No project dependencies, MCP connections or "
          "Snowflake resources configured.")
    print("Open the target as the VS Code workspace root and reload to check Copilot discovery.")
    print("Expected: eight snowflake-* skills, /snowflake-mcp-setup and /snowflake-sql-check.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Install Snowflake skills, prompts, documentation and Copilot instructions "
        "and create the medallion/dbt/Airflow folder layout in an existing project. "
        "Never overwrites conflicting files."
    )
    parser.add_argument("--target", type=Path, required=True, help="Existing target project root")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--yes", action="store_true",
                        help="Approve the displayed plan, including installation of missing uv")
    parser.add_argument("--no-install", action="store_true",
                        help="Never install uv; fail if the prerequisite is missing")
    args = parser.parse_args()
    if sys.version_info < (3, 10):
        parser.error("Python 3.10+ is required.")
    try:
        return install(args.target.expanduser(), args.dry_run, args.yes, args.no_install)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"Error: {error}", file=sys.stderr)
        if isinstance(error, subprocess.CalledProcessError) and error.stderr:
            print(error.stderr, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
