"""
MetricMind Backend - main.py (FastAPI entrypoint)
====================================================
Wires together every module:
  warehouse.py            -> Data Lakehouse (DuckDB, swap for Snowflake/Databricks)
  semantic_layer/metrics.py -> governed metric definitions (Cube.dev/dbt stand-in)
  orchestrator.py          -> Agentic Orchestrator (rule-based, or real LLM if
                               ANTHROPIC_API_KEY is set)
  data_pipeline/*          -> cleaning / EDA / charts, runnable via API too
  ../frontend/             -> served as static files at "/"

Run:
    cd backend
    uvicorn main:app --reload --port 8000
Then open http://localhost:8000
"""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from warehouse import Warehouse
from semantic_layer.metrics import METRICS, list_metrics, ALLOWED_DIMENSIONS, compute
from orchestrator import MetricMindOrchestrator, REGIONS, CATEGORIES
from data_pipeline import cleaning, eda as eda_module, charts as charts_module

ROOT = Path(__file__).resolve().parent.parent
CHART_DIR = ROOT / "outputs" / "charts"
FRONTEND_DIR = ROOT / "frontend"

app = FastAPI(title="MetricMind API", description="Agentic Semantic BI Engine", version="1.0.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

# --- Data Lakehouse + Orchestrator are built once at startup ---
warehouse: Warehouse | None = None
orchestrator: MetricMindOrchestrator | None = None


@app.on_event("startup")
def startup():
    global warehouse, orchestrator
    warehouse = Warehouse()
    orchestrator = MetricMindOrchestrator(warehouse)
    print(f"[startup] warehouse loaded: {warehouse.row_count:,} rows")
    print(f"[startup] orchestrator using: {type(orchestrator.parser).__name__}")


class QueryRequest(BaseModel):
    question: str


# ---------------- Health / meta ----------------

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "rows_in_warehouse": warehouse.row_count,
        "orchestrator_parser": type(orchestrator.parser).__name__,
    }


@app.get("/api/metrics")
def get_metrics():
    """Every governed metric the semantic layer exposes."""
    return {"metrics": list_metrics(), "allowed_dimensions": ALLOWED_DIMENSIONS}


# ---------------- Agentic orchestrator ----------------

@app.post("/api/query")
def query(req: QueryRequest):
    """Ask the agent a business question in natural language."""
    if not req.question.strip():
        raise HTTPException(400, "question must not be empty")
    return orchestrator.ask(req.question)


# ---------------- Dashboard data (feeds the 3D frontend charts) ----------------

@app.get("/api/dashboard/revenue-cube")
def revenue_cube():
    """Revenue by Region x Product Category x Quarter, via the governed metric."""
    rows = []
    for region in REGIONS:
        for category in CATEGORIES:
            for q in orchestrator.quarters:
                val = compute(warehouse, "revenue", {
                    "region": region, "product_category": category, "quarter_label": q
                })
                if val:
                    rows.append({"region": region, "category": category, "quarter": q, "revenue": val})
    return {"rows": rows, "regions": REGIONS, "categories": CATEGORIES, "quarters": orchestrator.quarters}


@app.get("/api/dashboard/margin-surface")
def margin_surface():
    """Gross Margin % across Region x Quarter, for the 3D surface plot."""
    grid = []
    for q in orchestrator.quarters:
        row = []
        for region in REGIONS:
            val = compute(warehouse, "gross_margin_pct", {"region": region, "quarter_label": q})
            row.append(val)
        grid.append(row)
    return {"z": grid, "x": REGIONS, "y": orchestrator.quarters}


# ---------------- Data pipeline, runnable from the API ----------------

@app.post("/api/pipeline/clean")
def run_cleaning():
    return cleaning.run()


@app.get("/api/pipeline/eda")
def run_eda():
    return eda_module.run()


@app.post("/api/pipeline/charts")
def run_charts():
    return {"generated": charts_module.run()}


@app.get("/api/charts/{filename}")
def get_chart(filename: str):
    path = CHART_DIR / filename
    if not path.exists() or path.parent != CHART_DIR:
        raise HTTPException(404, "chart not found")
    return FileResponse(path)


@app.get("/api/charts")
def list_charts():
    if not CHART_DIR.exists():
        return {"charts": []}
    return {"charts": sorted(p.name for p in CHART_DIR.glob("*.png"))}


# ---------------- Frontend (static SPA) ----------------
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
