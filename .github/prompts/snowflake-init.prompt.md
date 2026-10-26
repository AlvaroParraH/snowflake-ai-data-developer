---
name: snowflake-init
description: "Detect greenfield versus brownfield Snowflake projects and initialize Bronze ingestion, Silver/Gold dbt and Airflow folders, with an optional context-aware greenfield starter scaffold. Use for new project initialization, existing project layout assessment, or explicitly adding missing folders."
argument-hint: "Existing project root to initialize"
agent: "agent"
---

# Initialize a Snowflake pipeline project

Read the [project-structure skill](../skills/snowflake-project-structure/SKILL.md)
and [setup guidance](../../docs/copilot-setup.md). This is local initialization,
separate from kit installation.

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

   - **Greenfield:** report "No existing project signals found" and ask whether
     to create the **starter scaffold** or **folders only**. If the scaffold is
     selected, collect these project facts before previewing:
     1. Project name as a lowercase dbt identifier (for example
        `sales_analytics`); otherwise derive it from the target folder.
     2. Primary source type: `api`, `database`, `files`, `streaming`, `mixed`,
        or `undecided`.
     3. Initial planning environment: `dev`, `test`, `prod`, or `not_decided`.
        This records context only and does not configure a Snowflake target.
     4. Project owner/team (not a role), one-line purpose, business/data domain,
        initial data sensitivity (`not_assessed`, `public`, `internal`,
        `confidential`, `personal_data`, or `regulated`), and primary consumers.
        Use `not_assessed`/blank rather than guessing.

     Never ask for or store passwords, tokens, private keys, account
     identifiers, connection profiles, or sensitive row-level data. The
     scaffold adds `.gitignore`, project README/profile, area guides, an
     unimplemented source-aware Bronze placeholder, a minimal dbt project with
     a zero-row SQL model and model documentation, an empty Airflow DAG, and
     local test guidance. These are templates only: do not install
     dependencies, configure credentials, run dbt, connect to Snowflake, or
     deploy the DAG. Continue to the preview; approval is still required.
   - **Brownfield:** list the signals and use the question tool to offer:
     **Review existing layout (recommended)**, **Add missing agreed folders**,
     or **Cancel**. A review is local and read-only: summarize existing paths
     and differences without generating files or running an account audit.
     Do not scaffold after review unless the user explicitly chooses to proceed.
     If additive creation is approved, include `--allow-existing` in both the
     preview and actual initialization command. `--yes` alone is not brownfield
     approval. Never offer a force-overwrite or automatic migration option.
3. Use the installed [initializer](../../scripts/init_project.py) and, for the
   greenfield starter option only, its [scaffolder](../../scripts/scaffold_snowflake_project.py)
   with a locally available Python 3.10+ interpreter. Preview folder-only setup:

   ```bash
   python3 scripts/init_project.py --target /path/to/project --dry-run
   ```

   For the greenfield starter choice, add `--scaffold` and pass the collected
   context. For example:

   ```bash
   python3 scripts/init_project.py --target /path/to/project --dry-run --scaffold \
     --project-name sales_analytics --source-type api --environment dev \
     --owner "Data Engineering" --description "Sales analytics pipeline" \
     --domain sales --data-sensitivity internal --consumers "Finance reporting"
   ```

   Resolve the script from the target project's root; use its absolute path if
   running from another directory. Do not execute an unreviewed replacement script.
4. Show the exact target and planned folders. Ask for confirmation before running
   the same command with `--yes` instead of `--dry-run`. Preserve `--scaffold`
   only if the user selected starter files. The plan also initializes
   a local Git repository if the target is not already inside one. For a nested
   target, do not create a repository inside the parent repository. Use `--no-git`
   if the user opts out. `git init` creates no commit or remote and stages no files.
   Preserve `--allow-existing` only when explicitly approved. If detection
   changes between preview and execution, stop and review the new signals.
5. Verify all five leaf directories exist: `pipelines/ingestion/bronze/`,
   `pipelines/dbt/models/silver/staging/`, `pipelines/dbt/models/silver/intermediate/`,
   `pipelines/dbt/models/gold/marts/`, and `pipelines/orchestration/airflow/dags/`.
   Report failures explicitly. If `--scaffold` was selected, verify the full
   previewed list: `.gitignore`, `README.md`, `docs/project-profile.md`,
   `pipelines/ingestion/bronze/README.md`,
   `pipelines/ingestion/bronze/ingest_template.py`,
   `pipelines/dbt/README.md`, `pipelines/dbt/dbt_project.yml`,
   `pipelines/dbt/models/silver/staging/scaffold_example.sql`,
   `pipelines/dbt/models/silver/staging/_models.yml`,
   `pipelines/dbt/tests/README.md`, `pipelines/dbt/macros/README.md`,
   `pipelines/dbt/snapshots/README.md`,
   `pipelines/orchestration/airflow/README.md`,
   `pipelines/orchestration/airflow/dags/scaffold_pipeline.py`, and
   `tests/README.md`. Confirm the project facts were rendered accurately and no
   profile, dependency manifest, or credential file was created. A dry run is
   not completed initialization.

Folder-only mode creates no starter files. The optional greenfield scaffold
creates only the explicitly previewed starter files. Neither mode creates
credentials, installs dependencies, executes SQL/dbt, connects to Snowflake,
stages files, commits, configures remotes, activates MCP, or deploys anything.
The source type, environment, owner/team, project purpose, domain, sensitivity,
and consumers are documentation context, not Snowflake configuration. Starter
file conflicts and symlinks stop before writes; never bypass or overwrite
them. Existing content is preserved.
