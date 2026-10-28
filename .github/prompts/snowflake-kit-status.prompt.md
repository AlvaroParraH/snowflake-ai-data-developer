---
name: snowflake-kit-status
description: "Diagnose the local Snowflake development kit installation and prerequisites; report pass, warning, or failure with secret-safe remediation. Use after installation or when kit setup appears broken."
argument-hint: "Optional: --verbose for safe paths/counts, --offline to skip live Snowflake auth checks, or --json for structured output"
agent: "agent"
---

# /snowflake-kit-status — Snowflake development kit health check

Diagnose the Snowflake kit installation in the current project and report a
clear pass/warn/fail result with a concise remediation for every non-pass.
This is a read-only diagnostic workflow, not a repair/install command.

## Usage

```text
/snowflake-kit-status                 Full local audit; offer live auth check only with approval
/snowflake-kit-status --verbose       Include safe paths, counts, versions, and config key names
/snowflake-kit-status --offline       Skip network-dependent Snowflake authentication checks
/snowflake-kit-status --json          Return the same checks as JSON without surrounding prose
```

Flags can be combined. They control the requested report/check scope; this
prompt does not install a standalone executable or change process exit codes.
If automation needs machine-enforced exit status, use a dedicated diagnostic
script or CI check rather than treating generated JSON as an executable test.

## Scope and safety

- Diagnose the currently open workspace only. Confirm its root before checks.
- Do not install, update, repair, configure, delete, or modify anything.
- Do not read or print secret values, tokens, passwords, private keys,
  rendered Snowflake profiles, environment files, or credential-bearing
  configuration. Never include query text or user/account identifiers in
  verbose output.
- Do not run SQL, dbt, project scripts, the installer, Git hooks, or MCP
  tools as a diagnostic shortcut.
- Do not change hook configuration, stage files, or run a commit.
- Snowflake CLI authentication is network-dependent. Without `--offline`,
  report local CLI availability first, then name the configured connection
  only if the user has already provided it. State the exact connection and
  ask for confirmation before running `snow connection test`. If no
  connection was explicitly identified or the user does not approve, report
  authentication as not checked. Never discover connections by dumping
  profiles or retry with another identity.
- `/snowflake-check` remains the focused workflow for Snowflake CLI and
  connection readiness. Use it for connection troubleshooting; do not turn
  this kit-health report into an account or privilege audit.

## Checks

### 1. Local prerequisites

Check availability and version of:

- Git.
- Python 3.10 or newer.
- `uv`, required by the kit installer and used for its optional `.venv`
  creation.
- Snowflake CLI (`snow`), required by the kit installer and useful for
  Snowflake development.

Use read-only version checks only. Do not install missing tools. If a required
tool is absent, report it as a failure; if an optional tool is absent, mark it
as a warning.
The kit does not require Node.js, Databricks CLI, or Claude CLI.

### 2. Kit installation and assets

Check the workspace root for the expected project-local files and report
presence/counts without dumping content:

- `.github/copilot-instructions.md`.
- Fifteen `.github/skills/*/SKILL.md` files, each with valid `name` and
  `description` frontmatter matching its skill directory.
- Eleven `.github/prompts/*.prompt.md` files, each with meaningful prompt
  metadata.
- `scripts/install_kit.py`, `scripts/init_project.py`,
  `scripts/scaffold_snowflake_project.py`,
  `scripts/scaffold_dbt_model.py`,
  `scripts/installation_state.py`,
  `scripts/scan_secrets.py`, `.githooks/pre-commit`, and setup documentation.
- `.snowflake-kit-manifest.json` for tracked updates. An older installation
  without it needs the documented migration before `--update`; report a
  warning, not permission to manufacture tracking records or delete assets.
- Optional `.venv` health: recognizable `pyvenv.cfg` and working interpreter.
  If absent, report that the environment is optional/skipped; do not create it.

Compare skill names with the installed source kit only if the source kit is
available locally and the user asks for drift details. Do not assume that
missing local source assets mean installed files are corrupt. Do not print
skill or prompt bodies in the report.

### 3. Git and staged secret-scanning hook

If the workspace is a Git repository:

- Determine the active hook directory using `git rev-parse --git-path hooks`
  and `git config --path --get core.hooksPath` as applicable.
