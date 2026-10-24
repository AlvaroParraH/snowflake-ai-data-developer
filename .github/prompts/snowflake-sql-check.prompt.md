---
name: snowflake-sql-check
description: "Check changed Snowflake SQL with SQLFluff before committing. Distinguish staged from working-tree content, plain SQL from dbt, and syntax/templating errors from style violations without connecting to Snowflake."
argument-hint: "Optional SQL paths or scope: staged (default), working tree, or a specified Git diff"
agent: "agent"
---

# Check Snowflake SQL before committing

Run a focused, non-mutating SQLFluff check on the requested SQL changes.
This is a manually invoked workflow, not a Git hook, CI enforcement or
permission to commit. SQLFluff is a local parser/linter, not Snowflake's
authoritative compiler.

## 1. Establish the scope

- Read repository instructions and inspect Git status before running checks.
  Default to staged added/modified/renamed `.sql` files, using the new path
  for renames and excluding deletions. Use NUL-delimited Git filenames and
  argument arrays or properly quoted paths, not whitespace splitting.
- Explicit user paths or a requested working-tree/diff scope take precedence.
  If no repository is available, ask for explicit files rather than claiming
  there are no changes.
- Report when no SQL files are selected. Do not call that a successful SQL
  validation, and do not silently expand to the whole repository.
- Check complete files, not just changed lines. If dbt configuration, macros
  or dependencies changed, explain that additional models may be affected
  and ask before expanding scope.

### Staged content must be distinguished from working-tree content

For each staged path, compare the working-tree content with the index.
Linting the working tree validates the staged SQL only when the contents
match. Do not stage, stash, reset or overwrite changes to make them match.

If a selected file has unstaged edits, ask whether to validate an isolated
staged snapshot or the working-tree version. A staged snapshot must include
the required project configuration and templating context, not just SQL
copied into an unrelated temporary directory. Use a specifically scoped
temporary location and remove only files created for this check. If the
correct staged context cannot be reproduced safely, report it as unverified;
never present working-tree results as validation of the commit.

## 2. Inspect tooling and effective configuration

- Inspect `pyproject.toml`, `uv.lock`, SQLFluff configuration/ignore files,
  nested overrides and existing scripts/hooks. Use the project's pinned
  tool version and established command where appropriate.
- For uv projects with an already prepared environment, prefer:

  ```bash
  uv run --offline --no-sync sqlfluff --version
  uv run --offline --no-sync sqlfluff lint --dialect snowflake <selected-sql-paths>
  ```

  Replace placeholders with explicit, safely passed paths. Run from the
  appropriate project/config root and group files by configuration and
  templater. Do not invoke a project wrapper without first checking that it
  has no installation, database, auto-fix or other unexpected side effects.
- If uv, SQLFluff, the environment or the required templater is missing,
  report a blocked check with the exact missing prerequisite. Do not install
  dependencies, synchronize an environment, download an interpreter, modify
  lockfiles, or use an unpinned `uvx` fallback during this check.
- Require the Snowflake dialect for Snowflake SQL. Explain conflicting
  configuration rather than editing it silently. Respect intentional
  exclusions and `noqa` directives, but report ignored/suppressed files or
  violations and do not describe excluded files as checked.

## 3. Handle SQL and dbt separately

- **Plain Snowflake SQL:** use the project's appropriate raw/Jinja templater.
  Do not send dbt-specific `ref()`, `source()` or macros through the raw
  templater and claim that the result validates the model.
- **dbt models, tests and snapshots:** inspect `dbt_project.yml`, model paths,
  target configuration and macros. Use the project's compatible, pinned
  `sqlfluff-templater-dbt` and dbt adapter when configured.
- dbt templating can execute macros and connect to Snowflake during
  compilation. Run it only if its execution path is verified local-only and
  all required packages/configuration already exist. Otherwise mark dbt
  validation blocked and explain what is needed. Do not substitute raw or
  generic Jinja templating as equivalent dbt validation.
- Do not run `dbt deps`, `dbt debug`, `dbt compile`, `dbt build`, MCP tools or
  any warehouse query as an automatic fallback. A separate, explicitly
  authorized workflow is required for database-backed validation.

## 4. Run, diagnose and optionally recheck

Capture the actual command, exit status, checked paths and diagnostics.
Distinguish:

1. Parser/syntax errors.
2. Templating or configuration errors.
3. Style/layout violations.
4. Tool/environment failures and ignored or otherwise unverified files.

Do not hide parser/templater errors with ignore flags, disable rules to make
the check pass, or treat a failed command as an empty successful result.
Investigate possible parser limitations before claiming Snowflake syntax is
invalid. Report uncertainty explicitly.

Do not run `sqlfluff fix` or edit SQL unless the user approves fixes. After
approved edits, rerun the same focused check and report the resulting scope.
Fixes affect the working tree, not the staged commit until the user stages
them; do not stage changes automatically.

## Result

Report:

- **Scope:** paths and whether index or working-tree content was checked.
- **Tooling:** SQLFluff version, effective dialect, templater and config.
- **Execution:** commands, exit status and whether checks ran or were blocked.
- **Findings:** file/line, rule/error and category.
- **Coverage:** exclusions, suppressions and unverified files or dbt context.
- **Next step:** needed fixes or missing setup; no automatic commit/push.

Say "SQLFluff passed for the checked scope" only if it actually passed.
Never claim this proves object existence, privileges, business correctness,
query performance, or acceptance by Snowflake itself.
