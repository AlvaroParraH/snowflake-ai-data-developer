"""Configure an approved remote Snowflake MCP server without connecting."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import sys
import tempfile

from install_kit import check_destination, invalid_json_constant, json_object, mcp_content


def check_config_path(path: Path) -> None:
    check_destination(Path(path.anchor), path.relative_to(path.anchor))
    if path.exists() and not path.is_file():
        raise ValueError(f"MCP configuration is not a regular file: {path}")


@dataclass(frozen=True)
class MCPPlan:
    path: Path
    before: bytes | None
    content: bytes

    def preview(self) -> None:
        print(f"MCP configuration: {self.path}")
        config = json.loads(self.content)
        key = "servers" if "servers" in config else "mcpServers"
        print(json.dumps({key: {"snowflake": config[key]["snowflake"]}}, indent=2))
        print("Existing unrelated servers are preserved. No authentication or connection test.")
        print("Finish trust/sign-in in VS Code. For bearer auth, provide SNOWFLAKE_MCP_TOKEN "
              "in the VS Code host environment; never paste tokens into chat or config.")

    def apply(self) -> None:
        check_config_path(self.path)
        current = self.path.read_bytes() if self.path.exists() else None
        if current != self.before:
            raise ValueError(f"MCP file changed after preview: {self.path}")
        if current == self.content:
            print("MCP configuration already matches; unchanged.")
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.before is None:
            with self.path.open("xb") as stream:
                stream.write(self.content)
        else:
            with tempfile.NamedTemporaryFile(dir=self.path.parent, delete=False) as stream:
                temporary = Path(stream.name)
                try:
                    stream.write(self.content)
                    stream.flush()
                    check_config_path(self.path)
                    if self.path.read_bytes() != self.before:
                        raise ValueError(f"MCP file changed after preview: {self.path}")
                    os.replace(temporary, self.path)
                finally:
                    temporary.unlink(missing_ok=True)
        print("MCP configuration saved. Discovery, trust and authentication remain unverified.")


def add_mcp_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--setup-mcp", action="store_true",
                        help="Configure an approved remote MCP server in VS Code user configuration")
    parser.add_argument("--mcp-config", type=Path,
                        help="Absolute user MCP file path from VS Code: MCP: Open User Configuration")
    parser.add_argument("--mcp-format", choices=("vscode", "copilot"), default="vscode",
                        help="vscode: user-profile servers format; copilot: global mcpServers format")
    parser.add_argument("--mcp-tool", action="append", default=[],
                        help="Approved exact tool name; repeat for Copilot global format (no wildcard)")
    parser.add_argument("--mcp-endpoint", help="Exact administrator-approved HTTPS endpoint, no secrets")
    parser.add_argument("--mcp-auth", choices=("oauth", "bearer"))
    parser.add_argument("--mcp-oauth-client-id", help="Approved public OAuth client ID, not a secret")
    parser.add_argument("--mcp-approved", action="store_true",
                        help="Confirm administrator approval of endpoint, tools and client authentication")


def plan_mcp(args: argparse.Namespace) -> MCPPlan | None:
    requested = (args.setup_mcp or args.mcp_config is not None or args.mcp_endpoint is not None
                 or args.mcp_auth is not None or args.mcp_oauth_client_id is not None
                 or args.mcp_approved or args.mcp_tool or args.mcp_format != "vscode")
    if not requested:
        return None
    if args.dry_run and args.setup_mcp and not any((
        args.mcp_config, args.mcp_endpoint, args.mcp_auth, args.mcp_oauth_client_id,
        args.mcp_approved, args.mcp_tool, args.mcp_format != "vscode",
    )):
        print("MCP setup pending: supply approved details and --mcp-config for a concrete preview.")
        return None
    if args.setup_mcp and not args.dry_run and sys.stdin.isatty():
        if args.mcp_config is None:
            args.mcp_config = Path(input(
                "Absolute user MCP path from 'MCP: Open User Configuration': ").strip())
        if not args.mcp_endpoint:
            args.mcp_endpoint = input("Administrator-approved HTTPS MCP endpoint (no secrets): ").strip()
        if not args.mcp_auth:
            args.mcp_auth = input("Administrator-confirmed authentication (oauth/bearer): ").strip()
        if args.mcp_auth == "oauth" and not args.mcp_oauth_client_id:
            args.mcp_oauth_client_id = input("Administrator-provisioned public OAuth client ID: ").strip()
        if not args.mcp_approved:
            args.mcp_approved = input(
                "Administrator approved endpoint, exposed tools and client authentication? [y/N] "
            ).strip().lower() in {"y", "yes"}
    if not args.mcp_approved:
        raise ValueError("MCP setup requires --mcp-approved; --yes is not administrator approval.")
    if args.mcp_config is None or not args.mcp_endpoint or not args.mcp_auth:
        raise ValueError("MCP setup requires --mcp-config, --mcp-endpoint and --mcp-auth. "
                         "Obtain the user file path through 'MCP: Open User Configuration'.")
    path = args.mcp_config.expanduser()
    if not path.is_absolute():
        raise ValueError("--mcp-config must be an absolute VS Code user MCP file path.")
    check_config_path(path)
    before = path.read_bytes() if path.exists() else None
    if args.mcp_format == "vscode":
        if args.mcp_tool:
            raise ValueError("--mcp-tool applies to Copilot global format. Review/enable only "
                             "approved tools in VS Code; this format has no tool allowlist field.")
        existing = json.loads(before) if before is not None else {}
        if isinstance(existing, dict) and "mcpServers" in existing:
            raise ValueError("Portable MCP file requires --mcp-format copilot, not vscode.")
        content = mcp_content(before, args.mcp_endpoint, args.mcp_auth, args.mcp_oauth_client_id)
    else:
        if args.mcp_auth != "bearer":
            raise ValueError("Copilot global setup supports approved bearer authentication only. "
                             "For fixed-client OAuth use --mcp-format vscode with the Local harness; "
                             "do not copy VS Code OAuth fields into a portable file.")
        if not args.mcp_tool or any(not tool.strip() or "*" in tool or
                                   any(c.isspace() for c in tool) for tool in args.mcp_tool):
            raise ValueError("Copilot global setup requires exact approved --mcp-tool names, no wildcard.")
        entry = json.loads(mcp_content(None, args.mcp_endpoint, args.mcp_auth,
                                       args.mcp_oauth_client_id))["servers"]["snowflake"]
        entry["headers"]["Authorization"] = "Bearer ${SNOWFLAKE_MCP_TOKEN}"
        entry["tools"] = list(dict.fromkeys(args.mcp_tool))
        try:
            config = (json.loads(before, object_pairs_hook=json_object,
                                 parse_constant=invalid_json_constant) if before is not None else {})
        except (ValueError, UnicodeDecodeError) as error:
            raise ValueError("User MCP file must be strict JSON; merge JSONC manually.") from error
        if not isinstance(config, dict) or "servers" in config:
            raise ValueError("Copilot global setup requires an object in portable mcpServers format.")
        servers = config.setdefault("mcpServers", {})
        if not isinstance(servers, dict):
            raise ValueError("mcpServers must be a JSON object.")
        if "snowflake" in servers and servers["snowflake"] != entry:
            raise ValueError("Existing snowflake MCP server differs; merge it manually.")
        servers["snowflake"] = entry
        content = before if before is not None and json.loads(before) == config else (
            json.dumps(config, indent=2) + "\n").encode()
    return MCPPlan(path, before, content)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    add_mcp_arguments(parser)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--yes", action="store_true")
    args = parser.parse_args()
    try:
        plan = plan_mcp(args)
        if plan is None:
            if args.dry_run and args.setup_mcp:
                print("Dry run complete; nothing written.")
                return 0
            raise ValueError("Supply --setup-mcp or explicit MCP configuration arguments.")
        plan.preview()
        if args.dry_run:
            print("Dry run complete; nothing written.")
            return 0
        if not args.yes:
            if not sys.stdin.isatty():
                raise ValueError("Non-interactive changes require --yes; preview with --dry-run.")
            if input("Save this MCP configuration? [y/N] ").strip().lower() not in {"y", "yes"}:
                print("Cancelled; nothing written.")
                return 0
        plan.apply()
        return 0
    except (OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
