---
name: snowflake-data-governance
description: "Use when designing or reviewing Snowflake data governance: database/schema ownership, RBAC and database roles, managed access schemas, least-privilege grants, classification tags, masking and row access policies, stages/storage integrations, audit history, lineage, and governed sharing."
---

# Snowflake data governance

Govern data assets using Snowflake-native objects and semantics. This
guidance does not establish corporate naming, classification, retention,
or access policy.

## When to use

- Designing database/schema boundaries and ownership.
- Creating or reviewing roles, grants, future grants and managed access.
- Classifying sensitive data and designing masking or row access policies.
- Governing file access, integrations, sharing and external table storage.
- Investigating asset ownership, access, policy coverage or lineage.

Read existing project instructions and governance definitions first. Confirm
the account, environment, approved names, owners, intended consumers and
edition/feature availability. Dynamic Data Masking, row access policies,
Access History and some tagging capabilities have edition or feature
requirements; consult current documentation before promising availability.

This is local guidance, not permission to connect or mutate an account.
Examples below are review-only, independently scoped patterns, not a script
to execute in sequence. Identifiers such as `ANALYTICS_DEV`, `SALES` and
`GOVERNANCE` are illustrative and must be replaced with approved names.
Do not use `ACCOUNTADMIN` as an application or pipeline runtime role.

## Governance responsibilities

| Responsibility | Snowflake approach | Important consideration |
|---|---|---|
| Catalog/schema organization | Account, database, schema and object boundaries | No required database-per-environment or schema-per-layer mapping. |
| Group-based access | Identity-provider provisioning plus account/database roles | Roles carry privileges; an IdP group is not a Snowflake SQL grantee by itself. |
| Central grant administration | Managed access schemas and controlled role hierarchy | Schema owners or roles with `MANAGE GRANTS` manage object grants in managed access schemas. |
| Asset metadata and classification | Comments, object tags and approved classification workflows | A comment or tag is not an access restriction by itself. |
| Column and row protection | Masking policies / row access policies | Use policy objects and test Snowflake execution-context semantics. |
| Governed files | Named internal/external stages and storage integrations | A stage provides file access, not a general POSIX filesystem. |
| Audit and lineage | Account Usage, Information Schema and Snowsight lineage | Coverage, visibility, latency and retention differ by view and operation. |
| Cross-platform consumption | Secure Data Sharing, listings, or an evaluated Iceberg design | Choose supported interfaces and validate consumer access and policy behavior. |
| Cloud-service credentials | Connector-specific authentication, integrations and secrets | Storage integrations authorize supported cloud storage access, not arbitrary streaming APIs. |

## 1. Ownership and environment boundaries

Record each asset's domain, accountable team, technical owner role, purpose,
classification, retention and approved consumer interface. Business ownership
in comments/tags is distinct from Snowflake's `OWNERSHIP` privilege.

Choose accounts, databases and schemas according to administrative isolation,
data residency, lifecycle, deployment and recovery needs. Do not infer these
from Bronze/Silver/Gold folders. Keep development roles and integrations from
writing production targets.

Consider a managed access schema when grant administration should be
centralized. An approved provisioning role can create a new one:

```sql
CREATE SCHEMA ANALYTICS_DEV.SALES
  WITH MANAGED ACCESS
  COMMENT = 'Sales data products; accountable team: sales-data';
```

This assumes an existing database and the necessary creation privileges.
Inspect any existing schema instead of replacing it or assuming an
`IF NOT EXISTS` clause would reconcile its configuration. In managed access
schemas, object owners cannot independently grant access to their objects;
the schema owner or a role with `MANAGE GRANTS` controls those grants.
Keep global grant administration separate from ordinary pipeline execution.

## 2. Role design and explicit grants

Prefer role-based access, with user/service identity membership provisioned
through the approved identity lifecycle. Avoid direct per-user object grants
as the project convention; Snowflake also supports user-based access control,
so this is a governance choice, not a claim that direct grants are impossible.

- Use database roles for privilege bundles scoped to one database.
- Grant database roles to account roles for session use. Database roles cannot
  be activated directly and cannot hold warehouse privileges.
- Grant warehouse usage and cross-database/account privileges through
  appropriate account roles.
- Separate readers, pipeline writers/deployers, policy administrators and
  grant administrators. Grant only operations the actual workload needs.
