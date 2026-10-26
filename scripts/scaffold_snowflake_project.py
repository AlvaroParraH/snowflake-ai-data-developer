"""Render and write a starter Snowflake pipeline project for greenfield setup."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import subprocess
import sys


SOURCE_HINTS = {
    "api": "API or SaaS source",
    "database": "external relational or operational database",
    "files": "files or cloud object storage",
    "streaming": "event stream or message broker",
    "mixed": "multiple source types",
    "undecided": "not selected yet",
}
ENVIRONMENTS = ("not_decided", "dev", "test", "prod")
SENSITIVITIES = ("not_assessed", "public", "internal", "confidential", "personal_data", "regulated")


@dataclass(frozen=True)
class ScaffoldConfig:
    project_name: str = "snowflake_data_project"
    source_type: str = "undecided"
    environment: str = "not_decided"
    owner: str = ""
    description: str = ""
    domain: str = ""
    data_sensitivity: str = "not_assessed"
    consumers: str = ""


def project_slug(value: str) -> str:
    """Convert a directory or display name to a safe dbt project identifier."""
    slug = re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")
    if not slug:
        slug = "snowflake_project"
    if not slug[0].isalpha():
        slug = f"project_{slug}"
    return slug


def validate_config(config: ScaffoldConfig) -> None:
    if not re.fullmatch(r"[a-z][a-z0-9_]*", config.project_name):
        raise ValueError(
            "Project name must be a lowercase dbt identifier (letters, digits, "
            "and underscores; it must start with a letter)."
        )
    if config.source_type not in SOURCE_HINTS:
        raise ValueError(f"source_type must be one of {tuple(SOURCE_HINTS)}.")
    if config.environment not in ENVIRONMENTS:
        raise ValueError(f"environment must be one of {ENVIRONMENTS}.")
    if config.data_sensitivity not in SENSITIVITIES:
        raise ValueError(f"data_sensitivity must be one of {SENSITIVITIES}.")


def _clean(value: str) -> str:
    return " ".join(value.split())


def _display(value: str) -> str:
    return _clean(value) or "Not provided."


def starter_files(config: ScaffoldConfig | None = None) -> dict[Path, bytes]:
    config = config or ScaffoldConfig()
    validate_config(config)
    project_name = config.project_name
    source_hint = SOURCE_HINTS[config.source_type]
    context = {
        "description": _display(config.description),
        "domain": _display(config.domain),
        "owner": _display(config.owner),
        "consumers": _display(config.consumers),
        "environment": config.environment.replace("_", " "),
        "sensitivity": config.data_sensitivity.replace("_", " "),
    }

    return {
        Path("README.md"): f"""# {project_name}

{context["description"]}

## Project context

- **Domain:** {context["domain"]}
- **Owner/team:** {context["owner"]}
- **Data sensitivity:** {context["sensitivity"]}
- **Primary consumers:** {context["consumers"]}
- **Initial environment:** {context["environment"]}
- **Primary source:** {source_hint}

## Project layout

- `pipelines/ingestion/bronze/` - source extraction and raw ingestion.
- `pipelines/dbt/` - Silver transformations and Gold marts.
- `pipelines/orchestration/airflow/dags/` - orchestration.
- `tests/` - local Python test guidance.
- `docs/project-profile.md` - reviewed project context.

## Before implementation

Confirm existing project conventions, data classification, source access,
object ownership, environment boundaries, and deployment workflow. Replace
each clearly marked placeholder before using it.

This scaffold does not install dependencies, create connection profiles or
credentials, connect to Snowflake, execute dbt, or deploy Airflow. Running dbt
after configuring an approved profile can create Snowflake objects.
""".encode(),
        Path(".gitignore"): b"""# Python
.venv/
__pycache__/
*.py[cod]
*.egg-info/

# dbt generated output and local configuration
pipelines/dbt/target/
pipelines/dbt/logs/
pipelines/dbt/dbt_packages/
pipelines/dbt/profiles.yml

# Airflow local state
airflow.cfg
.airflow/
pipelines/orchestration/airflow/logs/

# Local secrets and private keys
.env
.env.*
!.env.example
*.pem
*.p8

# OS/editor
.DS_Store
""",
        Path("docs/project-profile.md"): f"""# Project profile

This is a local planning seed. Review and update it as project facts are
confirmed. Do not put credentials, tokens, private keys, or sensitive
row-level data here.

## Project

- **Name:** {project_name}
- **Purpose:** {context["description"]}
- **Domain:** {context["domain"]}
- **Owner/team:** {context["owner"]}
- **Primary consumers:** {context["consumers"]}
- **Initial environment:** {context["environment"]}
- **Data sensitivity:** {context["sensitivity"]}
- **Primary source type:** {source_hint}

