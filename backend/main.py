"""
Step 5 — REST API layer (FastAPI)
Exposes the semantic layer + agent to any frontend (Next.js, Streamlit, curl, etc.)
Run with:  uvicorn main:app --reload
"""
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from db import get_connection
from semantic_layer import create_semantic_view, METRICS, DIMENSIONS
from agent import ask_metricmind
from charts import make_chart_json

app = FastAPI(title="MetricMind API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this in production
    allow_methods=["*"],
    allow_headers=["*"],
)

con = get_connection()
create_semantic_view(con)


class Question(BaseModel):
    question: str


@app.get("/")
def root():
    return {"status": "MetricMind API running", "metrics": list(METRICS.keys()), "dimensions": DIMENSIONS}


@app.post("/ask")
def ask(payload: Question):
    """Main conversational BI endpoint — natural language in, governed answer out."""
    result = ask_metricmind(payload.question, con)
    chart = make_chart_json(result["result"], result["plan"]["metric"])
    return {**result, "chart": chart}


@app.get("/metrics/{metric_name}")
def get_metric(metric_name: str, region: str | None = None, group_by: str | None = Query(None)):
    """Direct metric access — bypasses the LLM, useful for dashboards."""
    from semantic_layer import build_query
    filters = {"region": region} if region else {}
    group = [group_by] if group_by else None
    sql = build_query(metric_name, filters, group)
    df = con.execute(sql).fetchdf()
    return {"sql": sql, "data": df.to_dict("records")}
