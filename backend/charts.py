"""
Step 4 — Data Visualization layer (Plotly, feeding ECharts-style JSON to the frontend)
Converts a query result into chart-ready JSON so Next.js/Tremor/ECharts can render it
without needing to know anything about SQL or DuckDB.
"""
import plotly.express as px
import pandas as pd


def make_chart_json(rows: list[dict], metric: str, x_field: str = "quarter"):
    """Builds a simple line/bar chart and returns Plotly figure JSON (frontend-ready)."""
    if not rows:
        return None
    df = pd.DataFrame(rows)
    if x_field in df.columns:
        fig = px.line(df, x=x_field, y=metric, markers=True, title=metric.replace("_", " ").title())
    else:
        fig = px.bar(df, y=metric, title=metric.replace("_", " ").title())
    return fig.to_json()
