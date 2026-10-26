---
name: snowflake-deploy
description: "Plan and review a Snowflake project deployment or environment promotion using the repository's existing tooling, with explicit target, change-set, approval, and rollback gates."
argument-hint: "Optional target environment, release, or deployment question"
agent: "agent"
---

# Plan and review a Snowflake deployment

Help the user plan or review a controlled release of Snowflake project code
and objects. Preserve the project's existing deployment tooling and
environment conventions. This prompt coordinates inspection and planning; it
does not itself authorize account access, SQL execution, CI/CD, compute, or
production changes.

## Usage

- `/snowflake-deploy` — inspect the local deployment approach and identify
  release readiness and unresolved decisions.
- `/snowflake-deploy <environment-or-release>` — assess the specified
  promotion or release, then ask for any missing target details.

## Safety boundaries

- Read repository instructions and the
  [Snowflake deployment skill](../skills/snowflake-deployment/SKILL.md)
  first. Preserve existing scripts, CI/CD, dbt, migration, and infrastructure
  workflows unless the user explicitly approves changing them.
- Do not read or echo credentials, tokens, private keys, rendered profiles,
  connection strings, secret-bearing environment values, or sensitive query
  output.
- Local repository review and plan authoring do not require a Snowflake
  connection. Do not connect, execute SQL, run a deployment, trigger CI/CD,
  install tools, or incur compute without explicit approval for the exact
  operation.
- Before any live or destructive action, state the target account and
  environment, identity/role if known, exact object/change scope, expected
  impact and compute, and recovery approach. Obtain explicit approval
  immediately before the action. Production, grant, overwrite, drop, and
  backfill operations need separate confirmation.
- Do not assume a successful dry-run proves the correct account or target.
  Inspect resolved configuration and actual change output where available.
- Do not treat `/snowflake-deploy` as permission to commit, push, merge,
  release, or change production.

## 1. Inspect the local release context

Read project instructions and inspect only relevant local files:

- Deployment and CI/CD configuration, scripts, migration definitions, dbt
  project/selection conventions, and application manifests.
- Environment and account-selection mechanisms without opening secret values.
- Git status and the proposed change set without altering user changes.
- Project documentation for release ownership, approvals, validation, and
  rollback.

Identify the tool owning each artifact. Do not assume Snowflake CLI, dbt,
Terraform, migration tooling, or a CI provider is present. If the project has
no established deployment path, present options and tradeoffs; do not select
or install one silently.

## 2. Clarify the promotion

Ask only for material missing details:

1. Exact target environment/account and approved deployment role.
2. Release revision/change set and Snowflake artifact scope.
3. Deployment mode: plan/review only, non-production release, or production
   promotion.
4. Expected data backfills, compute, object replacement, grants, and external
   dependencies.
5. Required approvals, validation, maintenance window, and recovery owner.

Never ask for secret values. If target resolution or impact is unclear, stop
before live operations and state the blocker.

## 3. Produce a reviewable deployment plan

Summarize:

- Source revision and target environment with evidence from configuration.
- Files, objects, dependencies, and tool responsible for each deployment.
- Proposed commands/workflow stages, without executing them.
- Validation and plan/preview steps, including how actual target resolution
  will be checked.
- Destructive, replacement, grant, data migration, compute, or other elevated
  impact with explicit approval points.
- Post-deployment verification, rollback limits, and unresolved risks.

Clearly distinguish observed repository facts from assumptions and user
decisions. Do not claim a deployment is safe solely because commands are
idempotent or a tool supports a preview.

## 4. Execute only if explicitly approved

If the user requests execution, confirm exact target and scope, and ask for
explicit approval immediately before the operation. Run only the approved
local validation or deployment command. Do not broaden selectors, change
targets, add `--yes` or destructive flags, or run an unapproved follow-up.
If the plan differs from the approved change set or target, stop and obtain
new approval.

Report commands run, target, checks, success/failure/partial state, compute
or operational effects observed, and any required manual recovery. Do not
report success if the result could not be verified.

## Related skills

- [Snowflake deployment and promotion](../skills/snowflake-deployment/SKILL.md)
- [dbt with Snowflake](../skills/snowflake-dbt-integration/SKILL.md)
- [Snowflake Tasks](../skills/snowflake-tasks/SKILL.md)
- [Streamlit in Snowflake](../skills/snowflake-streamlit/SKILL.md)
