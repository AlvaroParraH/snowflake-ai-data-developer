---
name: snowflake-naming-conventions
description: "Guidance for naming Snowflake identifiers and data or operational objects. Distinguishes Snowflake platform behavior from optional project defaults; existing project conventions take precedence."
---

# Snowflake Naming Conventions

Use this skill when choosing, reviewing, or discussing names for Snowflake
databases, schemas, data objects, and operational objects. It is guidance, not
an approved corporate naming standard. Inspect the current project for
established conventions first; follow them where applicable.

Do not create, rename, or migrate objects based only on examples in this skill.
Confirm the intended names, scope, and any environment or data-layer layout
before proposing DDL or changing code that refers to live objects.

## Snowflake platform facts

These behaviors are defined by Snowflake, not naming preferences:

- An unquoted identifier starts with a letter or underscore and can contain
  letters, underscores, digits, and `$`. Snowflake stores and resolves it in
  uppercase. Thus, unquoted `customer_orders`, `CUSTOMER_ORDERS`, and
  `Customer_Orders` refer to the same identifier.
- A double-quoted identifier preserves its exact case and must be referenced
  with the same spelling and quotes. For example, `"Customer_Orders"` is
  distinct from unquoted `customer_orders` (which resolves as
  `CUSTOMER_ORDERS`). Quoted identifiers may contain spaces and special
  characters, but those names can be cumbersome to reference consistently.
- Identifiers are limited to 255 characters, including spaces.
- `QUOTED_IDENTIFIERS_IGNORE_CASE` affects how quoted identifiers are stored
  and resolved. Do not change or assume this setting; check the account or
  project configuration when quoted-name behavior matters.
- A fully qualified schema object is
  `<database_name>.<schema_name>.<object_name>`. Snowflake also allows
  qualification to be omitted in supported contexts, in which case the current
  database/schema or query search path can affect resolution. Prefer explicit
  qualification in shared SQL and deployment code when ambiguity matters.
- A period separates parts of a qualified name. If a quoted identifier itself
  contains a period, quote that identifier as a whole, for example
  `"DB.NAME"."SCHEMA.NAME"."TABLE.NAME"`.

See Snowflake's documentation for the complete
[identifier requirements](https://docs.snowflake.com/en/sql-reference/identifiers-syntax)
and [object name resolution](https://docs.snowflake.com/en/sql-reference/name-resolution).

## Practical project defaults to consider

The following are suggestions to adopt only if the project has no conflicting
convention and the team agrees. They are not Snowflake requirements or
organization-wide policy.

- Prefer simple lowercase `snake_case` identifiers written unquoted, such as
  `customer_order` or `order_line`. Snowflake will store these unquoted names
  in uppercase; the lowercase spelling is a readability convention.
- Keep names descriptive, stable, and concise. Use letters, digits, and
  underscores; begin with a letter or underscore. Avoid spaces, punctuation,
  mixed-case quoted names, and embedding a database or schema name redundantly
  in every object name.
- Treat database and schema boundaries as project design choices. Do not assume
  that a database represents an environment or layer, or that a schema
  represents a source, domain, or layer. Use the project's documented model.
- Name tables and views for their business entity or purpose, for example
  `customer`, `order_line`, `active_customer`, or
  `daily_revenue_summary`. Use semantic prefixes such as `dim_`, `fact_`, or
  `vw_` only when the project explicitly adopts them.
- Consider a consistent, readable object name for each Snowflake object type.
  Examples to discuss with the project include:

  | Object type | Illustrative name |
  |---|---|
  | Database / schema | `analytics_db` / `customer_domain` |
  | Table / view | `customer` / `active_customer` |
  | Dynamic table / materialized view | `daily_revenue_summary` |
  | Stream / task / pipe | `customer_changes` / `refresh_customer_summary` / `ingest_customer` |
  | Stage / file format / sequence | `inbound_files` / `csv_standard` / `order_number` |
  | Warehouse / role | `analytics_wh` / `analytics_reader` |
  | UDF / procedure | `normalize_email` / `refresh_customer_summary` |
  | Policy / tag / integration | `pii_masking_policy` / `data_classification` / `external_data_access` |

  These examples are illustrative, not prescribed prefixes or a complete
  taxonomy. Apply the same project-specific style consistently to other
  objects, including alerts, pipes, streams, tasks, shares, integrations,
  policies, and tags.
- If a project elects to encode environment, data layer, source, or domain in a
  name, agree on the meaning, allowed values, ordering, and applicable object
  types first. Avoid encoding the same information in multiple name segments
  unless that duplication serves a documented purpose.
- Use descriptive column names that communicate meaning and, where helpful,
  units or temporal semantics. Avoid inventing universal metadata-column
  prefixes or copying another platform's metadata names without project
  agreement.
- Keep access-control names aligned with the project's role and privilege
  model. A role name should communicate its purpose or scope, not imply that
  naming alone grants or restricts access.

## Review checklist

When recommending or reviewing a name:

1. Check project configuration, migrations, SQL, and documentation for existing
   conventions and representative names.
2. Distinguish the Snowflake object type and qualification from the identifier
   itself. Check whether the name is unquoted or intentionally quoted and
   case-sensitive.
3. Confirm whether any environment, domain, source, or data-layer component is
   part of the project's agreed naming model; do not invent one.
4. Check for ambiguity, redundant segments, inconsistent spellings, and
   unnecessary quoting. Do not treat a suggested example as an approved name.
5. Before creating or migrating objects, confirm the exact names and impact
   with the user or project owner.
