"""
MetricMind - Step 4: Agentic Orchestrator
==========================================
This is the "LLM as orchestrator, not SQL writer" piece from the brief.

Design: the agent NEVER writes SQL and never touches raw rows with its
own logic. Its only job is:
  1. Parse the executive's question -> (metric, dimensions, time window)
  2. Call semantic_layer.compute() for the governed numbers
  3. If it's a "why" question, decompose the delta across sub-dimensions
     using the SAME governed metric, and rank the drivers
  4. Turn the numbers into a plain-English, multi-step explanation

Swapping in a real LLM (LangChain + Llama 3 / Claude): replace
`_extract_intent()` with a tool-calling LLM call whose only allowed
tool is `semantic_layer.compute(metric, filters)`. Because the tool's
schema only accepts governed metric keys and allowed dimensions, the
LLM is structurally prevented from hallucinating a formula -- this
file works identically whether intent parsing is regex-based (as
below, so it runs with zero API keys) or LLM-based.
"""

import re
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from semantic_layer.metrics import compute, resolve_metric, METRICS, ALLOWED_DIMENSIONS

DATA_PATH = ROOT / "data" / "processed" / "clean_data.csv"

REGIONS = ["Europe", "North America", "MEA", "LATAM", "APAC"]
CATEGORIES = ["Analytics Platform", "AI Agents", "Data Integration", "BI Dashboards", "Reporting Suite"]
SEGMENTS = ["Startup", "Mid-Market", "Enterprise", "SMB"]
QUARTER_WORDS = {"last quarter", "previous quarter", "prior quarter"}


@dataclass
class Intent:
    metric_key: Optional[str]
    region: Optional[str] = None
    category: Optional[str] = None
    segment: Optional[str] = None
    is_why_question: bool = False
    is_trend_question: bool = False
    wants_last_quarter: bool = False


