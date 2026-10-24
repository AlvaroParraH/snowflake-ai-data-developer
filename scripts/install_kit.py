"""Install project-local Copilot assets without replacing existing content."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit


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


def verify_git(executable: str) -> None:
    subprocess.run([executable, "--version"], check=True, stdin=subprocess.DEVNULL)


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


def json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON property; merge MCP configuration manually.")
        result[key] = value
    return result


def invalid_json_constant(value: str) -> None:
    raise ValueError("Non-finite JSON value; merge MCP configuration manually.")


def mcp_content(existing: bytes | None, endpoint: str, authentication: str) -> bytes:
    url = urlsplit(endpoint)
    if (url.scheme != "https" or not url.hostname or url.username or url.password
            or url.query or url.fragment or any(c.isspace() for c in endpoint)):
        raise ValueError("MCP requires an exact approved HTTPS endpoint without credentials, "
                         "query parameters, fragments or whitespace.")
    if authentication not in {"oauth", "bearer"}:
        raise ValueError("MCP authentication must be oauth or bearer, confirmed by your administrator.")
    try:
        config = (json.loads(existing, object_pairs_hook=json_object,
                             parse_constant=invalid_json_constant)
                  if existing is not None else {})
    except (ValueError, UnicodeDecodeError) as error:
        raise ValueError("Existing .vscode/mcp.json must be strict JSON for automated merging. "
                         "For JSONC/comments, use /snowflake-mcp-setup to merge manually.") from error
    if not isinstance(config, dict):
        raise ValueError(".vscode/mcp.json must contain a JSON object.")
    servers = config.setdefault("servers", {})
    if not isinstance(servers, dict):
        raise ValueError("MCP servers must be a JSON object.")
    entry: dict[str, object] = {"type": "http", "url": endpoint}
    if authentication == "bearer":
        entry["headers"] = {"Authorization": "Bearer ${env:SNOWFLAKE_MCP_TOKEN}"}
    if "snowflake" in servers and servers["snowflake"] != entry:
        raise ValueError("Existing snowflake MCP server differs; merge it manually.")
    servers["snowflake"] = entry
    if existing is not None and json.loads(existing) == config:
        return existing
    return (json.dumps(config, indent=2) + "\n").encode()


def environment_python(target: Path) -> Path:
    return target / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def needs_environment(target: Path) -> bool:
    check_destination(target, Path(".venv"))
    environment = target / ".venv"
    if not environment.exists():
        for manifest in ("poetry.lock", "Pipfile", "Pipfile.lock", "environment.yml",
                         "environment.yaml", ".python-version"):
            if (target / manifest).exists():
                raise ValueError(f"Existing {manifest} requires a project-specific environment "
                                 "decision. Use --skip-venv and the project's existing workflow.")
        return True
    configuration = environment / "pyvenv.cfg"
    if (not environment.is_dir() or not configuration.is_file()
            or configuration.is_symlink() or not environment_python(target).is_file()):
        raise ValueError("Existing .venv is not a recognizable virtual environment. "
                         "Preserve or repair it manually; it will not be overwritten.")
    return False


def verify_environment(target: Path) -> None:
    result = subprocess.run(
        [str(environment_python(target)), "-I", "-c",
         "import sys; print(sys.prefix); print(sys.base_prefix)"],
        check=True, capture_output=True, text=True, stdin=subprocess.DEVNULL,
    )
    prefixes = result.stdout.strip().splitlines()
    if (len(prefixes) != 2 or Path(prefixes[0]).resolve() != (target / ".venv").resolve()
            or prefixes[0] == prefixes[1]):
        raise ValueError("Virtual environment verification failed; inspect .venv before retrying.")
    print(f"Verified Python environment: {target / '.venv'} (no dependencies installed).")


def install(target: Path, dry_run: bool, assume_yes: bool, no_install: bool = False,
            *, skip_venv: bool = False, mcp_endpoint: str | None = None,
            mcp_auth: str | None = None, mcp_approved: bool = False) -> int:
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
    mcp = Path(".vscode/mcp.json")
    mcp_original = None
    if mcp_endpoint is not None:
        if not mcp_approved:
            raise ValueError("Confirm administrator approval of the MCP endpoint, exposed tools "
                             "and client-compatible authentication with --mcp-approved.")
        check_destination(target, mcp)
        config = target / mcp
        if config.exists() and not config.is_file():
            raise ValueError("MCP configuration is not a regular file.")
        mcp_original = config.read_bytes() if config.exists() else None
        files[mcp] = mcp_content(mcp_original, mcp_endpoint, mcp_auth or "")
    elif mcp_auth is not None or mcp_approved:
        raise ValueError("MCP authentication/approval requires --mcp-endpoint or --setup-mcp.")
    create_environment = not skip_venv and needs_environment(target)

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
        if relative == mcp and before != mcp_original:
            raise ValueError("MCP configuration changed during preview; rerun before making changes.")
        if before == content:
            unchanged += 1
        elif before is not None and relative not in {instructions, mcp}:
            conflicts.append(f"{relative}: existing content differs")
        else:
            changes.append((relative, content, before))

    print(f"Target: {target}")
    print(f"Prerequisites: Bash entrypoint; Python {sys.version.split()[0]} at {sys.executable}.")
    git = shutil.which("git")
    if not git:
        raise ValueError("Git is required. Install Git manually and add it to PATH; "
                         "no tools or project files changed.")
    print(f"Prerequisite: Git found at {git}; will verify with git --version.")
    if skip_venv:
        print("Python environment: skipped (--skip-venv); existing project tooling preserved.")
    else:
        print(f"  {'CREATE' if create_environment else 'VERIFY'} .venv "
              f"using local Python; no dependencies or interpreter downloads.")
    if mcp_endpoint is None:
        print("MCP: deferred. Use --setup-mcp or /snowflake-mcp-setup when details are approved.")
    else:
        print(f"MCP: VS Code HTTP server 'snowflake', endpoint {mcp_endpoint}, auth {mcp_auth}.")
        print(json.dumps({"servers": {"snowflake": json.loads(files[mcp])["servers"]["snowflake"]}},
                         indent=2))
        print("No connection will be made. Review trust, authentication and tool selection in VS Code.")
        if mcp_auth == "bearer":
            print("Provide SNOWFLAKE_MCP_TOKEN securely in the VS Code host environment later; "
                  "the installer never reads or stores it.")
        else:
            print("Complete the administrator-provisioned OAuth flow in VS Code later. "
                  "Static OAuth client details, if needed, require separate administrator setup.")
    for relative in directories:
        print(f"  MKDIR {relative}")
    for relative, _, before in changes:
        action = "MERGE" if relative == mcp else "APPEND"
        print(f"  {action if before is not None else 'CREATE'} {relative}")
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
    if not assume_yes and (changes or directories or not uv or create_environment):
        if not sys.stdin.isatty():
            raise ValueError("Non-interactive installation requires --yes; preview with --dry-run.")
        if input("Approve this plan, including environment/MCP setup and uv installation if listed? [y/N] "
                 ).strip().lower() not in {"y", "yes"}:
            print("Cancelled. No files written.")
            return 0
    verify_git(git)
    if not uv:
        uv = install_uv()
    verify_uv(uv)
    if not skip_venv and not create_environment:
        verify_environment(target)
    if not changes and not directories and not create_environment:
        print("Already installed; no files changed.")
        return 0

    written = 0
    created = 0
    try:
        if create_environment:
            check_destination(target, Path(".venv"))
            (target / ".venv").mkdir()
            environment = dict(os.environ, UV_VENV_SEED="false", UV_VENV_CLEAR="false")
            subprocess.run(
                [uv, "venv", "--no-config", "--offline", "--no-python-downloads",
                 "--python", sys.executable, str(target / ".venv")],
                check=True, stdin=subprocess.DEVNULL, env=environment, cwd=target,
            )
            verify_environment(target)
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
                if relative == mcp:
                    with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as stream:
                        temporary = Path(stream.name)
                        try:
                            stream.write(content)
                            stream.flush()
                            if destination.read_bytes() != before:
                                raise ValueError(f"File changed after preview: {destination}")
                            os.replace(temporary, destination)
                        finally:
                            temporary.unlink(missing_ok=True)
                else:
                    with destination.open("ab") as stream:
                        stream.write(content[len(before):])
            written += 1
    except (OSError, ValueError, subprocess.CalledProcessError):
        print(f"Installation interrupted after {written} file writes and {created} directory "
              "operations; inspect the target before retrying.",
              file=sys.stderr)
        if create_environment:
            print("Environment setup was attempted; .venv may remain. Inspect/repair it manually "
                  "before retrying. It will not be overwritten.", file=sys.stderr)
        raise
    print(f"Installed {written} files; created {created} pipeline directories. "
          "Prerequisites verified. No project dependencies installed or Snowflake connections made.")
    print("Open the target as the VS Code workspace root and reload to check Copilot discovery.")
    print("Expected: eight snowflake-* skills, /snowflake-mcp-setup and /snowflake-sql-check.")
    if not skip_venv:
        print(f"Select {environment_python(target)} as the project's VS Code interpreter.")
    if mcp_endpoint is not None:
        print("VS Code MCP configuration is ready for manual trust/authentication and approved "
              "tool selection. Connection not tested.")
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
    parser.add_argument("--skip-venv", action="store_true",
                        help="Preserve existing project environment conventions; do not set up .venv")
    parser.add_argument("--setup-mcp", action="store_true",
                        help="Prompt for approved VS Code MCP details at setup time")
    parser.add_argument("--mcp-endpoint", help="Exact approved HTTPS MCP endpoint; never include secrets")
    parser.add_argument("--mcp-auth", choices=("oauth", "bearer"),
                        help="Administrator-confirmed client-compatible authentication method")
    parser.add_argument("--mcp-approved", action="store_true",
                        help="Confirm the endpoint, exposed tools and client authentication are approved")
    args = parser.parse_args()
    if sys.version_info < (3, 10):
        parser.error("Python 3.10+ is required.")
    try:
        if args.setup_mcp and not args.mcp_endpoint:
            if args.dry_run:
                print("MCP setup pending: actual --setup-mcp will ask for the approved endpoint, "
                      "authentication and approval. No MCP file is planned yet.")
            elif not sys.stdin.isatty():
                raise ValueError("Non-interactive MCP setup requires --mcp-endpoint, "
                                 "--mcp-auth and --mcp-approved; --yes does not supply approval.")
            else:
                args.mcp_endpoint = input("Administrator-approved HTTPS MCP endpoint (no secrets): ").strip()
                args.mcp_auth = input("Administrator-confirmed authentication (oauth/bearer): ").strip()
                args.mcp_approved = input(
                    "Have the endpoint, exposed tools and VS Code authentication compatibility "
                    "been reviewed and approved by your administrator? [y/N] "
                ).strip().lower() in {"y", "yes"}
        return install(args.target.expanduser(), args.dry_run, args.yes, args.no_install,
                       skip_venv=args.skip_venv, mcp_endpoint=args.mcp_endpoint,
                       mcp_auth=args.mcp_auth, mcp_approved=args.mcp_approved)
    except (OSError, ValueError, EOFError, subprocess.CalledProcessError) as error:
        print(f"Error: {error}", file=sys.stderr)
        if isinstance(error, subprocess.CalledProcessError) and error.stderr:
            print(error.stderr, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
