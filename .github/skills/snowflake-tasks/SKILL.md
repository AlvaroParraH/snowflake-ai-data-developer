---
name: snowflake-tasks
description: "Use when designing or operating Snowflake Tasks and task graphs for scheduled or stream-triggered SQL and procedure workflows, including dependencies, compute, retries, notifications, monitoring, and orchestration choices."
---

# Snowflake Tasks and task graphs

Snowflake Tasks are Snowflake-native scheduled or triggered units of work.
Related Tasks can form a directed acyclic graph (DAG), with dependencies,
parallel branches, conditional execution, and an optional finalizer. This
guidance covers task behavior and operations, not a project-wide scheduling
standard or permission to create, resume, or execute account objects.

Inspect the repository's dbt, SQL, stored procedure, task, deployment, and
external orchestration patterns first. Follow current project conventions and
confirm the intended account, environment, owner role, warehouse/serverless
choice, schedule, alert path, and cost limits before proposing live changes.

## When to use

- Designing a Snowflake Task or dependency graph for SQL/procedure execution.
- Choosing between scheduled tasks, stream-triggered tasks, Dynamic Tables,
  dbt, and an external orchestrator.
- Configuring task compute, dependencies, retries, timeouts, overlap, or
  notifications.
- Investigating task history, failures, schedule gaps, and compute use.

Use the [medallion architecture skill](../snowflake-medallion-architecture/SKILL.md)
for layer responsibilities, CDC, and transformation design; use
[dbt integration](../snowflake-dbt-integration/SKILL.md) for dbt model
configuration and builds; use
[compute tagging](../snowflake-compute-tagging/SKILL.md) for cost attribution.

## Choose the right orchestration primitive

| Need | Consider | Important boundary |
|---|---|---|
| Supported SQL or stored procedure on a schedule | Standalone Task | Created suspended; explicit resume is required for ongoing schedule execution. |
| Ordered SQL/procedure workflow with fan-out/fan-in | Task graph | Root controls the schedule; children use predecessor dependencies; all graph tasks share a schema and owner role. |
| Process stream changes without polling | Stream-triggered Task | Change tracking/stream freshness and transactional consumption must be handled. |
| Declarative SELECT transformation with Snowflake-managed refresh | Dynamic Table | Target lag is a freshness objective, not a strict schedule; it is not a procedural task graph. |
| dbt project/model execution | Existing dbt and CI/orchestrator flow | Do not assume an arbitrary dbt command runs natively inside a Task. Use the approved external runtime where required. |
| Cross-system dependencies, Python application workflows, complex backfills | Existing external orchestrator | Keep one clear owner for retries, scheduling, state and alerts; avoid duplicate schedules. |

Tasks can execute supported SQL statements and stored procedures in supported
languages. They are not a general-purpose remote job runner: do not assume a
Task can launch arbitrary local scripts, access a developer's filesystem, or
replace an external runtime.

## Task graph shape

Create a root Task and child Tasks linked by `AFTER`. A root defines when a
graph runs. Child tasks with the same predecessor can run in parallel; a task
with multiple predecessors waits for the required predecessor outcomes.
Dependencies must form an acyclic graph.

Illustrative SQL shape only; identifiers, role, schedule, and SQL are
placeholders and must be reviewed for the target project:

```sql
CREATE TASK ANALYTICS_DB.ORCHESTRATION.ORDERS_ROOT
  WAREHOUSE = ETL_WH
  SCHEDULE = 'USING CRON 15 5 * * * UTC'
  USER_TASK_TIMEOUT_MS = 3600000
  SUSPEND_TASK_AFTER_NUM_FAILURES = 3
  AS CALL ANALYTICS_DB.ORCHESTRATION.LOAD_ORDERS();

CREATE TASK ANALYTICS_DB.ORCHESTRATION.ORDERS_SILVER
  AFTER ANALYTICS_DB.ORCHESTRATION.ORDERS_ROOT
  WAREHOUSE = ETL_WH
  AS CALL ANALYTICS_DB.ORCHESTRATION.BUILD_ORDERS_SILVER();

CREATE TASK ANALYTICS_DB.ORCHESTRATION.ORDERS_CUSTOMERS_SILVER
  AFTER ANALYTICS_DB.ORCHESTRATION.ORDERS_ROOT
  WAREHOUSE = ETL_WH
  AS CALL ANALYTICS_DB.ORCHESTRATION.BUILD_CUSTOMERS_SILVER();

CREATE TASK ANALYTICS_DB.ORCHESTRATION.ORDERS_GOLD
  AFTER ANALYTICS_DB.ORCHESTRATION.ORDERS_SILVER,
        ANALYTICS_DB.ORCHESTRATION.ORDERS_CUSTOMERS_SILVER
  WAREHOUSE = ETL_WH
  AS CALL ANALYTICS_DB.ORCHESTRATION.BUILD_ORDERS_GOLD();
```

The example graph is `ORDERS_ROOT` → two parallel Silver tasks → `ORDERS_GOLD`.
Do not execute illustrative DDL as part of reading this skill.

Key graph constraints and operating behavior:

