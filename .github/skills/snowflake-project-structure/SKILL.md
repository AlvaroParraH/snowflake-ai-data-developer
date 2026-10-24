---
name: snowflake-project-structure
description: "Use when creating, scaffolding, reviewing, or maintaining a Snowflake project layout, Python dependency management with uv, Bronze ingestion, Silver/Gold dbt models, or Airflow DAG locations. Preserve the agreed pipelines/ layout without moving existing projects automatically."
---

# Snowflake project structure

## Scope and precedence

Use this layout for new Snowflake pipeline projects adopting this kit and for
new files in projects that already follow it. It is the agreed project
convention, not a Snowflake/dbt requirement or an organization-wide policy.
This kit itself is a skill collection: do not reorganize its `.github/skills/`,
`.github/`, or documentation into a pipeline application.

Inspect the target repository first. Preserve an existing layout unless the
owner explicitly approves a migration. Do not move files, rename models,
create empty placeholder directories, install dependencies, connect to
Snowflake, or deploy Airflow merely because this skill was loaded.

## Canonical layout

The kit installer does not create pipeline folders. When explicitly requested,
use [the initialization prompt](../../prompts/snowflake-init.prompt.md) or the
installed [local script](../../../scripts/init_project.py) to preview and create
the core pipeline directories only. This does not generate the illustrative
application files below or migrate an existing layout.

```text
snowflake-data-project/
|-- README.md
|-- .env.example
|-- .gitignore
|-- pyproject.toml
|-- pipelines/
|   |-- ingestion/
|   |   `-- bronze/
|   |       |-- api_extractor.py
|   |       `-- load_files.sql
|   |-- dbt/
|   |   |-- dbt_project.yml
|   |   |-- packages.yml
|   |   |-- models/
|   |   |   |-- silver/
|   |   |   |   |-- staging/
|   |   |   |   |   `-- sales/
|   |   |   |   |       |-- _sources.yml
|   |   |   |   |       |-- _models.yml
|   |   |   |   |       `-- stg_sales__orders.sql
|   |   |   |   `-- intermediate/
|   |   |   |       `-- sales/
|   |   |   |           |-- _models.yml
|   |   |   |           `-- int_orders__enriched.sql
|   |   |   `-- gold/
|   |   |       `-- marts/
|   |   |           `-- sales/
|   |   |               |-- _models.yml
|   |   |               |-- dim_customers.sql
|   |   |               `-- fct_sales.sql
|   |   |-- tests/
|   |   |-- macros/
|   |   `-- snapshots/
|   `-- orchestration/
|       `-- airflow/
|           |-- dags/
|           |   `-- sales_pipeline.py
|           `-- requirements.txt
|-- tests/
|   |-- test_ingestion.py
|   `-- test_sales_dag.py
|-- infra/
`-- .github/
    `-- workflows/
        |-- ci.yml
        `-- deploy.yml
```

The sales domain, filenames and prefixes are examples; follow approved naming
conventions. Create only files needed for the requested implementation.
`packages.yml`, snapshots, macros, infrastructure and workflows are included
when needed, not mandatory empty scaffolding.

For new Python pipeline components, use `uv` with `pyproject.toml` and commit
`uv.lock`:

```bash
uv init --python <project-python-version>  # only for a new Python project
uv add <package>
uv lock
uv sync
uv run <project-command>
```

Use `uv run` for project Python commands so they execute in the locked project
environment. Onboarding or creating a project can use `uv init`; use the
existing project configuration and do not reinitialize an existing project.
Pin the Python version and dependency ranges according to the project.
Generate any platform-required `requirements.txt` from the selected locked
dependencies; do not maintain a separate, conflicting dependency list.

Existing projects retain their established dependency manager unless the
owner approves a migration. Do not add uv or rewrite dependency files just
because this skill was loaded. uv is not needed to read this skill kit.

## Placement rules

| Responsibility | Location | Boundary |
|---|---|---|
| Extract and load received source data | `pipelines/ingestion/bronze/` | Preserve provenance, replay and retry semantics; raw data lives in Snowflake, not this folder. |
| Source declarations and source-aligned normalization | `pipelines/dbt/models/silver/staging/<domain>/` | Declare Bronze relations with `source()`; staging is not Bronze ingestion. |
| Reusable joins, deduplication and refinement | `pipelines/dbt/models/silver/intermediate/<domain>/` | Use `ref()` for dbt-managed dependencies. |
| Consumer-facing facts, dimensions and metrics | `pipelines/dbt/models/gold/marts/<domain>/` | Define grain and consumer expectations. |
| dbt data tests and reusable SQL | `pipelines/dbt/tests/` and `pipelines/dbt/macros/` | Keep model properties and generic test declarations alongside models in YAML. |
| Schedules and task dependencies | `pipelines/orchestration/airflow/dags/` | DAGs coordinate ingestion and dbt; do not duplicate their business logic. |
| Python and DAG validation | Root `tests/` | Keep application tests separate from dbt SQL tests. |
| Approved resources, permissions and compute | `infra/` | Do not duplicate resource ownership in ingestion scripts. |
| Validation and deployment automation | `.github/workflows/` | Use environment boundaries and deployment approvals. |

