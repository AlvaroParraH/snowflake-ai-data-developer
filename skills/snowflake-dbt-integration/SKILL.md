---
name: snowflake-dbt-integration
description: "Build and operate SQL transformations for Snowflake with dbt and dbt-snowflake, including secure profiles, source/model structure, incremental models, tests, snapshots, and environment-aware deployment."
---

# dbt with Snowflake

Use dbt with the `dbt-snowflake` adapter for version-controlled SQL
transformations, dependencies, tests, and documentation on Snowflake. dbt is a
transformation/deployment tool; it does not replace source ingestion,
Snowflake access control, or all operational orchestration. First inspect the
repository's dbt version, adapter, project profile, packages, CI, and existing
model conventions. Do not create a parallel project layout or rename models
without agreement.

The directory and layer examples below are proposals only. Existing project
conventions and approved environment/database/schema design take precedence.

## Version and setup

Pin compatible dbt Core and `dbt-snowflake` versions using the project's
dependency lock mechanism. Confirm the adapter's supported Python/dbt versions
and Snowflake configuration before upgrading or adopting adapter-specific
materializations. Snowflake-specific options and dbt behavior can vary between
adapter versions.

Install and initialize only when setting up a project, using the version and
installation method chosen by that project:

```bash
python -m pip install "dbt-snowflake==<approved_version>"
dbt init <project_name>
```

Do not put credentials, private keys, account secrets, or production values in
the repository. Store local credentials in a protected profile outside the
repo or use the approved secret manager and CI authentication path. Restrict
the dbt role to intended read sources and write targets; avoid granting broad
account or production privileges for convenience.

The following profile is only a structural example; target, role, warehouse,
authentication method, and naming scheme require project configuration:

```yaml
<profile_name>:
  target: dev
  outputs:
    dev:
      type: snowflake
      account: "{{ env_var('SNOWFLAKE_ACCOUNT') }}"
      user: "{{ env_var('SNOWFLAKE_USER') }}"
      role: "{{ env_var('SNOWFLAKE_ROLE') }}"
      warehouse: "{{ env_var('SNOWFLAKE_WAREHOUSE') }}"
      database: "{{ env_var('SNOWFLAKE_DATABASE') }}"
      schema: "{{ env_var('SNOWFLAKE_SCHEMA') }}"
      threads: 4
      authenticator: externalbrowser
```

`externalbrowser` is an interactive authentication example, not a CI default.
Use the authentication method supported by the pinned adapter and approved
for the environment; use a managed identity/key-pair/OAuth method where
appropriate and protect all secrets. Do not commit the rendered profile.
Restrict `threads` and warehouse size to workload needs. Database, schema,
role, and warehouse values shown above are selected by the project, not
required Snowflake names.

Before any actual connection or model execution, ensure the role has only the
privileges required for selected features and objects. dbt may need read
access to source relations and write/create privileges in target schemas;
full refresh, snapshots, seeds, hooks, grants, and adapter features can
require additional privileges. Have a Snowflake administrator review grants
rather than applying a broad generic privilege list.

## Suggested project structure

One possible layout is:

```text
<project_name>/
├── dbt_project.yml
├── models/
│   ├── staging/
│   │   └── <source>/
│   │       ├── _sources.yml
│   │       └── stg_<source>__<entity>.sql
│   ├── intermediate/
│   │   └── <domain>/
│   │       └── int_<entity>__<purpose>.sql
│   └── marts/
│       └── <domain>/
│           ├── dim_<entity>.sql
│           └── fct_<process>.sql
├── tests/
├── macros/
├── snapshots/
└── packages.yml
```

This is an organizational proposal, not a mandated naming or medallion
mapping. In particular, dbt staging models do not replace Bronze ingestion:
they are transformations over declared sources. Choose schemas, model
materializations, and prefixes based on the project's design.

A minimal `dbt_project.yml` shape:

```yaml
name: "<project_name>"
version: "1.0.0"
config-version: 2
profile: "<profile_name>"

model-paths: ["models"]
test-paths: ["tests"]
macro-paths: ["macros"]
snapshot-paths: ["snapshots"]

models:
  <project_name>:
    staging:
      +materialized: view
    intermediate:
      +materialized: view
    marts:
      +materialized: table
```

Choose defaults only after considering source size, query patterns, freshness,
compute cost, grants, and downstream needs. A view is not automatically
cheaper than a table; every query against a view re-evaluates its definition.

## Sources and staging models

Declare external relations as dbt `sources`, include descriptions, and use
`source()` rather than embedding raw relation names in SQL. Use `ref()` for
dbt-managed dependencies so the DAG, environment schemas, and lineage work
correctly:

```yaml
version: 2

sources:
  - name: sales_source
    database: "<source_database>"
    schema: "<source_schema>"
    tables:
      - name: customer_order
        description: "Source order records; confirm grain and load semantics."
```

The names are placeholders. In Snowflake, `database` and `schema` are
separate identifiers; do not put a dotted multi-part schema string in the
`schema` field. Avoid `SELECT *` in published models unless schema drift is
intentionally part of the interface. Explicitly map source columns, types,
null behavior, and provenance.

Example staging model:

```sql
-- models/staging/sales_source/stg_sales_source__customer_order.sql
{{ config(materialized='view') }}

SELECT
    order_id::VARCHAR AS order_id,
    TRY_TO_NUMBER(order_total_text, 18, 2) AS order_total,
    TRY_TO_DATE(order_date_text, 'YYYY-MM-DD') AS order_date,
    source_updated_at,
    source_file_name
FROM {{ source('sales_source', 'customer_order') }}
```

This example assumes those exact columns and a single date format. It
illustrates syntax, not a rule to silently turn invalid values into nulls.
Add tests or an explicit rejected-row strategy for parse failures, and
preserve raw fields when reconciliation or replay requires them.

