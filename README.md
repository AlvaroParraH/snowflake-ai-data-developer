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

## Install into a project

Use Python 3.10+ and Bash to run the [project-local installer](install.sh).
The installer requires uv, checks for it on PATH, and verifies `uv --version`
before writing project files. No third-party Python packages, project virtual
environment, or Snowflake credentials are needed.

```bash
bash install.sh --target /path/to/existing-project --dry-run
bash install.sh --target /path/to/existing-project
```

Review the preview, then confirm installation. For non-interactive use, pass
`--yes` after reviewing a dry run; this also approves installing missing uv.
If uv is missing, installation is offered using Homebrew on macOS or Astral's
official installer on Linux. This needs network access and installs uv outside
the project. Linux installation uses `~/.local/bin` without editing shell
profiles; add that directory to PATH for future shells if needed.
Python and Homebrew (on macOS) must already be installed.

Use `--no-install` to prohibit tool installation; missing uv then stops an
actual run before project writes. A dry run only reports prerequisites and
planned changes: it downloads, executes and installs nothing.

The installer copies all eight full skills directly into `.github/skills/`,
both prompts and their supporting documentation.
It appends a marked guidance block to existing Copilot instructions without
changing the original text. Conflicting files stop installation before writes;
identical files are left alone, making repeat installations safe.

It also creates the following pipeline folders, preserving existing contents:

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

These are empty code folders, not a runnable dbt or Airflow project.
No example models, DAGs, credentials, or configuration files are generated.
Empty directories are not tracked by Git; add implementation files when ready.

The installer does not install Python dependencies, configure MCP, connect
to Snowflake, or modify personal assistant directories.
See [installation details](docs/copilot-setup.md#install-into-another-project)
for conflict handling and discovery verification.

## Visual reference

[Snowflake medallion + dbt project structure](docs/references/snowflake-medallion-dbt-project-structure.svg)
combines medallion and dbt guidance into a repository layout and data-flow
diagram. The [project-structure skill](.github/skills/snowflake-project-structure/SKILL.md)
preserves this agreed convention for new pipelines adopting it. The diagram
is guidance, not a required Snowflake database/schema layout; the installer
creates only the core pipeline folders shown above.
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
skill copy. There are eight skills, listed above.

Workspace prompts include
[`/snowflake-mcp-setup`](.github/prompts/snowflake-mcp-setup.prompt.md) for
approved MCP client configuration and
[`/snowflake-sql-check`](.github/prompts/snowflake-sql-check.prompt.md) for
manual pre-commit SQLFluff checks using existing project tooling. The SQL
check does not install dependencies, connect to Snowflake or enforce a Git hook.

See [Copilot setup](docs/copilot-setup.md) for project-local adoption, discovery
checks, and optional Snowflake MCP configuration guidance. No global installer,
MCP connection, credentials, or automatic database access is included. Copilot
instructions and MCP configuration are not Codex configuration.
