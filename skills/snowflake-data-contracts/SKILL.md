---
name: snowflake-data-contracts
description: "Specify producer-consumer guarantees for Snowflake data products, including schema, semantics, quality, freshness, ownership, access, evolution, and publication lifecycle."
---

# Snowflake Data Contracts

A data contract is an explicit agreement between a producer and its
consumers about a data product's interface, meaning, quality, delivery,
ownership, and change process. It can describe a Snowflake relation, but it
is not itself a Snowflake object or a substitute for access control, tests, or
operational monitoring.

Use a contract when a dataset has meaningful downstream consumers, service
expectations, or controlled change requirements. Keep internal staging
relations lightweight unless they have a separately agreed contract.
Existing organizational policy and approved contract tooling take precedence;
this skill does not imply a particular registry, governance DSL, steward
approval chain, lifecycle vocabulary, or service-level target.

## Contract contents

Record enough for a consumer to use the product safely:

- **Identity and ownership:** product/relation name, producer, accountable
  contact, support path, and intended consumer group.
- **Grain and semantics:** what one row represents, business definitions,
  units/currency, timestamp and timezone meaning, null meaning, keys, and
  known exclusions.
- **Schema:** column names, Snowflake data types, nullability expectations,
  descriptions, sensitivity classification, and compatibility status.
- **Delivery:** source lineage, load/change semantics, freshness objective,
  expected cadence, availability window, late data and correction behavior.
- **Quality:** testable invariants, thresholds and scope, severity, monitoring
  mechanism, and response owner.
- **Access and privacy:** approved roles/use, sensitive-data classification,
  retention, sharing restrictions, and approved masking/row-access controls.
- **Evolution:** compatibility definitions, notice window, versioning,
  migration period, deprecation date, and consumer communication.
- **Operations:** incident path, recovery/backfill expectations, known
  limitations, and last-reviewed date.

Do not turn illustrative freshness periods, quality percentages, layer
boundaries, or ownership roles into mandatory policy without the owners'
agreement.

## Lightweight contract example

The following YAML is a readable proposal, not a universally accepted schema
or a claim of compatibility with Open Data Contract Standard (ODCS) or any
registry. Adapt it to the format and validation tooling selected by the
project:

```yaml
apiVersion: "1"
kind: "data-product-contract"
name: "customer_orders"
version: "1.0.0"
owner:
  team: "<producer_team>"
  contact: "<support_contact>"
relation:
  database: "<database_name>"
  schema: "<schema_name>"
  name: "<object_name>"
  grain: "One row per order line"
  columns:
    - name: "order_id"
      data_type: "VARCHAR"
      nullable: false
      description: "Stable source order identifier"
    - name: "order_total"
      data_type: "NUMBER(18,2)"
      nullable: true
      description: "Order amount in the declared reporting currency"
quality:
  - id: "unique_order_id"
    expectation: "order_id is unique within the published relation"
    severity: "block"
delivery:
  freshness_target: "<agreed_duration>"
  late_data: "<agreed_behavior>"
access:
  classification: "<approved_classification>"
  consumer_roles:
    - "<approved_role>"
change_policy:
  compatibility_window: "<agreed_duration>"
  deprecation_notice: "<agreed_duration>"
```

For a formal, machine-validated contract format, choose and pin a specific
specification version and validate documents with its schema/tooling. Do not
label a local template “ODCS” unless it conforms to the selected ODCS
specification. A registry or catalog can store ownership and lifecycle data,
but the team must still decide how its metadata maps to Snowflake and CI/CD.

## Snowflake implementation options

Snowflake object comments and column comments can carry concise descriptions.
Snowflake tags can attach string-valued metadata to supported objects and
columns, and inherited/propagated tags can assist governance. A tag is
metadata, not access enforcement by itself. For protection, design and test
the appropriate roles, masking policies, row access policies, secure views,
or sharing controls separately.

Snowflake primary, unique, and foreign key constraints on standard tables
are generally not enforced. A declared key can document intent but cannot
replace a data quality test. `NOT NULL` is enforced on standard tables;
hybrid tables enforce primary, unique, and foreign keys and have different
behavior and workload characteristics. Confirm object kind and platform
behavior before depending on a constraint.

For scheduled monitoring, Snowflake Data Metric Functions and expectations
can express metrics and pass/fail thresholds on supported tables and views.
They do not provide the full semantic contract, owner communication, or
compatibility policy. See the data-quality skill for DMF cost and coverage
considerations.

In dbt, model properties document columns and tests. dbt model contracts can
preflight model output schema and include constraints, subject to the
materialization and adapter's support. On Snowflake, some declared
constraints such as primary/foreign/unique keys are metadata-only; the
`not_null` constraint is enforced. dbt model contracts do not cover every
resource type (for example, sources and snapshots), so use separate
documentation and tests where needed. A dbt contract is not automatically a
consumer-published data contract.

## Lifecycle and change management

The following lifecycle is a possible workflow, not an imposed standard:

1. Draft the contract with the producing owner and representative consumers.
2. Review schema, semantics, quality rules, access classification, and service
   targets against existing data and actual operational capability.
3. Implement metadata, tests, monitoring, and access separately; prove the
   checks run and identify who responds to violations.
4. Publish the contract with its relation and contact path.
5. Review changes with consumers before deployment. Classify compatibility
   based on impact, not merely whether the SQL compiles.
6. For a breaking change, agree on a migration/version plan, consumer
   communication, and retirement date before removing the old interface.
7. Revisit guarantees and ownership periodically and after incidents or
   material source changes.

Examples of potentially breaking changes include removing/renaming a column,
changing its meaning, changing grain, tightening null rules, altering units or
timezone semantics, changing key identity, or reducing freshness/retention
guarantees. Adding an optional field can still break strict consumers or
schema-bound tools; communicate it according to the actual interface.

Do not infer that a semantic version number, backward-compatibility window,
steward approval, deprecation duration, or lifecycle transition is mandated.
Agree and document those rules with the producer and consumers.

## Privacy and ownership

Data contracts should state classification and intended use, but names,
comments, and tags do not prove that data has been classified or secured.
Sensitive-data discovery is imperfect; require owner review. Apply
least-privilege roles and approved masking/row access controls, and test
consumer access using the intended roles. Minimize sensitive information in
contract files, test output, sample rows, and support tickets.

Every published product needs an accountable owner or escalation path. A
generic team placeholder is not operational ownership. Define who handles
schema questions, quality failures, late delivery, access requests, and
deprecation.

## Review checklist

1. Identify producer, consumers, exact relation, grain, and supported use.
2. Describe columns with Snowflake types and business meaning; state null,
   units, timezone, key, and privacy semantics.
3. Define measurable quality and freshness guarantees that the producer can
   actually support.
4. Separate descriptive metadata from enforcing tests, access controls, and
   monitoring.
5. Specify the contract format and validator, if machine-readable validation
   is required.
6. Define compatibility, notice, migration, and deprecation practices with
   consumers.
7. Confirm the owner and response path; do not publish placeholders as
   operational contacts.

## Snowflake and dbt references

- [Snowflake object tagging](https://docs.snowflake.com/en/user-guide/object-tagging/introduction)
- [Snowflake constraints](https://docs.snowflake.com/en/sql-reference/constraints-overview)
- [Snowflake data quality](https://docs.snowflake.com/en/user-guide/data-quality-intro)
- [dbt model contracts](https://docs.getdbt.com/docs/mesh/govern/model-contracts)
- [dbt data tests](https://docs.getdbt.com/reference/resource-properties/data-tests)
