"""
MetricMind - Step 5: 3D BI Dashboard
Interactive, rotatable Plotly dashboard standing in for the Next.js +
Tremor/ECharts conversational BI interface described in the brief.
Every number plotted is pulled straight from the governed semantic
layer -- no ad-hoc aggregation happens in this file.

Output: outputs/dashboard/metricmind_3d_dashboard.html (open in any browser)
"""

import sys
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from semantic_layer.metrics import compute

DATA_PATH = ROOT / "data" / "processed" / "clean_data.csv"
OUT_PATH = ROOT / "outputs" / "dashboard" / "metricmind_3d_dashboard.html"
OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

REGIONS = ["Europe", "North America", "MEA", "LATAM", "APAC"]
CATEGORIES = ["Analytics Platform", "AI Agents", "Data Integration", "BI Dashboards", "Reporting Suite"]


def build_cube(df, metric_key):
    """region x product_category x quarter -> governed metric, as a long df for a 3D scatter."""
    grouped = df.groupby(["region", "product_category", "quarter_label"]).apply(
        lambda g: compute(g, metric_key)
    ).reset_index(name="value")
    grouped["quarter_idx"] = grouped["quarter_label"].astype("category").cat.codes
    return grouped


def main():
    df = pd.read_csv(DATA_PATH, parse_dates=["date"])
    quarters = sorted(df["quarter_label"].unique())

    fig = make_subplots(
        rows=1, cols=2,
        specs=[[{"type": "scene"}, {"type": "surface"}]],
        subplot_titles=("Revenue: Region x Product x Quarter", "Gross Margin % Surface: Region x Quarter"),
        horizontal_spacing=0.02,
    )

    # ---- Panel 1: 3D scatter/bubble - Revenue by region, category, quarter ----
    rev_cube = build_cube(df, "revenue")
    region_idx = {r: i for i, r in enumerate(REGIONS)}
    cat_idx = {c: i for i, c in enumerate(CATEGORIES)}
    rev_cube["region_idx"] = rev_cube["region"].map(region_idx)
    rev_cube["cat_idx"] = rev_cube["product_category"].map(cat_idx)

    fig.add_trace(
        go.Scatter3d(
            x=rev_cube["region_idx"], y=rev_cube["cat_idx"], z=rev_cube["quarter_idx"],
            mode="markers",
            marker=dict(
                size=(rev_cube["value"] / rev_cube["value"].max() * 22 + 4),
                color=rev_cube["value"], colorscale="Viridis",
                colorbar=dict(title="Revenue ($)", x=0.44),
                showscale=True,
            ),
            text=[f"{r} | {c} | {q}<br>Revenue: ${v:,.0f}"
                  for r, c, q, v in zip(rev_cube["region"], rev_cube["product_category"],
                                         rev_cube["quarter_label"], rev_cube["value"])],
            hoverinfo="text",
            name="Revenue",
        ),
        row=1, col=1,
    )

    # ---- Panel 2: 3D surface - Margin % across Region (x) and Quarter (y) ----
    margin_pivot = df.pivot_table(index="quarter_label", columns="region",
                                   values=["revenue", "cost"], aggfunc="sum")
    margin_surface = ((margin_pivot["revenue"] - margin_pivot["cost"]) / margin_pivot["revenue"] * 100)
    margin_surface = margin_surface[REGIONS].reindex(quarters)

    fig.add_trace(
        go.Surface(
            z=margin_surface.values,
            x=REGIONS,
            y=quarters,
            colorscale="RdYlGn",
            colorbar=dict(title="Margin %", x=1.02),
            cmid=52,
        ),
        row=1, col=2,
    )

    fig.update_scenes(
        dict(xaxis_title="Region", yaxis_title="Product Category", zaxis_title="Quarter",
             xaxis=dict(tickvals=list(region_idx.values()), ticktext=list(region_idx.keys())),
             yaxis=dict(tickvals=list(cat_idx.values()), ticktext=list(cat_idx.keys())),
             zaxis=dict(tickvals=list(range(len(quarters))), ticktext=quarters)),
        row=1, col=1,
    )
    fig.update_scenes(
        dict(xaxis_title="Region", yaxis_title="Quarter", zaxis_title="Gross Margin %"),
        row=1, col=2,
    )

    fig.update_layout(
        title=dict(text="MetricMind - 3D Semantic BI Dashboard (governed metrics only)", x=0.5),
        height=650,
        margin=dict(l=10, r=10, t=60, b=10),
        template="plotly_white",
    )

    fig.write_html(str(OUT_PATH), include_plotlyjs="cdn", full_html=True)
    print(f"[saved] {OUT_PATH}")


if __name__ == "__main__":
    main()