- Review inherited privileges, active secondary roles and `PUBLIC` access.
  Do not attach a sensitive entitlement role beneath a broad role casually.

Illustrative reader setup, assuming the schema, warehouse and account role
already exist and the grant administrator is authorized:

```sql
CREATE DATABASE ROLE ANALYTICS_DEV.SALES_READER;
GRANT USAGE ON DATABASE ANALYTICS_DEV
  TO DATABASE ROLE ANALYTICS_DEV.SALES_READER;
GRANT USAGE ON SCHEMA ANALYTICS_DEV.SALES
  TO DATABASE ROLE ANALYTICS_DEV.SALES_READER;
GRANT SELECT ON TABLE ANALYTICS_DEV.SALES.FCT_SALES
  TO DATABASE ROLE ANALYTICS_DEV.SALES_READER;
GRANT DATABASE ROLE ANALYTICS_DEV.SALES_READER
  TO ROLE SALES_ANALYST;
GRANT USAGE ON WAREHOUSE ANALYTICS_WH TO ROLE SALES_ANALYST;
```

Object access needs the relevant parent database/schema privileges as well
as the object privilege. Warehouse-backed queries also need compute access.
Table grants do not automatically grant access to all views, stages, tasks
or policies, and do not bypass masking or row policies.

Writer/deployment permissions must reflect materializations and lifecycle:
creating a table, modifying its rows, managing a task and replacing a model
are different operations. Do not grant `ALL PRIVILEGES`, `OWNERSHIP`,
`MANAGE GRANTS` or grant options as a generic fix for permission errors.

### Existing objects and future grants

Prefer object-specific grants when only selected products are approved.
If an entire schema is explicitly approved for read access, these are
separate decisions:

```sql
GRANT SELECT ON ALL TABLES IN SCHEMA ANALYTICS_DEV.SALES
  TO DATABASE ROLE ANALYTICS_DEV.SALES_READER;
GRANT SELECT ON FUTURE TABLES IN SCHEMA ANALYTICS_DEV.SALES
  TO DATABASE ROLE ANALYTICS_DEV.SALES_READER;
```

The first covers current tables; the second covers new tables, not existing
ones. Views and other object types require their own applicable grants.
Schema-level future grants override database-level future grants for the
same object type, even when granted to different roles. Review both scopes.
Revoking a future grant does not remove privileges already granted to
existing objects. Cloning, replacement and ownership transfer require an
explicit grant review; do not assume permissions survive as intended.

## 3. Documentation, classification and tags

Document table purpose/grain, producer, consumers and important column
semantics. Do not store sensitive values, credentials or personal identifiers
in comments, tags, object names or query text.

Agree on classification vocabulary and stewardship before applying tags.
For example, an administrator could define a classification tag in an
existing governance schema and apply it to an existing column:

```sql
CREATE TAG ANALYTICS_DEV.GOVERNANCE.DATA_CLASSIFICATION
  ALLOWED_VALUES 'public', 'internal', 'confidential', 'restricted';
ALTER TABLE ANALYTICS_DEV.SALES.CUSTOMERS
  MODIFY COLUMN EMAIL
  SET TAG ANALYTICS_DEV.GOVERNANCE.DATA_CLASSIFICATION = 'restricted';
```

These values are proposals, not an approved taxonomy. Confirm creation and
tag-assignment privileges and inspect inherited/propagated tags. Do not assume
tags propagate through every transformation automatically.

A classification tag alone does not mask a column. Tag-based masking needs
an explicitly associated, type-compatible masking policy. Audit policy
associations as well as tag coverage. Human-review generated descriptions
and classification results; avoid exposing sample PII to unapproved AI tools.

## 4. Column-level masking

Separate policy authoring, policy application and data consumption. Confirm
`CREATE MASKING POLICY`, the appropriate policy `APPLY`/ownership permissions,
parent access and table-alter authority according to the chosen delegation
model; do not distribute global policy-administration rights to all writers.

This example assumes an existing account role `PII_READER`, an existing
VARCHAR email column and an approved governance schema:

