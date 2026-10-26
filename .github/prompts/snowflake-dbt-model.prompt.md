---
name: snowflake-dbt-model
description: "Create or update a reviewable dbt model and model documentation using the existing Snowflake project conventions. Use for a single staging, intermediate, or mart model."
argument-hint: "Model layer/name, source or upstream model, and requested columns"
agent: "agent"
---

# Create a Snowflake dbt model

Use the [dbt with Snowflake skill](../skills/snowflake-dbt-integration/SKILL.md)
and [project structure skill](../skills/snowflake-project-structure/SKILL.md).
This workflow generates local model files only. It never connects to Snowflake,
runs dbt, installs packages, or changes the project dependency environment.

## 1. Inspect before proposing

1. Establish the exact repository and dbt project root. For the canonical
   layout, the dbt root is `pipelines/dbt/`; preserve an existing custom layout.
2. Read project instructions, `dbt_project.yml`, nearby models and model YAML,
   source declarations, naming/materialization conventions, and relevant
   project profile facts. Do not print or copy secret-bearing profile values.
3. If there is no dbt project, stop and recommend `/snowflake-init` first or
   request an explicit approved project setup; do not create a second dbt
   project.
4. Do not assume model columns, source schemas, grain, transformation logic,
   or tests. Do not query Snowflake to discover them.

## 2. Gather only missing design facts

Ask the user for:

- Layer: `staging`, `intermediate`, or `marts`.
- Domain folder and full model name following repository conventions. Suggested
  patterns are `stg_<source>__<entity>`, `int_<entity>__<purpose>`, and
  `dim_<entity>` / `fct_<process>`; existing conventions take precedence.
- For staging, the already-declared dbt source name and table name. Verify the
  matching `source()` declaration in local YAML without displaying unrelated
  contents. If it is absent or ambiguous, pause and ask whether to create or
  separately review a source declaration; do not generate a model that points
  to a guessed source.
- For intermediate or marts, the exact existing upstream dbt model name.
- Exact input-column-to-output-column mappings, model description and grain.
- Any requested `not_null` or `unique` tests. Explain that these tests assert
  user-provided data rules and may scan data when later run.

Never ask for passwords, tokens, private keys, connection profiles, or
sensitive row samples. Keep unknown assumptions explicitly unresolved.

## 3. Preview generation

Use the installed `scripts/scaffold_dbt_model.py` from the repository root.
The `--target` is the dbt project directory (the directory containing
`dbt_project.yml`). First preview, providing a `--column` for every approved
output (use `OUTPUT=SOURCE` for a rename):

```bash
python3 scripts/scaffold_dbt_model.py \
  --target pipelines/dbt \
  --layer staging \
  --domain sales \
  --model-name stg_sales__orders \
  --source-name sales_source \
  --source-table customer_order \
  --column order_id \
  --column order_total=order_total_text \
  --description "One row per source order; confirm order grain" \
  --not-null order_id \
  --unique order_id \
  --dry-run
```

For an intermediate or mart model, use `--upstream-model <existing_model>` in
place of the source flags. `--not-null` and `--unique` are optional and may be
repeated for approved output columns. The generator validates simple SQL
identifiers, layer-specific model names, duplicate columns, and test columns.
It creates one `.sql` model and one matching `.yml` file in the selected layer
and domain directory. The SQL uses `source()` for staging and `ref()` for
downstream models, with only the explicitly supplied columns.

Review the entire printed preview and exact output paths. The utility refuses
existing files and symlink destinations; it has no overwrite mode. It does
not edit existing source/model YAML or infer model materialization.

## 4. Approval and verification

Show the user the preview. Ask for explicit approval before rerunning the same
command without `--dry-run`, adding `--yes` only after that approval. If any
project facts or paths changed after preview, preview again. Do not run
`dbt parse`, `dbt compile`, `dbt build`, SQL, or live Snowflake commands as
part of this workflow. After writing, verify that the two expected files exist,
review their contents and report the exact paths. State clearly that the
generated model has not been compiled or run.
