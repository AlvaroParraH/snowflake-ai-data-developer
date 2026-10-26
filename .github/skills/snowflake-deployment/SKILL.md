---
name: snowflake-deployment
description: "Use when planning, reviewing, or performing controlled promotion of Snowflake code and application objects across environments, including Snowflake CLI, dbt, migration tools, CI/CD, approvals, rollback, and drift."
---

# Snowflake deployment and promotion

Snowflake projects use different deployment mechanisms for SQL objects,
Streamlit apps, dbt models, tasks, and other workloads. There is no single
universal bundle format that should be imposed on every project. Preserve the
repository's established workflow and use Snowflake CLI, dbt, migration
frameworks, infrastructure-as-code, or a combination only where they fit the
project's explicit needs.

## When to use

- Choosing or documenting a promotion path for a Snowflake project.
- Reviewing deployment configuration, scripts, CI/CD workflows, or release
  changes.
- Promoting approved SQL, dbt models, Streamlit apps, or Snowflake objects
  between development, test, and production environments.
- Investigating drift, failed deployment, rollback, or deployment safety.

## Inspect and define the deployment unit

Before proposing changes, inspect project instructions, repository structure,
current deployment configuration, dependency manager, CI workflows, object
ownership, and documented environment boundaries. Do not migrate a working
project to a different deployment tool just because this skill was loaded.

Establish:

- Which files and Snowflake objects are included, and which tool owns each.
- How accounts, roles, databases, schemas, warehouses, integrations, and
  secrets are selected for each environment.
- How dependencies, ordering, state, drift, and failed or partial releases
  are handled.
- Which changes are generated, reviewed, approved, and promoted, and who owns
  release and rollback decisions.

Separate environment-specific configuration from reusable application code.
Use explicit, reviewed configuration and approved secret stores; never
commit credentials, rendered connection profiles, tokens, or private keys.
Do not infer production names or targets from local defaults.

## Select and use project tooling

Use a deployment mechanism appropriate to the artifact and project:

- Snowflake CLI can support developer-centric Snowflake workflows and
  project-based deployment where supported.
- dbt manages model selection, builds, and related model artifacts; it does
  not automatically own every Snowflake object in an application.
- Versioned SQL migrations can manage ordered schema/object changes when the
  chosen migration framework and project conventions support them.
- Terraform or another approved infrastructure-as-code tool may manage
  infrastructure and account objects within its configured ownership
  boundary.
- CI/CD coordinates validation, approvals, environment selection, and
  promotion; it does not replace least privilege or review.

Verify current tool commands, configuration syntax, supported object types,
and lifecycle behavior in the official documentation for the selected tool.
Do not mix multiple tools as competing owners of the same object without an
explicit ownership and drift strategy.

## Release gates

For each promotion:

1. Establish the exact source revision, target account/environment, active
   role, warehouse or compute, and intended object scope. Never reveal or
   collect credential values.
2. Review the change set and dependencies. Identify creates, replaces,
   drops, grants, data backfills, and other operations with irreversible or
   costly impact.
3. Run available local validation and non-production tests. Confirm the
   deployment does not inadvertently run broad dbt selections, full refreshes,
   unbounded backfills, or destructive SQL.
4. Preview the actual rendered plan or SQL where the tool supports it.
   Validate substitutions and target resolution; a CLI success message or
   dry-run is not proof of correct account selection.
5. Obtain explicit approval for live changes, production deployment, grants,
   destructive operations, overwrites, and material compute. Approval must
   cover the exact target and change set.
6. Promote using the approved pipeline and least-privileged deployment role.
   Keep deployment logs free of secrets and sensitive query results.
7. Verify the deployed state using bounded, appropriate checks. Report
   partial failures, drift, and post-deployment actions explicitly.

Never connect to an account, execute deployment commands, create or modify
live objects, or trigger CI/CD merely because the user asks for deployment
guidance. For actions, obtain approval immediately before the operation when
the target, scope, and impact are clear.

## Rollback and operational readiness

Define rollback before release. Determine whether the change is reversible,
whether data migrations or grants require a separate recovery step, and
whether restoring an earlier definition would lose newer data or state.
Prefer forward-fix for non-reversible data changes when appropriate and
approved. Do not promise rollback when object or data semantics cannot
restore the prior state.

After promotion, verify critical objects, dependencies, access, app or
pipeline health, and cost attribution. Record release identifier, source
revision, target, operator/approver, outcome, and recovery notes according
to project policy.

## Official references

- [Snowflake CLI](https://docs.snowflake.com/en/developer-guide/snowflake-cli/index)
- [dbt deployment](https://docs.getdbt.com/docs/deploy/deployments)
