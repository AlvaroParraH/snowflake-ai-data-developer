# Snowflake AI Data Developer — Architecture

This document describes the source kit and its shared plugin and project-local
distribution modes. The kit provides Snowflake-focused guidance and optional
local setup; it is not a Snowflake service or account bootstrapper.

## Shared plugin distribution

`bash install.sh --shared` delegates to `scripts/install_shared.py`. It builds
an Agent Plugins 1.0 bundle in a dedicated empty directory (by default
`~/.snowflake-ai-data-developer`). The bundle contains the canonical assets,
fifteen portable knowledge skill entry points, ten portable workflow skill
entry points, and four agents under `com.github.copilot/agents/`.
Entry points reference canonical guidance and describe relocatable kit-root
resolution separately from the consumer project's root. Script execution uses
the shared bundle and writes only approved project outputs.
After approval, the builder also creates and verifies a kit-local `.venv/`
with standard-library `venv` and bundled pip, without network downloads or
third-party packages. Shared workflow entry points select this interpreter.
The environment uses existing Python and must be rebuilt if the bundle moves.
Project environments are separate and are not created by project initialization.

VS Code activation is a separate user-level `chat.pluginLocations` setting.
The builder does not modify editor settings, install CLIs, create project environments,
or activate hooks. It never writes global always-on
instructions. Existing project-local installations are preserved; users must
avoid duplicate activation and review migration separately. Updates use a
fresh bundle directory, not overwrite or deletion of installed content.
Local bundle tests establish packaging and script behavior, not discovery in
a running VS Code harness.

Optional `--setup-mcp` delegates to `scripts/setup_mcp.py` for shared remote
MCP registration. An explicit user configuration path, administrator-approved
endpoint/authentication and write confirmation are required. The helper also
runs independently for existing installations. It reuses the project
installer's endpoint/auth validation and safe JSON merge conventions, with
separate VS Code `servers` and Copilot-global `mcpServers` formats. The latter
requires an exact tool allowlist and uses portable environment references.
Fixed-client OAuth is supported only in VS Code format; unsupported portable
OAuth configuration is rejected. No credential values, plugin MCP auto-start,
live authentication, server creation or remote test are included. Configuration
is previewed and checked for changes before writing; unrelated entries remain.

## System overview

```text
┌──────────────────────────────────────────────────────────────────────┐
│ Kit source repository                                                │
│                                                                      │
│ .github/                                                             │
│ ├── copilot-instructions.md  contributor/user routing guidance       │
│ ├── skills/                 Snowflake knowledge, loaded on demand     │
│ ├── prompts/                focused user-invoked workflows            │
│ └── agents/                 focused custom agent roles                │
│                                                                      │
│ scripts/install_kit.py ───── additive, conflict-safe distribution     │
│ scripts/init_project.py ──── separately approved empty folder setup   │
│ .githooks/pre-commit ─────── staged-blob secret-pattern scanning      │
└──────────────────────────────────────────────────────────────────────┘
                              │
                  explicit local installation
                              ▼
┌──────────────────────────────────────────────────────────────────────┐
│ Consumer project                                                     │
│                                                                      │
│ .github/copilot-instructions.md                                      │
│ .github/skills/  .github/prompts/  .github/agents/                   │
│ docs/  scripts/  .githooks/  optional .vscode/mcp.json               │
│                                                                      │
│ Copilot reads local instructions and invokes selected assets.        │
│ Snowflake access occurs only through separately approved tooling.     │
└──────────────────────────────────────────────────────────────────────┘
```

The source repository also contains contributor-facing `AGENTS.md` and this
architecture document. They explain how to maintain the kit and are not
included in the installed project payload.

## Component map