- Check whether the active `pre-commit` launcher exists and is executable.
- If the kit launcher is present, confirm it points to the workspace scanner
  by checking only safe path/identity details; do not execute the hook or
  scanner.
- If a different hook exists, report it as preserved/unknown, not as a failure
  and never suggest overwriting it.
- If the target is inside a parent repository, describe the hook as inherited
  from that repository; do not create a nested repository or hook.

If no Git repository is present, mark hook activation as deferred/optional.
Do not modify `core.hooksPath` or write hooks during this check.

### 4. Optional Snowflake CLI authentication

Skip this section when `--offline` is supplied. Otherwise, only after the
user explicitly approves a named configured connection, run:

```bash
snow connection test --connection "<user-approved-connection-name>"
```

Use the exact name the user provided. Do not list or dump connection profiles.
If the CLI version does not support this syntax, inspect local command help
and report a safe supported test command before running it. Sanitize output:
report pass or a broad failure category (authentication, network, policy,
configuration), never account host, username, SQL, or secrets.

A successful connection test proves only that authentication/connectivity
worked at that time. It does not prove object privileges, warehouse
availability, dbt readiness, or production access.

### 5. Optional MCP configuration presence

Report whether workspace MCP configuration exists at `.vscode/mcp.json`.
Do not display endpoint URLs, headers, OAuth settings, environment variable
names tied to credentials, or any values from the file. Presence is not proof
that the server is trusted, compatible, authenticated, or reachable.
MCP is optional; missing configuration is not a failure. Do not start servers
or invoke MCP tools.

### 6. Tracker and unrelated tooling

This Snowflake kit has no tracker credentials, tracker write probe, Databricks
workspace, or Claude authentication requirement. Mark these checks
not-applicable rather than searching home-directory configuration or
introducing those dependencies.

## Output

For text output, show one row per check with these status markers:

```text
  [✓]  name                   detail
  [!]  name                   detail
       → Fix: <one-line remediation>
  [✗]  name                   detail
       → Fix: <one-line remediation>
```

Use `[✗]` only for a missing or invalid required kit component or required
prerequisite. Use `[!]` for optional tools, skipped checks, unconfigured
optional features, or limited evidence. Warnings do not make the overall kit
status fail. Summarize as `PASS` when there are no failures, otherwise `FAIL`;
make clear if a live check was skipped.

Include these sections:

1. Prerequisites.
2. Kit installation and Copilot assets.
3. Python environment.
4. Git/pre-commit hook.
5. Snowflake CLI and authentication.
6. MCP configuration.
7. Not-applicable checks.

With `--verbose`, include only safe values: tool versions, project-relative
paths, file counts, hook path, and configuration key names. Do not show
credential values, endpoints, usernames, query text, or full file contents.

With `--json`, return one valid JSON object and no Markdown fences or extra
prose. Use this shape:

```json
{
  "overall": "PASS",
  "checks": [
    {
      "section": "Prerequisites",
      "name": "Python",
      "status": "pass",
      "detail": "Python 3.12",
      "remediation": null
    }
  ],
  "live_checks_skipped": true
}
```

Allowed statuses are `pass`, `warn`, `fail`, and `not_applicable`.
Use `overall: "FAIL"` only when at least one required check fails; otherwise
use `"PASS"`. Do not include raw command output if it could expose sensitive
information.

## Remediations

Give a safe one-line next step for each warning or failure. Examples:

- Missing Git/Python/uv: link to the official installation instructions; do
  not install automatically.
- Missing kit file or count mismatch: recommend rerunning the documented
  project-local installer after reviewing its dry run; do not run it.
- Invalid `.venv`: ask the owner to inspect it and use the project's
  environment workflow; do not overwrite it.
- Missing hook: explain that rerunning the installer can activate it after
  reviewing existing hooks, or that the target must first be a Git repository.
- Snowflake auth skipped/failed: direct the user to `/snowflake-check` or
  `/snowflake-connection-setup` and their Snowflake administrator as appropriate.
- MCP absent: explain that MCP setup is optional and point to
  `/snowflake-mcp-setup` if requested.

Never claim that a tool, connection, hook, MCP server, or asset is healthy
unless its relevant check was actually performed.
