---
name: snowflake-pipeline
description: "Guide a Snowflake medallion pipeline from source discovery through an approved plan and staged Bronze, Silver/dbt, Gold, and orchestration work, with review gates."
argument-hint: "Optional source, domain, or request to build or extend a Snowflake pipeline"
agent: "agent"
---

# Snowflake pipeline wizard

Guide the user through designing and, only with explicit approval, implementing
a source-to-consumer pipeline on Snowflake. Use the project's conventions and
the Snowflake skills; do not mechanically copy another platform's architecture.
This workflow is a coordinator, not permission to connect, spend compute, or
change live Snowflake objects.

## Usage

- `/snowflake-pipeline` — start an interactive pipeline discovery.
- `/snowflake-pipeline <source-or-domain>` — prefill that context, then ask
  about all unresolved decisions.
- `/snowflake-pipeline --resume` — resume only if this repository has an
  unambiguous, user-approved pipeline plan/checkpoint. Otherwise ask what to
  resume; do not invent or silently continue an old plan.

## Non-negotiable boundaries

- Inspect the repository and its instructions before proposing files. Preserve
  existing project structure, naming, dbt configuration, dependencies, and
  deployment process unless the user explicitly approves a change.
- Do not read, echo, or include credentials, rendered profiles, tokens,
  connection strings, secrets, or secret-bearing environment values.
- Local repository inspection and design require no Snowflake connection.
  Before any live account discovery, MCP call, warehouse use, SQL execution,
  or dbt command that may connect, state the exact account/environment,
  identity/role if known, scope, operations, and expected compute impact, then
  obtain explicit user approval.
- A live read-only query may still expose data and incur compute cost. Inspect
  metadata only by default; do not select business rows or sample table data
  unless the user separately approves the precise query and purpose.
- Never create or modify production objects, grants, roles, integrations,
  policies, tasks, pipes, or deployments without explicit approval of the
  exact target and operation. Destructive, replacement, overwrite, and
  production actions require a separate confirmation immediately before each
  action. Never use broad privilege grants to make a pipeline work.
- Do not install dependencies, modify lockfiles, stage/commit/push changes, or
  run project-defined hooks without approval.
- If a required skill, tool, source contract, permission, or decision is
  missing, identify the blocker and pause; do not silently invent a substitute.

## Skills to consult

Read relevant guidance before designing or editing:

- [Snowflake medallion architecture](../skills/snowflake-medallion-architecture/SKILL.md)
  for ingestion responsibilities, provenance, incremental processing,
  refresh, quality, recovery, and operational tradeoffs.
- [dbt with Snowflake](../skills/snowflake-dbt-integration/SKILL.md) for
  Snowflake adapter configuration, model conventions, tests, and build safety.
- [Snowflake Tasks and task graphs](../skills/snowflake-tasks/SKILL.md) for
  native task orchestration, compute models, retries, and monitoring.
- [Snowflake project structure](../skills/snowflake-project-structure/SKILL.md)
  for the agreed repository layout and existing-project precedence.
- [Snowflake data quality](../skills/snowflake-data-quality/SKILL.md) and
  [governance](../skills/snowflake-data-governance/SKILL.md) for appropriate
  quality and access-control design.
- Consult naming, contracts, or profiling skills when those concerns are in
  scope. A profile may guide design, but does not prove deployed account state.

## Phase 1 — Discover requirements

Inspect local files read-only: repository tree, project instructions, README,
dbt project/profile structure without credential values, Python manifests and
lockfiles, tests, CI/deployment configuration, existing ingestion and DAG
patterns, and any approved `docs/project-profile.md`. Do not run project code,
install packages, or connect while surveying.

Ask the user concise, grouped questions to establish only the unknowns:

1. **Source and contract:** system/object, delivery method, owner, schema,
   stable keys, grain, change signal/CDC, expected volume, late/corrected data,
   schema drift and replay expectations.
2. **Outcome and service level:** consumers, business purpose, freshness and
   availability, quality thresholds, retention, recovery and alert ownership.
3. **Existing project fit:** current layout and components to extend; approved
   database/schema/environment conventions; whether an existing raw landing
   zone means the pipeline starts at Silver.
4. **Implementation scope:** design only or repository edits; whether optional
   Snowflake access is requested; permitted account, role, warehouse, object
   scope, operations and cost limits.

Do not ask for or accept secret values. If decisions are unknown, mark them
unresolved and offer safe alternatives rather than selecting for the user.

## Phase 2 — Produce and confirm a plan

Show a concise end-to-end plan before editing or executing anything:

- Source-to-target flow and selected ingestion approach, with alternatives
  and assumptions.