| Component | Location | Responsibility |
|---|---|---|
| Repository instructions | `.github/copilot-instructions.md` | Snowflake safety boundaries and routing to relevant skills. |
| Skills | `.github/skills/<name>/SKILL.md` | On-demand Snowflake, dbt, medallion, governance, quality, naming, and operations knowledge. |
| Prompts | `.github/prompts/*.prompt.md` | User-invoked workflows such as audit, readiness, initialization, dbt model generation, kit maintenance, and pipeline planning. |
| Custom agents | `.github/agents/*.agent.md` | Focused investigation roles with explicit scope, minimal tools, and bounded outputs. |
| Installer | `install.sh`, `scripts/install_kit.py` | Preview and install project-local assets without replacing differing files. |
| Initializer | `scripts/init_project.py`, `scripts/scaffold_snowflake_project.py` | Separately preview and create the agreed `pipelines/` folders; optionally add a context-aware greenfield starter project and initialize Git with approval. |
| dbt model generator | `scripts/scaffold_dbt_model.py`, `/snowflake-dbt-model` | Inspect conventions, then preview one model and matching YAML docs in an existing dbt project; no dbt execution or Snowflake connection. |
| Secret scanner | `.githooks/pre-commit`, `scripts/scan_secrets.py` | Scan staged Git blobs for likely credential patterns without displaying matched values. |
| Documentation | `README.md`, `docs/` | Setup, operating boundaries, and visual project-layout guidance. |
| Tests | `tests/` | Installer, project initializer, dbt model generator, and secret-scanner behavior. |

### Skills, prompts, and agents

- **Skills** provide reusable expertise. Discovery metadata and full guidance
  live together in each `SKILL.md`; there is no separate generated skill copy.
- **Prompts** guide a user through one named workflow. They are not standalone
  executables and do not grant authority to connect to Snowflake.
- **Agents** are focused custom personas for tasks such as cost investigation,
  query diagnosis, naming review, and statistical profiling. Their tool
  declarations and instructions constrain intended behavior, but are not
  security controls or Snowflake grants.

Use a skill for reusable knowledge, a prompt for a user-directed workflow, and
an agent for a focused investigation with a concise result.

## Distribution and initialization

### Installation flow

`install.sh` delegates to `scripts/install_kit.py`. The installer:

1. Requires Git, Python 3.10+, Snowflake CLI (`snow`), and uv. With user
   approval, it may install missing CLI/uv tools on supported platforms. Both
   are version-checked before project writes.
2. Gathers Markdown/SVG assets from `.github/agents/`, `.github/skills/`,
   `.github/prompts/`, and `docs/`, plus the project hook and scripts.
3. Preflights destinations and refuses symlinks or files that differ from the
   source. Matching files are left unchanged; conflicting content requires a
   manual merge.
4. Previews changes with `--dry-run`; actual writes require an explicit
   interactive confirmation or `--yes`.
5. Creates a `.venv` by default unless skipped, and can optionally merge
   administrator-approved MCP configuration. Those side effects are described
   in the preview/setup documentation.

The installer does not install application dependencies, execute Snowflake
SQL, connect to an account, create database objects, or create pipeline
folders.

### Pipeline folder initialization

`/snowflake-init` and `scripts/init_project.py` are a separate opt-in workflow.
They classify local project signals and preview creation of empty pipeline
directories. A greenfield-only `--scaffold` option also records project
context and creates project documentation, `.gitignore`, an unimplemented
source-aware ingestion placeholder, a minimal dbt project with a zero-row
example model, model documentation and dbt test/macro/snapshot guidance, an
empty-task Airflow DAG example, and local test guidance. Context fields do
not configure Snowflake targets.
Templates do not install dependencies, create credentials/profiles, connect
to Snowflake, run dbt, or deploy workloads. Brownfield projects allow only
explicitly approved additive folders. The workflow does not migrate files.
Git initialization, when needed, is local only: it does not stage, commit,
configure remotes, or push.

`/snowflake-dbt-model` is a separate opt-in helper for an existing dbt project.
It previews and creates a single model with matching documentation, refuses
conflicts, and does not compile, execute, or connect to Snowflake.

### Secret-scanning hook

The optional staged pre-commit hook scans staged blobs for common credential
patterns. It reports path, line, and rule labels, never the matching value, and
blocks on scanner errors. This is heuristic protection, not a guarantee that
all secrets are detected; hooks can be bypassed. It does not run SQLFluff or
validate Snowflake SQL.