## Incremental models

Use incremental materialization only when a defined source change boundary
and retry/recovery strategy make it correct. Define `unique_key` only when
the model output is actually unique at that grain; the config does not enforce
uniqueness in Snowflake. Choose the Snowflake adapter's supported incremental
strategy and `on_schema_change` behavior from the pinned version's docs.

Illustrative merge model with an agreed lookback window:

```sql
{{ config(
    materialized='incremental',
    incremental_strategy='merge',
    unique_key='order_id'
) }}

WITH changed_source AS (
    SELECT
        order_id,
        order_total_text,
        order_date_text,
        source_updated_at,
        source_sequence
    FROM {{ source('sales_source', 'customer_order') }}
    {% if is_incremental() %}
    WHERE source_updated_at >= DATEADD(
        day,
        -3,
        COALESCE(
            (SELECT MAX(source_updated_at) FROM {{ this }}),
            '1900-01-01'::TIMESTAMP_NTZ
        )
    )
    {% endif %}
),
one_row_per_key AS (
    SELECT *
    FROM changed_source
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY order_id
        ORDER BY source_updated_at DESC, source_sequence DESC
    ) = 1
)
SELECT
    order_id,
    TRY_TO_NUMBER(order_total_text, 18, 2) AS order_total,
    TRY_TO_DATE(order_date_text, 'YYYY-MM-DD') AS order_date,
    source_updated_at,
    CURRENT_TIMESTAMP() AS transformed_at
FROM one_row_per_key
```

The three-day lookback, column names, timestamp type, source semantics, and
tie-break columns are illustrative, not approved policy. The ordering must
fully and stably break ties; otherwise deduplication is not deterministic.
Choose a watermark that includes corrections and late data, and test null
timestamps, timestamp ties, deletes/tombstones, empty initial targets, and
backfills. A `MERGE` with duplicate source keys can fail or insert duplicate
target rows; do not assume `unique_key` or a declared Snowflake key constraint
will prevent that. Make full-refresh behavior and schema-change policy
explicit; they can replace or alter existing data and interfaces.

For large targets, consider advanced adapter features such as incremental
predicates or clustering only after measuring the query profile and verifying
the exact version-specific behavior. Do not add static partitioning syntax
from other warehouses to Snowflake models.

## Tests, contracts, snapshots, and builds

Use built-in dbt data tests for expected properties. For example:

```yaml
version: 2

models:
  - name: customer_order
    description: "One row per order; confirm currency and date semantics."
    columns:
      - name: order_id
        data_tests:
          - not_null
          - unique
      - name: order_date
        data_tests:
          - not_null
```

`data_tests` is current dbt property syntax; pin dbt and use syntax supported
by that version. Add relationship/domain tests where the contract requires
them. Tests can scan relations and incur warehouse cost; scope tests
deliberately while preserving the property being asserted. A test only protects
the workflow that actually runs it.

dbt model contracts can validate a declared model schema for supported
materializations and adapters. On Snowflake, declared primary/foreign/unique
constraints are not enforced; test those properties with data tests. Contracts
do not apply to all resource types, such as sources and snapshots. Treat
Snowflake-native object metadata and consumer contracts separately.

Use dbt snapshots when an appropriate source change signal and historical
record strategy are defined. Snapshot strategy, `unique_key`, `updated_at`,
target schema, and invalidation behavior are project choices. Test snapshot
keys and timestamps; avoid assuming a transformation timestamp represents
source change time.

Typical local workflow, run only after configuring an authorized target:

```bash
dbt deps
dbt debug
dbt parse
dbt build --select <model_or_selector>
dbt docs generate
```

`dbt debug` verifies project/profile connectivity; `dbt build` can create or
change Snowflake objects. Inspect the rendered target and selection before
execution, and use a safe development target first. CI should test compilation
and selected models with the project's approved credentials and warehouse.
Protect production deployment with reviewed configuration, role boundaries,
and explicit promotion controls.

## Dynamic Tables and other adapter-specific features

`dbt-snowflake` supports Snowflake-specific capabilities that depend on the
adapter version. Dynamic Table materialization options and scheduler defaults
are version-sensitive and differ from native Snowflake defaults. Do not copy
`target_lag`, scheduler, refresh mode, clustering, or warehouse settings from
an unrelated project. Confirm the pinned adapter's configuration reference
and Snowflake query support before using Dynamic Tables. Choose either
Snowflake-managed refresh or dbt/external orchestration intentionally; avoid
competing schedulers.

## Operational checklist

1. Inspect installed dbt/adapter versions, project profile, source declarations,
   model conventions, package lock, and CI behavior.
2. Confirm target account/database/schema, role, warehouse, and authentication
   flow without exposing secrets.
3. Declare sources and use `source()`/`ref()`; document model grain and
   semantics.
4. Make parsing, null handling, incremental filters, key deduplication, and
   deletes/replays explicit.
5. Add tests and contract metadata for the properties consumers rely on.
6. Check adapter-specific materialization, grant, schema-change, and
   full-refresh implications.
7. Compile and test against a safe target before reviewed production
   promotion; account for scan/warehouse cost.

## References

- [`dbt-snowflake` connection configuration](https://docs.getdbt.com/docs/core/connect-data-platform/snowflake-setup)
- [Snowflake adapter configurations](https://docs.getdbt.com/reference/resource-configs/snowflake-configs)
- [dbt incremental models](https://docs.getdbt.com/docs/build/incremental-models)
- [dbt data tests](https://docs.getdbt.com/reference/resource-properties/data-tests)
- [dbt model contracts](https://docs.getdbt.com/docs/mesh/govern/model-contracts)
- [Snowflake MERGE](https://docs.snowflake.com/en/sql-reference/sql/merge)