- A graph is a DAG with one root; the root carries the schedule or trigger.
  A graph supports up to 1,000 tasks; each task can have up to 100 parents
  and 100 children.
- Tasks in a graph must be in the same schema and owned by the same role.
- Parallel children on a user-managed warehouse compete for its shared
  capacity. Estimate concurrency and queueing before selecting graph width.
- A finalizer can run cleanup or send an outcome notification after other
  graph tasks finish; it has no child tasks and one root can have one
  finalizer.
- Task graph behavior is not identical to a standalone Task's behavior.
  Confirm root/child state and graph-level settings before modifying it.

## Schedule, event trigger, and activation

Use a supported interval schedule or `USING CRON` with an explicit time zone
when local-time semantics matter. Check daylight-saving behavior, missed-run
expectations, source availability, and the required freshness objective.

For change-driven processing, a triggered Task can use
`WHEN SYSTEM$STREAM_HAS_DATA('<stream>')`. Triggered tasks avoid repeatedly
polling a quiet stream, but:

- A triggered task starts suspended and must be resumed to monitor changes.
- Snowflake documents a default minimum trigger interval; confirm current
  account/task settings rather than assuming immediate per-event execution.
- Only supported source types can trigger a Task; check current product
  documentation for the exact source and stream type.
- Consume stream changes transactionally and monitor staleness. A stream can
  become stale if its change history expires before consumption.
- A scheduled Task can also include a `WHEN` condition to check for work on
  its schedule; do not confuse this with an event-driven trigger.

New Tasks are suspended. `EXECUTE TASK` starts one manual graph run; it does
not enable future scheduled runs. Resuming a root or its dependents activates
recurring/triggered behavior and is an operational change. Never execute,
resume, suspend, or alter a live Task without explicit approval for the exact
target and action. For a graph, confirm child and finalizer states as well as
the root before activation.

## Compute selection and cost controls

Choose one supported compute model per Task:

| Model | Configuration | Tradeoffs |
|---|---|---|
| Serverless Task | No `WAREHOUSE`; Snowflake manages compute. The task role needs `EXECUTE MANAGED TASK`. | Convenient and Snowflake-sized; set and review supported minimum/maximum statement-size controls and target completion interval where applicable. |
| User-managed warehouse | Set `WAREHOUSE` explicitly. | Warehouse size, queueing, multi-cluster behavior and auto-suspend are controlled through the warehouse; concurrent graph children share its capacity. |

Serverless compute has supported size limits; if a workload needs compute
beyond those limits or specific warehouse controls, evaluate a user-managed
warehouse. Cost/performance settings and task feature availability can vary;
check current Snowflake docs and account entitlements.

Before production scheduling, estimate frequency × expected runtime ×
compute model, include retries and graph fan-out, and consider idle warehouse
cost when the warehouse is dedicated. Bound expensive work with a sensible
`USER_TASK_TIMEOUT_MS` and failure-suspension policy. A timeout is not a fix
for inefficient SQL; investigate query shape and measured runtime before
raising limits or warehouse size. Use
[Snowflake compute tagging](../snowflake-compute-tagging/SKILL.md) to design
warehouse/user/query cost attribution; Task run history alone is not a full
cost ledger.

## Dependencies, branching, and idempotency

Keep each Task body focused on one operational step. Express dependencies in
the graph instead of hiding a long orchestration sequence inside one
procedure, unless the procedure is the project's intentional unit of
transaction and recovery.

- Use sibling tasks for independent work and a downstream task with all
  required predecessors as the fan-in gate.
- Use supported `WHEN` expressions and predecessor return values only when
  conditional graph behavior is needed; confirm expression/function support
  and clearly define what happens when a condition is false.
- Keep cross-task state small and explicit. Prefer durable, auditable tables
  for manifests or larger payloads; do not put secret or business-row payloads
  into metadata or task return values.
- Make retries safe. Design SQL/procedures to be idempotent for a stable batch
  or run key; deduplicate source changes and make partial-write behavior
  explicit before enabling retries.
- Set overlap behavior intentionally. The default graph policy prevents
  overlapping graph runs; alternate policies can allow concurrent runs and
  require the pipeline to tolerate concurrent roots/children and isolated
  run state. Do not allow overlap for mutable shared targets without an
  explicit concurrency-safety design.

Do not assume a failed graph can be repaired with the same semantics as
re-running the entire pipeline. Snowflake supports retrying the latest graph
from the last failed Task and retrying older graph run groups; verify the
selected run and downstream side effects before requesting a retry. Automatic
graph retries can rerun graph work and are not a substitute for idempotency.
The root's `TASK_AUTO_RETRY_ATTEMPTS` and failure-suspension settings should
be reviewed together.

## Error handling, alerts, and events

Configure task timeout, automatic retry, and suspension-after-failure
explicitly for production workloads where defaults do not match the
operational contract. Retrying a non-idempotent operation can duplicate
effects. A root failure-suspension setting applies to graph failures; review
the graph-level retry behavior as well.

Snowflake supports error and success notifications through configured cloud
notification integrations. These require administrator-owned integration
setup, permissions and same-cloud compatibility. Notification delivery can
be at-least-once, so consumers must tolerate duplicates. Do not create an
integration or send a test notification without approval.

