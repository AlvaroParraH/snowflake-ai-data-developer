---
name: snowflake-compute-tagging
description: "Use when designing or reviewing Snowflake cost attribution with warehouse/user object tags and session QUERY_TAG values, including tag governance, IaC, coverage audits, and usage reporting."
---

# Snowflake compute cost attribution

Design a consistent, reviewable way to attribute Snowflake compute usage to
projects, teams, environments, workloads, or business activities. Snowflake
object tags and the `QUERY_TAG` session parameter are complementary mechanisms,
not interchangeable tag layers. This skill provides patterns, not an approved
company-wide taxonomy or permission to change a Snowflake account.

Read existing project instructions, IaC, tag definitions, cost reports,
warehouses, dbt configuration and session setup first. Reuse established
conventions. Confirm the account/environment, accountable owner, cost model,
tag administrator and permitted changes with the project owner before
creating or assigning tags.

## When to use

- Designing cost center, project, owner, environment, or workload attribution.
- Tagging dedicated or shared warehouses and users.
- Adding query tags to applications, dbt, or other workload sessions.
- Reviewing tag coverage or explaining warehouse/query cost reports.

This is about cost attribution. For data classification, masking, row access,
and other data governance controls, use the
[Snowflake data governance skill](../snowflake-data-governance/SKILL.md).
Object tags are metadata, not access controls. For pipeline layer and workload
design, also consult
[medallion architecture](../snowflake-medallion-architecture/SKILL.md) and
[dbt integration](../snowflake-dbt-integration/SKILL.md).

## Snowflake attribution model

Snowflake recommends using object tags to associate resources and users with
cost groupings, and query tags to associate individual queries with a grouping
when a shared application runs on behalf of multiple teams or departments.

| Cost scenario | Attribution pattern | What the measure represents |
|---|---|---|
| Warehouse dedicated to one project or cost center | Apply controlled object tags to the warehouse; analyze warehouse metering with its tag assignments. | Warehouse-level consumption, including idle compute where the selected usage measure includes it. |
| Warehouse shared by users or teams | Tag users where appropriate and attribute query compute by user; alternatively use per-query tags for an application acting on behalf of multiple groups. | Query-attributed warehouse compute, not a complete allocation of every Snowflake cost. |
| Shared application, dbt project, or service identity | Set a stable, non-sensitive `QUERY_TAG` on each relevant session/query; report by query tag using supported query history/attribution sources. | Query-level compute attribution where available; not idle time or all non-warehouse costs. |
| Serverless features or other non-warehouse spend | Use the documented usage/accounting views for that feature and account for its own attribution fields. | Feature-specific usage; warehouse tags or query credits alone do not explain it. |

Do not add together warehouse metering and per-query attribution as though
they were independent costs: query-attributed credits are a component of
warehouse compute, not an additional charge. Reconcile totals with the
appropriate billing/usage source and accounting period.

## Before proposing tag changes

Ask and resolve:

1. Which account(s), environment(s), warehouses, users, applications, or
   workloads are in scope?
2. What decision will the report support: showback, chargeback, budgets, or
   optimization? Which system owns the authoritative project/team/cost-center
   identifiers?
3. Which dimensions are required and which values are approved? Is the cost
   grouping attached to a warehouse, user, or individual query?
4. Are resources dedicated or shared? Will session pooling, scheduled jobs,
   dbt, or application impersonation require query-level tags?
5. Who owns the tag definitions, assignment, change control and cross-account
   distribution? What IaC or provisioning process should maintain them?
6. Which billing/usage sources, retention windows, reporting latency and
   non-warehouse costs must be included?
7. Is the request design-only, a repository/IaC change, an account metadata
   audit, or an approved live mutation?

Present the resolved tag keys, values, target objects, reporting method,
privileges, and IaC files before writing configuration or executing commands.
Do not silently select example names or values from this skill.

## Choose a stable taxonomy

Use the smallest set of dimensions that supports the organization's reporting.
Possible dimensions include:

| Dimension | Example purpose | Example values (illustrative only) |
|---|---|---|
| `COST_CENTER` | Finance ownership or allocation | `analytics`, `marketing` |
| `PROJECT` | A durable workload/project identifier | `orders-platform` |
| `ENVIRONMENT` | Lifecycle boundary | `dev`, `test`, `prod` |
| `OWNER` | Responsible team or service owner | `data-platform` |
| `WORKLOAD` | Workload purpose | `ingestion`, `transformation`, `reporting` |
| `DATA_SOURCE` | External source for ingestion work | `crm`, `billing-api` |

