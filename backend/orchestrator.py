"""
MetricMind Backend - Agentic Orchestrator
============================================
The LLM/agent layer. It NEVER writes SQL and never touches `transactions`
directly. Its only job:
  1. Parse the question -> (metric, dimensions, time window, question type)
  2. Call semantic_layer.compute(warehouse, metric, filters) for governed numbers
  3. For "why" questions, decompose the delta across product_category using
     the SAME governed metric, and rank drivers
  4. Return a plain-English, multi-step explanation + structured data the
     frontend can chart

Two interchangeable intent-extraction backends, same architecture either way:
  - RuleBasedIntentParser (default): regex/keyword matching, zero API keys,
    fully deterministic, so the whole project runs offline.
  - LLMIntentParser (optional): real tool-calling via the Anthropic API.
    Activate by setting ANTHROPIC_API_KEY. Its ONLY tool is
    semantic_layer.compute(metric, filters) -- the tool schema itself
    (governed metric keys + allowed dimensions only) is what prevents
    hallucination, not which parser is in front of it. If the key isn't
    set, or the call fails for any reason, the orchestrator transparently
    falls back to the rule-based parser so the API never has to be "up"
    for the app to work.
"""

import os
import re
import json
from dataclasses import dataclass
from typing import Optional

from semantic_layer.metrics import compute, resolve_metric, METRICS, ALLOWED_DIMENSIONS

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


class RuleBasedIntentParser:
    """Zero-dependency intent extraction. Stands in for an LLM tool call."""

    def parse(self, question: str) -> Intent:
        q = question.lower()
        metric_key = resolve_metric(q)
        region = next((r for r in REGIONS if r.lower() in q), None)
        category = next((c for c in CATEGORIES if c.lower() in q), None)
        segment = next((s for s in SEGMENTS if s.lower() in q), None)
        is_why = bool(re.search(r"\bwhy\b", q))
        is_trend = bool(re.search(r"\btrend|over time|by quarter|history\b", q))
        return Intent(metric_key, region, category, segment, is_why, is_trend)


class LLMIntentParser:
    """
    Optional real-LLM path via the Anthropic Messages API with tool-calling.
    The model's ONLY tool is `extract_intent`, whose JSON schema restricts
    `metric` to METRICS.keys() and every dimension to ALLOWED_DIMENSIONS --
    so even a real LLM here is structurally boxed into the semantic layer,
    exactly like the rule-based parser is by construction.

    Requires: pip install anthropic, and ANTHROPIC_API_KEY set.
    """

    def __init__(self, model: str = "claude-sonnet-4-6"):
        import anthropic  # imported lazily so the app runs without the package installed
        self.client = anthropic.Anthropic()
        self.model = model
        self.fallback = RuleBasedIntentParser()

    def parse(self, question: str) -> Intent:
        tool = {
            "name": "extract_intent",
            "description": "Extract the governed metric and filters for a BI question.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "metric": {"type": "string", "enum": list(METRICS.keys()) + ["none"]},
                    "region": {"type": "string", "enum": REGIONS + ["none"]},
                    "category": {"type": "string", "enum": CATEGORIES + ["none"]},
                    "segment": {"type": "string", "enum": SEGMENTS + ["none"]},
                    "is_why_question": {"type": "boolean"},
                    "is_trend_question": {"type": "boolean"},
                },
                "required": ["metric", "is_why_question", "is_trend_question"],
            },
        }
        try:
            resp = self.client.messages.create(
                model=self.model,
                max_tokens=300,
                tools=[tool],
                tool_choice={"type": "tool", "name": "extract_intent"},
                messages=[{"role": "user", "content": question}],
            )
            block = next(b for b in resp.content if b.type == "tool_use")
            data = block.input
            return Intent(
                metric_key=None if data.get("metric") == "none" else data.get("metric"),
                region=None if data.get("region", "none") == "none" else data.get("region"),
                category=None if data.get("category", "none") == "none" else data.get("category"),
                segment=None if data.get("segment", "none") == "none" else data.get("segment"),
                is_why_question=data.get("is_why_question", False),
                is_trend_question=data.get("is_trend_question", False),
            )
        except Exception:
            # Never let an LLM/API outage break the app -- fall back.
            return self.fallback.parse(question)


