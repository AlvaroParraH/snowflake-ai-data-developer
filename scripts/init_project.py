"""Create the agreed pipeline folders without generating application files."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess
import sys


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


def check_directory(target: Path, relative: Path) -> None:
    current = target
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            raise ValueError(f"Refusing symlink directory: {current}")
        if current.exists() and not current.is_dir():
            raise ValueError(f"Not a directory: {current}")


def detect_project(target: Path) -> dict[str, list[str]]:
    signals: list[str] = []
    for relative in ("snowflake.yml", "snowflake.yaml", "dbt_project.yml",
                     "pipelines/dbt/dbt_project.yml", "docs/project-profile.md"):
        path = target / relative
        if path.is_symlink():
            raise ValueError(f"Refusing symlink detection path: {path}")
        if path.is_file():
            signals.append(relative)
    for relative in ("src", "pipelines", "models", "dags", "bronze", "silver", "gold"):
        path = target / relative
        if path.is_symlink():
            raise ValueError(f"Refusing symlink detection path: {path}")
        if path.is_dir():
            pending = [path]
            populated = False
            while pending and not populated:
                for child in pending.pop().iterdir():
                    if child.is_symlink():
                        raise ValueError(f"Refusing symlink detection path: {child}")
                    if child.is_dir():
                        pending.append(child)
                    elif child.is_file():
                        populated = True
                        break
            if populated:
                signals.append(f"{relative}/ contains files")
    return {"signals": signals}


def git_repository(target: Path) -> tuple[Path, str] | None:
    executable = shutil.which("git")
    if executable is None:
        raise ValueError("Git is required for Git initialization. Install Git or use --no-git.")
    result = subprocess.run(
        [executable, "-C", str(target), "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, check=False,
    )
    if result.returncode:
        if (target / ".git").exists():
            raise ValueError(f"Git metadata exists but cannot be inspected at {target / '.git'}.")
        return None
    return Path(result.stdout.strip()).resolve(), executable


def initialize(target: Path, dry_run: bool, assume_yes: bool, *,
               detect_only: bool = False, allow_existing: bool = False,
               no_git: bool = False) -> int:
    if not target.is_dir():
        raise ValueError("Target must be an existing project directory.")
    target = target.resolve()
    if target == Path.home().resolve() or target == Path(target.anchor):
        raise ValueError("Choose a project directory, not your home or filesystem root.")
    if (target / "scripts/install_kit.py").is_file():
        raise ValueError("Refusing to scaffold inside the skill kit; choose a target project.")
    signals = detect_project(target)["signals"]
    print(f"Project state: {'brownfield (existing project)' if signals else 'greenfield (no project signals found)'}.")
    for signal in signals:
        print(f"  SIGNAL {signal}")
    print("Detection is local and heuristic; no account access or configuration values read.")
    if detect_only:
        print("Detection complete. No files or directories created.")
        return 0
    repository = None if no_git else git_repository(target)
    initialize_git = repository is None and not no_git
    if no_git:
        print("Git initialization: skipped (--no-git).")
    elif repository is None:
        print("  GIT INIT: initialize a local Git repository at the target root.")
    elif repository[0] == target:
        print(f"Git initialization: skipped; target is already a Git repository ({repository[0]}).")
    else:
        print(f"Git initialization: skipped; target is already inside parent repository "
              f"{repository[0]} (no nested repository will be created).")
    missing: list[Path] = []
    for relative in PIPELINE_DIRECTORIES:
        check_directory(target, relative)
        if not (target / relative).exists():
            missing.append(relative)
    print(f"Target: {target}")
    for relative in missing:
        print(f"  MKDIR {relative}")
    print(f"Planned directories: {len(missing)}. Existing files and folders remain unchanged.")
    if dry_run:
        print("Dry run complete. No Git repository or directories created.")
        return 0
    if not missing and not initialize_git:
        print("Already initialized; no changes.")
        return 0
    if signals and not allow_existing and (missing or initialize_git):
        raise ValueError("Existing project detected. Review its layout first. Use --allow-existing "
                         "only after approving the requested additive setup; --yes alone is not approval.")
    if not assume_yes:
        if not sys.stdin.isatty():
            raise ValueError("Non-interactive initialization requires --yes; preview with --dry-run.")
        if input("Apply this plan, including Git initialization if listed? [y/N] "
                 ).strip().lower() not in {"y", "yes"}:
            print("Cancelled. No repository or directories created.")
            return 0
    created = 0
    git_created = False
    try:
        if initialize_git:
            executable = shutil.which("git")
            if executable is None:
                raise ValueError("Git disappeared after preview; no directories created.")
            result = subprocess.run(
                [executable, "-C", str(target), "init"],
                check=True, capture_output=True, text=True,
            )
            git_created = True
            print(f"Initialized Git repository at {target}.")
            if result.stdout.strip():
                print(result.stdout.strip())
        for relative in missing:
            check_directory(target, relative)
            (target / relative).mkdir(exist_ok=True)
            created += 1
    except (OSError, ValueError):
        print(f"Initialization interrupted after Git initialization={git_created} and "
              f"{created} directory operations; "
              "inspect the target before retrying.", file=sys.stderr)
        raise
    print(f"Created {created} directories; Git initialized={git_created}. No starter files, "
          "dependencies, Snowflake connections or deployments.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, required=True, help="Existing project root")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--yes", action="store_true", help="Approve creating the displayed folders")
    parser.add_argument("--detect-only", action="store_true",
                        help="Report local greenfield/brownfield signals without creating folders")
    parser.add_argument("--allow-existing", action="store_true",
                        help="Explicitly approve additive folders in an existing project; never overwrites")
    parser.add_argument("--no-git", action="store_true",
                        help="Do not initialize Git when the target is not already in a repository")
    args = parser.parse_args()
    if sys.version_info < (3, 10):
        parser.error("Python 3.10+ is required.")
    try:
        return initialize(args.target.expanduser(), args.dry_run, args.yes,
                          detect_only=args.detect_only, allow_existing=args.allow_existing,
                          no_git=args.no_git)
    except (OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
