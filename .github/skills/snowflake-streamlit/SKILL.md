---
name: snowflake-streamlit
description: "Use when designing, building, reviewing, or deploying Streamlit in Snowflake apps, including runtime choice, Snowflake data access, app permissions, package availability, secrets, external access, performance, and operational safeguards."
---

# Streamlit in Snowflake

Build data applications that run within Snowflake and use governed Snowflake
data without moving it to an external application service. This skill covers
Snowflake-specific architecture, security, data access, and deployment. For
general Streamlit APIs and UI patterns, use the
[official Streamlit documentation](https://docs.streamlit.io/).

## When to use

- Creating or changing a Streamlit app hosted in Snowflake.
- Choosing between the warehouse and container runtimes.
- Wiring an app to Snowflake data, packages, secrets, or approved external
  services.
- Reviewing app permissions, query behavior, deployment, or sharing.

This skill is not a deployment authorization. Do not connect to an account,
create or alter Snowflake objects, install packages, or publish an app unless
the user explicitly requests the operation and the account, target, and impact
are clear. Follow project and organization conventions first.

## Choose the runtime and application boundary

Streamlit in Snowflake supports warehouse and container runtimes. Choose based
on the app's dependency and execution needs, supported features, operational
constraints, and expected cost. Verify current runtime capabilities and
regional/account availability before committing to a design; do not assume the
runtimes are interchangeable.

Prefer this hosted model when the app's primary job is interactive access to
Snowflake data and its dependencies fit the supported runtime. Consider a
separately hosted application only when requirements cannot be met by the
Snowflake runtime, and document the added network, identity, data-egress, and
operations boundaries.

Keep the app as a consumer interface, not a substitute for ingestion,
transformation, or orchestration pipelines. Query curated, consumer-ready
relations where possible. Follow the existing repository's app layout; this
kit does not prescribe a Streamlit application directory or create app files
automatically.

## Data access and authorization

- Identify the app owner, intended viewers, execution identity, and exact
  database objects before implementation. Confirm whether the configured app
  access model evaluates data privileges as the app owner or as the viewer;
  verify the current behavior and limitations for the selected runtime and
  app configuration.
- Grant only the privileges required by the app to the appropriate role.
  Review the complete role hierarchy and data-access path; app visibility does
  not itself authorize access to every underlying object.
- Do not assume that a UI filter, hidden widget, or client-side control is an
  authorization boundary. Enforce row/column restrictions in Snowflake with
  approved roles and policies, and test using representative identities.
- Use the Snowflake-managed session or supported connection mechanism for the
  selected runtime. Do not embed account credentials, passwords, private
  keys, tokens, or personal access tokens in app source, configuration, or
  logs.
- Apply the project's existing governance guidance for role design, masking,
  row access, data classification, and sharing:
  [Snowflake data governance](../snowflake-data-governance/SKILL.md).

## Query design and app state

- Use parameterized Snowpark or connector APIs for values. Do not concatenate
  untrusted input into SQL text or identifiers. When dynamic identifiers are
  needed, validate them against a fixed allowlist.
- Select only required columns and rows, push filters and aggregations to
  Snowflake, and inspect likely scan/warehouse costs. A result `LIMIT` bounds
  returned rows, not necessarily scanned data or compute.
- Avoid executing expensive queries on every rerun. Use Streamlit state and
  caching only when their freshness, invalidation, user isolation, and
  authorization behavior are appropriate. Do not cache sensitive results
  across users or permission contexts without verifying isolation.
- Make expensive or mutating actions explicit, bounded, and idempotent where
  possible. Report query failures and partial results accurately; do not
  display stale cached data as if it were current.
- Keep application state separate from durable business data. Write to
  Snowflake only when the app's purpose requires it and the user has approved
  the target objects and write behavior.

## Packages, secrets, and external services

- Check package availability and supported versions for the chosen runtime
  before adding dependencies. Use the runtime's supported package mechanisms
  and approved package sources; do not assume arbitrary `pip install`,
  internet access, or local development packages are available in deployment.
- Treat outbound network access as disabled unless it has been explicitly
  configured and approved. Use Snowflake's supported external access
  mechanisms and network rules for necessary endpoints, scoped as narrowly
  as practical.
- Store credentials with supported Snowflake secret objects and integrations
  or the organization's approved secret mechanism. Grant the app only the
  required secret access. Never put secret values in source, SQL examples,
  widget defaults, exception messages, or logs.
- Review third-party services for data handling, residency, retention, and
  authorization before sending Snowflake data outside the account.

## Build, test, and deploy

1. Inspect the existing project, approved naming and deployment workflow, and
   applicable governance rules. Confirm the runtime, owner, viewers, source
   relations, read/write scope, and any external dependencies.
2. Implement the smallest app that meets the requirement. Keep SQL/data access
   separable from UI code where useful, make user-triggered writes explicit,
   and provide useful empty, loading, and error states.
3. Test UI behavior and data access with non-production data and least-
   privileged representative roles. Check reruns, empty results, query
   failures, cache behavior, and permissions.
4. Review the exact target account, database/schema, app object, runtime,
   warehouse or compute resources, grants, package configuration, and
   deployment changes before publishing. Obtain explicit approval for
   production changes and any overwrite or destructive operation.
5. After deployment, verify the published app, access behavior, query
   attribution/cost, and error visibility. Document ownership and the
   project's rollback or update path.

Do not infer a Snowflake SQL command, runtime property, grant, or deployment
behavior from a sample or from a different Snowflake feature. Verify
version-sensitive details against current Snowflake documentation.

## Official references

- [About Streamlit in Snowflake](https://docs.snowflake.com/en/developer-guide/streamlit/about-streamlit)
- [Getting started with Streamlit in Snowflake](https://docs.snowflake.com/en/developer-guide/streamlit/getting-started/overview)
- [Snowflake access control](https://docs.snowflake.com/en/user-guide/security-access-control-overview)
- [Streamlit documentation](https://docs.streamlit.io/)
