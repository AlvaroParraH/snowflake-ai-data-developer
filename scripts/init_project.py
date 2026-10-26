"""Initialize agreed pipeline folders, with an optional context-aware scaffold."""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys


SCAFFOLDER_SPEC = importlib.util.spec_from_file_location(
    "snowflake_scaffold_project", Path(__file__).with_name("scaffold_snowflake_project.py"),
)
assert SCAFFOLDER_SPEC is not None and SCAFFOLDER_SPEC.loader is not None
greenfield_scaffolder = importlib.util.module_from_spec(SCAFFOLDER_SPEC)
sys.modules[SCAFFOLDER_SPEC.name] = greenfield_scaffolder
write_bytecode = sys.dont_write_bytecode
sys.dont_write_bytecode = True
try:
    SCAFFOLDER_SPEC.loader.exec_module(greenfield_scaffolder)
finally:
    sys.dont_write_bytecode = write_bytecode


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
               no_git: bool = False, scaffold: bool = False,
               scaffold_options: dict[str, str] | None = None) -> int:
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
    if scaffold and signals:
        raise ValueError("Greenfield starter scaffolding is only available when no existing "
                         "Snowflake project signals are detected. Use the folder-only setup "
                         "after reviewing this existing project.")
    starter_files: dict[Path, bytes] = {}
    starter_directories: list[Path] = []
    if scaffold:
        options = scaffold_options or {}
        config = greenfield_scaffolder.ScaffoldConfig(
            project_name=options.get("project_name") or
                greenfield_scaffolder.project_slug(target.name),
            source_type=options.get("source_type", "undecided"),
            environment=options.get("environment", "not_decided"),
            owner=options.get("owner", ""),
            description=options.get("description", ""),
            domain=options.get("domain", ""),
            data_sensitivity=options.get("data_sensitivity", "not_assessed"),
            consumers=options.get("consumers", ""),
        )
        starter_files, starter_directories = greenfield_scaffolder.plan_scaffold(
            target, config,
        )
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
    directories = (*PIPELINE_DIRECTORIES, *starter_directories)
    for relative in directories:
        check_directory(target, relative)
        if not (target / relative).exists() and relative not in missing:
            missing.append(relative)
    print(f"Target: {target}")
    for relative in missing:
        print(f"  MKDIR {relative}")
    for relative in starter_files:
        print(f"  CREATE {relative}")
    print(f"Planned directories: {len(missing)}; starter files: {len(starter_files)}. "
          "Existing files and folders remain unchanged.")
    if dry_run:
        print("Dry run complete. No Git repository, directories or files created.")
        return 0
    if not missing and not starter_files and not initialize_git:
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
    files_created = 0
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
        for relative, content in starter_files.items():
            files_created += greenfield_scaffolder.write_scaffold(
                target, {relative: content},
            )
    except (OSError, ValueError):
        if starter_files:
            operations = f"{created} directory and {files_created} file operations"
        else:
            operations = f"{created} directory operations"
        print(f"Initialization interrupted after Git initialization={git_created} and "
              f"{operations}; inspect the target before retrying.", file=sys.stderr)
        raise
    print(f"Created {created} directories and {files_created} starter files; "
          f"Git initialized={git_created}. No dependencies installed, "
          "Snowflake connections or deployments.")
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
    parser.add_argument("--scaffold", action="store_true",
                        help="Create a context-aware Snowflake starter project in greenfield; never overwrites")
    parser.add_argument("--project-name",
                        help="Lowercase dbt project identifier; defaults to a normalized target-directory name")
    parser.add_argument("--source-type", choices=tuple(greenfield_scaffolder.SOURCE_HINTS),
                        default="undecided", help="Primary source category recorded in starter files")
    parser.add_argument("--environment", choices=greenfield_scaffolder.ENVIRONMENTS,
                        default="not_decided", help="Planning context only; does not configure a target")
    parser.add_argument("--owner", default="", help="Project owner or team (not a Snowflake role)")
    parser.add_argument("--description", default="", help="One-line project purpose")
    parser.add_argument("--domain", default="", help="Business or data domain")
    parser.add_argument("--data-sensitivity", choices=greenfield_scaffolder.SENSITIVITIES,
                        default="not_assessed", help="Initial classification; project policy remains authoritative")
    parser.add_argument("--consumers", default="", help="Primary data consumers")
    parser.add_argument("--no-git", action="store_true",
                        help="Do not initialize Git when the target is not already in a repository")
    args = parser.parse_args()
    scaffold_context_supplied = any((
        args.project_name is not None,
        args.source_type != "undecided",
        args.environment != "not_decided",
        bool(args.owner),
        bool(args.description),
        bool(args.domain),
        args.data_sensitivity != "not_assessed",
        bool(args.consumers),
    ))
    if scaffold_context_supplied and not args.scaffold:
        parser.error("Project context options require --scaffold.")
    if sys.version_info < (3, 10):
        parser.error("Python 3.10+ is required.")
    try:
        return initialize(args.target.expanduser(), args.dry_run, args.yes,
                          detect_only=args.detect_only, allow_existing=args.allow_existing,
                          no_git=args.no_git, scaffold=args.scaffold,
                          scaffold_options={
                              "project_name": args.project_name or "",
                              "source_type": args.source_type,
                              "environment": args.environment,
                              "owner": args.owner,
                              "description": args.description,
                              "domain": args.domain,
                              "data_sensitivity": args.data_sensitivity,
                              "consumers": args.consumers,
                          })
    except (OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
