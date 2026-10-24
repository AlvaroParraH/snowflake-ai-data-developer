# GitHub Copilot setup

GitHub Copilot is an assistant target in its own right, not an alias for
OpenAI Codex. This kit supplies Copilot-native project instructions and skill
skills with their full guidance. It does not install or configure Codex.

## Project-local files

| Path relative to the project root | Purpose |
|---|---|
| `.github/copilot-instructions.md` | Repository-wide Copilot instructions and skill routing. |
| `.github/skills/<skill-name>/SKILL.md` | Full skill guidance and native Copilot discovery metadata (`name` and `description` frontmatter). |
| `.github/prompts/<name>.prompt.md` | Workspace task prompt, available by name in Copilot Chat. |
| `.github/github-app.yml` | Copilot app project instructions; no scripts or automation are configured. |

The eight skills cover naming conventions, Bronze profiling,
medallion architecture, data quality, data contracts, dbt integration, and
project structure (Bronze ingestion, Silver/Gold dbt models and Airflow DAGs),
plus data governance (roles/grants, classification, policies and audit).
Maintain discovery metadata and full guidance together in each skill file;
there is no separate root-level skill copy.

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

### Check SQL before a commit

Run `/snowflake-sql-check` in VS Code Copilot Chat to invoke the
[SQL check prompt](../.github/prompts/snowflake-sql-check.prompt.md).
It defaults to staged SQL files and distinguishes working-tree edits from
the content being committed. It uses existing SQLFluff tooling with the
Snowflake dialect, reports syntax/templating/style issues separately, and
does not install tools, auto-fix, commit, or connect to Snowflake. dbt
templating is blocked unless its execution path is verified local-only.
No selected SQL files or missing tooling is reported explicitly, not as a
successful validation.

This prompt is manual guidance, not a pre-commit hook or required CI check.
This documentation-only kit does not install SQLFluff. To use the prompt
in a pipeline repository, copy it into that repository's `.github/prompts/`
and provide the project's pinned tooling and configuration.

### Client availability

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

#### Install into another project

From the kit checkout, run:

```bash
bash install.sh --target /path/to/existing-project --dry-run
bash install.sh --target /path/to/existing-project
```

The target must already exist and must be outside this kit. The installer
needs Bash, Python 3.10+, and uv. Its Python code uses only the standard library.
The first command previews all writes and prerequisites; the second asks for
confirmation. For automation, use `--yes` to approve the displayed plan,
including installing missing uv. No target is selected implicitly.

##### uv prerequisite

- If uv is on PATH, the installer verifies `uv --version`; existing installations
  are not upgraded or replaced. Verification failure stops before project writes.
- If uv is missing, the preview lists the installation action. Accepting the
  plan (or using `--yes`) approves downloading/installing uv outside the target.
  On macOS it runs `brew install uv`, requiring existing Homebrew.
  On Linux it downloads `https://astral.sh/uv/install.sh` with curl to a temporary
  file, then runs it with sh, installing to `~/.local/bin` using
  `UV_INSTALL_DIR` and `UV_NO_MODIFY_PATH=1`. It does not edit shell profiles;
  add `~/.local/bin` to PATH for future shells if needed.
- Python, Homebrew, curl, and sh are not installed automatically. Unsupported
  platforms or missing installation tools produce manual-install guidance.
- `--no-install` prohibits uv installation. If uv is missing, an actual run
  fails before project writes. With uv already on PATH, installation needs no
  network access.
- `--dry-run` reports status without executing uv or any installation commands,
  downloading anything, or writing files. A missing uv report is not verification.

Target conflicts are checked before uv installation. A failed uv installation
or verification stops before project writes, but any external tool installation
may have partially completed. An installed uv is not rolled back if later project
writes fail. No project environment is initialized and no dependencies are synced.
See the [official uv installation guidance](https://docs.astral.sh/uv/getting-started/installation/)
for manual installation.

The installer also creates the agreed pipeline directory layout by default:

```text
pipelines/
|-- ingestion/bronze/
|-- dbt/models/
|   |-- silver/
|   |   |-- staging/
|   |   `-- intermediate/
|   `-- gold/marts/
`-- orchestration/airflow/dags/
```

Missing folders appear as `MKDIR` in the preview. Existing folders and their
contents are preserved; files blocking a required folder or symlink destinations
stop installation before any writes. Repeat runs restore missing folders.
The installer does not move existing pipelines or generate models, DAGs,
`dbt_project.yml`, Python manifests, or other runtime configuration. These empty
code folders are not a runnable project and are not tracked by Git until files
are added. `--dry-run` creates neither folders nor files.

Installed assets:

- All eight full skills under `.github/skills/`, including discovery metadata.
- Both `.github/prompts/` workflows and supporting Markdown/SVG files under
  `docs/`, preserving relative links.
- A marked Snowflake guidance block appended to
  `.github/copilot-instructions.md`. Existing project text is preserved.
  Kit-maintenance instructions are not copied into application instructions.

Apart from the pipeline folders, no other application files are copied or modified. The
installer does not overwrite README files or app configuration, install
project dependencies, configure MCP, or access Snowflake. The only optional
non-project change is the explicitly approved uv installation described above;
no assistant home configuration or shell profiles are changed.
Review and enable Copilot app configuration manually as described below.

Identical assets are skipped on repeat runs. If any destination asset differs
or a managed instruction block has been edited, the installer exits with an
error before writing. There is no force-overwrite mode: compare the source
and destination, manually merge or back up/move the specific conflicting
asset, and rerun. Do not delete the target project. Symlink destinations are
rejected. A filesystem failure during writes can leave a partial install;
the error reports completed file writes and pipeline directory operations.
Inspect the target and rerun
after resolving the failure; already identical assets will be skipped.

For targets installed with the older split layout, manually merge the full
skills into `.github/skills/` and update instruction links before rerunning.
Remove only the obsolete root-level kit skill copies after reviewing and
preserving any local edits. The installer does not delete or migrate existing
project content automatically, and an older managed instruction block still
requires a manual merge.

Open the target itself as the workspace root and verify discovery using the
steps below. Copying files does not guarantee that a particular client or
chat mode has loaded them.

#### Manual adoption

For a subset of skills or custom placement, review and manually merge the
following into the target repository root:

1. The desired `.github/skills/<skill-name>/` directories. Each `SKILL.md`
   contains both discovery metadata and full guidance.
2. Relevant guidance from `.github/copilot-instructions.md`. Merge with the
   repository's instructions rather than overwriting them.
3. For Copilot app projects, merge the instruction routing from
   `.github/github-app.yml` with existing app configuration and review it in
   the app. Do not replace existing scripts or settings.
4. Copy desired `.github/prompts/` workflows and their supporting documentation.
   Preserve or update their relative links.

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
> Read its full SKILL.md and cite the local path. Do not connect to
> Snowflake or run SQL.

Confirm that the assistant can read the full skill directly under
`.github/skills/`. If not, check the workspace root, exact uppercase `SKILL.md` filename,
YAML frontmatter, relative links, duplicate skill names, and client support.
Do not solve a discovery failure by granting more database permissions.

For artifact changes, validate Markdown links/fences and YAML
frontmatter/examples locally, check that every skill's `name` matches its
directory, and review illustrative SQL without running it. No Snowflake
credentials, database, dbt installation, or application build is required.
For installer code changes, run the standard-library integration tests:

```bash
python3 -B -m unittest discover -s tests -p 'test_installer.py' -v
```

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