class MetricMindAgent:
    """Agentic orchestrator: NL question -> semantic layer calls -> answer."""

    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.quarters = sorted(df["quarter_label"].unique())

    # ---------- 1. Intent extraction (stand-in for LLM tool-calling) ----------
    def _extract_intent(self, question: str) -> Intent:
        q = question.lower()

        metric_key = resolve_metric(q)

        region = next((r for r in REGIONS if r.lower() in q), None)
        category = next((c for c in CATEGORIES if c.lower() in q), None)
        segment = next((s for s in SEGMENTS if s.lower() in q), None)

        is_why = bool(re.search(r"\bwhy\b", q))
        is_trend = bool(re.search(r"\btrend|over time|by quarter|history\b", q))
        wants_last_q = any(phrase in q for phrase in QUARTER_WORDS)

        return Intent(metric_key, region, category, segment, is_why, is_trend, wants_last_q)

    # ---------- 2. Governed computation ----------
    def _filters_for(self, intent: Intent) -> dict:
        filters = {}
        if intent.region:
            filters["region"] = intent.region
        if intent.category:
            filters["product_category"] = intent.category
        if intent.segment:
            filters["customer_segment"] = intent.segment
        return filters

    def _resolve_quarter_pair(self):
        """Returns (current_quarter_label, previous_quarter_label)."""
        return self.quarters[-1], self.quarters[-2]

    # ---------- 3. "Why did X drop" decomposition ----------
    def _explain_drop(self, intent: Intent) -> str:
        metric = METRICS[intent.metric_key]
        base_filters = self._filters_for(intent)
        cur_q, prev_q = self._resolve_quarter_pair()

        cur_val = compute(self.df, intent.metric_key, {**base_filters, "quarter_label": cur_q})
        prev_val = compute(self.df, intent.metric_key, {**base_filters, "quarter_label": prev_q})
        delta = cur_val - prev_val
        direction = "dropped" if delta < 0 else "rose"

        lines = []
        scope = intent.region or "Global"
        lines.append(f"**{metric.name} ({scope})**: {prev_q} = {prev_val:,.2f}{metric.unit} -> "
                      f"{cur_q} = {cur_val:,.2f}{metric.unit}  ({direction} by {abs(delta):,.2f}{metric.unit})")

        # Decompose by product_category to find the driver, using the
        # SAME governed metric -- this is the "multi-step analytical
        # explanation" the brief asks for.
        drivers = []
        scoped_df_cur = self.df.copy()
        scoped_df_prev = self.df.copy()
        if intent.region:
            scoped_df_cur = scoped_df_cur[scoped_df_cur["region"] == intent.region]
            scoped_df_prev = scoped_df_prev[scoped_df_prev["region"] == intent.region]

        for cat in CATEGORIES:
            cur_c = compute(self.df, intent.metric_key, {**base_filters, "quarter_label": cur_q, "product_category": cat})
            prev_c = compute(self.df, intent.metric_key, {**base_filters, "quarter_label": prev_q, "product_category": cat})
            if prev_c == prev_c and cur_c == cur_c:  # not NaN
                drivers.append((cat, cur_c - prev_c))

        drivers.sort(key=lambda x: x[1])
        lines.append(f"\nBreaking {metric.name} down by product line ({prev_q} -> {cur_q}):")
        for cat, d in drivers:
            arrow = "down" if d < 0 else "up"
            lines.append(f"  - {cat:20s}: {arrow} {abs(d):,.2f}{metric.unit}")

        biggest = drivers[0]
        lines.append(f"\n**Primary driver**: {biggest[0]} contributed the largest swing "
                      f"({biggest[1]:,.2f}{metric.unit}) to the {scope} {metric.name} {direction} in {cur_q}.")

        # Also check discount / cost pressure as a secondary explanation for margin questions
        if intent.metric_key == "gross_margin_pct":
            cur_cost_ratio = compute(self.df, "cost", {**base_filters, "quarter_label": cur_q}) / \
                              max(compute(self.df, "revenue", {**base_filters, "quarter_label": cur_q}), 1e-9)
            prev_cost_ratio = compute(self.df, "cost", {**base_filters, "quarter_label": prev_q}) / \
                               max(compute(self.df, "revenue", {**base_filters, "quarter_label": prev_q}), 1e-9)
            lines.append(f"\nCost-to-revenue ratio moved from {prev_cost_ratio*100:.1f}% to {cur_cost_ratio*100:.1f}% "
                         f"over the same period, {'which is consistent with rising delivery/discount costs.' if cur_cost_ratio > prev_cost_ratio else 'so cost pressure is not the main cause.'}")

        return "\n".join(lines)

    # ---------- 4. Simple point-in-time / trend answers ----------
    def _answer_simple(self, intent: Intent) -> str:
        metric = METRICS[intent.metric_key]
        filters = self._filters_for(intent)
        scope = intent.region or intent.category or intent.segment or "Global"

        if intent.is_trend_question:
            trend = self.df.copy()
            if intent.region:
                trend = trend[trend["region"] == intent.region]
            series = trend.groupby("quarter_label").apply(
                lambda g: compute(g, intent.metric_key)
            )
            lines = [f"**{metric.name} trend ({scope})**:"]
            for q, v in series.items():
                lines.append(f"  {q}: {v:,.2f}{metric.unit}")
            return "\n".join(lines)

        val = compute(self.df, intent.metric_key, filters)
        return f"**{metric.name} ({scope})** = {val:,.2f}{metric.unit}\n({metric.description})"

    # ---------- Entry point ----------
    def ask(self, question: str) -> str:
        intent = self._extract_intent(question)

        if intent.metric_key is None:
            return (f"I can't answer that -- '{question}' doesn't map to a metric defined in the "
                     f"semantic layer, and I won't guess a formula. "
                     f"Governed metrics are: {', '.join(METRICS.keys())}.")

        header = f"> \"{question}\"\n"
        if intent.is_why_question:
            return header + self._explain_drop(intent)
        return header + self._answer_simple(intent)


def main():
    df = pd.read_csv(DATA_PATH, parse_dates=["date"])
    agent = MetricMindAgent(df)

    demo_questions = [
        "Why did our European margins drop last quarter?",
        "What is our global revenue this quarter?",
        "Show me the churn trend for Enterprise customers",
        "What's the average deal size in APAC?",
        "Why did North America revenue change last quarter?",
        "What is our customer NPS score?",  # ungoverned -> must decline
    ]

    print("=" * 78)
    print("METRICMIND CONVERSATIONAL AGENT - DEMO SESSION")
    print("=" * 78)
    for q in demo_questions:
        print("\n" + agent.ask(q))
        print("-" * 78)


if __name__ == "__main__":
    main()
