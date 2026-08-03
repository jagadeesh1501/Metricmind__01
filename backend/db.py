"""
Step 1 — Data Lakehouse layer (DuckDB stand-in for Snowflake/Databricks)
Loads the CSV into DuckDB and exposes a single connection to the rest of the app.
"""
import duckdb
import os

CSV_PATH = os.path.join(os.path.dirname(__file__), "metricmind_enterprise_analytics_20k.csv")
DB_PATH = os.path.join(os.path.dirname(__file__), "metricmind.duckdb")


def get_connection():
    """Returns a DuckDB connection with the raw sales table loaded."""
    con = duckdb.connect(DB_PATH)
    con.execute(f"""
        CREATE TABLE IF NOT EXISTS sales AS
        SELECT * FROM read_csv_auto('{CSV_PATH}')
    """)
    return con


if __name__ == "__main__":
    con = get_connection()
    print(con.execute("SELECT COUNT(*) FROM sales").fetchall())
