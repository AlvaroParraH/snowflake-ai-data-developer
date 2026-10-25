---
name: snowflake-audit
description: "Audit a Snowflake data project repository and optionally approved Snowflake account metadata, then create or refresh a project profile with evidence-based findings."
argument-hint: "Optional scope: repo-only (default), approved account metadata scope, sync existing profile, or output path"
agent: "agent"
---

# Audit a Snowflake data project

Create or refresh a structured project profile from repository evidence.
Default to a local, repository-only audit that works offline. Account-side
inspection is optional and requires explicit user approval, a bounded scope,
and an already configured, administrator-approved connection or MCP server.
This audit is observational; do not make project or Snowflake changes.

Read the [Snowflake project structure skill](../skills/snowflake-project-structure/SKILL.md),
[dbt integration skill](../skills/snowflake-dbt-integration/SKILL.md),
[medallion architecture skill](../skills/snowflake-medallion-architecture/SKILL.md),
and [governance skill](../skills/snowflake-data-governance/SKILL.md) as relevant.
Respect repository instructions and existing project conventions.

## Usage

- `/snowflake-audit` — audit the local repository and propose
  `docs/project-profile.md`.
- `/snowflake-audit repo-only` — explicitly skip account-side inspection.
- `/snowflake-audit sync` — refresh an existing profile after showing what
  will change; preserve unrelated content.
- `/snowflake-audit account metadata for <explicit scope>` — request a bounded
  account metadata audit. First identify the exact account/environment,
  databases/schemas or objects, connection/tool and intended checks; do not
  proceed until the user explicitly approves the live inspection.
- `/snowflake-audit --output <path>` — use a user-approved alternate report
  path.

These are natural-language scope examples, not a command-line parser. Do not
claim that a scanner or script ran unless one exists in the repository and was
actually executed.

## 1. Establish the audit boundary

- Confirm the repository root; inspect its instructions and Git status.
- Default to repository-only and offline. Do not connect to Snowflake, invoke
  MCP tools, inspect user profiles, or infer that a local CLI profile is
  authorized.
- If the user requests account inspection, clarify the exact account and
  environment, object scope, requested metadata, client/tool, and read-only
  permissions. State any likely warehouse use or query cost and obtain
  explicit confirmation before invoking the connection or tool.
- If access is unavailable, approval is absent, or scope is too broad, report
  account inspection as not performed; continue with the local audit if
  appropriate.
- Never inspect, echo, copy, or include secrets, tokens, private keys,
  connection strings, credential files, or secret values. Do not run project
  code, dbt commands, macros, CI/CD deployments, or scripts with unknown
  side effects as an audit shortcut.

## 2. Audit the repository locally

Inspect relevant files and structure without changing them. Use bounded
searches; exclude `.git/`, `.venv/`, generated build output, dependency caches,
and secrets. Do not dump large files or environment files into chat or the
profile. Record evidence by relative path and line or configuration key when
practical; distinguish observed facts from inferences and recommendations.

Review only applicable areas:

- **Project identity and stack:** project documentation, Python packaging and
  tooling, SQL, dbt configuration/adapters, orchestration, CI/CD, tests, and
  declared Snowflake CLI usage.
- **Layout and medallion flow:** actual ingestion/Bronze, Silver, Gold,
  orchestration, model, macro, seed, test and documentation paths. Do not
  require a particular database/schema-per-layer design or treat folder names
  as proof of deployed objects.
- **dbt and SQL configuration:** project/profile structure, targets, model
  paths, package declarations, tests, hooks and deployment patterns. Record
  presence and structure only; do not print credential-bearing profile values,
  resolve environment variables, install packages, or execute dbt.
- **Governance and operational posture:** documented owners, role/grant
  boundaries, classification and policy references, data quality, freshness,
  observability, recovery, cost controls, environment separation and promotion
  safeguards. Do not claim controls exist based only on a name or example.
- **Repository hygiene:** tests, dependency/lockfile state, secret-handling
  patterns, documentation consistency, and configuration that appears
  incomplete or contradictory. Do not attempt to prove absence of secrets with
  broad content dumps; use existing safe repository tooling only if its
  behavior is understood.

Do not infer that a feature is deployed, secure, compliant, tested, or
authorized merely because a file mentions it. Do not classify personal data
from column names unless the data itself was explicitly authorized for
inspection; repository-only evidence supports, at most, a clearly labeled
heuristic note.

## 3. Optional account metadata review

Only after the approval in step 1, use the selected preconfigured connection
or administrator-approved read-only MCP tools for the exact agreed scope.
Prefer narrow metadata inspection and existing account views with known
visibility/latency limits. Report the effective account, role and environment
only if the approved tool can establish them safely.

- Do not enumerate an entire account by default. Bound database, schema,
  object counts, and any sample size before starting; stop at the agreed cap.
- Do not read table rows, sample business data, query sensitive values, or
  inspect secret-bearing stages or integration configuration.
- Do not use a warehouse or run SQL without approval of the scope and expected
  compute impact. Metadata commands and Information Schema queries may still
  have account visibility, latency, or cost limitations.
- Do not create, alter, grant, revoke, suspend, resume, deploy, or delete
  objects. Do not run `dbt debug`, `dbt compile`, `dbt build`, migrations, or
  project-defined checks that may connect or write.
- If a permission error occurs, report the requested metadata as unavailable.
  Do not retry with a more privileged role or broaden access.

Keep repository and account evidence separate. Do not claim drift or
deployment parity unless both sides were inspected for the same explicitly
mapped objects and environment.

## 4. Profile format and write approval

Propose a concise `docs/project-profile.md` with YAML frontmatter as the
machine-readable source of truth and a short human-readable summary:

```markdown
---
meta:
  schema_version: 1
  audited_at: <ISO-8601 timestamp>
  mode: repo-only
project:
  name: <observed or user-approved name>
repo:
  languages: []
  frameworks: []
  layout: {}
  notes: []
snowflake:
  inspection: not-performed
findings: []
recommendations: []
---

# <project name> — Snowflake Project Profile

<Brief scope-aware summary with evidence-backed findings and limitations.>
```

Adapt sections to evidence; omit empty details instead of inventing values.
For account inspection, record only the approved scope, sanitized metadata
summary, observation time, and coverage/limitations; never put credentials or
business row data in the profile. Use `mode: repo-only` unless an approved
account scan actually ran.

Before writing, show the target path and a concise summary of proposed content.
Ask for confirmation. For `sync`, compare with the existing profile, preserve
user-maintained or unrelated sections, and update only agreed audit sections.
Never overwrite an existing file or resolve a conflicting profile format
without approval. Do not edit code, config, grants, roles, or Snowflake objects
as a result of audit findings.

## 5. Findings and recommendations

Use evidence-based findings. For each, include severity (`HIGH`, `MEDIUM`,
`LOW`, or `INFO`), area, observation, evidence path/scope, confidence, and
impact. Severity is prioritization, not proof of exploitability or a compliance
determination. Recommendations should be concrete and non-mutating; ask before
implementing any fix.

Separate:

1. Observed facts.
2. Inferences and their confidence.
3. Unknown or uninspected areas.
4. Recommendations and the owner/approval needed.

Do not report an empty finding set as proof that the project is safe,
compliant, cost-efficient, or production-ready.

## 6. Completion report

Summarize the audit mode, files or approved account scope actually inspected,
profile path written (if approved), top findings, and limitations. If a scan
was partial or blocked, say so explicitly. Offer a focused follow-up such as
reviewing a specific dbt model, role design, data-quality tests, or deployment
plan; do not automatically expand the audit or make changes.