## Interaction and data flow

### Local guidance without Snowflake access

```text
User asks for Snowflake/dbt guidance
        │
        ▼
Copilot reads repository instructions and selected skill/prompt/agent
        │
        ▼
Assistant reviews local project files and drafts a plan or code
        │
        ▼
User reviews and applies changes through the project's normal workflow
```

Most kit usage is local and does not require Snowflake credentials, MCP, or a
live connection.

### Optional approved Snowflake tooling

```text
User approves a specific operation and account context
        │
        ▼
Copilot uses an administrator-approved MCP server or local Snowflake CLI
        │
        ▼
Snowflake evaluates the request under the configured identity and grants
        │
        ▼
Assistant reports results, scope, and limitations to the user
```

MCP configuration is optional client setup; it does not itself authenticate,
authorize tools, or establish least privilege. Tool availability is not
authorization. Account grants, role selection, endpoint trust, and explicit
approval remain independent controls. Read-only exploration must be bounded;
`LIMIT` limits returned rows, not necessarily scanned data or compute.

## Safety model

- **Local-first:** authoring and static review do not connect to Snowflake.
- **Explicit authority:** live reads and especially writes require approval for
  the target and operation; MCP presence is not permission.
- **Least privilege:** use approved identities and tools; do not discover,
  print, or commit credentials.
- **Review before impact:** show exact targets, statements, and expected
  effects before destructive or overwriting actions.
- **Bounded exploration:** inspect relevant metadata, project only required
  columns, and scope scans to a justified period or subset.
- **No success-shaped fallbacks:** surface errors, missing permissions,
  uncertainties, and partial operations.
- **Conflict preservation:** installer/update workflows do not silently
  overwrite differing project files.
- **Platform-native guidance:** use Snowflake and `dbt-snowflake` behavior;
  do not infer Spark, Databricks, or another platform's execution semantics.

These are assistant and installer design rules, not technical enforcement of
Snowflake account permissions.

## Design decisions

| Decision | Rationale |
|---|---|
| Copilot-native project assets | Instructions, skills, prompts, and agents are stored in their supported workspace locations. |
| Keep complete skill guidance in `SKILL.md` | Discovery metadata and content stay together and links remain project-local. |
| Use prompts for workflows and agents for focused investigations | Keeps workflows user-directed and investigations bounded; neither is represented as an executable tool. |
| Project-local installation | Avoids changes to personal assistant configuration and keeps assets versioned with the consumer project. |
| Preview and refuse conflicting files | Preserves user customizations and makes updates reviewable rather than destructive. |
| Separate folder initialization from installation | Installing guidance should not restructure an application repository. |
| Make MCP optional | Most guidance works offline; administrators control the endpoint, authentication, and grants. |
| Distinguish warehouse metering from query attribution | Prevents treating per-query allocations as total Snowflake cost or adding them to warehouse totals. |
| Examples are not organization policy | Teams must confirm naming, roles, environments, thresholds, and data contracts locally. |
| No dependency or service bootstrap | The kit does not create a Snowflake account, deploy a service, install application dependencies, or make pipelines runnable. |

## Extension points

1. **Add a skill:** create `.github/skills/<name>/SKILL.md` with valid
   discovery frontmatter, Snowflake-grounded guidance, and relevant links.
2. **Add a prompt:** create `.github/prompts/<name>.prompt.md` for one
   user-invoked workflow with clear scope, approvals, and stop conditions.
3. **Add an agent:** create `.github/agents/<name>.agent.md` for one focused
   role. Use the minimum appropriate tools and define bounded investigation
   and output behavior.
4. **Change installation or initialization:** update the relevant script,
   tests, README, and setup documentation. Preserve dry-run behavior, conflict
   checks, idempotency, symlink protections, and explicit approvals.
5. **Add documentation:** store references under `docs/` and keep Markdown
   links relative so the installer can preserve their layout.

Validate links, frontmatter, examples, and relevant tests for each addition.
Do not run illustrative SQL against a live account as a documentation check.
