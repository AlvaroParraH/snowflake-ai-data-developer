# Snowflake AI Data Developer

A focused collection of AI skills for Snowflake data development. Skills provide
platform guidance and clearly labeled project-default suggestions; they do not
establish organization-wide naming policy.

## Skills

- [Snowflake naming conventions](skills/snowflake-naming-conventions/SKILL.md) —
  Snowflake identifier behavior, qualification, and practical naming guidance
  for data and operational objects.
- [Snowflake Bronze profiler](skills/snowflake-bronze-profiler/SKILL.md) —
  bounded, read-only source profiling before Silver transformations.
- [Snowflake medallion architecture](skills/snowflake-medallion-architecture/SKILL.md) —
  Snowflake-native Bronze, Silver, and Gold design and processing patterns.
- [Snowflake data quality](skills/snowflake-data-quality/SKILL.md) —
  layer-appropriate checks using Snowflake features, dbt tests, or SQL.
- [Snowflake data contracts](skills/snowflake-data-contracts/SKILL.md) —
  define and manage producer-consumer expectations for data products.
- [dbt with Snowflake](skills/snowflake-dbt-integration/SKILL.md) —
  project structure, `dbt-snowflake` configuration, models, tests, and builds.
- [Snowflake project structure](skills/snowflake-project-structure/SKILL.md) —
  preserve the agreed `pipelines/` layout for Bronze ingestion, Silver/Gold
  dbt models and Airflow DAGs; guide scaffolding and approved path changes.
- [Snowflake data governance](skills/snowflake-data-governance/SKILL.md) —
  ownership, roles/grants, managed access, classification, masking, row access,
  governed files, audit/lineage and sharing using Snowflake-native semantics.

Existing project conventions take precedence. Confirm names and applicable
conventions before creating or migrating objects.

## Visual reference

[Snowflake medallion + dbt project structure](docs/references/snowflake-medallion-dbt-project-structure.svg)
combines medallion and dbt guidance into a repository layout and data-flow
diagram. The [project-structure skill](skills/snowflake-project-structure/SKILL.md)
preserves this agreed convention for new pipelines adopting it. It is not a
scaffold or a required Snowflake database/schema layout.
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
native skill discovery under `.github/skills/`. Each Copilot skill entry
directs the assistant to the full guidance in `skills/`, keeping that guidance
in one place. There are eight skills, listed above.

See [Copilot setup](docs/copilot-setup.md) for project-local adoption, discovery
checks, and optional Snowflake MCP configuration guidance. No global installer,
MCP connection, credentials, or automatic database access is included. Copilot
instructions and MCP configuration are not Codex configuration.
