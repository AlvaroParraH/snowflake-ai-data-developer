---
name: snowflake-semantic-views-analyst
description: "Use when defining governed business metrics and relationships in Snowflake Semantic Views or building, testing, and integrating natural-language analytics with Cortex Analyst."
---

# Snowflake Semantic Views and Cortex Analyst

Semantic Views express business concepts, metrics, dimensions, facts, and
relationships over Snowflake data. Cortex Analyst can use these definitions
to answer natural-language questions over structured data. Treat the
semantic layer as governed business logic: its definitions and examples
influence generated SQL and downstream decisions.

## When to use

- Defining shared metric and dimension meaning for analysts or applications.
- Creating or reviewing a Semantic View and its logical-table relationships.
- Building or evaluating a Cortex Analyst experience over structured data.
- Replacing duplicated KPI definitions or preparing a governed natural-
  language analytics interface.

For unstructured document retrieval, see
[Cortex Search and RAG](../snowflake-cortex-search/SKILL.md). For general
LLM transformations, see [Cortex AI Functions](../snowflake-cortex-ai-functions/SKILL.md).

## Model business meaning before authoring

- Confirm business owner, intended consumers, approved source relations,
  grain, keys, join cardinality, time semantics, and row/column access
  requirements before defining logical tables.
- Define facts at the correct row grain, dimensions with clear business
  meaning, and metrics with explicit aggregation and null/zero behavior.
  Identify additive, semi-additive, and non-additive measures; do not expose
  an aggregation that produces misleading rollups.
- Document relationships and join paths. Check for fanout, many-to-many
  joins, duplicate keys, and ambiguous paths using approved metadata or
  bounded local/test evidence before publishing.
- Use names, descriptions, synonyms, verified examples, and instructions
  that match the organization's business vocabulary. Treat examples as
  guidance, not a substitute for correct logic.
- Keep definitions aligned with the project's approved source models and
  contracts. Do not silently redefine an existing KPI to fit generated SQL.

## Author and govern Semantic Views

Use the supported authoring interface for the project, such as SQL, Semantic
Studio, or an approved specification workflow. Verify current syntax and
feature support before writing DDL or YAML. Existing project conventions and
approved deployment methods take precedence.

Review the view's dependencies, ownership, grants, and exposure. A Semantic
View is not by itself an authorization policy: enforce data access with
Snowflake privileges and applicable row/column policies. Grant access only
to intended consumers and test using representative roles.

Do not expose sensitive attributes, descriptions, sample questions, or
example results that should not be available to the intended audience. Keep
development and production definitions distinct where the deployment
workflow supports environment promotion.

## Build and evaluate Cortex Analyst

- Use Semantic Views for new work where supported and appropriate. Legacy
  semantic model files may exist; preserve them unless migration is requested
  and planned.
- Give Analyst only the semantic context and access it needs. Confirm the
  selected API, authentication, account/region availability, privileges, and
  caller execution context in current documentation.
- Test with a reviewed set of representative questions, including synonyms,
  ambiguous terms, time windows, filters, multi-table joins, empty results,
  and questions outside the model's scope.
- Inspect generated SQL before treating an answer as correct. Validate
  aggregation, joins, filters, access context, and returned values against
  trusted SQL or business-owner-approved results.
- Measure question interpretation, SQL correctness, answer accuracy, and
  abstention separately. Provide clarification or an explicit no-answer
  response when the model lacks enough context.
- Do not allow generated SQL to execute with broader privileges than the
  application or end user is intended to have. Do not assume natural-language
  instructions enforce authorization.

## Change control and validation

Treat metric definitions, relationships, synonyms, examples, and access
changes as contract changes. Review impact on existing consumers, test
regressions, record ownership/version context, and get business-owner
approval for changes to governed definitions. Obtain explicit approval
before creating or replacing production objects or changing grants.

## Official references

- [Semantic Views overview](https://docs.snowflake.com/en/user-guide/views-semantic/overview)
- [CREATE SEMANTIC VIEW](https://docs.snowflake.com/en/sql-reference/sql/create-semantic-view)
- [Querying Semantic Views](https://docs.snowflake.com/en/user-guide/views-semantic/querying)
- [Cortex Analyst](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-analyst)
