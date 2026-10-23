---
name: snowflake-bronze-profiler
description: "Guide read-only, bounded profiling of unfamiliar Snowflake source or Bronze tables before Silver transformations; check actual schema, nulls and sentinels, parsing, keys, joins, referential gaps, and semi-structured values."
---

# Snowflake Bronze Profiler

Profile the actual source or Bronze relation before writing transformations
that depend on its schema, types, row grain, or key behavior. This is a
read-only investigation guide, not a fixed script: inspect the real columns
first and tailor checks to the data and business expectations. Do not infer the
schema from a ticket, sample file, or remembered source definition.

Profiling does not authorize changes to source data or live objects. Keep
Bronze as-landed unless the project has explicitly chosen another ingestion
contract; apply agreed normalization and deduplication in the downstream
transformation.

## Before querying

Establish the context that makes results interpretable:

- What does one row represent (the expected grain)?
- Which system and ingestion method produced the table? Is it a snapshot,
  incremental extract, CDC feed, or file landing?
- What is the expected business key and update cadence?
- Which downstream transformations and joins are planned?
- Which columns are dates, timestamps, numbers, booleans, identifiers, or
  categories despite their physical type?
- Are there expected nulls, sentinel values, late-arriving records, or known
  source quirks?
- Which database, schema, table, and time range are in scope? What warehouse,
  query/runtime budget, sampling approach, and data sensitivity restrictions
  apply?

If context is unavailable, record assumptions as unverified and distinguish
observations from conclusions.

## Start with the actual schema

Use Snowflake metadata to establish the names and physical types before
generating column-specific SQL. For example:

```sql
DESCRIBE TABLE <database_name>.<schema_name>.<table_name>;
```

`<...>` denotes a placeholder, not literal SQL; substitute the confirmed
three-part object name. For a programmatic inventory, inspect the database's
`INFORMATION_SCHEMA.COLUMNS` view. Avoid relying on unqualified names if the
current database or schema could change resolution.

Compare metadata with the intended business meaning. In Snowflake, identifiers
that are unquoted resolve as uppercase; quoted identifiers preserve case and
must be referenced exactly as created. Use the actual names shown by metadata,
and quote identifiers correctly when needed. Do not assume Spark backtick
quoting or Spark reserved-word rules apply.

Snowflake standard tables can contain `VARIANT`, `OBJECT`, and `ARRAY` data in
addition to relational columns. Inspect semi-structured paths only when the
table has such data and the downstream contract needs them.

## Profile within a stated budget

Start with the smallest query that answers the question. Narrow scans using a
known date, batch, source, or other selective predicate when appropriate.
Choose and state a sample strategy for exploratory checks:

```sql
SELECT <columns_to_inspect>
FROM <database_name>.<schema_name>.<table_name> SAMPLE SYSTEM (5)
LIMIT 1000;
```

This is an illustrative 5% block sample plus a result cap, not a guaranteed
maximum scan or a representative statistical sample. `SYSTEM` sampling selects
storage blocks and can be biased, particularly on small tables. `BERNOULLI`
samples rows probabilistically; fixed-size `SAMPLE ROW (n ROWS)` is available
for a bounded number of sampled rows. Sampling does not prove uniqueness,
absence of rare sentinels, or referential integrity. Record the method and
limits with every sampled conclusion.

`LIMIT` caps returned rows, not necessarily rows scanned or compute consumed.
Exact full-table counts, distinct counts, duplicate checks, and orphan checks
can scan substantial data. Run them only when needed and within an agreed
warehouse/time budget. Prefer scoped checks first; use a sample for discovery,
then run a targeted exact check if a decision requires proof. Do not change
warehouse size, session/account limits, or other shared settings without
authorization. Never select sensitive payloads wholesale merely to inspect
them; restrict columns, mask values in findings, and follow project access
controls.

The SQL below is illustrative. Replace placeholders with inspected identifiers
and adapt expressions to actual physical types, source semantics, and scope.
Do not run generated SQL against Snowflake without the requested approval and
applicable access.

## Checks to select

### Column reality and intended types

For every downstream reference, verify that the column exists and its physical
type matches the transformation's assumption. For string columns that are
expected to hold dates or numbers, use Snowflake's `TRY_TO_DATE`,
`TRY_TO_TIMESTAMP_*`, or `TRY_TO_NUMBER` functions to count parse failures
instead of converting blindly:

```sql
SELECT
  COUNT(*) AS rows_checked,
  COUNT_IF(order_date_text IS NOT NULL) AS non_null_values,
  COUNT_IF(
    order_date_text IS NOT NULL
    AND TRY_TO_DATE(order_date_text, 'YYYY-MM-DD') IS NULL
  ) AS failed_iso_dates
FROM <database_name>.<schema_name>.<table_name>
WHERE <scope_predicate>;
```

Test each plausible source format separately, count values that match none,
and note overlapping formats or ambiguous day/month ordering. Snowflake
`TRY_` conversion functions return `NULL` on conversion errors; that result
must be counted so invalid values are not silently lost downstream. For
timestamps, identify timezone semantics before choosing `NTZ`, `LTZ`, or
`TZ`; parsing success alone does not establish the correct timezone.

