"""
MetricMind Backend - Warehouse module (stand-in for Snowflake/Databricks)
===========================================================================
Loads the cleaned CSV into an in-process DuckDB table so the semantic layer
can compile governed SQL against it. Swapping DuckDB for Snowflake/Databricks
in production means changing only the connection string in __init__ --
every governed query above this layer (semantic_layer/metrics.py,
orchestrator.py) is written in portable SQL and doesn't change.
"""

import duckdb
from pathlib import Path

DEFAULT_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "processed" / "clean_data.csv"


class Warehouse:
    def __init__(self, csv_path: Path = DEFAULT_DATA_PATH):
        if not csv_path.exists():
            raise FileNotFoundError(
                f"{csv_path} not found. Run the data pipeline first: "
                f"python3 backend/data_pipeline/cleaning.py"
            )
        self.con = duckdb.connect(database=":memory:")
        self.con.execute(
            f"CREATE TABLE transactions AS SELECT * FROM read_csv_auto('{csv_path}', dateformat='%Y-%m-%d')"
        )
        self.row_count = self.con.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]

    def query_df(self, sql: str, params: list | None = None):
        """Run governed SQL, return a pandas DataFrame."""
        return self.con.execute(sql, params or []).fetchdf()

    def query_scalar(self, sql: str, params: list | None = None):
        """Run governed SQL, return a single scalar value."""
        row = self.con.execute(sql, params or []).fetchone()
        return row[0] if row else None

    def distinct_values(self, column: str) -> list:
        return [r[0] for r in self.con.execute(
            f"SELECT DISTINCT {column} FROM transactions ORDER BY {column}"
        ).fetchall()]