class MetricMindOrchestrator:
    def __init__(self, warehouse, intent_parser=None):
        self.wh = warehouse
        self.quarters = sorted(warehouse.distinct_values("quarter_label"))

        if intent_parser is not None:
            self.parser = intent_parser
        elif os.environ.get("ANTHROPIC_API_KEY"):
            try:
                self.parser = LLMIntentParser()
            except Exception:
                self.parser = RuleBasedIntentParser()
        else:
            self.parser = RuleBasedIntentParser()

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
        return self.quarters[-1], self.quarters[-2]

    def _explain_drop(self, intent: Intent) -> dict:
        metric = METRICS[intent.metric_key]
        base_filters = self._filters_for(intent)
        cur_q, prev_q = self._resolve_quarter_pair()

        cur_val = compute(self.wh, intent.metric_key, {**base_filters, "quarter_label": cur_q})
        prev_val = compute(self.wh, intent.metric_key, {**base_filters, "quarter_label": prev_q})
        delta = cur_val - prev_val
        direction = "dropped" if delta < 0 else "rose"
        scope = intent.region or "Global"

        driver_rows = []
        for cat in CATEGORIES:
            cur_c = compute(self.wh, intent.metric_key, {**base_filters, "quarter_label": cur_q, "product_category": cat})
            prev_c = compute(self.wh, intent.metric_key, {**base_filters, "quarter_label": prev_q, "product_category": cat})
            if cur_c is not None and prev_c is not None:
                driver_rows.append({"category": cat, "prev": prev_c, "current": cur_c, "delta": cur_c - prev_c})
        driver_rows.sort(key=lambda r: r["delta"])
        biggest = driver_rows[0]

        text_lines = [
            f"**{metric.description} ({scope})**: {prev_q} = {prev_val:,.2f}{metric.unit} -> "
            f"{cur_q} = {cur_val:,.2f}{metric.unit} ({direction} by {abs(delta):,.2f}{metric.unit})",
            "",
            f"Breaking {metric.key} down by product line ({prev_q} -> {cur_q}):",
        ]
        for r in driver_rows:
            arrow = "down" if r["delta"] < 0 else "up"
            text_lines.append(f"  - {r['category']:20s}: {arrow} {abs(r['delta']):,.2f}{metric.unit}")
        text_lines.append("")
        text_lines.append(f"**Primary driver**: {biggest['category']} contributed the largest swing "
                           f"({biggest['delta']:,.2f}{metric.unit}) to the {scope} {metric.key} {direction} in {cur_q}.")

        if intent.metric_key == "gross_margin_pct":
            cur_cost = compute(self.wh, "cost", {**base_filters, "quarter_label": cur_q})
            cur_rev = compute(self.wh, "revenue", {**base_filters, "quarter_label": cur_q})
            prev_cost = compute(self.wh, "cost", {**base_filters, "quarter_label": prev_q})
            prev_rev = compute(self.wh, "revenue", {**base_filters, "quarter_label": prev_q})
            cur_ratio = cur_cost / cur_rev * 100 if cur_rev else 0
            prev_ratio = prev_cost / prev_rev * 100 if prev_rev else 0
            note = "consistent with rising delivery/discount costs" if cur_ratio > prev_ratio else "not the main cause"
            text_lines.append(f"\nCost-to-revenue ratio moved from {prev_ratio:.1f}% to {cur_ratio:.1f}% "
                               f"over the same period, which is {note}.")

        return {
            "answer": "\n".join(text_lines),
            "metric": metric.key,
            "scope": scope,
            "prev_quarter": prev_q, "current_quarter": cur_q,
            "prev_value": prev_val, "current_value": cur_val, "delta": delta,
            "drivers": driver_rows,
        }

    def _answer_simple(self, intent: Intent) -> dict:
        metric = METRICS[intent.metric_key]
        filters = self._filters_for(intent)
        scope = intent.region or intent.category or intent.segment or "Global"

        if intent.is_trend_question:
            series = []
            for q in self.quarters:
                dim_filters = {**filters, "quarter_label": q}
                v = compute(self.wh, intent.metric_key, dim_filters)
                series.append({"quarter": q, "value": v})
            text = f"**{metric.description} trend ({scope})**:\n" + "\n".join(
                f"  {p['quarter']}: {p['value']:,.2f}{metric.unit}" for p in series
            )
            return {"answer": text, "metric": metric.key, "scope": scope, "series": series}

        val = compute(self.wh, intent.metric_key, filters)
        text = f"**{metric.description} ({scope})** = {val:,.2f}{metric.unit}"
        return {"answer": text, "metric": metric.key, "scope": scope, "value": val}

    def ask(self, question: str) -> dict:
        intent = self.parser.parse(question)

        if intent.metric_key is None:
            return {
                "answer": (f"I can't answer that -- it doesn't map to a metric defined in the "
                            f"semantic layer, and I won't guess a formula. "
                            f"Governed metrics: {', '.join(METRICS.keys())}."),
                "metric": None,
            }

        if intent.is_why_question:
            result = self._explain_drop(intent)
        else:
            result = self._answer_simple(intent)

        result["question"] = question
        result["parser"] = type(self.parser).__name__
        return result
