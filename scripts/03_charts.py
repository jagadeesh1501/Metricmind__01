"""
MetricMind - Step 3: Chart Generation
Static charts (matplotlib/seaborn) for the report/deck. These mirror
exactly what the conversational agent renders, because both pull from
the same semantic layer -- no separate "chart math".
"""

import sys
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DATA_PATH = ROOT / "data" / "processed" / "clean_data.csv"
CHART_DIR = ROOT / "outputs" / "charts"
CHART_DIR.mkdir(parents=True, exist_ok=True)

sns.set_style("whitegrid")
PALETTE = "viridis"


def savefig(name):
    plt.tight_layout()
    plt.savefig(CHART_DIR / name, dpi=150)
    plt.close()
    print(f"[saved] {CHART_DIR / name}")


def chart_revenue_trend(df):
    trend = df.groupby("quarter_label")["revenue"].sum().reset_index()
    plt.figure(figsize=(12, 5))
    sns.lineplot(data=trend, x="quarter_label", y="revenue", marker="o", color="#2563eb")
    plt.xticks(rotation=45, ha="right")
    plt.title("Quarterly Revenue Trend (All Regions)")
    plt.ylabel("Revenue ($)")
    plt.xlabel("Quarter")
    plt.gca().yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x/1e6:.1f}M"))
    savefig("01_revenue_trend.png")


def chart_margin_by_region(df):
    m = df.groupby("region").apply(
        lambda g: (g["revenue"].sum() - g["cost"].sum()) / g["revenue"].sum() * 100
    ).sort_values()
    plt.figure(figsize=(9, 5))
    colors = ["#dc2626" if v == m.min() else "#2563eb" for v in m.values]
    bars = plt.bar(m.index, m.values, color=colors)
    plt.title("Gross Margin % by Region (lowest highlighted)")
    plt.ylabel("Gross Margin %")
    for b in bars:
        plt.text(b.get_x() + b.get_width()/2, b.get_height() + 0.3, f"{b.get_height():.1f}%", ha="center")
    savefig("02_margin_by_region.png")


def chart_margin_trend_europe_vs_others(df):
    df = df.copy()
    df["is_europe"] = df["region"] == "Europe"
    grp = df.groupby(["quarter_label", "is_europe"]).apply(
        lambda g: (g["revenue"].sum() - g["cost"].sum()) / g["revenue"].sum() * 100
    ).reset_index(name="margin_pct")
    grp["cohort"] = grp["is_europe"].map({True: "Europe", False: "Rest of World"})
    plt.figure(figsize=(12, 5))
    sns.lineplot(data=grp, x="quarter_label", y="margin_pct", hue="cohort", marker="o",
                 palette={"Europe": "#dc2626", "Rest of World": "#2563eb"})
    plt.xticks(rotation=45, ha="right")
    plt.title("Gross Margin % Trend: Europe vs Rest of World")
    plt.ylabel("Gross Margin %")
    plt.xlabel("Quarter")
    savefig("03_margin_trend_europe_vs_row.png")


def chart_revenue_by_category(df):
    cat = df.groupby("product_category")["revenue"].sum().sort_values(ascending=False)
    plt.figure(figsize=(9, 5))
    sns.barplot(x=cat.values, y=cat.index, hue=cat.index, palette=PALETTE, legend=False)
    plt.title("Total Revenue by Product Category")
    plt.xlabel("Revenue ($)")
    plt.gca().xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x/1e6:.1f}M"))
    savefig("04_revenue_by_category.png")


def chart_churn_by_segment(df):
    churn = (df.groupby("customer_segment")["churn_flag"].mean() * 100).sort_values(ascending=False)
    plt.figure(figsize=(8, 5))
    sns.barplot(x=churn.index, y=churn.values, hue=churn.index, palette="rocket", legend=False)
    plt.title("Churn Rate % by Customer Segment")
    plt.ylabel("Churn Rate %")
    savefig("05_churn_by_segment.png")


def chart_csat_vs_latency(df):
    plt.figure(figsize=(8, 6))
    sample = df.sample(min(3000, len(df)), random_state=42)
    sns.scatterplot(data=sample, x="avg_query_latency_ms", y="csat_score",
                     hue="region", alpha=0.5, palette="Set2", s=25)
    plt.title("Agent Query Latency vs Customer Satisfaction")
    plt.xlabel("Avg Query Latency (ms)")
    plt.ylabel("CSAT Score")
    savefig("06_latency_vs_csat.png")


def chart_kpi_attainment_heatmap(df):
    pivot = df.pivot_table(index="region", columns="product_category",
                            values="kpi_actual", aggfunc="sum") / \
            df.pivot_table(index="region", columns="product_category",
                            values="kpi_target", aggfunc="sum") * 100
    plt.figure(figsize=(10, 6))
    sns.heatmap(pivot, annot=True, fmt=".0f", cmap="RdYlGn", center=100)
    plt.title("KPI Attainment % — Region x Product Category")
    savefig("07_kpi_attainment_heatmap.png")


def main():
    df = pd.read_csv(DATA_PATH, parse_dates=["date"])
    chart_revenue_trend(df)
    chart_margin_by_region(df)
    chart_margin_trend_europe_vs_others(df)
    chart_revenue_by_category(df)
    chart_churn_by_segment(df)
    chart_csat_vs_latency(df)
    chart_kpi_attainment_heatmap(df)
    print("\n[done] all charts generated")


if __name__ == "__main__":
    main()