## Confirm before connecting or deploying

- Source systems, data owner, access approval, and ingestion/replay behavior.
- Approved account/environment, roles, warehouse, database, schema, and object
  ownership for each environment; use the approved local authentication
  mechanism without recording connection values here.
- Data classification, retention, masking, sharing, and consumer access rules.
- dbt adapter/version, profile strategy, selected models, and deployment owner.
- Airflow runtime, provider versions, authentication, and release process.
- Testing, CI/CD approvals, rollback, and operational monitoring.

## Decisions and links

TODO: record reviewed decisions and non-secret references.
""".encode(),
        Path("pipelines/ingestion/bronze/README.md"): f"""# Bronze ingestion

**Primary source type selected:** {source_hint}.

`ingest_template.py` is intentionally unimplemented. Use it only as a boundary
placeholder. Before implementing extraction and load logic, agree the source,
approved authentication, data classification, incremental/replay semantics,
error handling, and raw-object ownership. Raw data belongs in Snowflake, not
in this source-code directory.
""".encode(),
        Path("pipelines/ingestion/bronze/ingest_template.py"): f'''"""Unimplemented Bronze ingestion boundary for {project_name}.

Selected source type: {source_hint}.

No network, Snowflake, or credential access is performed by this template.
"""


def extract_and_load() -> None:
    """Implement only after source, replay, and authentication choices are reviewed."""
    raise NotImplementedError(
        "Implement the approved {config.source_type} ingestion workflow first."
    )
'''.encode(),
        Path("pipelines/dbt/README.md"): f"""# dbt project

The dbt project name is `{project_name}`. The starter model at
`models/silver/staging/scaffold_example.sql` is a deterministic zero-row
example and reads no project data. Replace it before selecting it in a real
build. A dbt run can create or change Snowflake objects.

No `profiles.yml`, adapter dependency, package, or lockfile is generated.
Confirm the dbt version, Snowflake adapter, approved profile/authentication
strategy, target environment, object ownership, and deployment workflow before
running dbt.

## Model areas

- `models/silver/staging/`
- `models/silver/intermediate/`
- `models/gold/marts/`
- `tests/` - dbt tests, separate from the root Python test directory.
- `macros/` - reusable SQL macros when needed.
- `snapshots/` - approved history capture when needed.
""".encode(),
        Path("pipelines/dbt/dbt_project.yml"): f'''name: {project_name}
version: "1.0.0"
config-version: 2
profile: {project_name}

model-paths: ["models"]
test-paths: ["tests"]
macro-paths: ["macros"]
snapshot-paths: ["snapshots"]

models:
  {project_name}:
    silver:
      staging:
        +materialized: view
      intermediate:
        +materialized: view
    gold:
      marts:
        +materialized: table
'''.encode(),
        Path("pipelines/dbt/models/silver/staging/scaffold_example.sql"): b"""-- Starter only: deterministic zero-row example with no project data sources.
-- Replace this model and confirm the target/profile before running dbt.
select cast(null as varchar) as scaffold_placeholder
where 1 = 0
""",
        Path("pipelines/dbt/models/silver/staging/_models.yml"): b"""version: 2

models:
  - name: scaffold_example
    description: "Zero-row starter model; replace before using in a real build."
    columns:
      - name: scaffold_placeholder
        description: "Always NULL in this starter model."
""",
        Path("pipelines/dbt/tests/README.md"): b"""# dbt tests

Keep dbt data and generic tests here. Add assertions only after the model
grain, nullability, uniqueness, accepted values, and data-owner expectations
are reviewed. These are separate from the root Python tests.
""",
        Path("pipelines/dbt/macros/README.md"): b"""# dbt macros

Add reusable SQL macros here when a real project need emerges. Keep
project-specific business rules visible in the model unless reuse is useful.
""",
        Path("pipelines/dbt/snapshots/README.md"): b"""# dbt snapshots

Add snapshots only after confirming the source key, change-capture semantics,
history requirements, retention, and Snowflake storage/cost expectations.
""",
        Path("pipelines/orchestration/airflow/README.md"): b"""# Airflow orchestration

`dags/scaffold_pipeline.py` contains a single empty task. It performs no
Snowflake or data operations. Confirm the Airflow runtime, provider versions,
approved authentication, schedule/timezone, and release process before
extending or deploying it.

