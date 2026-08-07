"""MetricMind Backend - data_pipeline.cleaning
Importable + runnable. Same logic as the original scripts/01_data_cleaning.py,
now callable from the API (POST /api/pipeline/clean) as well as from the CLI.
"""

import pandas as pd
import numpy as np
from pathlib import Path

RAW_PATH = Path(__file__).resolve().parents[2] / "data" / "raw" / "metricmind_enterprise_analytics_.csv"
OUT_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"


def clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df = df.drop_duplicates(subset="transaction_id", keep="first")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])

    numeric_cols = ["units_sold", "unit_price", "discount_pct", "revenue",
                     "cost", "profit", "kpi_target", "kpi_actual",
                     "csat_score", "agentic_query_count", "avg_query_latency_ms"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=numeric_cols)

    df = df[(df["revenue"] >= 0) & (df["cost"] >= 0) & (df["units_sold"] >= 0)]
    df["profit"] = (df["revenue"] - df["cost"]).round(2)
    df["csat_score"] = df["csat_score"].clip(1, 5)

    cap = df["revenue"].quantile(0.995)
    df.loc[df["revenue"] > cap, "revenue"] = cap

    text_cols = ["region", "country", "department", "product_category",
                 "product_name", "customer_segment", "channel", "sales_rep"]
    for col in text_cols:
        df[col] = df[col].astype(str).str.strip()

    df["year"] = df["date"].dt.year
    df["quarter"] = df["date"].dt.quarter
    df["quarter_label"] = df["year"].astype(str) + "-Q" + df["quarter"].astype(str)
    df["month"] = df["date"].dt.to_period("M").astype(str)

    df["gross_margin_pct"] = np.where(df["revenue"] > 0, (df["profit"] / df["revenue"]) * 100, np.nan)
    df["kpi_attainment_pct"] = np.where(df["kpi_target"] > 0, (df["kpi_actual"] / df["kpi_target"]) * 100, np.nan)

    return df.sort_values("date").reset_index(drop=True)


def run(raw_path: Path = RAW_PATH, out_dir: Path = OUT_DIR) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(raw_path)
    clean_df = clean(df)
    csv_out, parquet_out = out_dir / "clean_data.csv", out_dir / "clean_data.parquet"
    clean_df.to_csv(csv_out, index=False)
    clean_df.to_parquet(parquet_out, index=False)
    return {"rows_in": len(df), "rows_out": len(clean_df), "csv": str(csv_out), "parquet": str(parquet_out)}


if __name__ == "__main__":
    print(run())