```sql
CREATE MASKING POLICY ANALYTICS_DEV.GOVERNANCE.MASK_EMAIL
  AS (VAL VARCHAR) RETURNS VARCHAR ->
    CASE
      WHEN IS_ROLE_IN_SESSION('PII_READER') THEN VAL
      ELSE '***MASKED***'
    END;

ALTER TABLE ANALYTICS_DEV.SALES.CUSTOMERS
  MODIFY COLUMN EMAIL
  SET MASKING POLICY ANALYTICS_DEV.GOVERNANCE.MASK_EMAIL;
```

Input and output types must match. Inspect any existing policy before
attachment; do not force a replacement or unset protection to bypass an
error. The example fully masks the value; partial masks and hashes can leak
information and are not automatically anonymization.

`IS_ROLE_IN_SESSION` checks the active account-role hierarchy, including
secondary roles; `CURRENT_ROLE()` equality checks only the current primary
role. For database-role entitlements, evaluate
`IS_DATABASE_ROLE_IN_SESSION` and its database-context rules instead.
Use role names with their stored case.

Test actual execution contexts: reader, entitled reader, inherited/secondary
roles, null inputs, service identities and owner-rights code. The function
can return NULL for shared objects accessed by a consumer; this CASE falls
back to masking. Design and test sharing-specific entitlements rather than
assuming provider role names work in consumer accounts.

## 5. Row-level access

Use a row access policy for allowed-row visibility, not a view filter that
consumers can bypass by reading an unprotected base table. For a simple
role/region example:

```sql
CREATE ROW ACCESS POLICY ANALYTICS_DEV.GOVERNANCE.SALES_REGION_ACCESS
  AS (REGION_CODE VARCHAR) RETURNS BOOLEAN ->
    IS_ROLE_IN_SESSION('SALES_ALL_REGIONS')
    OR (
      IS_ROLE_IN_SESSION('SALES_EU_READER')
      AND REGION_CODE = 'EU'
    );

ALTER TABLE ANALYTICS_DEV.SALES.FCT_SALES
  ADD ROW ACCESS POLICY ANALYTICS_DEV.GOVERNANCE.SALES_REGION_ACCESS
  ON (REGION_CODE);
```

Confirm existing roles, column type, attachment privileges and current policy
state. Deny by default: rows are visible only when the expression is TRUE.
Test unauthorized roles, null/unmapped regions and roles inherited through
the hierarchy. A row access policy does not prevent inserts or provide a
general write-authorization mechanism.

For many entitlements, use an approved mapping-table design. The policy
owner needs access to lookup objects; consumers need not have direct lookup
table access. Keep entitlement administration controlled, consider locality
and database-role context, and test lookup cost and recovery behavior.
Review masking/row policy signature restrictions and interactions before
combining policies on the same columns.

## 6. Files, external storage and integrations

Use named stages for approved file landing/access paths. Internal-stage
`READ`/`WRITE` privileges differ from external-stage `USAGE`; check the
operation's exact privilege requirements and parent-object access.
Stage access is a separate exposure path from table access. Masking a table
does not protect raw files that users can read directly.

For cloud storage, prefer an approved storage integration with scoped
locations and cloud IAM permissions instead of embedding cloud keys.
Creation of an external stage needs the appropriate schema and integration
privileges. Keep integration administration, stage creation and runtime file
access separate. Do not assume that runtime readers need permission to
administer the integration.

A Snowflake external volume serves supported Iceberg storage use cases,
not general-purpose file access. Govern its cloud IAM, catalog integration
and table ownership separately. Streaming/API connectors need their
supported authentication path; select integrations and secrets according
to the connector's documented requirements.

## 7. Discovery, audit, lineage and costs

Start with metadata and least-privileged visibility. For authorized
inspection, scope grant checks to known objects/roles:

```sql
SHOW GRANTS ON TABLE ANALYTICS_DEV.SALES.FCT_SALES;
SHOW GRANTS TO ROLE SALES_ANALYST;
SHOW GRANTS TO DATABASE ROLE ANALYTICS_DEV.SALES_READER;
SHOW FUTURE GRANTS IN SCHEMA ANALYTICS_DEV.SALES;
```

Direct grants on an object alone do not prove effective access. Trace
database-role/account-role inheritance, parent privileges, secondary roles,
`PUBLIC`, policy behavior and alternative interfaces.

