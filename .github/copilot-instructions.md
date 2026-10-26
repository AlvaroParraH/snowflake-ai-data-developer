# Snowflake development instructions for GitHub Copilot

Use the project's existing Snowflake conventions and approved tooling first.
The kit's examples are proposals, not an approved corporate naming standard,
environment layout, quality threshold, or data contract.

## Skill guidance

Copilot discovers project skills in `.github/skills/`. Each skill's `SKILL.md`
contains its discovery metadata and full guidance. Read the relevant skill
before applying it; do not rely only on its description.

- Naming, casing, quoting, qualification, or object names:
  [naming conventions](skills/snowflake-naming-conventions/SKILL.md).
- Before Silver transformations or when investigating source types, nulls,
  dates, duplicates, or joins:
  [Bronze profiler](skills/snowflake-bronze-profiler/SKILL.md).
- Layer responsibilities, incremental processing, or orchestration:
  [medallion architecture](skills/snowflake-medallion-architecture/SKILL.md).
- Quality rules, tests, thresholds, quarantine, or DMF monitoring:
  [data quality](skills/snowflake-data-quality/SKILL.md).
- Ownership, consumer guarantees, schema evolution, or service objectives:
  [data contracts](skills/snowflake-data-contracts/SKILL.md).
- dbt sources, models, tests, snapshots, or adapter configuration:
  [dbt integration](skills/snowflake-dbt-integration/SKILL.md).
- Project scaffolding, folder structure, new pipeline file placement,
  Silver/Gold dbt paths, or Airflow DAG locations:
  [project structure](skills/snowflake-project-structure/SKILL.md).
  Preserve its agreed `pipelines/` layout in projects adopting it. Do not
  reorganize this skill kit or migrate existing projects automatically.
- RBAC, database roles, object ownership, managed access schemas, grants,
  classification tags, masking, row access policies, stage permissions,
  audit/lineage, or governed sharing:
  [data governance](skills/snowflake-data-governance/SKILL.md).
- Streamlit apps hosted in Snowflake, including runtime choice, Snowflake data
  access, app permissions, packages, secrets, external access, or deployment:
  [Streamlit in Snowflake](skills/snowflake-streamlit/SKILL.md).
- Batch text, document, image, or multimodal AI work using Snowflake-managed
  functions:
  [Cortex AI Functions](skills/snowflake-cortex-ai-functions/SKILL.md).
- Hybrid search, retrieval, or RAG over Snowflake data:
  [Cortex Search and RAG](skills/snowflake-cortex-search/SKILL.md).
- Governed metrics or natural-language analytics over structured data:
  [Semantic Views and Cortex Analyst](skills/snowflake-semantic-views-analyst/SKILL.md).
- Deployment or promotion of Snowflake code and objects across environments:
  [deployment and promotion](skills/snowflake-deployment/SKILL.md); use
  `/snowflake-deploy` for a release review or plan.

## Safety and scope

- Confirm exact names and impact before object creation or migration. Do not
  connect to Snowflake just to author or review local files.
- MCP availability is not authorization to query or mutate an account.
  Use only approved tools, accounts, environments, and least-privileged roles.
  Review actual tool behavior; tool names and read-only hints are not access
  controls.
- Before destructive or overwriting SQL, show the exact statements, target
  account/environment and objects, and expected impact; obtain explicit
  confirmation for those statements. Do not treat a general pipeline request
  as permission for destructive operations or full refreshes.
- For approved exploration, inspect metadata first, select only needed
  columns, use aggregates or sampling, and bound row previews to 100 rows
  (up to 1000 only when justified). A result `LIMIT` is not a scan-cost cap.
- Keep credentials, tokens, private keys, and sensitive sample data out of
  source files, examples, logs, and responses. Use the host's approved secret
  mechanism rather than committing rendered connection configuration.
- Surface errors, uncertain assumptions, and unverified platform behavior.
  Do not silently discard invalid rows or substitute success-shaped defaults.

## Editing this kit

Keep discovery metadata and substantive guidance together in each
`.github/skills/<skill-name>/SKILL.md`. Preserve neutral Snowflake-focused
branding in new files and leave external reference material untouched.
Update the README and setup documentation when skill paths change.

For documentation changes, check local links, YAML frontmatter/examples,
fenced blocks, and that each skill's metadata matches its directory name.
Review SQL examples against Snowflake/dbt documentation; do not execute them
as a documentation check. This kit has no application build or dependency
installation requirement.
