"""
Step 4 — Data Visualization layer (ECharts, matching the official brief)
Converts a query result into an ECharts `option` object (as JSON) so the
Next.js frontend can render it directly with echarts-for-react.
"""


def make_chart_json(rows: list[dict], metric: str, x_field: str = "quarter"):
    """Builds an ECharts option config and returns it as a dict (frontend-ready)."""
    if not rows:
        return None

    has_x = x_field in rows[0]
    categories = [str(r[x_field]) for r in rows] if has_x else [str(i) for i in range(len(rows))]
    values = [r[metric] for r in rows]

    option = {
        "title": {"text": metric.replace("_", " ").title(), "textStyle": {"fontSize": 13}},
        "grid": {"left": 50, "right": 24, "top": 50, "bottom": 40, "containLabel": True},
        "tooltip": {"trigger": "axis"},
        "xAxis": {"type": "category", "data": categories, "name": x_field if has_x else "index"},
        "yAxis": {"type": "value"},
        "series": [
            {
                "data": values,
                "type": "line" if has_x and len(rows) > 1 else "bar",
                "smooth": True,
                "symbolSize": 8,
                "barWidth": 40,
            }
        ],
    }
    return option