# GitHub Copilot setup

GitHub Copilot is an assistant target in its own right, not an alias for
OpenAI Codex. This kit supplies Copilot-native project instructions and skill
discovery entries. It does not install or configure Codex.

## Project-local files

| Path relative to the project root | Purpose |
|---|---|
| `.github/copilot-instructions.md` | Repository-wide Copilot instructions and skill routing. |
| `.github/skills/<skill-name>/SKILL.md` | Native Copilot discovery entry with required `name` and `description` frontmatter. |
| `.github/prompts/<name>.prompt.md` | Workspace task prompt, available by name in Copilot Chat. |
| `skills/<skill-name>/SKILL.md` | Full platform guidance read by the corresponding discovery entry. |
| `.github/github-app.yml` | Copilot app project instructions; no scripts or automation are configured. |

The eight discovery entries cover naming conventions, Bronze profiling,
medallion architecture, data quality, data contracts, dbt integration, and
project structure (Bronze ingestion, Silver/Gold dbt models and Airflow DAGs),
plus data governance (roles/grants, classification, policies and audit).
Only their task descriptions and routing are repeated. Maintain detailed
guidance in `skills/` to avoid two divergent implementations.

### Configure an approved Snowflake MCP server

Run `/snowflake-mcp-setup` from this workspace to configure an existing,
administrator-approved Snowflake-managed MCP server for VS Code, Copilot CLI,
or the Copilot app. The prompt uses the client-specific configuration path,
previews any local file change for approval, and does not create server-side
Snowflake objects or test the connection. Read the full
[MCP guidance](#optional-snowflake-mcp-guidance) first. The administrator must
provide the exact endpoint, approved tools, and client-compatible
authentication setup; never put tokens or client secrets in project files.

To preserve the agreed folder layout, invoke `snowflake-project-structure`
when scaffolding or placing pipeline files. It defines the `pipelines/`
convention without reorganizing this kit or migrating existing repositories.

### Work on this kit

Open `snowflake-ai-data-developer/` itself as the project/workspace root.
Opening only the parent folder does not install the nested kit's instructions
or skills for every project under that parent. No files have been added to
the parent workspace's `.github/` or to personal skill directories.

Use a current Copilot client with Agent Skills support. GitHub documents
project skill support for Copilot CLI, the Copilot app, cloud agent, code
review, and supported IDE agent modes; availability and UI differ by client.
Skill selection is based on relevance and is not a promise that every chat
mode will load a skill.

For the Copilot app, review and accept `.github/github-app.yml` when prompted.
The app does not apply repository configuration changes until they are
trusted. This file adds project instructions only; it does not start a
server, install dependencies, or activate database access.

### Adopt in another Snowflake repository

Review the files, then manually merge the following into the target
repository root:

1. The desired `skills/<skill-name>/` directories and their matching
   `.github/skills/<skill-name>/` directories. Keep both paths together:
   discovery entries explicitly read the full files via relative links.
2. Relevant guidance from `.github/copilot-instructions.md`. Merge with the
   repository's instructions rather than overwriting them.
3. For Copilot app projects, merge the instruction routing from
   `.github/github-app.yml` with existing app configuration and review it in
   the app. Do not replace existing scripts or settings.

Preserve the relative layout shown above, including cross-skill links, or
update and verify those links when adopting only a subset. Do not copy the
kit wholesale over an existing `.github/` directory. No global installer or
home-directory modification is needed. Do not configure the same skill name
in multiple discoverable skill roots.

### Verify discovery without database access

After adoption, reload/open the target project in a supported Copilot client.
In the Copilot app, inspect **Customize > Skills**; in other clients use their
skill management or discovery interface. Check that all intended
`snowflake-*` names appear.

Ask a local-only question such as:

> Use snowflake-naming-conventions to explain unquoted versus quoted names.
> Read its linked full skill and cite the local path. Do not connect to
> Snowflake or run SQL.

Confirm that the assistant can read both the discovery entry and the full
skill. If not, check the workspace root, exact uppercase `SKILL.md` filename,
YAML frontmatter, relative links, duplicate skill names, and client support.
Do not solve a discovery failure by granting more database permissions.

For artifact changes, validate Markdown links/fences and YAML
frontmatter/examples locally, check that every native entry resolves to its
full skill, and review illustrative SQL without running it. No Snowflake
credentials, database, dbt installation, or application build is required.

## Optional Snowflake MCP guidance

The skills work without MCP. The following is configuration guidance only:
no active MCP configuration, credentials, connection, or live Snowflake
objects are supplied by this kit.

Choose an approved server with the Snowflake administrator. Snowflake's
managed MCP server can expose Cortex Analyst, Cortex Search, Cortex Agents,
SQL execution, and custom tools, depending on its specification and grants.
It is not automatically a read-only SQL connection or a general metadata
browser. A third-party/local server has its own setup and trust requirements;
do not substitute one without reviewing its implementation and permissions.

For an existing Snowflake-managed server, have the administrator provide:

- The account-specific HTTPS endpoint and intended environment.
- The exact tools and underlying objects authorized for use.
- A least-privileged role and approved warehouse/cost budget.
- The OAuth client registration and callback/scopes appropriate to the
  chosen Copilot client, or another explicitly approved authentication path.
- Network policy/private connectivity requirements and audit expectations.

The documented managed endpoint shape is:

```text
https://<account_url>/api/v2/databases/<database>/schemas/<schema>/mcp-servers/<name>
```

Use the administrator-provided URL rather than guessing account or identifier
spellings. Snowflake recommends hyphens instead of underscores in the account
hostname. Its managed MCP server does not support dynamic OAuth client
registration: verify that the chosen client's authentication flow supports
the provisioned integration. Do not assume generic HTTP support alone
guarantees OAuth interoperability.

### Client-specific configuration

These are separate configuration surfaces, not interchangeable files:

| Copilot surface | Configuration approach |
|---|---|
| VS Code agent mode | Configure a remote HTTP server through the MCP UI or repository `.vscode/mcp.json`, using its `servers` schema. Review server trust and authentication prompts. |
| Copilot CLI | Use `/mcp add`; supported project files include `.github/mcp.json` and `.mcp.json` using `mcpServers`. Check client version and precedence before merging. |
| Copilot app | Use **Customize > MCP** for an approved server; the app also uses servers configured for Copilot CLI/repositories. Do not assume VS Code's file is read by the app. |
| Copilot cloud agent / code review | Repository administrators configure MCP under repository **Settings > Copilot > MCP servers**. Current GitHub documentation says remote OAuth MCP servers are not supported there; do not assume a local OAuth setup will transfer. |

For VS Code, this is a credential-free JSON example for an existing remote
server. Replace the placeholder only after administrator review, and merge
with existing configuration:

```json
{
  "servers": {
    "snowflake": {
      "type": "http",
      "url": "<approved_snowflake_mcp_url>"
    }
  }
}
```

For Copilot CLI project configuration, the equivalent structural example is:

```json
{
  "mcpServers": {
    "snowflake": {
      "type": "http",
      "url": "<approved_snowflake_mcp_url>",
      "tools": ["<approved_tool_name>"]
    }
  }
}
```

These snippets do not configure OAuth registrations, secrets, or grants and
are not ready-to-connect configurations. Use the selected host's supported
authentication and protected secret mechanism. Do not paste bearer tokens
into tracked JSON, shell command history, skill files, or chats. Avoid
wildcard tool approval; select only reviewed tools. Do not bypass a client's
OAuth limitation by committing a long-lived token.

### Review before enabling

Instructions and MCP annotations are not a security boundary. Configure
server-side RBAC and tool exposure for the required access; tools backed by
procedures or agents can have effects beyond the apparent request. Cloud
agent tools can run autonomously, so do not rely on an interactive approval
dialog as the only protection.

For a future authorized connection, verify the effective account, role,
warehouse, accessible objects, tools, and budget before querying business
data. Start with narrowly scoped metadata and aggregate inspection; limit
row previews and avoid sensitive payloads. Read-only queries can still incur
compute charges and expose data to the assistant host. Never grant write
access solely to enable profiling. Obtain explicit confirmation of exact
destructive/overwriting statements and their targets before execution.

Do not create an MCP server object, OAuth integration, grants, or network
policy as part of adopting this kit. Those are separate, administrator-owned
changes requiring review. Authentication compatibility, account availability,
tool selection, and privacy approval remain deployment decisions, not
assertions that this local documentation has tested a connection.

## Official references

- [Copilot Agent Skills and supported project paths](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills)
- [Copilot skill file format](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/add-skills)
- [Repository custom instructions](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/add-custom-instructions/add-repository-instructions)
- [Copilot app repository configuration](https://docs.github.com/en/copilot/reference/github-copilot-app-reference/repository-configuration)
- [Copilot app skills and MCP](https://docs.github.com/en/copilot/how-tos/github-copilot-app/customize-github-copilot-app)
- [Copilot CLI MCP configuration](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-mcp-servers)
- [VS Code Copilot MCP configuration](https://docs.github.com/en/copilot/how-tos/copilot-in-your-ide/customize-copilot/extend-copilot-with-tools-and-context/extend-copilot-chat-with-mcp)
- [Cloud agent MCP configuration and limitations](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/configure-mcp-servers)
- [Snowflake-managed MCP server, authentication, and grants](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-agents-mcp)