These names and values are proposals, not policy. Follow existing casing and
normalization rules; stable values are essential for grouping. Avoid putting
personal data, credentials, customer identifiers, query contents, or other
sensitive values in tags or query tags. Do not encode volatile details such
as run IDs or timestamps in object tags. If query tags include run-level
context, keep the format bounded and avoid sensitive values.

Snowflake tags are schema-level objects with string values. An object can have
multiple tags; Snowflake documents a maximum of 50 tags per object. Tag
definitions can constrain values with `ALLOWED_VALUES`. Use an owner-managed
tag schema and least-privileged tag administration. Cross-account use may
require an approved replication strategy; do not create organization-level
replication as part of an ordinary project change.

Keep cost tags separate from classification tags even though both use
Snowflake's object-tag feature. Avoid automatic tag propagation for cost
dimensions unless the project explicitly wants and has verified the
inheritance/propagation behavior: inherited or propagated labels can be
incorrect for a different cost owner or workload.

## Object tags for resource attribution

For a warehouse dedicated to one cost center, assign the approved cost tags
directly to that warehouse. If warehouse ownership or usage crosses teams,
do not label all warehouse spend as if it belonged to one team; use user or
query attribution for the shared portion, or separate workloads where that
matches the operational design.

Illustrative pattern only, assuming the tag already exists and all identifiers
and values are approved:

```sql
ALTER WAREHOUSE ANALYTICS_WH
  SET TAG GOVERNANCE.COST_TAGS.COST_CENTER = 'analytics';
```

Apply the tag through the existing IaC/provisioning path where possible so
subsequent deployments do not remove or drift from the assignment. Do not
create a tag schema, tag, warehouse, user, grant, or account-wide default
without explicit approval. Verify exact object-tagging privileges and
ownership requirements against the account's role model.

User tags can support attribution when warehouse queries are executed by
different Snowflake users. They do not, by themselves, distinguish end users
when an application uses one shared service identity. In that case, use
approved per-query tagging or another supported attribution design.

## Query tags for shared applications and workflows

`QUERY_TAG` is a session parameter whose value is attached to query records.
Set it at the narrowest appropriate scope (typically a client/session or
workload target), not as an account-wide default unless the account owner has
approved that policy. A query tag can identify an application, project,
cost center, or workload; it is not a Snowflake object tag and does not
automatically tag the warehouse, database, tables, or user.

Illustrative session-only pattern:

```sql
ALTER SESSION SET QUERY_TAG = 'project=orders-platform;workload=dbt;environment=dev';
```

For application or connection-pool code, set the query tag using the
supported driver/session configuration, and reset or replace it when a
session is reused. Otherwise one request's attribution can leak into another.
For dbt or other adapters, verify the pinned adapter's supported query-tag
configuration before changing profiles or project targets. Preserve other
session parameters and never embed credentials or sensitive row values.

Choose a deterministic format with documented keys and normalized values.
Avoid unbounded JSON or high-cardinality identifiers unless the reporting
system explicitly supports them. Check the Snowflake parameter's current
length/format constraints and the consuming application's behavior.

## Verify coverage and report usage

First inspect current tag definitions and assignments using the appropriate
`SHOW` commands, Information Schema, or Account Usage tag-reference views and
functions. Distinguish direct assignment from inherited or propagated
association where the metadata exposes `APPLY_METHOD`. Remember that
visibility is role-dependent: an empty inventory is not proof that no tags
exist.

For billing/reporting, select the source based on the attribution question:

- `SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY` reports hourly
  warehouse credits. Join warehouse identity to its applicable object-tag
  assignments for warehouse-level attribution. Account Usage latency and
  retention apply; warehouse totals include idle compute.
- `SNOWFLAKE.ACCOUNT_USAGE.QUERY_ATTRIBUTION_HISTORY` attributes warehouse
  compute to queries using weighted resource consumption. It excludes
  warehouse idle time, cloud services, data transfer, storage, serverless
  feature costs, and AI service token costs. Very short queries may not have
  attribution rows; Adaptive Warehouses have a separate metering view.
