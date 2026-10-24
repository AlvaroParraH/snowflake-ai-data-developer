---
name: snowflake-medallion-architecture
description: "Use when designing Snowflake data pipelines using Bronze, Silver, and Gold as project-defined data responsibilities; covers ingestion provenance, incremental processing, transformations, orchestration, quality, and environment separation without assuming an approved layout."
---

# Snowflake Medallion Architecture

Bronze, Silver, and Gold are useful names for progressively refined data
responsibilities. They are an architectural pattern, not Snowflake object
types or a required Snowflake layout. Define the boundaries, ownership,
retention, access, refresh expectations, and names for each project; inspect
existing conventions first. This skill does not establish a company-wide
environment or layer standard.

Use this guidance when designing a new pipeline or making a meaningful change
to ingestion, refinement, or consumption. Before proposing live DDL or
migrations, confirm object names, source contract, role/access design,
freshness, recovery, and compute/cost expectations with the project owner.

## Layer responsibilities

| Layer | Responsibility | Practical guidance |
|---|---|---|
| **Bronze** | Preserve received source data and enough provenance to explain how it arrived. | Keep source values and load boundaries inspectable. Choose raw columns, `VARIANT` envelopes, or a hybrid layout to suit the source and retention needs. Avoid silently applying business corrections during ingestion. |
| **Silver** | Produce typed, normalized, deduplicated, and quality-checked representations with declared grain and key semantics. | Make parsing and null handling explicit; preserve source lineage and important change semantics. Quarantine or surface invalid records according to the agreed contract rather than quietly discarding them. |
| **Gold** | Provide stable business-facing facts, dimensions, aggregates, or other consumer-oriented products. | Document metric definitions, grain, owners, freshness, and intended consumers. Gold may be a table, view, dynamic table, or other agreed object; the layer name does not dictate the physical object. |

Not every system needs three materialized copies. A view or dynamic table may
be appropriate for a refinement step; a simple source may not need a separate
layer at all. Choose boundaries based on auditability, reuse, latency, access,
and cost rather than copying a diagram mechanically.

## Snowflake facts and architectural choices

- Use database, schema, and object boundaries according to the project's
  ownership, deployment, and access model. Snowflake does not require a
  database-per-environment or schema-per-layer layout.
- Snowflake automatically stores standard table data in micro-partitions.
  Users do not define traditional static partitions. Do not copy
  `PARTITIONED BY` patterns from another platform. Consider a clustering key
  only after query history and pruning evidence show a specific large-table
  workload would benefit; clustering has maintenance and compute cost.
- A standard Snowflake table's primary, unique, and foreign key constraints
  are generally not enforced. Validate data quality in pipeline logic and
  monitoring. `NOT NULL` is enforced on standard tables; hybrid tables have
  different constraints and workload tradeoffs.
- Explicitly choose identifier spelling and quoting. Prefer the project's
  established naming conventions; the accompanying
  [naming-conventions skill](../snowflake-naming-conventions/SKILL.md)
  explains Snowflake case and qualification behavior.
- Snowflake Time Travel, zero-copy cloning, and replication/failover can be
  useful platform capabilities, but they do not by themselves define
  promotion, environment isolation, or recovery policy. Validate retention,
  permissions, costs, and dependency behavior for the account and workload.

## Ingestion and Bronze

Choose ingestion based on how data arrives and required latency:

| Source shape / need | Possible Snowflake approach |
|---|---|
| Existing files, one-time or scheduled batch | Stage plus `COPY INTO` with an explicit file format and load options. |
| Files arriving continuously, available within minutes is sufficient | Snowpipe with a stage and pipe, if cloud notifications and operating requirements fit. |
| Rows/events arriving continuously with lower-latency requirements | Snowpipe Streaming or a supported connector, after evaluating client, ordering, delivery, and operations requirements. |
| SaaS/database source | An available managed connector, Openflow, partner tooling, or a project-managed ingestion service; validate source support and ownership. |
| Non-trivial source-side changes or custom logic | Land first, then use SQL, Snowpark, or an external transformation/orchestration tool as appropriate. |

