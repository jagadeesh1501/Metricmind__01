"""MetricMind Backend - data_pipeline.charts
Generates the static chart set into outputs/charts/, and is also callable
from the API (POST /api/pipeline/charts) to regenerate on demand.
"""

from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns

ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "data" / "processed" / "clean_data.csv"
CHART_DIR = ROOT / "outputs" / "charts"

sns.set_style("whitegrid")


def _save(name):
    plt.tight_layout()
    plt.savefig(CHART_DIR / name, dpi=150)
    plt.close()


def run(data_path: Path = DATA_PATH, chart_dir: Path = CHART_DIR) -> list:
    chart_dir.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(data_path, parse_dates=["date"])
    generated = []

    trend = df.groupby("quarter_label")["revenue"].sum().reset_index()
    plt.figure(figsize=(12, 5))
    sns.lineplot(data=trend, x="quarter_label", y="revenue", marker="o", color="#2563eb")
    plt.xticks(rotation=45, ha="right")
    plt.title("Quarterly Revenue Trend (All Regions)")
    plt.gca().yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x/1e6:.1f}M"))
    _save("01_revenue_trend.png"); generated.append("01_revenue_trend.png")

    m = df.groupby("region").apply(lambda g: (g["revenue"].sum() - g["cost"].sum()) / g["revenue"].sum() * 100).sort_values()
    plt.figure(figsize=(9, 5))
    colors = ["#dc2626" if v == m.min() else "#2563eb" for v in m.values]
    plt.bar(m.index, m.values, color=colors)
    plt.title("Gross Margin % by Region (lowest highlighted)")
    _save("02_margin_by_region.png"); generated.append("02_margin_by_region.png")

    df2 = df.copy()
    df2["is_europe"] = df2["region"] == "Europe"
    grp = df2.groupby(["quarter_label", "is_europe"]).apply(
        lambda g: (g["revenue"].sum() - g["cost"].sum()) / g["revenue"].sum() * 100
    ).reset_index(name="margin_pct")
    grp["cohort"] = grp["is_europe"].map({True: "Europe", False: "Rest of World"})
    plt.figure(figsize=(12, 5))
    sns.lineplot(data=grp, x="quarter_label", y="margin_pct", hue="cohort", marker="o",
                 palette={"Europe": "#dc2626", "Rest of World": "#2563eb"})
    plt.xticks(rotation=45, ha="right")
    plt.title("Gross Margin % Trend: Europe vs Rest of World")
    _save("03_margin_trend_europe_vs_row.png"); generated.append("03_margin_trend_europe_vs_row.png")

    cat = df.groupby("product_category")["revenue"].sum().sort_values(ascending=False)
    plt.figure(figsize=(9, 5))
    sns.barplot(x=cat.values, y=cat.index, hue=cat.index, palette="viridis", legend=False)
    plt.title("Total Revenue by Product Category")
    plt.gca().xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x/1e6:.1f}M"))
    _save("04_revenue_by_category.png"); generated.append("04_revenue_by_category.png")

    churn = (df.groupby("customer_segment")["churn_flag"].mean() * 100).sort_values(ascending=False)
    plt.figure(figsize=(8, 5))
    sns.barplot(x=churn.index, y=churn.values, hue=churn.index, palette="rocket", legend=False)
    plt.title("Churn Rate % by Customer Segment")
    _save("05_churn_by_segment.png"); generated.append("05_churn_by_segment.png")

    plt.figure(figsize=(8, 6))
    sample = df.sample(min(3000, len(df)), random_state=42)
    sns.scatterplot(data=sample, x="avg_query_latency_ms", y="csat_score", hue="region", alpha=0.5, palette="Set2", s=25)
    plt.title("Agent Query Latency vs Customer Satisfaction")
    _save("06_latency_vs_csat.png"); generated.append("06_latency_vs_csat.png")

    pivot = df.pivot_table(index="region", columns="product_category", values="kpi_actual", aggfunc="sum") / \
            df.pivot_table(index="region", columns="product_category", values="kpi_target", aggfunc="sum") * 100
    plt.figure(figsize=(10, 6))
    sns.heatmap(pivot, annot=True, fmt=".0f", cmap="RdYlGn", center=100)
    plt.title("KPI Attainment % — Region x Product Category")
    _save("07_kpi_attainment_heatmap.png"); generated.append("07_kpi_attainment_heatmap.png")

    return generated


if __name__ == "__main__":
    print(run())