- Use `QUERY_HISTORY` or other documented sources to retrieve `QUERY_TAG` or
  user metadata and join by stable query identifiers when needed. Confirm
  that the exact columns exist in the chosen view/version before relying on
  them.
- Use feature-specific usage views for serverless or other non-warehouse
  consumption. Do not treat query-attributed warehouse credits as a complete
  Snowflake bill.

Time-bound audit queries and select only needed columns. Account Usage data
has documented latency and retention; same-day totals can be incomplete.
Check role visibility and required grants rather than switching to an
administrative role. Query execution can consume warehouse credits; show the
exact SQL, scope and estimated impact and get approval before running it.

Do not claim successful attribution solely because tags are visible. Verify
that expected workloads set the tags, that the cost source includes their
resource type, that usage aligns over a complete reporting window, and that
untagged/unattributed usage is measured separately.

## Anti-patterns

| Anti-pattern | Why it fails | Better approach |
|---|---|---|
| Treating object tags and `QUERY_TAG` as interchangeable | They label different entities and support different attribution paths. | Select object tags for resources/users and query tags for individual shared-workload queries. |
| Assigning one team's cost center to a shared warehouse | Warehouse-level reporting can misattribute other teams' work and idle time. | Attribute query compute by user/query where suitable, or separate workloads if operationally justified. |
| Claiming query attribution is the complete cost | It excludes idle warehouse, serverless, cloud services, storage, transfer, and AI service costs. | Reconcile all applicable usage categories separately. |
| Using tags as access control | Tags do not grant or restrict privileges by themselves. | Configure RBAC and policies independently. |
| Hardcoding example tag names, values, or databases | Examples are not an organizational taxonomy. | Confirm approved vocabulary and current project conventions. |
| Updating tags manually outside IaC | A later deployment can undo the change or leave environments inconsistent. | Put the assignment in the authoritative provisioning path and review its diff. |
| Setting account-wide query tags for one workload | It can label unrelated sessions and queries. | Scope tags to the application/session/target that owns the workload. |
| Reusing pooled sessions without resetting `QUERY_TAG` | Later queries can inherit another request's attribution. | Set/reset query context when borrowing and returning the session. |
| Including PII, secrets, or unrestricted high-cardinality data | Metadata can be widely visible and degrade reports. | Use approved, stable, non-sensitive dimensions. |
| Assuming inherited/propagated tags represent cost ownership | Metadata propagation may not match the consumer or chargeback owner. | Verify assignments and attribution semantics explicitly. |

## Pre-change checklist

Before applying a tag or query-tag configuration, confirm:

- [ ] Account/environment, resource scope, business owner and approval are known.
- [ ] Taxonomy and value casing are approved and already available or explicitly
      approved for creation.
- [ ] Dedicated versus shared workload behavior is accounted for.
- [ ] Object tags, user tags, and query tags are chosen for the correct entities.
- [ ] The authoritative IaC/provisioning/session configuration is identified.
- [ ] Required privileges, cross-account needs, and tag limits are reviewed.
- [ ] Reporting sources and their latency, retention, exclusions and compute
      costs are understood.
- [ ] Exact changes and rollback plan are reviewed; no account mutation is
      performed without explicit authorization.

## References

- [Snowflake cost attribution](https://docs.snowflake.com/en/user-guide/cost-attributing).
- [Object tagging introduction](https://docs.snowflake.com/en/user-guide/object-tagging/introduction).
- [Working with object tags](https://docs.snowflake.com/en/user-guide/object-tagging/work).
- [QUERY_TAG parameter](https://docs.snowflake.com/en/sql-reference/parameters#label-query-tag).
- [QUERY_ATTRIBUTION_HISTORY](https://docs.snowflake.com/en/sql-reference/account-usage/query_attribution_history).
- [WAREHOUSE_METERING_HISTORY](https://docs.snowflake.com/en/sql-reference/account-usage/warehouse_metering_history).
- [Account Usage views](https://docs.snowflake.com/en/sql-reference/account-usage).

## Related skills

- [Data governance](../snowflake-data-governance/SKILL.md).
- [Medallion architecture](../snowflake-medallion-architecture/SKILL.md).
- [dbt integration](../snowflake-dbt-integration/SKILL.md).
- [Project structure](../snowflake-project-structure/SKILL.md).
