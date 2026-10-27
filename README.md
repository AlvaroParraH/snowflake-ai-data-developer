# Snowflake AI Data Developer

A focused collection of AI skills for Snowflake data development. Skills provide
platform guidance and clearly labeled project-default suggestions; they do not
establish organization-wide naming policy.

## Skills

- [Snowflake naming conventions](.github/skills/snowflake-naming-conventions/SKILL.md) —
  Snowflake identifier behavior, qualification, and practical naming guidance
  for data and operational objects.
- [Snowflake Bronze profiler](.github/skills/snowflake-bronze-profiler/SKILL.md) —
  bounded, read-only source profiling before Silver transformations.
- [Snowflake medallion architecture](.github/skills/snowflake-medallion-architecture/SKILL.md) —
  Snowflake-native Bronze, Silver, and Gold design and processing patterns.
- [Snowflake data quality](.github/skills/snowflake-data-quality/SKILL.md) —
  layer-appropriate checks using Snowflake features, dbt tests, or SQL.
- [Snowflake data contracts](.github/skills/snowflake-data-contracts/SKILL.md) —
  define and manage producer-consumer expectations for data products.
- [dbt with Snowflake](.github/skills/snowflake-dbt-integration/SKILL.md) —
  project structure, `dbt-snowflake` configuration, models, tests, and builds.
- [Snowflake project structure](.github/skills/snowflake-project-structure/SKILL.md) —
  preserve the agreed `pipelines/` layout for Bronze ingestion, Silver/Gold
  dbt models and Airflow DAGs; guide scaffolding and approved path changes.
- [Snowflake data governance](.github/skills/snowflake-data-governance/SKILL.md) —
  ownership, roles/grants, managed access, classification, masking, row access,
  governed files, audit/lineage and sharing using Snowflake-native semantics.
- [Snowflake compute tagging](.github/skills/snowflake-compute-tagging/SKILL.md) —
  warehouse object tags and query tags for Snowflake cost attribution.
- [Snowflake tasks](.github/skills/snowflake-tasks/SKILL.md) —
  scheduled and triggered Tasks, task graphs, retries, monitoring, and
  orchestration tradeoffs.
- [Streamlit in Snowflake](.github/skills/snowflake-streamlit/SKILL.md) —
  runtime selection, governed data access, app permissions, package and
  external access, performance, and deployment guidance.
- [Snowflake Cortex AI Functions](.github/skills/snowflake-cortex-ai-functions/SKILL.md) —
  batch AI analysis, quality evaluation, cost, privileges, and data handling.
- [Snowflake Cortex Search and RAG](.github/skills/snowflake-cortex-search/SKILL.md) —
  corpus design, hybrid retrieval, freshness, filters, evaluation, and
  grounded application patterns.
- [Snowflake Semantic Views and Cortex Analyst](.github/skills/snowflake-semantic-views-analyst/SKILL.md) —
  governed metrics and relationships for tested natural-language analytics.
- [Snowflake deployment and promotion](.github/skills/snowflake-deployment/SKILL.md) —
  tool-agnostic release planning, environment promotion, approvals, and
  rollback safeguards.

Existing project conventions take precedence. Confirm names and applicable
conventions before creating or migrating objects.

## Python tooling for pipeline projects

