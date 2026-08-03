"""
Step 3 — Agentic Orchestrator (LangChain / LLM stand-in)
Turns a natural-language question into a STRUCTURED PLAN (metric + filters),
never into raw SQL. The plan is then compiled by semantic_layer.build_query(),
executed, and the result is explained back in plain English.

Works with OpenAI if OPENAI_API_KEY is set; otherwise falls back to a simple
rule-based planner so the whole pipeline still runs end-to-end for free.
"""
import os
import json
from semantic_layer import METRICS, DIMENSIONS, build_query

USE_LLM = bool(os.getenv("OPENAI_API_KEY"))

if USE_LLM:
    from langchain_openai import ChatOpenAI
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


PLAN_PROMPT = """You are a query planner for a business intelligence system.
You may ONLY use these metrics: {metrics}
You may ONLY filter/group by these dimensions: {dims}

Question: "{question}"

Respond with ONLY a JSON object, no prose, in this exact shape:
{{"metric": "<one of the metrics>", "filters": {{"region": "Europe"}}, "group_by": ["quarter"]}}
Omit filters/group_by keys if not needed.
"""


def plan_with_llm(question: str) -> dict:
    prompt = PLAN_PROMPT.format(metrics=list(METRICS.keys()), dims=DIMENSIONS, question=question)
    response = llm.invoke(prompt).content
    return json.loads(response)


def plan_with_rules(question: str) -> dict:
    """Fallback planner: simple keyword matching, no API key required."""
    q = question.lower()
    metric = next((m for m in METRICS if m.replace("_", " ") in q), "revenue")
    if "margin" in q:
        metric = "margin_pct"
    if "churn" in q:
        metric = "churn_rate"
    if "kpi" in q:
        metric = "kpi_attainment"

    filters = {}
    for dim_value in ["Europe", "APAC", "North America", "LATAM", "MEA"]:
        if dim_value.lower() in q:
            filters["region"] = dim_value

    group_by = ["quarter"] if "quarter" in q or "trend" in q else None
    return {"metric": metric, "filters": filters, "group_by": group_by}


def ask_metricmind(question: str, con) -> dict:
    """
    Step-by-step agent loop:
    1. Plan  2. Compile SQL  3. Execute  4. Self-check  5. Explain
    """
    # 1. Plan (structured intent, not SQL)
    plan = plan_with_llm(question) if USE_LLM else plan_with_rules(question)

    # 2. Compile SQL from the governed semantic layer only
    sql = build_query(plan["metric"], plan.get("filters"), plan.get("group_by"))

    # 3. Execute
    result = con.execute(sql).fetchdf()

    # 4. Self-check
    if result.empty:
        return {"plan": plan, "sql": sql, "result": [], "answer": "No data found for that question."}

    # 5. Explain (LLM if available, else a plain templated summary)
    if USE_LLM:
        explain_prompt = f"Explain this business result in 2 sentences for an executive: {result.to_dict('records')}"
        answer = llm.invoke(explain_prompt).content
    else:
        answer = f"Result for {plan['metric']} " \
                  f"({', '.join(f'{k}={v}' for k, v in plan.get('filters', {}).items()) or 'all data'}): " \
                  f"{result.to_dict('records')}"

    return {"plan": plan, "sql": sql, "result": result.to_dict("records"), "answer": answer}