Bronze, Silver and Gold folders organize code responsibilities, not physical
data. They do not prescribe database/schema names or require three stored
copies. The expected flow is source -> Bronze -> Silver staging ->
Silver intermediate -> Gold marts.

## dbt path configuration

The dbt project root is `pipelines/dbt/`. Paths in `dbt_project.yml` remain
relative to that root. For this layout, nest model configuration under the
actual layer directories, rather than leaving staging and marts directly
under the project key:

```yaml
name: sales_analytics
version: "1.0.0"
config-version: 2
profile: sales_analytics
model-paths: ["models"]
test-paths: ["tests"]
macro-paths: ["macros"]
snapshot-paths: ["snapshots"]

models:
  sales_analytics:
    silver:
      staging:
        +materialized: view
      intermediate:
        +materialized: view
    gold:
      marts:
        +materialized: table
```

Replace `sales_analytics` with the project's actual name/profile; the model
configuration key must match `name`. Materializations above are illustrative,
not fixed policy. Select them for workload, freshness, grants and cost.
Use `--project-dir pipelines/dbt` from the repository root or run from the
dbt directory. Check selectors and CI paths when nesting models under layers.
Keep rendered profiles and credentials outside source control.

## Airflow integration

The DAG source directory is `pipelines/orchestration/airflow/dags/`.
Configure the deployed Airflow runtime's `dags_folder`, or deploy/mount that
directory to its configured DAG location, such as `/opt/airflow/dags` in
Docker. Repository paths and worker runtime paths are not interchangeable.

Deploy the ingestion package/scripts, dbt project, compatible dependencies
and approved authentication to the actual execution workers or task
containers as well. DAG deployment alone does not make those available.
Pin providers and runtime dependencies compatibly with the project's chosen
Airflow version. Use the project's uv lock as the dependency source of truth;
if the Airflow runtime expects `requirements.txt`, generate it from the
compatible locked set, including any required Airflow constraints.

Keep extraction, warehouse connections and dbt execution out of DAG
parse/import time. A typical DAG coordinates:

```text
Load Bronze -> Check readiness -> Build/test Silver -> Build/test Gold
```

Ensure the chosen selection includes intended models/tests and fails visibly
on errors. Define retries and backfills without duplicate loads; prevent
competing schedulers from owning the same segment. Do not add a second DAG
for backfills unless the project's recovery design needs one.

## Workflow

1. Inspect the target tree, instructions, manifests, dbt configuration,
   DAG deployment and CI paths. Determine whether this layout is adopted.
2. For new work, map each requested file to the placement rules. For a
   conflicting existing layout, present an explicit old-to-new path mapping
   and obtain migration approval before moving anything.
3. Implement only the requested artifacts. If paths change, update imports,
   package configuration, dbt paths/selectors, DAG references, worker mounts,
   CI working directories, tests and documentation together.
4. Validate local links/configuration and run relevant existing tests,
   including DAG import/dependency checks where Airflow is available.
   Validate the configured layer paths and matching dbt project key.
   Warehouse-backed builds or connection checks require separate
   authorization; do not run them for a layout-only change.
5. Report files created/moved, checks performed, missing validation
   dependencies and intentional exceptions. Never claim a diagram or
   scaffold is a deployed, runnable pipeline.

## Related guidance

- [Medallion architecture](../snowflake-medallion-architecture/SKILL.md):
  layer semantics, ingestion and orchestration choices.
- [dbt integration](../snowflake-dbt-integration/SKILL.md):
  adapter configuration, model behavior and safe builds.
- [Naming conventions](../snowflake-naming-conventions/SKILL.md):
  identifier and naming guidance.
- [Visual layout](../../../docs/references/snowflake-medallion-dbt-project-structure.svg):
  a companion diagram, not a separate source of folder policy.

When changing this convention, update this skill, the diagram and the README
together. The dbt skill's generic layout is compatible guidance; this skill
supplies the adopted Silver/Gold nesting for projects using this convention.
