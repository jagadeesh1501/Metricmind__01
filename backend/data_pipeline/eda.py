"""MetricMind Backend - data_pipeline.eda
Produces a JSON-friendly EDA summary the API can serve directly
(GET /api/pipeline/eda), plus writes the plain-text report to disk.
"""

from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "data" / "processed" / "clean_data.csv"
REPORT_PATH = ROOT / "outputs" / "eda_report.txt"


def run(data_path: Path = DATA_PATH, report_path: Path = REPORT_PATH) -> dict:
    df = pd.read_csv(data_path, parse_dates=["date"])
    report_path.parent.mkdir(parents=True, exist_ok=True)

    revenue_by_region = df.groupby("region")["revenue"].sum().sort_values(ascending=False).round(2).to_dict()
    margin_by_region = df.groupby("region").apply(
        lambda g: (g["revenue"].sum() - g["cost"].sum()) / g["revenue"].sum() * 100 if g["revenue"].sum() else np.nan
    ).round(2).sort_values().to_dict()
    churn_by_segment = (df.groupby("customer_segment")["churn_flag"].mean() * 100).round(2).sort_values(ascending=False).to_dict()
    quarterly_revenue = df.groupby("quarter_label")["revenue"].sum().round(2).to_dict()

    summary = {
        "rows": len(df),
        "columns": df.shape[1],
        "date_range": [str(df["date"].min().date()), str(df["date"].max().date())],
        "missing_values": int(df.isnull().sum().sum()),
        "revenue_by_region": revenue_by_region,
        "margin_by_region_pct": margin_by_region,
        "churn_by_segment_pct": churn_by_segment,
        "quarterly_revenue": quarterly_revenue,
    }

    lines = ["METRICMIND EDA SUMMARY", "=" * 40]
    for k, v in summary.items():
        lines.append(f"\n{k}:\n{v}")
    report_path.write_text("\n".join(lines))

    return summary


if __name__ == "__main__":
    import json
    print(json.dumps(run(), indent=2, default=str))
