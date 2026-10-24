"""Block likely credentials in Git's staged blobs without printing their values."""

from __future__ import annotations

import re
import subprocess
import sys


PATTERNS = (
    ("private key", re.compile(rb"-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY-----")),
    ("GitHub token", re.compile(rb"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{50,})")),
    ("AWS access key", re.compile(rb"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("bearer token", re.compile(rb"(?i)\bbearer\s+[A-Za-z0-9_.~+/-]{20,}={0,2}")),
    ("JWT", re.compile(rb"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}")),
)
ASSIGNMENT = re.compile(
    rb"""(?ix)
    (?<![a-z0-9_])
    (?:snowflake[_-])?
    (?:password|passwd|pwd|token|pat|api[_-]?key|client[_-]?secret|
       private[_-]?key[_-]?passphrase|aws[_-]?secret[_-]?access[_-]?key|secret)
    ["']?\s*[:=]\s*["']?([^\s"'`,;}\]]+)
    """
)


def placeholder(value: bytes) -> bool:
    return (value.startswith((b"${", b"$", b"<", b"{{", b"%(", b"os.environ",
                              b"os.getenv", b"env_var(", b"getenv("))
            or value.lower() in {b"none", b"null", b"true", b"false"})


def git(*arguments: str) -> bytes:
    return subprocess.run(["git", "--literal-pathspecs", *arguments],
                          check=True, capture_output=True).stdout


def scan() -> int:
    paths = git("diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z").split(b"\0")
    found = False
    for raw_path in filter(None, paths):
        path = raw_path.decode("utf-8", errors="surrogateescape")
        metadata = git("ls-files", "--stage", "-z", "--", path).split(b"\0")
        entry = next((item.split(b"\t", 1)[0] for item in metadata
                      if item and item.split(b"\t", 1)[1] == raw_path), None)
        if entry is None:
            raise ValueError("Cannot resolve a staged path; resolve index conflicts before committing.")
        mode, object_id, stage = entry.split()
        if stage != b"0":
            raise ValueError("Unmerged staged path; resolve conflicts before committing.")
        if mode == b"160000":
            continue
        content = git("cat-file", "blob", object_id.decode("ascii"))
        for number, line in enumerate(content.splitlines(), 1):
            labels = [label for label, pattern in PATTERNS if pattern.search(line)]
            if any(not placeholder(match[1]) and len(match[1]) >= 8
                   for match in ASSIGNMENT.finditer(line)):
                labels.append("credential assignment")
            if labels:
                print(f"Secret scan blocked: {ascii(path)}:{number}: {', '.join(labels)}.",
                      file=sys.stderr)
                found = True
    if found:
        print("Remove staged credentials; use approved OAuth/secret storage. "
              "Rotate any real exposed credentials. Matched values are never printed.",
              file=sys.stderr)
        return 1
    return 0


def main() -> int:
    try:
        return scan()
    except (OSError, ValueError, subprocess.CalledProcessError):
        print("Secret scan failed: Git index could not be read. Commit blocked; "
              "check Git availability and resolve index errors.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
