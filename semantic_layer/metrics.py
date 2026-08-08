"""
MetricMind - Semantic Layer
============================
This is the single source of mathematical truth for every business metric.
Neither the AI agent nor any chart is ever allowed to compute a metric its
own way -- everything routes through METRICS below. This is what stops the
LLM from "hallucinating joins" or inventing its own definition of margin:
it can only ever ask this layer for a metric that already exists here.

To add a new governed metric, add one entry to METRICS. Nothing else in
the codebase should ever contain a raw formula for revenue, margin, etc.
"""

from dataclasses import dataclass, field
from typing import Callable, Optional
import pandas as pd


ALLOWED_DIMENSIONS = [
    "region", "country", "department", "product_category", "product_name",
    "customer_segment", "channel", "sales_rep", "quarter_label", "year", "quarter",
]

TIME_DIMENSION = "quarter_label"


@dataclass
class Metric:
    name: str
    description: str
    unit: str
    # aggregate(df) -> float : the governed formula, and the ONLY place
    # this metric's math is allowed to live.
    aggregate: Callable[[pd.DataFrame], float]
    higher_is_better: bool = True


def _revenue(df):
    return df["revenue"].sum()

def _cost(df):
    return df["cost"].sum()

def _profit(df):
    # Governed definition: profit is always revenue - cost, computed on the
    # SAME rows being aggregated (not summed independently), so it can
    # never drift from the underlying transactions.
    return df["revenue"].sum() - df["cost"].sum()

def _gross_margin_pct(df):
    rev = df["revenue"].sum()
    if rev == 0:
        return float("nan")
    return (df["revenue"].sum() - df["cost"].sum()) / rev * 100

def _avg_deal_size(df):
    return df["revenue"].mean() if len(df) else float("nan")

def _churn_rate_pct(df):
    return df["churn_flag"].mean() * 100 if len(df) else float("nan")

def _csat_avg(df):
    return df["csat_score"].mean() if len(df) else float("nan")

def _kpi_attainment_pct(df):
    target = df["kpi_target"].sum()
    if target == 0:
        return float("nan")
    return df["kpi_actual"].sum() / target * 100

def _units_sold(df):
    return df["units_sold"].sum()

def _agent_query_volume(df):
    return df["agentic_query_count"].sum()

def _avg_query_latency_ms(df):
    return df["avg_query_latency_ms"].mean() if len(df) else float("nan")


METRICS: dict[str, Metric] = {
    "revenue":            Metric("revenue", "Total booked revenue", "$", _revenue),
    "cost":                Metric("cost", "Total cost of goods/services delivered", "$", _cost, higher_is_better=False),
    "profit":              Metric("profit", "Revenue minus cost (gross profit, governed)", "$", _profit),
    "gross_margin_pct":    Metric("gross_margin_pct", "Gross profit as % of revenue (governed formula)", "%", _gross_margin_pct),
    "avg_deal_size":       Metric("avg_deal_size", "Average revenue per transaction", "$", _avg_deal_size),
    "churn_rate_pct":      Metric("churn_rate_pct", "% of transactions flagged as churned", "%", _churn_rate_pct, higher_is_better=False),
    "csat_avg":            Metric("csat_avg", "Average customer satisfaction score (1-5)", "score", _csat_avg),
    "kpi_attainment_pct":  Metric("kpi_attainment_pct", "Actual KPI vs target, %", "%", _kpi_attainment_pct),
    "units_sold":          Metric("units_sold", "Total units sold", "units", _units_sold),
    "agent_query_volume":  Metric("agent_query_volume", "Total agentic BI query volume", "queries", _agent_query_volume),
    "avg_query_latency_ms":Metric("avg_query_latency_ms", "Average agent response latency", "ms", _avg_query_latency_ms, higher_is_better=False),
}

# Natural-language synonyms -> governed metric key. This is the ONLY place
# where "margin" is allowed to be interpreted -- it always resolves to the
# same governed metric, so Finance and Sales get identical numbers.
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


def resolve_metric(user_phrase: str) -> Optional[str]:
    """Map a natural-language phrase to a governed metric key, or None if
    it doesn't match anything defined in the semantic layer. This is the
    guardrail: an undefined metric returns None and the agent MUST decline
    rather than guess."""
    phrase = user_phrase.lower().strip()
    if phrase in METRICS:
        return phrase
    for synonym, metric_key in METRIC_SYNONYMS.items():
        if synonym in phrase:
            return metric_key
    return None


def compute(df: pd.DataFrame, metric_key: str, filters: Optional[dict] = None) -> float:
    """The only sanctioned way to get a metric value. Applies filters over
    ALLOWED_DIMENSIONS only, then routes to the metric's governed formula."""
    if metric_key not in METRICS:
        raise ValueError(f"'{metric_key}' is not a governed metric. Refusing to compute an ungoverned number.")

    filtered = df
    if filters:
        for dim, value in filters.items():
            if dim not in ALLOWED_DIMENSIONS:
                raise ValueError(f"'{dim}' is not an allowed dimension.")
            if dim in ("year", "quarter"):
                filtered = filtered[filtered[dim] == value]
            else:
                filtered = filtered[filtered[dim].str.lower() == str(value).lower()]

    return METRICS[metric_key].aggregate(filtered)


def list_metrics() -> str:
    lines = ["Governed metrics available in the semantic layer:"]
    for m in METRICS.values():
        lines.append(f"  - {m.name} ({m.unit}): {m.description}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(list_metrics())
