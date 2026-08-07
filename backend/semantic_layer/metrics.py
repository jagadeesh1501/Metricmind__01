"""
MetricMind Backend - Semantic Layer (Cube.dev / dbt Semantic Layer stand-in)
=============================================================================
Single source of mathematical truth. Every metric is one governed SQL
aggregate expression, defined ONCE. Nothing else in the codebase -- not
the orchestrator, not the API, not the frontend -- is allowed to write
its own revenue/margin formula.

compute() is the ONLY function permitted to build a SQL query. It only
ever interpolates column names pulled from ALLOWED_DIMENSIONS (a fixed
whitelist), and always parameterizes filter VALUES -- so even though the
orchestrator/agent decides *which* metric and *which* filters, it can
never inject arbitrary SQL or invent a new formula.
"""

from dataclasses import dataclass
from typing import Callable, Optional


ALLOWED_DIMENSIONS = [
    "region", "country", "department", "product_category", "product_name",
    "customer_segment", "channel", "sales_rep", "quarter_label", "year", "quarter",
]
TIME_DIMENSION = "quarter_label"


@dataclass
class Metric:
    key: str
    description: str
    unit: str
    sql_expr: str            # governed aggregate expression, e.g. "SUM(revenue)"
    higher_is_better: bool = True


METRICS: dict[str, Metric] = {
    "revenue": Metric("revenue", "Total booked revenue", "$",
                       "SUM(revenue)"),
    "cost": Metric("cost", "Total cost of goods/services delivered", "$",
                    "SUM(cost)", higher_is_better=False),
    "profit": Metric("profit", "Revenue minus cost (governed)", "$",
                      "SUM(revenue) - SUM(cost)"),
    "gross_margin_pct": Metric("gross_margin_pct", "Gross profit as % of revenue (governed formula)", "%",
                                "(SUM(revenue) - SUM(cost)) / NULLIF(SUM(revenue), 0) * 100"),
    "avg_deal_size": Metric("avg_deal_size", "Average revenue per transaction", "$",
                             "AVG(revenue)"),
    "churn_rate_pct": Metric("churn_rate_pct", "% of transactions flagged as churned", "%",
                              "AVG(churn_flag) * 100", higher_is_better=False),
    "csat_avg": Metric("csat_avg", "Average customer satisfaction score (1-5)", "score",
                        "AVG(csat_score)"),
    "kpi_attainment_pct": Metric("kpi_attainment_pct", "Actual KPI vs target, %", "%",
                                  "SUM(kpi_actual) / NULLIF(SUM(kpi_target), 0) * 100"),
    "units_sold": Metric("units_sold", "Total units sold", "units",
                          "SUM(units_sold)"),
    "agent_query_volume": Metric("agent_query_volume", "Total agentic BI query volume", "queries",
                                  "SUM(agentic_query_count)"),
    "avg_query_latency_ms": Metric("avg_query_latency_ms", "Average agent response latency", "ms",
                                    "AVG(avg_query_latency_ms)", higher_is_better=False),
}

METRIC_SYNONYMS = {
    "revenue": "revenue", "sales": "revenue", "topline": "revenue",
    "cost": "cost", "costs": "cost", "spend": "cost",
    "profit": "profit", "profits": "profit",
    "margin": "gross_margin_pct", "margins": "gross_margin_pct",
    "gross margin": "gross_margin_pct", "gm": "gross_margin_pct",
    "deal size": "avg_deal_size", "average deal": "avg_deal_size",
    "churn": "churn_rate_pct", "churn rate": "churn_rate_pct",
    "csat": "csat_avg", "satisfaction": "csat_avg",
    "kpi": "kpi_attainment_pct", "kpi attainment": "kpi_attainment_pct", "target": "kpi_attainment_pct",
    "units": "units_sold", "volume": "units_sold",
    "query volume": "agent_query_volume", "agent usage": "agent_query_volume",
    "latency": "avg_query_latency_ms", "response time": "avg_query_latency_ms",
}


def resolve_metric(phrase: str) -> Optional[str]:
    """NL phrase -> governed metric key, or None. None means the caller
    MUST decline rather than guess a formula."""
    phrase = phrase.lower().strip()
    if phrase in METRICS:
        return phrase
    for synonym, key in METRIC_SYNONYMS.items():
        if synonym in phrase:
            return key
    return None


def compute(wh, metric_key: str, filters: Optional[dict] = None) -> float:
    """The only sanctioned way to get a governed number. `wh` is a
    warehouse.Warehouse instance."""
    if metric_key not in METRICS:
        raise ValueError(f"'{metric_key}' is not a governed metric.")

    where_clauses, params = [], []
    if filters:
        for dim, value in filters.items():
            if dim not in ALLOWED_DIMENSIONS:
                raise ValueError(f"'{dim}' is not an allowed dimension.")
            if dim in ("year", "quarter"):
                where_clauses.append(f"{dim} = ?")
                params.append(value)
            else:
                where_clauses.append(f"lower({dim}) = lower(?)")
                params.append(str(value))

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
    sql = f"SELECT {METRICS[metric_key].sql_expr} AS value FROM transactions {where_sql}"
    return wh.query_scalar(sql, params)


def list_metrics() -> list[dict]:
    return [
        {"key": m.key, "description": m.description, "unit": m.unit,
         "higher_is_better": m.higher_is_better}
        for m in METRICS.values()
    ]