Do not put credentials or rendered connection profiles in this repository.
""",
        Path("pipelines/orchestration/airflow/dags/scaffold_pipeline.py"): f'''"""Empty Airflow DAG starter for {project_name}; no Snowflake work is performed."""

import pendulum
from airflow import DAG
from airflow.operators.empty import EmptyOperator


with DAG(
    dag_id="{project_name}_pipeline",
    start_date=pendulum.datetime(2025, 1, 1, tz="UTC"),
    schedule=None,
    catchup=False,
    doc_md="Replace the empty task with reviewed project orchestration.",
) as dag:
    placeholder = EmptyOperator(task_id="replace_with_project_tasks")
'''.encode(),
        Path("tests/README.md"): b"""# Local tests

Keep Python unit tests here and keep dbt model tests under
`pipelines/dbt/tests/`. Use mocks or fixtures for external systems; tests should
not require Snowflake credentials or make account calls unless a separately
approved integration-test workflow explicitly provides them.
""",
    }


def plan_scaffold(
    target: Path,
    config: ScaffoldConfig | None = None,
) -> tuple[dict[Path, bytes], list[Path]]:
    files = starter_files(config)
    directories: list[Path] = []
    seen: set[Path] = set()
    conflicts: list[str] = []

    for relative in files:
        current = target
        for part in relative.parts[:-1]:
            current /= part
            if current.is_symlink():
                raise ValueError(f"Refusing symlink directory: {current}")
            if current.exists() and not current.is_dir():
                raise ValueError(f"Not a directory: {current}")
            if not current.exists() and current not in seen:
                directories.append(current.relative_to(target))
                seen.add(current)
        destination = target / relative
        if destination.is_symlink():
            raise ValueError(f"Refusing symlink file: {destination}")
        if destination.exists():
            conflicts.append(relative.as_posix())

    if conflicts:
        raise FileExistsError(
            "Refusing to overwrite existing starter files:\n  "
            + "\n  ".join(conflicts)
        )
    return files, directories


def write_scaffold(target: Path, files: dict[Path, bytes]) -> int:
    written = 0
    for relative, content in files.items():
        current = target
        for part in relative.parts[:-1]:
            current /= part
            if current.is_symlink():
                raise ValueError(f"Refusing symlink directory: {current}")
            if not current.is_dir():
                raise ValueError(f"Not a directory: {current}")
        destination = current / relative.name
        if destination.is_symlink():
            raise ValueError(f"Refusing symlink file: {destination}")
        if destination.exists():
            raise FileExistsError(f"Refusing to overwrite existing starter file: {destination}")
        with destination.open("xb") as stream:
            stream.write(content)
        written += 1
    return written


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Preview or create a Snowflake greenfield pipeline starter scaffold.",
    )
    parser.add_argument("--target", type=Path, required=True, help="Existing greenfield project root")
    parser.add_argument(
        "--project-name",
        help="Lowercase dbt project identifier; defaults to a normalized target-directory name",
    )
    parser.add_argument(
        "--source-type", choices=tuple(SOURCE_HINTS), default="undecided",
        help="Primary source category recorded in the starter context",
    )
    parser.add_argument(
        "--environment", choices=ENVIRONMENTS, default="not_decided",
        help="Initial environment recorded for planning; does not configure a target",
    )
    parser.add_argument("--owner", default="", help="Project owner or team (not a Snowflake role)")
    parser.add_argument("--description", default="", help="One-line project purpose")
    parser.add_argument("--domain", default="", help="Business or data domain")
    parser.add_argument(
        "--data-sensitivity", choices=SENSITIVITIES, default="not_assessed",
        help="Initial data classification; project policy remains authoritative",
    )
    parser.add_argument("--consumers", default="", help="Primary data consumers")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--yes", action="store_true", help="Approve the displayed plan")
    parser.add_argument("--no-git", action="store_true", help="Do not initialize Git")
    args = parser.parse_args()
    project_name = args.project_name or project_slug(args.target.name)
    command = [
        sys.executable,
        str(Path(__file__).with_name("init_project.py")),
        "--target",
        str(args.target),
        "--scaffold",
        "--project-name",
        project_name,
        "--source-type",
        args.source_type,
        "--environment",
        args.environment,
        "--owner",
        args.owner,
        "--description",
        args.description,
        "--domain",
        args.domain,
        "--data-sensitivity",
        args.data_sensitivity,
        "--consumers",
        args.consumers,
    ]
    if args.dry_run:
        command.append("--dry-run")
    if args.yes:
        command.append("--yes")
    if args.no_git:
        command.append("--no-git")
    return subprocess.run(command, check=False).returncode


if __name__ == "__main__":
    sys.exit(main())
