"""
MetricMind - Step 2: Exploratory Data Analysis
Reads the CLEAN data only (never raw), and writes a plain-text EDA report
plus a correlation heatmap. This is what a Finance/Sales stakeholder would
review before trusting the semantic layer's numbers.
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from semantic_layer.metrics import compute, METRICS

DATA_PATH = ROOT / "data" / "processed" / "clean_data.csv"
CHART_DIR = ROOT / "outputs" / "charts"
REPORT_PATH = ROOT / "outputs" / "eda_report.txt"
CHART_DIR.mkdir(parents=True, exist_ok=True)


def main():
    df = pd.read_csv(DATA_PATH, parse_dates=["date"])
    lines = []

    lines.append("=" * 70)
    lines.append("METRICMIND - EXPLORATORY DATA ANALYSIS REPORT")
    lines.append("=" * 70)
    lines.append(f"\nRows: {len(df):,} | Columns: {df.shape[1]}")
    lines.append(f"Date range: {df['date'].min().date()} to {df['date'].max().date()}")

    lines.append("\n--- Governed Metric Snapshot (whole dataset) ---")
    for key in METRICS:
        val = compute(df, key)
        lines.append(f"  {key:22s} = {val:,.2f} {METRICS[key].unit}")

    lines.append("\n--- Revenue by Region ---")
    lines.append(df.groupby("region")["revenue"].sum().sort_values(ascending=False).round(2).to_string())

    lines.append("\n--- Gross Margin % by Region ---")
    margin_by_region = df.groupby("region").apply(
        lambda g: (g["revenue"].sum() - g["cost"].sum()) / g["revenue"].sum() * 100
        if g["revenue"].sum() else np.nan
    ).sort_values()
    lines.append(margin_by_region.round(2).to_string())

    lines.append("\n--- Revenue by Product Category ---")
    lines.append(df.groupby("product_category")["revenue"].sum().sort_values(ascending=False).round(2).to_string())

    lines.append("\n--- Churn Rate % by Customer Segment ---")
    lines.append((df.groupby("customer_segment")["churn_flag"].mean() * 100).round(2).sort_values(ascending=False).to_string())

    lines.append("\n--- Quarterly Revenue Trend ---")
    lines.append(df.groupby("quarter_label")["revenue"].sum().round(2).to_string())

    lines.append("\n--- Missing Values ---")
    nulls = df.isnull().sum()
    lines.append(nulls[nulls > 0].to_string() if nulls.sum() else "  none")

    lines.append("\n--- Numeric Summary ---")
    lines.append(df[["revenue", "cost", "profit", "gross_margin_pct", "csat_score", "churn_flag"]].describe().round(2).to_string())

    report = "\n".join(lines)
    REPORT_PATH.write_text(report)
    print(report)
    print(f"\n[saved] {REPORT_PATH}")

    # Correlation heatmap
    numeric_df = df[["units_sold", "unit_price", "discount_pct", "revenue", "cost",
                      "profit", "gross_margin_pct", "kpi_attainment_pct", "csat_score",
                      "churn_flag", "agentic_query_count", "avg_query_latency_ms"]]
    plt.figure(figsize=(11, 9))
    sns.heatmap(numeric_df.corr(), annot=True, fmt=".2f", cmap="coolwarm", center=0, square=True)
    plt.title("MetricMind - Feature Correlation Heatmap")
    plt.tight_layout()
    plt.savefig(CHART_DIR / "correlation_heatmap.png", dpi=150)
    plt.close()
    print(f"[saved] {CHART_DIR / 'correlation_heatmap.png'}")


if __name__ == "__main__":
    main()
