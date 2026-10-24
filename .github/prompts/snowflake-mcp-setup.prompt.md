---
name: snowflake-mcp-setup
description: "Configure an existing, administrator-approved Snowflake-managed MCP server for a supported Copilot client. Use for Snowflake MCP setup, endpoint wiring, or client configuration."
argument-hint: "Client (VS Code, Copilot CLI, or Copilot app) and administrator-provided Snowflake MCP endpoint, if available"
agent: "agent"
---

# Configure Snowflake MCP for this client

Help the user configure a connection to an **existing, administrator-approved
Snowflake-managed MCP server**. This is client configuration only. Do not
install or create a server, Snowflake object, OAuth integration, grant, role,
network policy, or local MCP implementation.

Read [Copilot setup](../../docs/copilot-setup.md) and follow its MCP safety,
client-compatibility, and authentication guidance. Do not infer an endpoint,
tools, account, environment, scopes, or authorization from repository content.

## Procedure

1. **Identify the client and scope.** Ask whether this is VS Code agent mode,
   Copilot CLI, or Copilot app, and whether the user intends user-level or
   workspace/project configuration. Do not assume a config file is shared
   between clients.
2. **Confirm server details.** Obtain the exact HTTPS endpoint and intended
   account/environment from the user or their Snowflake administrator.
   Confirm the approved tool names and that the server is meant for this
   client. Do not construct an endpoint by guessing account, database,
   schema, or server names.
3. **Check authentication compatibility.** Confirm the administrator has
   provisioned the OAuth client registration/callback/scopes or other
   explicitly approved authentication path for this client. Snowflake's
   managed MCP server does not support dynamic OAuth client registration.
   If compatibility is unknown or unsupported, stop and explain what the
   administrator/client owner must resolve. Never work around this with a
   committed token, bearer string, or credential in a config file.
4. **Choose the client-specific setup path:**
   - **VS Code agent mode:** use VS Code's MCP UI or the workspace
     `.vscode/mcp.json` `servers` schema. If editing the file is requested,
     preserve existing JSONC content and entries.
   - **Copilot CLI:** prefer the CLI's `/mcp add` flow when suitable for the
     installed client, or use its supported project MCP configuration format
     (`mcpServers`). Do not write VS Code's `servers` format into a CLI file.
   - **Copilot app:** guide the user through **Customize > MCP**. Do not
     invent an app config file or claim it reads VS Code settings.
   - **Copilot cloud agent/code review:** direct the user to repository
     administrator configuration under **Settings > Copilot > MCP servers**.
     Remote OAuth support is limited; do not proceed unless the exact
     authentication mode is supported.
5. **Inspect before editing.** For a local file change, read the existing
   target config and preserve all unrelated servers, settings, comments and
   formatting where practical. Do not overwrite an existing server entry
   without explaining the conflict and obtaining approval.
6. **Preview and ask before writing.** Show the exact proposed change and
   target file. Ask the user to confirm before creating or modifying any
   local configuration. Do not write config in response to a general setup
   request without this confirmation.
7. **Validate locally.** Check JSON syntax where applicable, endpoint shape
   (without altering it), and that only approved tools are configured. Do
   not start the MCP server, authenticate, connect to Snowflake, invoke
   tools, or run SQL as an installation test.
8. **Complete transparently.** Tell the user what was configured, which
   manual authentication/trust/restart steps remain, and how to diagnose
   client discovery. Clearly distinguish local config validation from a
   tested server connection.

## Security and authorization

- Never ask the user to paste passwords, private keys, bearer tokens,
  access tokens, OAuth client secrets, or connection strings into chat.
- Never store credentials in tracked files, workspace settings, logs,
  examples, shell history, or screenshots. Use the client's protected
  authentication flow/secret storage.
- Do not enable wildcard tool access. Configure only administrator-approved,
  reviewed tools; MCP annotations and names do not enforce server-side
  permissions.
- Do not grant write access just to make MCP work. Server-side RBAC,
  accessible objects, query cost controls and audit expectations belong to
  the Snowflake administrator.
- Do not test with a live data query. Even read-only queries can incur compute
  charges and expose data to the assistant host.

## Credential-free configuration shapes

Use only the format documented for the selected client, merge with existing
settings, and substitute only an administrator-provided endpoint and
tool allowlist. These examples do not configure authentication or grant
access.

VS Code:

```json
{
  "servers": {
    "snowflake": {
      "type": "http",
      "url": "<administrator_provided_https_endpoint>"
    }
  }
}
```

Copilot CLI:

```json
{
  "mcpServers": {
    "snowflake": {
      "type": "http",
      "url": "<administrator_provided_https_endpoint>",
      "tools": ["<approved_tool_name>"]
    }
  }
}
```
