---
name: snowflake-data-quality
description: "Design and operate data quality checks for Snowflake tables, views, and dbt models, including Data Metric Functions, expectations, SQL tests, severity, quarantine, and cost-aware monitoring."
---

# Snowflake Data Quality

Choose checks that verify an explicit data contract or business expectation.
Profile unfamiliar sources before setting thresholds, and distinguish a
measured anomaly from a confirmed defect. Apply checks at the layer where a
failure can be acted on: inspect at ingestion, validate types and keys in
Silver, and protect consumer-facing measures in Gold.

This skill does not prescribe universal pass rates, a required framework, or
an organization-wide quality score. Use existing project policy where
defined; agree on thresholds, severity, owners, and remediation before
enforcement.

## Select a validation mechanism

| Need | Suitable mechanism | Tradeoffs |
|---|---|---|
| Validate a build or release; keep rules in code | dbt data tests or explicit SQL assertions in orchestration | Version controlled and close to model logic; tests must be selected and run, and they add query cost. |
| Monitor recurring metrics on Snowflake objects | Snowflake Data Metric Functions (DMFs) with expectations | Snowflake schedules evaluation and records violations; scheduled DMFs use serverless compute and can add monitoring/logging cost. |
| Enforce row constraints at write time | Snowflake table constraints where supported and enforced | `NOT NULL` and `CHECK` are enforced on standard tables; primary, unique, and foreign keys are generally not enforced on standard tables. Hybrid-table semantics differ. |
| Express a specialized recurring metric | Custom DMF or a query owned by the pipeline | Adds implementation, permission, maintenance, and evaluation-cost responsibility. |
| Preserve invalid rows for investigation | Explicit quarantine/reject relation or error output | Define access, retention, replay, and remediation; do not silently discard failures. |

These options complement rather than automatically replace one another. A dbt
test is not a continuously scheduled Snowflake DMF, and a declared standard
table primary key is not an enforced uniqueness check.

## Define useful checks

Start with checks derived from the actual grain, schema, and consumers:

- **Completeness:** required keys, dates, or measures are not null; treat
  optional fields and empty strings according to their source meaning.
- **Validity:** values parse into the intended Snowflake type; numbers, date
  ranges, identifiers, and categories match documented expectations.
- **Uniqueness:** rows are unique at the declared grain. For a composite key,
  test the complete set of key columns and test nullability separately.
- **Referential integrity:** child keys resolve to the expected parent set,
  accounting for legitimate late-arriving or optional relationships.
- **Freshness and volume:** data arrived within the agreed interval and row
  counts remain within an explained range. Confirm whether the timestamp
  measures source time, event time, load time, or last DML time.
- **Reconciliation:** source, staging, refined, and published totals agree
  within defined rules for filtering, late changes, and rounding.
- **Schema compatibility:** unexpected adds, removals, renames, or type
  changes are reviewed before consumers break.
- **Privacy and exposure:** confirm access paths and classifications; do not
  log sensitive row values as test evidence.

Do not make a column non-null or a domain exhaustive merely because an
exploratory sample contains no exceptions. Confirm expectations with the
producer or data owner.

## Snowflake Data Metric Functions

Snowflake system DMFs measure common attributes such as null counts and
freshness. An expectation defines which returned metric values pass. For
example, this illustrates a zero-null expectation:

```sql
ALTER TABLE <database_name>.<schema_name>.<table_name>
  ADD DATA METRIC FUNCTION SNOWFLAKE.CORE.NULL_COUNT
    ON (<required_column>)
    EXPECTATION no_nulls (VALUE = 0);
```

This is an example shape, not a command to run. Confirm the object, column,
role privileges, supported object kind, feature availability, and desired
schedule before associating a DMF. A DMF measures a value; it does not
automatically decide whether the value is a defect without the expectation.

