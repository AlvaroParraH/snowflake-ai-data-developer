"""Track kit-owned files and apply reviewed, hash-checked local updates."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import uuid


MANIFEST = Path(".snowflake-kit-manifest.json")
BACKUPS = Path(".snowflake-kit-backups")
INSTRUCTIONS = Path(".github/copilot-instructions.md")
START = b"<!-- snowflake-ai-data-developer:start -->"
END = b"<!-- snowflake-ai-data-developer:end -->"
SCRIPTS = {
    "scan_secrets.py", "init_project.py", "scaffold_snowflake_project.py",
    "scaffold_dbt_model.py", "installation_state.py",
}


def check_path(target: Path, relative: Path) -> None:
    if relative.is_absolute() or not relative.parts or any(
        part in {".", ".."} for part in relative.parts
    ):
        raise ValueError(f"Unsafe kit path: {relative}")
    path = target / relative
    for ancestor in (path, *path.parents):
        if ancestor.is_symlink():
            raise ValueError(f"Refusing symlink path: {ancestor}")
    for ancestor in path.parents:
        if ancestor.exists() and not ancestor.is_dir():
            raise ValueError(f"Not a directory: {ancestor}")
    if path.exists() and not path.is_file():
        raise ValueError(f"Not a regular file: {path}")


def managed_path(relative: Path, mode: str) -> bool:
    parts = relative.parts
    if relative == INSTRUCTIONS or relative == Path(".githooks/pre-commit"):
        return True
    if len(parts) == 2 and parts[0] == "scripts":
        names = SCRIPTS | ({"install_kit.py", "install_shared.py", "setup_mcp.py"}
                           if mode == "shared" else set())
        return parts[1] in names
    if relative.suffix in {".md", ".svg"}:
        if parts[:1] == ("docs",) or parts[:2] in {
            (".github", "skills"), (".github", "prompts"), (".github", "agents"),
        }:
            return True
        if mode == "shared" and (
            parts[:1] == ("skills",) or parts[:2] == ("com.github.copilot", "agents")
        ):
            return True
    return mode == "shared" and relative.as_posix() in {
        "install.sh", "README.md", "ARCHITECTURE.md", "AGENTS.md", "plugin.json",
    }


def instruction_block(content: bytes) -> bytes:
    if content.count(START) != 1 or content.count(END) != 1:
        raise ValueError("Missing or malformed Snowflake instruction block; merge it manually.")
    start, end = content.index(START), content.index(END)
    if end < start:
        raise ValueError("Malformed Snowflake instruction block; merge it manually.")
    return content[start:end + len(END)]


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def tracked_content(relative: Path, content: bytes, mode: str) -> bytes:
    return instruction_block(content) if mode == "project" and relative == INSTRUCTIONS else content


def manifest_content(files: dict[Path, bytes], mode: str) -> bytes:
    records = {}
    for relative, content in sorted(files.items()):
        if (relative.is_absolute() or not relative.parts
                or any(part in {".", ".."} for part in relative.parts)
                or not managed_path(relative, mode)):
            raise ValueError(f"Not a kit-owned path: {relative}")
        records[relative.as_posix()] = digest(tracked_content(relative, content, mode))
    return (json.dumps({"version": 1, "mode": mode, "files": records}, indent=2) + "\n").encode()


def read_file(target: Path, relative: Path) -> bytes | None:
    check_path(target, relative)
    path = target / relative
    return path.read_bytes() if path.exists() else None


def prepare_manifest(target: Path, files: dict[Path, bytes], mode: str) -> bytes:
    content = manifest_content(files, mode)
    existing = read_file(target, MANIFEST)
    if existing is not None and existing != content:
        raise ValueError("Installed kit manifest differs. Use --update; do not overwrite tracking state.")
    return content


def atomic_write(target: Path, relative: Path, content: bytes, before: bytes | None) -> None:
    if read_file(target, relative) != before:
        raise ValueError(f"File changed after preview: {relative}")
    path = target / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    if before is None:
        with path.open("xb") as stream:
            stream.write(content)
        return
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(content)
            stream.flush()
            os.chmod(temporary, path.stat().st_mode & 0o777)
            if read_file(target, relative) != before:
                raise ValueError(f"File changed after preview: {relative}")
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)


def save_manifest(target: Path, content: bytes) -> None:
    existing = read_file(target, MANIFEST)
    if existing == content:
        return
    if existing is not None:
        raise ValueError("Kit manifest changed during installation; inspect before retrying.")
    atomic_write(target, MANIFEST, content, None)


def load_records(content: bytes, mode: str) -> dict[Path, str]:
    def unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate key in kit manifest.")
            result[key] = value
        return result

    data = json.loads(content, object_pairs_hook=unique)
    if (not isinstance(data, dict) or data.get("version") != 1 or data.get("mode") != mode
            or not isinstance(data.get("files"), dict) or not data["files"]):
        raise ValueError("Invalid kit manifest version, mode, or file records.")
    records: dict[Path, str] = {}
    for name, value in data["files"].items():
        relative = Path(name)
        if (relative.as_posix() != name or relative.is_absolute()
                or any(part in {".", ".."} for part in relative.parts)
                or not managed_path(relative, mode)
                or not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value)):
            raise ValueError(f"Unsafe or invalid kit manifest record: {name}")
        records[relative] = value
    return records


def update(target: Path, files: dict[Path, bytes], mode: str, *, dry_run: bool, yes: bool) -> int:
    if not target.is_dir():
        raise ValueError("Update target must be an existing installation.")
    old_manifest = read_file(target, MANIFEST)
    if old_manifest is None:
        raise ValueError("No kit manifest: this is an older/untracked installation. "
                         "For shared mode, build once into a fresh directory and switch registration. "
                         "For project mode, review/merge old assets, then rerun the normal installer "
                         "when they match the current kit to establish tracking. No files changed.")
    records = load_records(old_manifest, mode)
    new_manifest = manifest_content(files, mode)
    snapshots = {relative: read_file(target, relative) for relative in records.keys() | files.keys()}
    changes: list[tuple[Path, bytes | None]] = []
    conflicts = []
    for relative, before in sorted(snapshots.items()):
        content = files.get(relative)
        current = tracked_content(relative, before, mode) if before is not None else None
        desired = tracked_content(relative, content, mode) if content is not None else None
        if current == desired:
            continue
        if before is not None and (
            relative not in records or digest(tracked_content(relative, before, mode)) != records[relative]
        ):
            conflicts.append(str(relative))
            continue
        if mode == "project" and relative == INSTRUCTIONS and before is not None:
            if desired is None:
                raise ValueError("Refusing to remove the project instruction block.")
            content = before.replace(instruction_block(before), desired, 1)
        changes.append((relative, content))

    print(f"Update {mode} kit: {target}")
    print("Credentials, MCP, editor settings, environments, active hooks and project code are untouched.")
    for relative, content in changes:
        action = "DELETE" if content is None else (
            "CREATE" if snapshots[relative] is None else "REPLACE"
        )
        print(f"  {action} {relative}")
    print(f"Planned file changes: {len(changes)}; tracking manifest will be updated if needed.")
    if conflicts:
        raise ValueError("Locally modified or untracked conflicting files; no files written. "
                         "Review/merge manually, then re-preview:\n  " + "\n  ".join(conflicts))
    if not changes and new_manifest == old_manifest:
        print("Already up to date; no files changed.")
        return 0
    print(f"Backup: {target / BACKUPS}/<unique-update-id>/ (changed originals and old manifest).")
    if dry_run:
        print("Dry run complete; nothing written.")
        return 0
    if not yes:
        if not sys.stdin.isatty():
            raise ValueError("Non-interactive update requires --yes; preview with --dry-run.")
        if input("Apply this update and back up changed files? [y/N] ").strip().lower() not in {"y", "yes"}:
            print("Cancelled; nothing written.")
            return 0

    def verify_snapshot() -> None:
        if read_file(target, MANIFEST) != old_manifest:
            raise ValueError("Kit manifest changed after preview.")
        for relative, before in snapshots.items():
            if read_file(target, relative) != before:
                raise ValueError(f"File changed after preview: {relative}")

    verify_snapshot()
    backup = BACKUPS / uuid.uuid4().hex
    # Back up only kit-owned originals, never unrelated project or credential files.
    for relative, _ in changes:
        before = snapshots[relative]
        if before is not None:
            atomic_write(target, backup / relative, before, None)
    atomic_write(target, backup / MANIFEST, old_manifest, None)
    verify_snapshot()
    applied = 0
    try:
        for relative, content in changes:
            before = snapshots[relative]
            if content is None:
                if read_file(target, relative) != before:
                    raise ValueError(f"File changed after preview: {relative}")
                (target / relative).unlink()
            else:
                atomic_write(target, relative, content, before)
            applied += 1
        atomic_write(target, MANIFEST, new_manifest, old_manifest)
    except (OSError, ValueError):
        print(f"Update interrupted after {applied} changes. Originals are in {target / backup}; "
              "inspect and restore before retrying. No automatic rollback attempted.", file=sys.stderr)
        raise
    print(f"Update complete. Backup: {target / backup}")
    print("Reload VS Code and verify customization discovery; no Snowflake connection was made.")
    return 0
