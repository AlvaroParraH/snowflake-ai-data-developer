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

The nine skills cover naming conventions, Bronze profiling,
medallion architecture, data quality, data contracts, dbt integration, and
project structure (Bronze ingestion, Silver/Gold dbt models and Airflow DAGs),
data governance (roles/grants, classification, policies and audit), and
compute cost attribution using Snowflake object and query tags.
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
The installer enables a separate secret-scanning hook, not SQL enforcement.
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
needs Git, Bash, Python 3.10+, and uv. Its Python code uses only the standard library.
The first command previews all writes and prerequisites; the second asks for
confirmation. For automation, use `--yes` to approve the displayed plan,
including installing missing uv. No target is selected implicitly.

Git is checked on PATH and verified using `git --version`. Python is the
interpreter running the installer, with a 3.10+ version check; the Bash entrypoint
checks for Python before launching it. Git and Python are never auto-installed.
VS Code and GitHub Copilot must be installed and enabled separately; the installer
does not require a `code` CLI or sign into your account.

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
writes fail. No dependencies are synced.
See the [official uv installation guidance](https://docs.astral.sh/uv/getting-started/installation/)
for manual installation.

##### Python environment

The default plan includes creation of `.venv/` using:

```text
uv venv --no-config --offline --no-python-downloads --python <installer-python> <target>/.venv
```

This uses the existing Python interpreter, not a downloaded runtime. No seed
packages (including pip), project dependencies, Python manifests or lockfiles
are installed/generated. The installer verifies the environment's interpreter
and `sys.prefix` locally. Existing recognizable `.venv` environments are verified
and preserved, including their packages; broken environments are never cleared.
Confirm the installer interpreter meets your project-specific Python requirements.

Use `--skip-venv` to retain another workflow or interpreter. If `.venv` is absent
but Poetry/Pipenv/Conda manifests or `.python-version` are present, setup stops
and requests that decision. Existing dependency manifests are never changed.
Exclude `.venv/` from Git. Select its interpreter in VS Code or activate it with
`source .venv/bin/activate` on macOS/Linux.

A failed creation may leave a partial `.venv`; inspect/repair it manually before
retrying. The installer reports failure rather than overwriting it on the next run.
`--no-install` prohibits installing the uv tool, not creating the local environment;
combine it with `--skip-venv` to prohibit environment creation too.

##### VS Code Snowflake MCP configuration

Use `--setup-mcp` to enter the endpoint, authentication (`oauth` or `bearer`),
and administrator approval at setup time. Never enter a credential into these
prompts. Before approving, confirm the exact endpoint, exposed tools and
client-compatible authentication with your Snowflake administrator. OAuth client
registration/callback/scopes must already be provisioned; dynamic registration is
not supported by Snowflake-managed MCP.

For OAuth, provide the administrator-provisioned public client ID through the
setup prompt or `--mcp-oauth-client-id`. The installer writes
`"oauth": {"clientId": "<approved-public-client-id>"}` in the Snowflake server
entry and requires this value for OAuth setup. Client secrets must never be
entered. Your administrator must confirm VS Code supports the registration's
client type, callback and scopes; do not substitute a confidential client that
requires a secret when the client supports only a public client ID.
On first use, review VS Code's trust/sign-in flow; VS Code manages authorization
and stored credentials. No token is written into MCP headers in OAuth mode, and
the installer does not read Snowflake CLI connections, extract CLI tokens, or
automatically select a different account/profile.

For non-interactive use, provide all details explicitly:

```bash
bash install.sh --target /path/to/existing-project --dry-run \
  --mcp-endpoint https://approved.example/mcp --mcp-auth oauth \
  --mcp-oauth-client-id approved-public-client-id --mcp-approved
bash install.sh --target /path/to/existing-project --yes \
  --mcp-endpoint https://approved.example/mcp --mcp-auth oauth \
  --mcp-oauth-client-id approved-public-client-id --mcp-approved
```

The endpoint above is illustrative; use the exact approved endpoint.
`--yes` approves writes but does not replace `--mcp-approved`. A dry run with
`--setup-mcp` alone reports pending details without prompting or creating a config;
provide the explicit options to preview the concrete MCP change.

The installer merges a `snowflake` HTTP entry into `.vscode/mcp.json` using the
VS Code `servers` schema. Unrelated entries are preserved semantically; JSON
formatting is normalized only when a merge is needed. Identical configurations
are left byte-for-byte unchanged. A conflicting Snowflake entry, symlink, invalid
JSON or JSONC/comments stops before environment/tool installation or project writes.
Use `/snowflake-mcp-setup` for manual JSONC merges and more complex OAuth setup.

Bearer mode stores only `Authorization: Bearer ${env:SNOWFLAKE_MCP_TOKEN}`.
Supply the value securely in the VS Code host environment later, not in source,
chat, logs, or shell history. The installer does not read it. Unlike interactive
`${input:...}` variables, environment references can be used with Copilot harness
sessions. Review the current
[VS Code MCP configuration reference](https://code.visualstudio.com/docs/agents/reference/mcp-configuration)
for client capabilities.

No MCP server is installed or started, no authentication is performed, and no
Snowflake connection, tool invocation or SQL test is made. Complete the reviewed
client trust/authentication steps and select only approved tools in VS Code later.
Configuration does not enforce a tool allowlist or establish server-side grants.
Without endpoint details, MCP is explicitly deferred; the setup prompt remains
available. No placeholder endpoint is written.

##### Git pre-commit secret scanning

The installer copies `.githooks/pre-commit` and `scripts/scan_secrets.py`.
After approval, it inspects the target Git repository's active hook directory,
honoring `core.hooksPath` without changing it. It enables the launcher there,
with executable permissions. Existing matching launchers are reused; existing
different hooks (including third-party hook frameworks) stop activation before
uv/environment/project writes. Manually integrate the scanner with the existing
hook, or use `--skip-hooks` to keep active hooks unchanged. Other hooks are not
modified. Installing into a nested folder of a parent repository requires
choosing the Git root or explicitly skipping hook activation.

A non-Git project receives the assets but reports activation as deferred.
After `git init`, rerun the installer, or copy `.githooks/pre-commit` to the
repository's active hook directory and mark it executable after reviewing conflicts.
The kit repository uses the same hook. No Git repository is initialized implicitly.
Dry runs do not execute Git inspection commands or change hook permissions/config:
hook compatibility inspection is explicitly pending until an actual run.

The Python standard-library scanner reads full staged blobs via their object IDs;
unstaged content is not used. Added/modified/copied/renamed paths are scanned,
deleted paths are ignored, and spaces/newlines in paths are supported. Credential
patterns include Snowflake/generic password/token/client-secret assignments,
private keys, JWTs, GitHub tokens and AWS access keys. Environment references
and public OAuth client IDs are not credentials. No file subtree is automatically
exempted. Error output contains only escaped paths, line numbers and rule labels,
not matched values; index-reading errors fail closed.

This pattern-based safeguard has false positives and false negatives and can be
bypassed locally; it is not a substitute for CI secret scanning or credential
rotation. Remove secrets from staged content and rotate any real exposed values.
No SQL linting is included in this hook; use `/snowflake-sql-check` separately.

##### Initialize project folders separately

The installer adds `/snowflake-init` and `scripts/init_project.py`; it does not
create pipeline folders. After adopting the kit, invoke `/snowflake-init` in
Copilot Chat or run the script from the target project's root:

```bash
python3 scripts/init_project.py --target /path/to/existing-project --dry-run
python3 scripts/init_project.py --target /path/to/existing-project
```

The script requires Python 3.10+ and Git by default; it does not require uv, a
virtual environment or network access. Use `--no-git` to skip Git and avoid the
Git requirement. It previews the complete plan and requires confirmation before
creating folders or initializing Git; use `--yes` for explicit non-interactive
approval.
Before planning creation, the script detects local project state and reports
per-signal evidence:

- **Greenfield:** no known project signals found. This does not necessarily mean
  an empty directory; installed kit assets, README, Git metadata, MCP settings,
  `.venv` and empty code folders do not count.
- **Brownfield:** `snowflake.yml`, `snowflake.yaml`, root or
  `pipelines/dbt/dbt_project.yml`, `docs/project-profile.md`, or populated
  `src/`, `pipelines/`, `models/`, `dags/`, `bronze/`, `silver/`, `gold/`.

Use `--detect-only` to report state without planning or creating folders.
Detection inspects paths only, not configuration values or account resources.
Unrecognized layouts remain possible; inspect the evidence before proceeding.
In `/snowflake-init`, brownfield detection offers a read-only local layout review
(recommended), explicit additive creation, or cancellation. It does not invoke a
Snowflake audit or create a project profile.
For approved additive creation, use `--allow-existing` with the preview and
actual command. `--yes` alone cannot approve a brownfield layout change.
No force-greenfield/overwrite escape hatch is provided. Existing files are
never moved, replaced or deleted.

If the target is already a Git repository, it is left as-is. If it is inside
a parent repository, no nested repository is created. Otherwise `git init`
initializes the target root by default; `--no-git` opts out. This creates no
commit, remote, staged files or push. The command does not activate the copied
secret-scanning hook; rerun the kit installer after Git initialization to
enable it safely in the new repository.

Initialization creates this agreed pipeline layout:

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

Missing folders appear as `MKDIR` in the initialization preview. Existing folders and their
contents are preserved; files blocking a required folder or symlink destinations
stop initialization before any writes. Repeat initialization restores missing
folders; rerunning the installer does not. The script refuses the kit checkout,
home and filesystem root. For a project using another layout, explicitly approve
adding this parallel layout rather than assuming a migration.
Neither installation nor initialization moves existing pipelines or generates models, DAGs,
`dbt_project.yml`, Python manifests, or pipeline runtime configuration. These empty
code folders are not a runnable project and are not tracked by Git until files
are added. Initialization `--dry-run` creates neither folders nor repository.
No starter files, `.gitkeep`, account auditing, Snowflake connections or
deployment are performed. Filesystem failures report partial
directory operations; inspect the target before retrying.

Installed assets:

- All nine full skills under `.github/skills/`, including discovery metadata.
- `.githooks/pre-commit` and `scripts/scan_secrets.py` for staged secret scanning.
- All six `.github/prompts/` workflows, `scripts/init_project.py`, and supporting Markdown/SVG files under
  `docs/`, preserving relative links.
- A marked Snowflake guidance block appended to
  `.github/copilot-instructions.md`. Existing project text is preserved.
  Kit-maintenance instructions are not copied into application instructions.

Besides the kit assets, the installer creates `.venv` by default, and optionally
creates/merges `.vscode/mcp.json`. Pipeline creation is a separate explicit step. It does not
overwrite README files, install project dependencies, or access Snowflake. The only optional
non-project change is the explicitly approved uv installation described above;
no assistant home configuration or shell profiles are changed.
Review and enable Copilot app configuration manually as described below.

Identical assets are skipped on repeat runs. If any destination asset differs
or a managed instruction block has been edited, the installer exits with an
error before writing. There is no force-overwrite mode: compare the source
and destination, manually merge or back up/move the specific conflicting
asset, and rerun. Do not delete the target project. Symlink destinations are
rejected. A filesystem failure during writes can leave a partial install;
the error reports completed file writes.
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
python3 -B -m unittest discover -s tests -p 'test_*.py' -v
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