### True nulls, sentinels, and domains

Distinguish SQL `NULL`, empty strings, whitespace, and source-specific
sentinels such as `NA`, `N/A`, `null`, `none`, or `-`. Check only sentinel
spellings relevant to the source and compare case-insensitively only if that is
semantically appropriate. Do not globally map strings like `"null"` to SQL
`NULL` without confirming the source contract.

Check ranges and categorical domains for fields where expectations exist:
minimum/maximum values for dates or numbers, and counts of unexpected status,
code, or category values. A surprising value is a finding to discuss; it is
not automatically invalid.

### Grain and duplicate keys

Define a candidate natural/business key from source semantics, then measure
duplicates on the full relevant scope:

```sql
SELECT <key_column_1>, <key_column_2>, COUNT(*) AS row_count
FROM <database_name>.<schema_name>.<table_name>
WHERE <scope_predicate>
GROUP BY <key_column_1>, <key_column_2>
HAVING COUNT(*) > 1
ORDER BY row_count DESC
LIMIT 100;
```

Also check null key components separately. A capped result list may omit
additional duplicate groups; it does not make the full duplicate check cheap.
Distinguish genuine repeated events/history from accidental duplication.
Before any Silver `MERGE`, define a deterministic rule for choosing one source
row per target key, such as a trusted source sequence and timestamp with a
stable final tie-breaker. Do not use arbitrary ordering or rely on a declared
key constraint as proof of uniqueness on a standard Snowflake table.

### Join keys and referential gaps

Inspect both sides' actual key types and normalization (whitespace, case,
leading zeros, collation-sensitive values) before joining. A cast that
syntactically succeeds may still change key identity; do not normalize keys
without a domain rule. For planned joins, report:

- Null keys on each side.
- Distinct or duplicate key counts where useful.
- Match rate and unmatched child keys within the same time/source scope.
- Whether gaps are expected because of filtering, late arrivals, or
  intentionally optional relationships.

Use an anti-join or `NOT EXISTS` for gap checks and count the result rather
than dumping unmatched sensitive records. A sampled gap check is exploratory;
it does not establish complete referential integrity.

### Semi-structured values

For relevant `VARIANT` columns, inspect representative paths and their types
with `TYPEOF(payload:<path>)`; count missing paths, SQL nulls, JSON nulls, and
value types separately when those distinctions affect the transformation.
`IS_NULL_VALUE` can identify JSON null values; a missing path and SQL `NULL`
are not interchangeable with JSON null. Use `LATERAL FLATTEN` only when the
shape and expected row expansion are understood. Bound its input first, and
watch for array expansion that multiplies rows.

Do not dump full nested documents into logs or findings when they can contain
personal, confidential, or secret values. Report path names, types, and
aggregated counts instead.

## Findings and next-step handoff

Summarize, with scope and method:

- Relation, inspection time, scope predicate, sample method/size, and
  limitations.
- Observed column names/types and columns whose semantic types differ.
- Null/sentinel counts and date/number parse success and failure counts.
- Expected grain, key nulls and duplicate groups, including whether checks
  were sampled or exact.
- For planned joins: key type/normalization comparisons, match rate, and
  unmatched counts.
- Semi-structured paths/types inspected and any missing/null distinctions.
- Each finding's evidence, confidence, business impact, and proposed Silver
  handling or owner decision.

Do not use universal percentage thresholds as automatic release gates. What is
material depends on the field's role, table grain, and business use. Treat a
non-unique business key without a deterministic tie-breaker, an unsafe key
conversion, or widespread unparsable required dates as a blocker to an
unambiguous transformation. Record lower-volume anomalies for the owner to
classify. Proceed only after material assumptions and Silver behavior are
agreed.

## Common pitfalls

- Assuming planned or remembered schema instead of inspecting live metadata.
- Treating sample results, capped duplicate lists, or sampled anti-joins as
  proof that all rows are clean.
- Treating `LIMIT` as a reliable scan-cost limit.
- Using conversion that silently becomes `NULL` without counting failures.
- Deduplicating without an agreed grain and stable, deterministic tie-breaker.
- Assuming standard-table primary, unique, or foreign key constraints enforce
  uniqueness or referential integrity; these constraints are generally not
  enforced on standard Snowflake tables. Hybrid tables have different
  constraint behavior.
- Applying Spark/Databricks SQL syntax or assumptions, such as backtick
  quoting, to Snowflake SQL.
- Fixing source values in the Bronze landing table before the project has
  agreed to mutate that ingestion contract.

## Snowflake references

- [Identifier requirements](https://docs.snowflake.com/en/sql-reference/identifiers-syntax)
- [DESCRIBE TABLE](https://docs.snowflake.com/en/sql-reference/sql/desc-table)
- [SAMPLE / TABLESAMPLE](https://docs.snowflake.com/en/sql-reference/constructs/sample)
- [TRY_TO_DATE](https://docs.snowflake.com/en/sql-reference/functions/try_to_date)
- [FLATTEN](https://docs.snowflake.com/en/sql-reference/functions/flatten)
- [Constraint overview](https://docs.snowflake.com/en/sql-reference/constraints-overview)