| Evidence | Snowflake surface | Caveat |
|---|---|---|
| Assets, ownership and grants | Information Schema, `SHOW` commands, Account Usage | Visibility depends on the inspecting role; empty results do not prove absence. |
| Queries and authentication | `QUERY_HISTORY`, `LOGIN_HISTORY` | Scope and protect audit data; query text may contain sensitive literals. |
| Object/column access and lineage | `ACCESS_HISTORY`, Snowsight lineage | Feature availability, supported statements and lineage coverage vary. |
| Policy inventory and attachment | `MASKING_POLICIES`, `ROW_ACCESS_POLICIES`, `POLICY_REFERENCES` | Attachment alone does not prove correct authorization logic. |
| Tag assignment | `TAG_REFERENCES` views/functions | Distinguish direct, inherited and propagated associations. |
| Compute usage | Warehouse/account metering views | Warehouse credits do not by themselves provide exact per-query cost attribution. |

Use authorized Snowflake database roles or other approved monitoring grants
for the needed views, not blanket admin access. Time-bound audit queries,
select only required columns and limit exploratory previews to 100 rows
(up to 1000 only with justification). Limits do not cap scan cost. Check
documented latency/retention per view, and design durable audit export where
required. Access History is not a complete real-time log of every statement.

## 8. Sharing and change lifecycle

Evaluate secure views, Secure Data Sharing/listings, or supported Iceberg
interoperability for the actual consumer and platform. Review export,
cross-region, residency, costs and consumer-context policy behavior.
Do not grant base-table access when the approved interface is a restricted
view. A secure view is not a substitute for correct grants and policy logic.

For grant changes, ownership transfers, policy removal/replacement, cloning
or dbt rebuilds, record the exact targets, approval, blast radius, rollback
and validation plan. Obtain explicit confirmation before destructive or
overwriting SQL. Access revocation or a policy change can also disrupt
consumers even if it deletes no data; obtain approval for that impact.

For projects following this kit's layout, place approved governance/IaC
definitions under `infra/`, not in Airflow DAG business logic. Ensure dbt
replacement/materialization behavior preserves or reapplies intended grants,
tags and policies; test the resulting objects instead of assuming inheritance.

## Acceptance checklist

1. Confirm account/environment, naming, owners and feature availability.
2. Review minimum privileges and inherited effective access; avoid broad
   grants, unnecessary ownership and direct-user privilege sprawl.
3. Review current versus future grants and managed access administration.
4. Document classification and verify actual protection, not tags alone.
5. Test allow and deny cases for policies, including role hierarchies,
   service execution, nulls and any shared-consumer contexts.
6. Check alternate exposure paths: raw stages, base tables, clones and exports.
7. Verify audit/lineage visibility, limitations and retention requirements.
8. Validate deployment/rebuild effects and report untested assumptions.
   Do not connect or execute SQL merely to validate this documentation.

## Related skills

- [Naming conventions](../snowflake-naming-conventions/SKILL.md).
- [Medallion architecture](../snowflake-medallion-architecture/SKILL.md).
- [Data contracts](../snowflake-data-contracts/SKILL.md).
- [Data quality](../snowflake-data-quality/SKILL.md).
- [dbt integration](../snowflake-dbt-integration/SKILL.md).
- [Project structure](../snowflake-project-structure/SKILL.md).

## Snowflake references

- [Access control overview](https://docs.snowflake.com/en/user-guide/security-access-control-overview).
- [Configuring access control: managed access and future grants](https://docs.snowflake.com/en/user-guide/security-access-control-configure).
- [Object-specific privileges](https://docs.snowflake.com/en/user-guide/security-access-control-privileges).
- [Object tagging](https://docs.snowflake.com/en/user-guide/object-tagging/introduction).
- [Dynamic Data Masking](https://docs.snowflake.com/en/user-guide/security-column-ddm-intro).
- [Masking policy syntax](https://docs.snowflake.com/en/sql-reference/sql/create-masking-policy).
- [Row access policies](https://docs.snowflake.com/en/user-guide/security-row-intro).
- [IS_ROLE_IN_SESSION](https://docs.snowflake.com/en/sql-reference/functions/is_role_in_session).
- [Cloud storage integration example](https://docs.snowflake.com/en/user-guide/data-load-s3-config-storage-integration).
- [Access History and coverage](https://docs.snowflake.com/en/user-guide/access-history).