- Proposed Bronze landing/provenance and replay/error-handling behavior.
- Silver transformations, keys/grain, type/null rules, incremental boundary,
  deduplication, late data and invalid-row handling.
- Gold consumer contract, metric definitions, freshness and access boundary.
- Quality tests, observability, recovery/backfill, retention and cost controls.
- Optional orchestration choice and responsibility boundaries. Compare
  Snowflake-native scheduling/processing, dbt orchestration, and the project's
  existing external orchestrator; do not add a new platform by default.
- Repository files to add or change, exact target paths, dependencies if any,
  test/validation commands, live Snowflake operations if any, and known risks.

Respect platform distinctions: Bronze/Silver/Gold are project-defined data
responsibilities, not Snowflake object types or mandatory database/schema
names. dbt staging models do not replace ingestion. Snowflake standard-table
primary/unique/foreign-key constraints are generally not enforced. Do not
copy static partitioning assumptions from other platforms; clustering requires
workload evidence.

Wait for explicit approval of the plan and scope. A general request to "build
a pipeline" is not approval to connect, install dependencies, or apply DDL.
Record unresolved decisions and pause if they prevent a safe implementation.

## Phase 3 — Implement in reviewable stages

Do not attempt all layers in one unreviewed batch. For each approved stage:
state the intended changes, edit only its relevant repository files, run
local checks that do not connect, summarize the diff and results, then pause
for the user's review and explicit direction before proceeding.

### 3a. Bronze / ingestion

Choose the ingestion mechanism only after confirming source and latency fit:
existing managed connector/Openflow/partner tool, staged files with `COPY
INTO`, Snowpipe, Snowpipe Streaming, or a project-owned extractor/orchestrator.
State prerequisites and ownership; do not create integrations, stages, pipes,
or network policies as a guess.

Specify load identifiers and provenance available from the chosen path,
idempotency/replay, schema drift, parse failures, duplicate delivery,
retention, and recovery. Preserve source evidence as required by the approved
contract. Add code or SQL only within the confirmed repository scope. Before
live ingestion or object creation, obtain exact target-specific approval.

Pause after the stage for review. Do not continue automatically.

### 3b. Silver / dbt transformations

Follow the installed project's dbt version, `dbt-snowflake` adapter, profile
approach, materializations, naming, model paths, and dependency lock. If no dbt
project exists, propose its exact layout and dependency changes first; do not
run `dbt init`, `uv add`, `dbt deps`, or edit lockfiles without approval.

Use declared sources and `ref()` dependencies, explicit columns, documented
grain and keys, deterministic deduplication, safe incremental semantics,
appropriate tests, and clear handling of parse failures and late changes.
Keep credentials outside tracked files. Do not assume schema names or enable
grants/hooks from examples.

Local static inspection or parsing is not proof of Snowflake execution.
`dbt debug`, compile/build/test, hooks, macros, and adapters may connect,
consume warehouse compute, or write objects. Before running any such command,
inspect its effective project/target and side effects, explain them, and get
approval; use an approved non-production target and bounded selectors.

Pause after the stage for review. Do not continue automatically.

### 3c. Gold / consumer products

Define consumer-facing facts, dimensions, views or aggregates from agreed
business definitions, grain, ownership, freshness and access. Make metric
logic and tests explicit. Do not invent business rules or publish data to an
unapproved schema. Treat materialization, grants and deployment as decisions,
not consequences of writing SQL.

Pause after the stage for review. Do not continue automatically.

### 3d. Orchestration and operations (only if approved)

Prefer the project's existing scheduler and deployment model. Define
dependencies, schedule, retry/backfill behavior, idempotency, alert ownership,
timeouts, concurrency, observability and warehouse/cost expectations. Add
Airflow, Snowflake Tasks, Dynamic Tables, or another orchestrator only when
its role and ownership are selected and its tradeoffs are reviewed.

Do not activate schedules, resume tasks, deploy DAGs, or trigger production
runs without explicit target-specific approval. Pause for review before any
deployment or live run.

## Phase 4 — Verify and report

Run the smallest relevant local validation already available in the project.
Do not install missing tools or connect to Snowflake as a fallback. Report
exact commands and outcomes; distinguish static checks, local tests, and
authorized live validation.

Provide a Markdown report in chat, and create a repository report file only
with approval. Include:

- source, target responsibilities and approved environment;
- implemented files and reviewed diffs;
- data grain/keys, incremental and replay semantics;
- tests and validation actually run;
- account operations actually approved and completed, if any;
- security, cost, freshness, recovery and operational assumptions;
- unresolved decisions, limitations, and next steps.

Do not claim deployment, object existence, access, data correctness, or
production readiness without direct evidence. Do not commit, push, or leave
live schedules enabled unless separately requested and explicitly approved.