Snowflake's quality monitoring can run DMFs on schedules; the default schedule
is hourly unless configured otherwise. Scheduled DMF evaluations use
serverless compute and incur cost. Choose frequency based on detection needs,
table size, and expected violation response. Monitor usage and violations.
DMFs are supported on tables, views, dynamic tables, materialized views,
external tables, Iceberg tables, and event tables, but not hybrid tables or
stream objects. Check the current Snowflake documentation for availability
and limitations in the target account.

System DMF names and signatures vary by metric. Select only a DMF documented
for the intended data type and question. Use a custom DMF only when system
metrics do not fit, and review its query cost, ownership, privileges, and
failure behavior. Manual ad hoc metric calls and scheduled monitoring have
different billing implications.

Do not use Cortex Data Quality suggestions as approved policy. Review
AI-generated checks and expectations with a domain owner before enabling
scheduled checks; confirm that account settings, privacy requirements, and
cost controls permit the feature.

## dbt and SQL tests

Use dbt data tests where quality assertions should be reviewed and versioned
alongside transformations. For example, this properties-file fragment uses
dbt's built-in generic tests; `data_tests` and nested `arguments` match
current dbt property syntax:

```yaml
models:
  - name: customer
    columns:
      - name: customer_id
        data_tests:
          - not_null
          - unique
      - name: segment
        data_tests:
          - accepted_values:
              arguments:
                values: ['consumer', 'business']
```

Choose package-based tests only when the package is already an accepted,
version-pinned project dependency. A singular SQL test can select violating
rows; zero rows means it passes:

```sql
-- tests/customer_orders_have_valid_totals.sql
SELECT order_id
FROM {{ ref('customer_order') }}
WHERE order_total < 0;
```

Use dbt's severity and warning configuration intentionally. A warning is
visible but is not equivalent to a blocked deployment; define CI behavior
explicitly. dbt tests generally query the built relation and do not make
Snowflake reject future writes.

For a custom orchestration path, use the same core shape: compute a violation
count, compare it with an agreed threshold, and either fail visibly or route
violating records to a controlled quarantine path. Capture check identifier,
relation, evaluation time, scope, total/violation counts, threshold, and run
identifier. Avoid persisting row-level sensitive values in generic logs.

## Severity and response

Agree on the response for each rule before enabling it:

- **Block:** failure would make the output unsafe or materially wrong; fail
  the build/publication and provide an actionable message.
- **Warn:** an anomaly needs owner review but the agreed contract allows
  publication; page or report according to the service expectation.
- **Quarantine:** retain the source row and reason for later correction or
  replay; define who can read it and when it is deleted.
- **Observe:** establish a baseline before setting a hard threshold.

Do not automatically drop bad records just to make a check pass. Define how
rejected data is counted, retained, reprocessed, and reconciled. Alert
recipients, escalation, and remediation time belong to the owning team's
operational agreement.

## Review checklist

1. State the table grain, consumers, source behavior, and intended invariant.
2. Test the whole key and relevant table scope, not just a convenient sample.
3. Distinguish SQL `NULL`, blanks, sentinels, missing semi-structured paths,
   and JSON null where relevant.
4. Set threshold and severity with evidence and the data owner.
5. Choose dbt tests, SQL assertions, DMFs, enforced constraints, or a
   deliberate combination based on when and where detection is needed.
6. Estimate frequency, warehouse/serverless cost, and alert noise.
7. Record evidence and failures without exposing sensitive payloads.
8. Define owner, response, quarantine/replay, and deployment gate before
   calling a check production-ready.

## Snowflake references

- [Data quality overview](https://docs.snowflake.com/en/user-guide/data-quality-intro)
- [System DMFs](https://docs.snowflake.com/en/user-guide/data-quality-system-dmfs)
- [SQL expectations](https://docs.snowflake.com/en/user-guide/data-quality-expectations)
- [Custom DMFs](https://docs.snowflake.com/en/user-guide/data-quality-custom-dmfs)
- [Constraint overview](https://docs.snowflake.com/en/sql-reference/constraints-overview)
- [dbt data tests](https://docs.getdbt.com/reference/resource-properties/data-tests)
