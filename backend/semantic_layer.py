"""
Step 2 — Semantic Layer (Cube.dev/dbt Semantic Layer stand-in)
Every business metric is defined ONCE here, as code. The agent and the API
are only ever allowed to use these formulas — never invent their own.
"""

# Governed metric definitions (edit formulas here only, never inline elsewhere)
METRICS = {
    "revenue":     "SUM(revenue)",
    "cost":        "SUM(cost)",
    "profit":      "SUM(profit)",
    "margin_pct":  "ROUND(SUM(profit) / SUM(revenue) * 100, 2)",
    "churn_rate":  "ROUND(AVG(churn_flag) * 100, 2)",
    "avg_csat":    "ROUND(AVG(csat_score), 2)",
    "kpi_attainment": "ROUND(SUM(kpi_actual) / SUM(kpi_target) * 100, 2)",
}

# Governed dimensions the agent is allowed to filter/group by
DIMENSIONS = ["region", "country", "department", "product_category",
              "customer_segment", "channel", "sales_rep", "year", "quarter"]


def create_semantic_view(con):
    """Materializes the semantic layer as a DuckDB view built from METRICS."""
    metric_cols = ",\n        ".join(f"{expr} AS {name}" for name, expr in METRICS.items())
    con.execute(f"""
        CREATE OR REPLACE VIEW semantic_metrics AS
        SELECT
            region, country, department, product_category, customer_segment, channel,
            EXTRACT(year FROM date)    AS year,
            EXTRACT(quarter FROM date) AS quarter,
            {metric_cols}
        FROM sales
        GROUP BY region, country, department, product_category, customer_segment,
                 channel, year, quarter
    """)


def build_query(metric: str, filters: dict, group_by: list[str] | None = None) -> str:
    """
    Compiles a SAFE query from a metric name + filters.
    This is the function that replaces "let the LLM write SQL" —
    the LLM only ever supplies metric/filters/group_by; this function
    is the only place that touches SQL syntax.
    """
    if metric not in METRICS:
        raise ValueError(f"Unknown metric '{metric}'. Allowed: {list(METRICS.keys())}")

    # year/quarter aren't real columns on the raw table — derive them from date
    derived = {
        "year": "EXTRACT(year FROM date)",
        "quarter": "EXTRACT(quarter FROM date)",
    }

    def col_expr(dim):
        return derived.get(dim, dim)

    group_exprs = [f"{col_expr(g)} AS {g}" for g in (group_by or [])]
    select_cols = group_exprs + [f"{METRICS[metric]} AS {metric}"]
    sql = f"SELECT {', '.join(select_cols)} FROM sales"

    where_clauses = []
    for dim, value in (filters or {}).items():
        if dim not in DIMENSIONS:
            raise ValueError(f"Unknown filter dimension '{dim}'")
        where_clauses.append(f"{col_expr(dim)} = '{value}'" if dim not in derived else f"{col_expr(dim)} = {value}")
    if where_clauses:
        sql += " WHERE " + " AND ".join(where_clauses)

    if group_by:
        group_exprs_only = [col_expr(g) for g in group_by]
        sql += " GROUP BY " + ", ".join(group_exprs_only)
        sql += " ORDER BY " + ", ".join(group_exprs_only)

    return sql