Snowpipe loads files; it is not a general transformation engine for joins,
aggregations, or filters. File format settings, error handling, schema drift,
replay, and duplicate delivery behavior belong in the ingestion design.

Capture provenance useful to audit and replay the load, as applicable:
source system/object, source file or event identifier, ingestion/load time,
batch or request identifier, and source change/version metadata. Use column
names consistent with the project. Avoid promising metadata that the
ingestion path cannot supply. Do not use a processing timestamp as a
substitute for a source event time or CDC sequence.

Bronze may be append-oriented, but append-only is a project contract, not a
platform guarantee. Avoid replacing prior loads if replay, audit, or late data
requires history. If retention or compaction strategy changes raw data, record
how the original evidence can be recovered.

## Silver transformations and idempotency

Build transformations from explicit columns and explicit type/null rules.
`TRY_TO_*` functions can make parse failures observable; count and route them
according to the agreed data contract. Keep raw values available where they
are needed for reconciliation or reprocessing.

For incremental work, identify the change boundary and failure/retry behavior:

- A source watermark must be based on a reliable source update sequence/time
  and handle ties, late arrivals, and backfills. A processing timestamp alone
  is not a safe cursor for source changes.
- Reprocessing a batch should produce the same intended target state. Use a
  stable business key and deterministic source-row selection. Apply explicit
  `MERGE` column mappings or carefully controlled inserts/updates; avoid
  broad `ALL BY NAME` when source/target schemas can drift.
- Deduplicate the `MERGE` source to at most one applicable row per target key.
  Snowflake can raise an error or produce duplicate inserts when a source has
  multiple matches; source uniqueness is not guaranteed by a standard-table
  key declaration.
- Make deletes, tombstones, and updates explicit for CDC sources. Do not
  interpret an absent row in an incremental batch as a delete unless the
  source contract says the batch is a complete snapshot.
- Record run/batch status, counts, and failure details using the project's
  operational patterns. Ensure retries do not skip data or advance state
  before successful consumption.

Illustrative deduplication shape for a Silver source query:

```sql
SELECT
  source_key,
  source_updated_at,
  source_sequence,
  source_value
FROM <database_name>.<schema_name>.<bronze_table>
QUALIFY ROW_NUMBER() OVER (
  PARTITION BY source_key
  ORDER BY source_updated_at DESC, source_sequence DESC
) = 1;
```

This is deterministic only if the ordering columns break ties reliably and the
chosen row semantics match the source contract. Add an agreed final
tie-breaker when needed; otherwise surface the ambiguity rather than choosing
arbitrarily. Placeholders are illustrative. Validate the exact syntax,
identifiers, and conversion rules against the target schema before use.

## Selecting processing and orchestration patterns

These Snowflake features are alternatives with different semantics, not
interchangeable labels for another platform's streaming or pipeline features:

### Dynamic Tables

Consider a Dynamic Table when the transformation can be expressed as a
supported `SELECT`, Snowflake-managed dependency refresh is useful, and a
target-lag freshness objective is acceptable. Refresh mode (incremental/full/
automatic, as supported by the query) and compute configuration affect cost
and behavior. A target lag is a freshness goal, not a guarantee of an exact
refresh time. Dynamic Tables do not fit every procedural transformation or
strictly timed workflow; check current query support and refresh monitoring.

### Streams and Tasks

Consider a Stream when downstream logic needs row-level changes since an
offset on a supported source object. A Stream is a change-data bookmark, not
an independent copy of source data. Its offset advances when change data is
consumed in a committed DML transaction. If it is not consumed before the
source change history expires, it can become stale; monitor its state and
design a recovery/reinitialization path.

Consider a Task for scheduled or event-triggered SQL/procedure execution, and
task graphs for dependencies or branching that need explicit orchestration.
Tasks need an appropriate compute model (warehouse or supported serverless
configuration), privileges, retry/failure handling, and monitoring.
Stream-triggered tasks can be useful for CDC, but make the consuming DML
transaction and retry semantics explicit.

