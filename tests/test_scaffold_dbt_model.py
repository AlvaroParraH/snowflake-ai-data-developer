from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/scaffold_dbt_model.py"


class DbtModelScaffoldTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="snowflake-dbt-scaffold-")
        self.addCleanup(temporary.cleanup)
        self.target = Path(temporary.name) / "pipelines/dbt"
        self.target.mkdir(parents=True)
        (self.target / "dbt_project.yml").write_text(
            'name: test_project\nversion: "1.0.0"\nconfig-version: 2\n'
        )

    def run_scaffold(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-B", str(SCRIPT), "--target", str(self.target), *arguments],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            check=False,
        )

    def staging_arguments(self) -> tuple[str, ...]:
        return (
            "--layer", "staging",
            "--domain", "sales",
            "--model-name", "stg_sales__orders",
            "--source-name", "sales_source",
            "--source-table", "orders",
            "--column", "order_id",
            "--column", "order_total=order_total_text",
            "--description", "One row per order",
        )

    def test_preview_shows_full_plan_without_writing(self) -> None:
        result = self.run_scaffold(*self.staging_arguments(), "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("CREATE models/silver/staging/sales/stg_sales__orders.sql", result.stdout)
        self.assertIn("CREATE models/silver/staging/sales/stg_sales__orders.yml", result.stdout)
        self.assertIn("source('sales_source', 'orders')", result.stdout)
        self.assertIn("order_total_text as order_total", result.stdout)
        self.assertEqual(list(self.target.rglob("*.sql")), [])
        self.assertEqual(
            list(self.target.rglob("*.yml")),
            [self.target / "dbt_project.yml"],
        )

    def test_staging_model_and_yaml_are_written_with_requested_tests(self) -> None:
        result = self.run_scaffold(
            *self.staging_arguments(),
            "--not-null", "ORDER_ID",
            "--unique", "order_id",
            "--yes",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        model = self.target / "models/silver/staging/sales/stg_sales__orders.sql"
        docs = self.target / "models/silver/staging/sales/stg_sales__orders.yml"
        self.assertTrue(model.is_file())
        self.assertIn("from {{ source('sales_source', 'orders') }}", model.read_text())
        self.assertIn("order_total_text as order_total", model.read_text())
        self.assertIn("description: \"One row per order\"", docs.read_text())
        self.assertIn("- not_null", docs.read_text())
        self.assertIn("- unique", docs.read_text())
        self.assertIn("Snowflake were not run", result.stdout)

    def test_intermediate_model_uses_ref(self) -> None:
        result = self.run_scaffold(
            "--layer", "intermediate",
            "--domain", "sales",
            "--model-name", "int_orders__enriched",
            "--upstream-model", "stg_sales__orders",
            "--column", "order_id",
            "--yes",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        model = self.target / "models/silver/intermediate/sales/int_orders__enriched.sql"
        self.assertIn("from {{ ref('stg_sales__orders') }}", model.read_text())

    def test_mart_model_uses_gold_path(self) -> None:
        result = self.run_scaffold(
            "--layer", "marts",
            "--domain", "sales",
            "--model-name", "fct_sales",
            "--upstream-model", "int_orders__enriched",
            "--column", "order_id",
            "--yes",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(
            (self.target / "models/gold/marts/sales/fct_sales.sql").is_file()
        )

    def test_conflicts_and_symlinks_are_refused(self) -> None:
        existing = self.target / "models/silver/staging/sales/stg_sales__orders.sql"
        existing.parent.mkdir(parents=True)
        existing.write_text("preserve\n")
        result = self.run_scaffold(*self.staging_arguments(), "--yes")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Refusing to overwrite", result.stderr)
        self.assertEqual(existing.read_text(), "preserve\n")
        (self.target / "models/silver/staging/sales").rename(
            self.target / "existing-models"
        )
        (self.target / "models/silver/staging/sales").symlink_to(
            self.target / "existing-models", target_is_directory=True
        )
        result = self.run_scaffold(*self.staging_arguments(), "--yes")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("symlink", result.stderr)

    def test_invalid_names_or_unsupported_columns_are_refused(self) -> None:
        result = self.run_scaffold(
            "--layer", "staging", "--domain", "../sales",
            "--model-name", "stg_sales__orders",
            "--source-name", "sales_source", "--source-table", "orders",
            "--column", "order_id", "--dry-run",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Domain must be a lowercase identifier", result.stderr)
        result = self.run_scaffold(
            "--layer", "staging", "--domain", "sales",
            "--model-name", "stg_sales__orders",
            "--source-name", "sales_source", "--source-table", "orders",
            "--column", "order_id; drop table users",
            "--dry-run",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Invalid column mapping", result.stderr)

    def test_requires_existing_dbt_project_and_explicit_columns(self) -> None:
        (self.target / "dbt_project.yml").unlink()
        result = self.run_scaffold(*self.staging_arguments(), "--dry-run")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("dbt_project.yml", result.stderr)
        (self.target / "dbt_project.yml").write_text("name: test_project\n")
        result = self.run_scaffold(
            "--layer", "staging", "--domain", "sales",
            "--model-name", "stg_sales__orders",
            "--source-name", "sales_source", "--source-table", "orders",
            "--dry-run",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("at least one --column", result.stderr)


if __name__ == "__main__":
    unittest.main()