For task event-based alerting, configure the active event table and suitable
`LOG_EVENT_LEVEL`. Capturing both success and failure events (for example,
`INFO`) is necessary if an alert computes an error rate; recording only
failures overstates that rate. Event-table and alert owners need the required
visibility. Avoid account-wide logging changes just to monitor one pipeline.

## Monitor and troubleshoot runs

Use the narrowest appropriate surface:

- `INFORMATION_SCHEMA.TASK_HISTORY` table function for a bounded operational
  window; filter with task/database/schema arguments where available. Its
  default result limit is 100, and scheduled future entries can affect which
  rows appear; explicitly bound the scheduled-time range to inspect completed
  runs.
- `SNOWFLAKE.ACCOUNT_USAGE.TASK_HISTORY` for longer history and reporting.
  Snowflake documents up to 45 minutes latency and up to 365 days of history.
- Snowsight task graph view for dependencies, current state, and run details.
- Event table and configured notification history for event/alert diagnosis.

Task history visibility depends on role privileges; missing rows do not prove
that a Task does not exist or did not run. Account Usage can be delayed.
Time-bound queries and select only needed columns; monitoring queries can
consume warehouse credits. Do not elevate to an admin role to work around
visibility.

Before retrying a run, capture the root, graph run group, failed Task, error,
completed predecessors, target batch/window, and whether any side effects
already occurred. Prefer retrying the failed graph run when semantics are
safe. If the operation is not idempotent or current state is uncertain, stop
and reconcile before reprocessing.

## Anti-patterns

| Anti-pattern | Risk | Better practice |
|---|---|---|
| Treating Tasks as arbitrary compute jobs | Tasks execute supported SQL/procedures; local Python or cross-system orchestration may need another runtime. | Keep execution in the right runtime and use Tasks for Snowflake-native steps. |
| Using a Task for a declarative SELECT refresh without comparing Dynamic Tables | Adds manual scheduling/operational state unnecessarily. | Evaluate Dynamic Tables for supported declarative transformations. |
| Scheduling the same work in a Task, dbt scheduler and Airflow | Duplicate runs, writes and compute cost. | Assign one scheduler as owner for each pipeline segment. |
| Resuming the root without checking child state | A graph may skip suspended children or run an incomplete path. | Review/enable the intended graph dependents deliberately. |
| Retrying non-idempotent work | Duplicate inserts or external side effects. | Design idempotency and reconcile partial effects before retries. |
| Allowing graph overlap without isolation | Concurrent runs can race on shared state and targets. | Keep default no-overlap or document concurrency safety before changing policy. |
| Relying on a task schedule as exact wall-clock SLA | Queues, prior runs and platform scheduling may affect start time. | Define freshness/SLA tolerance and monitor actual completion. |
| Treating task history as full cost accounting | It omits other cost categories and can be delayed or permission-limited. | Reconcile usage views and attribution tags for the full cost model. |
| Broad account grants for task operation | Expands blast radius unnecessarily. | Use a purpose-built owner role with only required privileges, including managed-task privilege only when serverless is selected. |

## Pre-deploy checklist

- [ ] Task bodies, root/dependency graph, and finalizer (if needed) are reviewed.
- [ ] Schedule/time zone or stream trigger matches the source freshness contract.
- [ ] Compute model, warehouse, serverless privileges, concurrency and estimated
      cost are understood.
- [ ] Timeout, retries, idempotency, failure suspension and overlap behavior
      are intentional.
- [ ] Owner role can execute each step and has only required privileges.
- [ ] Events, alerts, notification integrations and alert ownership are agreed.
- [ ] Deployment/IaC is the source of truth; no unmanaged live edits are planned.
- [ ] Exact account, environment, task names and activation/deployment actions
      have explicit approval.
- [ ] Local validation and any approved execution plan are documented.

## References

- [Introduction to Tasks](https://docs.snowflake.com/en/user-guide/tasks-intro).
- [Task graphs](https://docs.snowflake.com/en/user-guide/tasks-graphs).
- [Triggered Tasks](https://docs.snowflake.com/en/user-guide/tasks-triggered).
- [Task alerts and notifications](https://docs.snowflake.com/en/user-guide/tasks-errors).
- [Task execution events](https://docs.snowflake.com/en/user-guide/tasks-events).
- [CREATE TASK](https://docs.snowflake.com/en/sql-reference/sql/create-task).
- [EXECUTE TASK](https://docs.snowflake.com/en/sql-reference/sql/execute-task).
- [TASK_HISTORY table function](https://docs.snowflake.com/en/sql-reference/functions/task_history).
- [TASK_HISTORY Account Usage view](https://docs.snowflake.com/en/sql-reference/account-usage/task_history).

## Related skills

- [Medallion architecture](../snowflake-medallion-architecture/SKILL.md).
- [dbt integration](../snowflake-dbt-integration/SKILL.md).
- [Compute tagging](../snowflake-compute-tagging/SKILL.md).
- [Data governance](../snowflake-data-governance/SKILL.md).
- [Project structure](../snowflake-project-structure/SKILL.md).
