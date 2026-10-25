---
name: snowflake-init
description: "Detect greenfield versus brownfield Snowflake projects and initialize Bronze ingestion, Silver/Gold dbt and Airflow folders. Use for new project initialization, existing project layout assessment, or explicitly adding missing folders."
argument-hint: "Existing project root to initialize"
agent: "agent"
---

# Initialize Snowflake pipeline folders

Read the [project-structure skill](../skills/snowflake-project-structure/SKILL.md)
and [setup guidance](../../docs/copilot-setup.md). This is local, folder-only
initialization, separate from kit installation.

1. Confirm the exact existing target project root. Never select the kit checkout,
   filesystem root, or home directory. Inspect the current layout first.
2. **Determine project state (greenfield versus brownfield).** Run:

   ```bash
   python3 scripts/init_project.py --target /path/to/project --detect-only
   ```

   Read the reported state and per-signal evidence, not merely the exit code.
   Detection considers local Snowflake CLI project files (`snowflake.yml` or
   `snowflake.yaml`), root or canonical dbt project configuration, an existing
   project profile, and populated `src/`, `pipelines/`, `models/`, `dags/`,
   `bronze/`, `silver/`, or `gold/` directories. Empty folders and installed kit
   assets, `.venv`, Git metadata, README files and MCP config alone are not
   brownfield signals. Detection is heuristic: no signals does not prove an
   empty directory or absence of a Snowflake project. Do not read credentials,
   execute project code, or connect to Snowflake to classify the project.

   - **Greenfield:** report "No existing project signals found" and continue to
     the preview, still requiring approval before creation.
   - **Brownfield:** list the signals and use the question tool to offer:
     **Review existing layout (recommended)**, **Add missing agreed folders**,
     or **Cancel**. A review is local and read-only: summarize existing paths
     and differences without generating files or running an account audit.
     Do not scaffold after review unless the user explicitly chooses to proceed.
     If additive creation is approved, include `--allow-existing` in both the
     preview and actual initialization command. `--yes` alone is not brownfield
     approval. Never offer a force-overwrite or automatic migration option.
3. Use the installed [scaffolding script](../../scripts/init_project.py) with a
   locally available Python 3.10+ interpreter:

   ```bash
   python3 scripts/init_project.py --target /path/to/project --dry-run
   ```

   Resolve the script from the target project's root; use its absolute path if
   running from another directory. Do not execute an unreviewed replacement script.
4. Show the exact target and planned folders. Ask for confirmation before running
   the same command with `--yes` instead of `--dry-run`. The plan also initializes
   a local Git repository if the target is not already inside one. For a nested
   target, do not create a repository inside the parent repository. Use `--no-git`
   if the user opts out. `git init` creates no commit or remote and stages no files.
   Preserve `--allow-existing` only when explicitly approved. If detection
   changes between preview and execution, stop and review the new signals.
5. Verify all five leaf directories exist: `pipelines/ingestion/bronze/`,
   `pipelines/dbt/models/silver/staging/`, `pipelines/dbt/models/silver/intermediate/`,
   `pipelines/dbt/models/gold/marts/`, and `pipelines/orchestration/airflow/dags/`.
   Report failures explicitly. A dry run is not completed initialization.

Create folders only: no starter models, DAGs, `.gitkeep`, manifests, lockfiles,
credentials, file staging, commits, remotes, environment setup, dependency installation,
MCP activation, Snowflake SQL, or deployment. Empty folders are not tracked by
Git. Existing content is preserved; conflicts and symlinks must be resolved
manually, never bypassed or overwritten.
