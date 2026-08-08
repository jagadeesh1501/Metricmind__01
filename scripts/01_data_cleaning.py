"""
MetricMind - Step 1: Data Cleaning
Loads the raw enterprise analytics extract, validates it, fixes common
data-quality issues, engineers time dimensions, and writes a clean
parquet+csv pair that every downstream module (EDA, semantic layer,
agent, dashboard) reads from. This is the ONLY place raw data is touched.
"""

import pandas as pd
import numpy as np
from pathlib import Path

RAW_PATH = Path(__file__).resolve().parents[1] / "data" / "raw" / "metricmind_enterprise_analytics_.csv"
OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "processed"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def load_raw(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    print(f"[load] {len(df):,} rows, {df.shape[1]} columns")
    return df


def clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # 1. Drop exact duplicate transactions
    before = len(df)
    df = df.drop_duplicates(subset="transaction_id", keep="first")
    print(f"[dedupe] removed {before - len(df)} duplicate transaction_id rows")

    # 2. Parse dates, drop unparseable rows instead of silently coercing them
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    bad_dates = df["date"].isna().sum()
    if bad_dates:
        print(f"[dates] dropping {bad_dates} rows with unparseable dates")
        df = df.dropna(subset=["date"])

    # 3. Numeric sanity checks - financial fields cannot be negative
    numeric_cols = ["units_sold", "unit_price", "discount_pct", "revenue",
                     "cost", "profit", "kpi_target", "kpi_actual",
                     "csat_score", "agentic_query_count", "avg_query_latency_ms"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    before = len(df)
    df = df.dropna(subset=numeric_cols)
    print(f"[numeric] dropped {before - len(df)} rows with non-numeric values")

    negative_mask = (df["revenue"] < 0) | (df["cost"] < 0) | (df["units_sold"] < 0)
    if negative_mask.any():
        print(f"[sanity] dropping {negative_mask.sum()} rows with negative revenue/cost/units")
        df = df[~negative_mask]

    # 4. Recompute profit from source columns rather than trusting the raw
    #    field -- this guarantees profit is always internally consistent,
    #    which is the whole point of a governed semantic layer later on.
    df["profit"] = (df["revenue"] - df["cost"]).round(2)

    # 5. Clip csat_score to its valid 1-5 scale (defensive - protects any
    #    future data refresh from silently corrupting downstream metrics)
    df["csat_score"] = df["csat_score"].clip(1, 5)

    # 6. Winsorize extreme revenue outliers (>99.5th pct) instead of
    #    dropping them, so a handful of enterprise mega-deals don't
    #    get lost but also don't dominate every chart.
    cap = df["revenue"].quantile(0.995)
    outliers = (df["revenue"] > cap).sum()
    if outliers:
        print(f"[outliers] capping {outliers} extreme revenue rows at {cap:,.2f}")
        df.loc[df["revenue"] > cap, "revenue"] = cap

    # 7. Standardize text columns
    text_cols = ["region", "country", "department", "product_category",
                 "product_name", "customer_segment", "channel", "sales_rep"]
    for col in text_cols:
        df[col] = df[col].astype(str).str.strip()

    # 8. Engineer time dimensions the semantic layer will rely on
    df["year"] = df["date"].dt.year
    df["quarter"] = df["date"].dt.quarter
    df["quarter_label"] = df["year"].astype(str) + "-Q" + df["quarter"].astype(str)
    df["month"] = df["date"].dt.to_period("M").astype(str)

    # 9. Derived ratios used across EDA / agent / dashboard
    df["gross_margin_pct"] = np.where(
        df["revenue"] > 0, (df["profit"] / df["revenue"]) * 100, np.nan
    )
    df["kpi_attainment_pct"] = np.where(
        df["kpi_target"] > 0, (df["kpi_actual"] / df["kpi_target"]) * 100, np.nan
    )

    df = df.sort_values("date").reset_index(drop=True)
    return df


def main():
    df = load_raw(RAW_PATH)
    clean_df = clean(df)

    csv_out = OUT_DIR / "clean_data.csv"
    parquet_out = OUT_DIR / "clean_data.parquet"
    clean_df.to_csv(csv_out, index=False)
    clean_df.to_parquet(parquet_out, index=False)

    print(f"\n[done] {len(clean_df):,} clean rows written to:")
    print(f"   {csv_out}")
    print(f"   {parquet_out}")
    print(f"\n[sample]\n{clean_df.head(3)}")


if __name__ == "__main__":
    main()
