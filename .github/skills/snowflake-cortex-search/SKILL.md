---
name: snowflake-cortex-search
description: "Use when designing or operating Snowflake Cortex Search for hybrid retrieval, enterprise search, or retrieval-augmented generation (RAG), including source preparation, filtering, freshness, evaluation, and application integration."
---

# Snowflake Cortex Search and RAG

Cortex Search provides managed hybrid retrieval over Snowflake data and can
serve as the retrieval layer for search and RAG applications. This skill
covers Snowflake-specific retrieval and governance decisions, not a generic
vector-database recipe. Confirm current product capabilities, limits, costs,
and availability for the target account and region.

## When to use

- Building a search experience or RAG application over governed text data.
- Preparing a corpus and creating, refreshing, querying, or evaluating a
  Cortex Search service.
- Adding retrieval to a Streamlit app or Cortex Agent.
- Reviewing retrieval freshness, access, cost, or answer grounding.

For batch embeddings or other AI transformations, see
[Cortex AI Functions](../snowflake-cortex-ai-functions/SKILL.md). For
structured business questions, see
[Semantic Views and Cortex Analyst](../snowflake-semantic-views-analyst/SKILL.md).

## Design the corpus and service

- Start from a curated, access-approved source relation. Define document
  identity, text content, metadata, update/delete behavior, and ownership.
  Preserve source identifiers and provenance for result traceability.
- Prepare usable text and metadata before indexing. Split long documents into
  meaningful, overlap-aware chunks where appropriate; retain document and
  chunk identifiers and the context needed to cite or open the original.
- Select only fields needed for retrieval, response context, and approved
  filters. Do not include sensitive columns merely because they exist in the
  source relation.
- Choose a target freshness based on the user-facing service objective and
  acceptable refresh cost. Verify the service's refresh behavior and
  propagation delay for the selected source and configuration; do not promise
  immediate consistency.
- Select text columns, attributes, embedding/model options, and any supported
  indexing configuration based on representative queries and current product
  guidance. Do not copy a configuration without validating its assumptions.

## Querying, filters, and authorization

- Request only the result columns and number of matches needed. Use supported
  filters for relevance and scope, and validate filter values at the
  application boundary.
- Treat filters as query constraints, not automatically as an authorization
  boundary. Confirm how the service owner, caller role, source privileges, and
  row/column policies interact for the chosen query API. Test with least-
  privileged representative roles and separate tenants.
- Do not retrieve a broad corpus and rely on the LLM to hide unauthorized
  results. Enforce access before or during retrieval using approved Snowflake
  privileges and supported isolation patterns.
- Keep credentials and API tokens out of code and logs. Use an approved
  Snowflake API authentication method or supported in-platform integration.
- Avoid passing unnecessary retrieved content to a generation model. Apply
  context-size limits and preserve source metadata for citations.

## Build and evaluate RAG

Keep retrieval and answer generation as separately observable stages:

1. Retrieve a bounded set of relevant passages for a representative query.
2. Inspect relevance, coverage, duplication, metadata filters, and source
   freshness.
3. Generate an answer from retrieved context with instructions to say when
   evidence is insufficient, and retain citations/source identifiers.
4. Verify that cited passages support the answer; do not present plausible
   model output as a sourced fact when retrieval did not support it.

Create a reviewed evaluation set covering common, ambiguous, no-answer,
adversarial, stale-source, and cross-tenant cases. Measure retrieval quality
separately from answer quality. Tune chunking, filters, result count, and
ranking only against that evaluation set; do not select settings from one
handpicked example.

For consequential or regulated use, provide human review and a clear
unanswered/escalation path. Do not assume model-generated citations are
accurate without checking them against retrieved source content.

## Cost, refresh, and operations

- Review service creation/indexing, ongoing refresh, query volume, target
  freshness, warehouse use, and model/API use as separate cost contributors.
- Test on a bounded representative corpus before creating or refreshing a
  large service. Explain expected compute and service impact before approved
  live operations.
- Monitor service state, source freshness, query failures, retrieval quality,
  and application latency. Surface unavailable or stale retrieval rather
  than silently falling back to unsupported answers.
- Review source schema changes, retention/deletion requirements, service
  ownership, grants, and the documented rebuild or rollback path before
  updates.
- Obtain explicit approval for creating, replacing, suspending, or dropping
  services and for production changes. Never interpret a general RAG request
  as permission to incur compute or alter account objects.

## Official references

- [Cortex Search overview](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-search/cortex-search-overview)
- [Query a Cortex Search service](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-search/query-cortex-search-service)
- [Cortex Search cost considerations](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-search/cortex-search-costs)
- [Cortex Search with Agents](https://docs.snowflake.com/en/user-guide/snowflake-cortex/cortex-search/cortex-search-agents)