### Other options

Use ordinary scheduled SQL or an external orchestrator when that fits the
project's deployment and operational controls. Snowpark can suit procedural
or language-specific transformations. Choose one primary ownership model for
each pipeline segment to avoid duplicate schedulers and competing refreshes.

Do not assume Dynamic Tables are Streams and Tasks, or that either is an
equivalent of Spark Structured Streaming, Delta Live Tables, or another
platform-specific feature. Compare supported SQL, latency, state/change
semantics, observability, compute, deployment, and recovery for the actual
workload.

## Gold, quality, and publication

Define each Gold product's grain, metric logic, null treatment, currency/unit,
time zone, and late-data behavior. Keep logic testable and documented. Use a
view for a live logical interface where query-time work is acceptable; use a
materialized or refreshed object when measured reuse/freshness needs justify
the storage and refresh cost. Do not require a daily snapshot or a specific
`dim_`/`fact_` prefix unless the project has adopted that convention.

At each boundary, select checks appropriate to its contract:

- Schema and required-column compatibility.
- Non-null and accepted-value rules.
- Grain/key uniqueness, validated in data for standard tables.
- Referential and join coverage, including expected exceptions.
- Freshness, volume changes, and late-arriving data.
- Reconciliation from source/load batch through Silver and Gold.

Check upstream readiness before publishing downstream results when an empty
or stale input would be misleading. Gate against a meaningful expectation
(for example, current batch completion or a documented minimum), not merely
`COUNT(*) > 0` when the source can legitimately be empty. Fail visibly with
actionable context; do not replace a failed refresh with stale-looking
success.

## Environment separation and promotion

No environment naming scheme is approved here. Treat names such as `dev`,
`test`, and `prod`, and layouts such as separate accounts or databases, as
design proposals until the project owner confirms them.

Separate environments according to the required isolation of data, roles,
integrations, compute, and deployment permissions. Separate Snowflake
accounts can provide stronger administrative and security isolation; multiple
databases in one account may be simpler but share account-level context and
administration. Evaluate the actual threat model and operational needs.

Parameterize environment-specific object references and integration
configuration in deployment tooling rather than editing SQL by hand for each
promotion. Promote reviewed code/configuration through the team's CI/CD
process. Protect production writes with role boundaries and explicit
approvals. Cloning can help with development/test workflows but is not a
replacement for a deployment process or isolation review.

## Design checklist

1. Record source contract, grain, freshness, volume, latency, and recovery
   needs.
2. Confirm project naming and database/schema/environment boundaries; do not
   assume a layer layout from this pattern.
3. Choose the ingestion path that matches source shape and latency; define
   replay and schema-drift behavior.
4. Define Bronze provenance, Silver keys/types/null rules and deterministic
   incremental semantics, and Gold consumer contracts.
5. Select Dynamic Tables, Streams/Tasks, scheduled SQL, or external
   orchestration based on their actual capabilities and operational tradeoffs.
6. Define quality gates, failure visibility, monitoring, and backfill/recovery
   before production promotion.
7. Review compute, storage, refresh frequency, retention, and permissions.
   Do not add static partitions or clustering keys by habit.
8. Confirm proposed object names and any live-object changes with the owner
   before deployment.

## Snowflake references

- [Bulk loading with COPY](https://docs.snowflake.com/en/sql-reference/sql/copy-into-table)
- [Snowpipe](https://docs.snowflake.com/en/user-guide/data-load-snowpipe-intro)
- [Micro-partitions and clustering](https://docs.snowflake.com/en/user-guide/tables-clustering-micropartitions)
- [Constraints overview](https://docs.snowflake.com/en/sql-reference/constraints-overview)
- [MERGE](https://docs.snowflake.com/en/sql-reference/sql/merge)
- [Streams](https://docs.snowflake.com/en/user-guide/streams-intro)
- [Tasks](https://docs.snowflake.com/en/user-guide/tasks-intro)
- [Dynamic Tables](https://docs.snowflake.com/en/user-guide/dynamic-tables/overview)