| Tool | Version | Use |
|---|---|---|
| [uv](https://docs.astral.sh/uv/) | Latest stable | Manage environments and dependencies for new Python pipeline projects. |

Declare dependencies in `pyproject.toml` and commit `uv.lock` for reproducible
installs. Install uv using the
[official installation instructions](https://docs.astral.sh/uv/getting-started/installation/).
uv is a prerequisite for the project installer and the convention for Python
pipeline development. It is not needed merely to read this documentation or
its skills.

## Shared installation for VS Code Copilot

To keep the kit outside your projects, build a shared agent plugin:

```bash
bash install.sh --shared --dry-run
bash install.sh --shared --yes
```

The default destination is `~/.snowflake-ai-data-developer`. Use
`--target /absolute/path/to/shared-kit` to choose another empty directory.
The shared installer needs an existing Python 3.10+ with `venv`/`ensurepip`
support. After approval, it creates the kit's own `.venv/` inside the shared
directory, using that interpreter and bundled pip without network downloads.
No third-party packages, CLIs, credentials, local MCP servers or Git hooks
are installed. Editor settings change only with optional approved registration.
Optional approved remote MCP registration is described
below. Shared workflows use this kit interpreter; project
dependencies belong in a separate project environment. `/snowflake-init`
does not automatically create a project `.venv`.

The default kit interpreter is `~/.snowflake-ai-data-developer/.venv/bin/python`
on macOS/Linux (`.venv/Scripts/python.exe` on Windows). Virtual environments
are not relocatable: rebuild the bundle at its final path if moving it.
If environment creation fails, the installer reports failure and leaves the
partial directory for inspection; it does not overwrite it on retry.

Register the resulting folder in **VS Code User settings**, not workspace
settings (replace the example with your absolute path):

The installer can register it automatically with preview and approval:

```bash
bash install.sh --shared --target "$HOME/.snowflake-ai-data-developer-v2" \
  --register-vscode --vscode-settings "/absolute/path/to/User/settings.json" --dry-run
```

Open **Preferences: Open User Settings (JSON)** to obtain the exact active
profile file path if specifying it explicitly. After reviewing the preview,
replace `--dry-run` with `--yes`, or omit both to approve interactively.
With just `--register-vscode`, the installer discovers saved default and named
profile settings in the standard VS Code and VS Code Insiders user directories
on macOS, Linux and Windows. A single candidate is previewed automatically;
multiple candidates require an interactive numbered selection or an explicit
`--vscode-settings` path (also required for ambiguous dry runs). The active
profile is not inferred. Portable/custom user-data locations require an
explicit path. The settings file must already exist and contain strict JSON;
JSONC comments/trailing commas require the manual merge below, without
`--register-vscode` or `--vscode-settings`.

Use repeated `--disable-plugin "/absolute/path/to/old-kit"` options to
explicitly disable existing old entries; other plugins are never disabled
automatically. Settings are written only after successful bundle/environment
creation, and changed files or symlinked paths are rejected. The installer
always prints the exact registration entry, old-copy reminder, reload and
command-discovery steps. It does not reload VS Code or claim discovery.

```json
{
  "chat.pluginLocations": {
    "/Users/your-name/.snowflake-ai-data-developer": true
  }
}
```

Merge this entry with existing settings; do not replace the settings file.
Agent plugins must be enabled and permitted by your organization's policy.
`chat.pluginLocations` is experimental and requires a supporting VS Code
version. Check **Chat: Open Customizations** for the plugin and verify
`/snowflake-init` and `/snowflake-dbt-model` are available in your chosen
harness. Discovery in a running editor is a separate check from building
the package.

The bundle exposes fifteen guidance skills, eleven workflow skills (the same
workflow names as the project prompts), and four Copilot agents. Workflow
skills read the canonical prompt files inside the bundle; no duplicated
workflow source is maintained. Scoped safety guidance loads with each skill,
not as global instructions for unrelated projects. Shared helpers generate
only approved project files in the selected project; do not copy the bundle
into it.

Existing project-local installations are not removed automatically. Avoid
enabling both copies in the same workspace; disable the shared plugin there
until you explicitly review removal of project-local kit assets. Never remove
customized files or project profiles as an automatic migration. For updates,
build into a fresh shared directory, validate it, and switch the user setting;
the shared installer refuses nonempty destinations and does not overwrite.

See the [VS Code plugin documentation](https://code.visualstudio.com/docs/agent-customization/agent-plugins)
and [format reference](https://code.visualstudio.com/docs/agents/reference/agent-plugin-reference).

### Optional shared remote MCP setup

Shared installation accepts `--setup-mcp` to collect an approved remote endpoint,
authentication and an explicit user configuration path. MCP setup is optional;
`--yes` never substitutes for administrator approval. No server, Snowflake
object, grant, authentication flow or connection test is run.

Choose the configuration for your harness:

- **Copilot global:** use **MCP: Add Server > Global > Copilot Global**.
  The file is `$COPILOT_HOME/mcp-config.json`, falling back to
  `~/.copilot/mcp-config.json`. Use `--mcp-format copilot`, approved bearer
  authentication and repeated exact `--mcp-tool` names. The helper does not
  support fixed-client OAuth in this format.
- **VS Code Local harness:** use **MCP: Open User Configuration** to obtain
  your active user-profile MCP path. Use `--mcp-format vscode` (the default).
  Fixed-client OAuth requires `--mcp-oauth-client-id` with the administrator's
  public client ID. This user-profile format is not universal across harnesses.

For example, after replacing all sample values with approved details, preview
a fresh shared installation with Copilot-global registration:

```bash
bash install.sh --shared --dry-run \
  --mcp-config "$HOME/.copilot/mcp-config.json" \
  --mcp-format copilot \
  --mcp-endpoint "https://approved-host.example/approved-mcp-path" \
  --mcp-auth bearer --mcp-tool approved_metadata_tool --mcp-approved
```

After reviewing the exact preview, replace `--dry-run` with `--yes`.
For an already installed kit, use its standalone helper instead of reinstalling:

```bash
"$HOME/.snowflake-ai-data-developer/.venv/bin/python" \
  "$HOME/.snowflake-ai-data-developer/scripts/setup_mcp.py" --setup-mcp
```

Pass `--mcp-format copilot` and exact `--mcp-tool` names for the global format.
The helper previews the server entry before confirmation, preserves unrelated
servers, and refuses conflicting Snowflake entries, symlinks, or JSONC merges.
It also supports explicit arguments with `--dry-run` and `--yes`.
Bearer credentials remain outside configuration: supply `SNOWFLAKE_MCP_TOKEN`
through the environment of the host running your session. The helper writes
only the format-appropriate variable reference, never a token.
For OAuth, complete browser sign-in in VS Code. Review trust and tool access
in the selected client; registration is not permission to invoke tools.
No live connection is verified during setup. Do not duplicate the server
in each project's configuration.

## Install into a project (alternative)

Use Git, Python 3.10+, Bash, and the Snowflake CLI (`snow`) to run the
[project-local installer](install.sh). It checks Git, Snowflake CLI, and uv on
PATH and verifies their version commands before writing project files. With
your approval, it can install missing uv and Snowflake CLI. No Snowflake account
credentials are needed just to install the kit.

```bash
bash install.sh --target /path/to/existing-project --dry-run
bash install.sh --target /path/to/existing-project
```

Review the preview, then confirm installation. For non-interactive use, pass
`--yes` after reviewing a dry run; this also approves installing missing uv
and Snowflake CLI.
If uv is missing, installation is offered using Homebrew on macOS or Astral's
official installer on Linux. This needs network access and installs uv outside
the project. Linux installation uses `~/.local/bin` without editing shell
profiles; add that directory to PATH for future shells if needed.
If Snowflake CLI is missing on macOS or Linux, the installer offers Snowflake's
official signed-binary installer. It installs under
`~/.local/share/snowflake-cli` (or `$XDG_DATA_HOME/snowflake-cli`) without
editing shell profiles; add its `bin/` directory to PATH for future shells if
needed. Windows and unsupported systems need a manual install using the
[official instructions](https://docs.snowflake.com/en/developer-guide/snowflake-cli/installation/installation).
Git, Python, Homebrew (on macOS, only for installing uv), and curl/sh (for
installing Snowflake CLI) must already be installed.

Use `--no-install` to prohibit automatic tool installation; missing uv or
Snowflake CLI then stops an actual run before project writes. A dry run only
reports prerequisites and planned changes: it downloads, executes and installs
nothing.

The installer copies all fifteen full skills directly into `.github/skills/`,
all eleven prompts, the project initializer and starter generators, and their
supporting documentation.
It appends a marked guidance block to existing Copilot instructions without
changing the original text. Conflicting files stop installation before writes;
identical files are left alone, making repeat installations safe.

### Initialize pipeline folders or a project starter scaffold

Installation does not create or restore pipeline folders. After installation,
run `/snowflake-init` in Copilot Chat, or run the installed script from the
target project:

```bash
python3 scripts/init_project.py --target /path/to/your-project --dry-run
python3 scripts/init_project.py --target /path/to/your-project
```

By default, initialization creates only the agreed folders. To preview the
optional greenfield starter scaffold, add `--scaffold`:

```bash
python3 scripts/init_project.py --target /path/to/your-project --dry-run --scaffold
python3 scripts/init_project.py --target /path/to/your-project --scaffold
```

The scaffold adds project-context documentation, a `.gitignore`, area guides,
an unimplemented source-aware Bronze Python placeholder, a minimal dbt project
with a documented zero-row SQL example, an empty Airflow DAG, and test guidance.
Provide optional project context with `--project-name`, `--source-type`,
`--environment`, `--owner`, `--description`, `--domain`,
`--data-sensitivity`, and `--consumers`. The environment and sensitivity are
planning notes only, not Snowflake configuration. These are templates, not a
configured/runnable pipeline. It does not install dependencies, create
credentials/profiles, connect to Snowflake, run dbt, or deploy Airflow. Review
the preview and confirm creation (or pass `--yes` for automation).
Initialization first reports **greenfield** (no existing project signals) or
**brownfield** (existing local Snowflake/dbt configuration, project profile, or
populated code folders), with the evidence. Installed kit assets and an empty
pipeline layout alone do not mark a project as brownfield.
Use `--detect-only` for a read-only classification. Existing projects require
explicit `--allow-existing` approval before missing folders can be added;
`--yes` alone does not bypass that check. The starter scaffold is greenfield-only;
existing project signals require a separate reviewed workflow and never enable
starter-file generation. In Copilot, `/snowflake-init` offers folder-only or
starter-file setup for greenfield projects, and local layout review, additive
folder creation, or cancellation for brownfield projects. Unless `--no-git` is
passed, it also runs `git init` when the target
is not already in a repository. Existing repositories and parent repositories
are not reinitialized and do not get a nested repository. Git initialization
does not add files, create commits, configure remotes, or publish anything.
After initializing a Git repository, rerun `install.sh` if you want to activate
the staged secret-scanning hook. No account audit or overwrite mode is included.

### Generate a dbt model

After `/snowflake-init` (or in an existing dbt project), use `/snowflake-dbt-model`
to inspect conventions and prepare one model with matching YAML documentation.
The workflow uses the existing dbt project root and asks for the exact upstream
relation/model, selected columns, and any tests before generating files.
Preview from the repository root with the required model details:

```bash
python3 scripts/scaffold_dbt_model.py \
  --target pipelines/dbt --layer staging --domain sales \
  --model-name stg_sales__orders \
  --source-name sales_source --source-table orders \
  --column order_id --column order_total \
  --dry-run
```

The helper only writes local `.sql` and `.yml` files after approval, refuses
conflicts, and never invokes dbt or connects to Snowflake.

Initialization creates the following folders, preserving existing contents:

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

Folder-only initialization creates empty code folders, not a runnable dbt or
Airflow project. The optional scaffold creates clearly marked example model/DAG
templates and minimal dbt project configuration, but no credentials or runtime
dependencies. The dbt example creates a zero-row relation only if you later
configure a profile and run dbt. Empty directories are not tracked by Git; add
implementation files when ready.

### Python environment

By default, the installer creates `.venv/` with `uv venv`, using the Python
interpreter running the installer, offline and without downloading Python or
installing dependencies (including pip). Existing valid environments are verified
and left unchanged. No `pyproject.toml` or `uv.lock` is generated or modified.
Select `.venv/bin/python` in VS Code or activate with `source .venv/bin/activate`.
Confirm that this interpreter meets your project's Python requirements.

Use `--skip-venv` for an existing environment workflow. A missing `.venv` alongside
Poetry/Pipenv/Conda manifests or `.python-version` stops setup and requests that
decision rather than silently replacing the project's conventions.
Invalid existing environments are not overwritten. Exclude `.venv/` from Git.

### Optional VS Code Snowflake MCP setup

Add `--setup-mcp` to enter the endpoint and authentication details interactively:

```bash
bash install.sh --target /path/to/existing-project --setup-mcp
```

Supply an exact administrator-approved HTTPS endpoint, choose `oauth` or `bearer`,
and confirm the exposed tools and VS Code authentication path are approved.
OAuth is recommended: supply the administrator-provisioned **public client ID**
when prompted (or use `--mcp-oauth-client-id`). The config stores
`oauth.clientId`, not a secret or token. VS Code handles authorization and
credential storage on first use. No Snowflake CLI profile is read, no CLI tokens
are extracted, and no bearer header is configured in OAuth mode.
The installer creates or merges `.vscode/mcp.json`, preserving unrelated server
entries. Conflicting Snowflake entries or JSONC/comments require a manual merge.
OAuth must already be provisioned for the client; Snowflake-managed MCP does not
support dynamic OAuth client registration. Bearer mode writes only an environment
variable reference, `${env:SNOWFLAKE_MCP_TOKEN}`, never a token. Provide that variable
securely to the VS Code host later; do not save it in project files or shell history.
Interactive `${input:...}` secrets are not used because they are not forwarded to
Copilot harness sessions.

Without MCP details, configuration is explicitly deferred and the setup prompt is
still installed. The installer never starts MCP, authenticates, connects to
Snowflake, or executes SQL. Review server trust and select only approved tools in
VS Code before use; writing configuration is not a tested connection.

The installer does not install project dependencies or modify personal assistant directories.
See [installation details](docs/copilot-setup.md#install-into-another-project)
for conflict handling and discovery verification.

### Git pre-commit secret scanning

The kit includes a [pre-commit launcher](.githooks/pre-commit) and a
[standard-library scanner](scripts/scan_secrets.py). Installation copies both
assets and enables the hook in a target Git repository's active hook directory
after approval, without changing `core.hooksPath`. The kit repository also uses
this hook. Existing different hooks are never overwritten: manually chain the
scanner or use `--skip-hooks` to leave hook activation unchanged.
Non-Git targets receive the assets, with activation explicitly deferred.

The scanner checks staged blobs, including renamed files, for likely passwords,
tokens, private keys and other credential patterns. It reports paths, line
numbers and rule labels, never secret values. It blocks on scanning errors.
This is heuristic protection, not proof that all secrets were detected, and local
hooks can be bypassed. Rotate exposed real credentials.
It does not install/run SQLFluff; `/snowflake-sql-check` remains a separate workflow.

## Visual reference

[Snowflake medallion + dbt project structure](docs/references/snowflake-medallion-dbt-project-structure.svg)
combines medallion and dbt guidance into a repository layout and data-flow
diagram. The [project-structure skill](.github/skills/snowflake-project-structure/SKILL.md)
preserves this agreed convention for new pipelines adopting it. The diagram
is guidance, not a required Snowflake database/schema layout; the installer
installs `/snowflake-init` to create only the core pipeline folders shown above,
when explicitly invoked.
The diagram groups ingestion, dbt and Airflow orchestration under `pipelines/`:
Bronze ingestion code in `pipelines/ingestion/bronze/`, Silver models
in `pipelines/dbt/models/silver/{staging,intermediate}/`, Gold models in
`pipelines/dbt/models/gold/marts/`, and DAGs in
`pipelines/orchestration/airflow/dags/`. These are code folders, not local data storage.
Configure Airflow's `dags_folder` or deploy/mount the DAG directory into the
runtime's configured location (for example, `/opt/airflow/dags` in Docker).
Workers also need access to ingestion code, the dbt project, dependencies and
approved runtime credentials; deploying DAG files alone is not sufficient.
For this proposed layout, nest dbt's staging/intermediate model configurations
under `silver` and marts configurations under `gold` in `dbt_project.yml`;
keep `model-paths: ["models"]` relative to the dbt project. dbt staging models
transform declared sources; they do not replace Bronze ingestion.

## Assistant support

**GitHub Copilot is a supported target, separate from OpenAI Codex.** Copilot
project instructions live in
[`.github/copilot-instructions.md`](.github/copilot-instructions.md), with
native skill discovery under `.github/skills/`. Each skill's `SKILL.md` contains
both discovery metadata and full guidance; there is no separate root-level
skill copy. There are fifteen skills, listed above.

Workspace custom agents provide focused investigations:

- [`snowflake-cost-investigator`](.github/agents/snowflake-cost-investigator.agent.md)
  ranks bounded query and warehouse compute usage; it distinguishes query
  attribution from warehouse metering and requires approval before live access.
- [`snowflake-query-optimizer`](.github/agents/snowflake-query-optimizer.agent.md)
  diagnoses one completed query from available history/profile evidence without
  rerunning it.
- [`snowflake-naming-auditor`](.github/agents/snowflake-naming-auditor.agent.md)
  statically checks project naming against documented rules without querying
  Snowflake or renaming objects.
- [`snowflake-data-profiler`](.github/agents/snowflake-data-profiler.agent.md)
  produces bounded, aggregate-only profiles for an explicitly scoped dataset.
  It complements the Bronze profiling skill.

Workspace prompts include
[`/snowflake-audit`](.github/prompts/snowflake-audit.prompt.md) for a local
repository audit and optional approved, bounded account metadata review,
[`/snowflake-check`](.github/prompts/snowflake-check.prompt.md) for local
prerequisite checks and an approved Snowflake CLI connection test,
[`/snowflake-connection-setup`](.github/prompts/snowflake-connection-setup.prompt.md)
for selecting a user-level Snowflake CLI connection per project,
[`/snowflake-dbt-model`](.github/prompts/snowflake-dbt-model.prompt.md) for
reviewed generation of one dbt model and matching YAML documentation,
[`/snowflake-init`](.github/prompts/snowflake-init.prompt.md) for explicitly
creating the agreed pipeline folders or optional greenfield starter project,
[`/snowflake-kit-status`](.github/prompts/snowflake-kit-status.prompt.md) for a
read-only local kit health check,
[`/snowflake-kit-update`](.github/prompts/snowflake-kit-update.prompt.md) for a
reviewed, non-destructive refresh of project-local Snowflake kit assets,
[`/snowflake-mcp-setup`](.github/prompts/snowflake-mcp-setup.prompt.md) for
approved MCP client configuration,
[`/snowflake-pipeline`](.github/prompts/snowflake-pipeline.prompt.md) for
staged, review-gated pipeline design and implementation, and
[`/snowflake-sql-check`](.github/prompts/snowflake-sql-check.prompt.md) for
manual pre-commit SQLFluff checks using existing project tooling. The SQL
check does not install dependencies, connect to Snowflake or enforce a Git hook.

See [Copilot setup](docs/copilot-setup.md) for project-local adoption, discovery
checks, and optional Snowflake MCP configuration guidance. No global installer,
MCP connection, credentials, or automatic database access is included. Copilot
instructions and MCP configuration are not Codex configuration.

For contributors maintaining this repository, see
[AGENTS.md](AGENTS.md) for coding-agent guidance and
[ARCHITECTURE.md](ARCHITECTURE.md) for the component map, installation
boundaries, safety model, and design decisions. These contributor documents
are not copied into consuming projects.
