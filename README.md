# MetricMind — Agentic Semantic BI Engine

An AI agent that answers business questions ("Why did our European margins
drop last quarter?") by calling a **governed semantic layer** instead of
writing raw SQL — so Finance and Sales always see the exact same number.

There are two ways to use this project, both tested end-to-end:

1. **`scripts/`** — the original standalone data-science pipeline (cleaning
   → EDA → charts → agent demo → static 3D dashboard HTML). No server, just
   run Python scripts. Good for a portfolio write-up / notebook-style demo.
2. **`backend/` + `frontend/`** — the full-stack app: a FastAPI backend
   (`main.py`, `orchestrator.py`, `warehouse.py`, `semantic_layer/`) serving
   a live chat + 3D dashboard frontend. This is what you asked for now.

Both read from the same `data/` and share the same governed metric
definitions — they're two interfaces onto one semantic layer, not two
separate projects.

## Full-stack app — quick start

```bash
cd backend
pip install -r requirements.txt
python3 data_pipeline/cleaning.py     # only needed once, to produce data/processed/clean_data.csv
uvicorn main:app --reload --port 8000
```
Open **http://localhost:8000** — chat with the agent, rotate the 3D
dashboard, browse the chart gallery, inspect the semantic layer.

Or with Docker (Dockerfile/compose included, standard setup — not
build-tested in this sandbox since no Docker daemon was available here,
but it's a plain `pip install -r requirements.txt` + `uvicorn` image):
```bash
docker compose up --build
```

## Full-stack project structure
```
metricmind/
├── backend/
│   ├── main.py                    # FastAPI entrypoint — wires every module together
│   ├── orchestrator.py            # Agentic Orchestrator (rule-based + optional LLM tool-calling)
│   ├── warehouse.py                # Data Lakehouse (DuckDB — swap for Snowflake/Databricks)
│   ├── semantic_layer/
│   │   └── metrics.py              # governed metric SQL definitions — the ONE source of truth
│   ├── data_pipeline/
│   │   ├── cleaning.py             # importable + runnable (also POST /api/pipeline/clean)
│   │   ├── eda.py                  # GET /api/pipeline/eda
│   │   └── charts.py               # POST /api/pipeline/charts
│   └── requirements.txt
├── frontend/                        # lightweight chat + 3D dashboard SPA (vanilla JS + Plotly.js)
│   ├── index.html
│   ├── app.js
│   └── styles.css
├── scripts/                          # standalone CLI pipeline (original, still works)
├── semantic_layer/                   # pandas-based semantic layer used by scripts/ only
├── data/
├── outputs/
├── Dockerfile
├── docker-compose.yml
└── run_all.py                        # runs scripts/ pipeline end to end
```

## API reference (backend/main.py)
| Method | Path | What it does |
|---|---|---|
| GET | `/api/health` | warehouse row count + which orchestrator parser is active |
| GET | `/api/metrics` | every governed metric + allowed filter dimensions |
| POST | `/api/query` | `{"question": "..."}` → agent answer + structured data |
| GET | `/api/dashboard/revenue-cube` | Revenue × Region × Category × Quarter, for the 3D scatter |
| GET | `/api/dashboard/margin-surface` | Margin % × Region × Quarter, for the 3D surface |
| POST | `/api/pipeline/clean` | re-run data cleaning |
| GET | `/api/pipeline/eda` | EDA summary as JSON |
| POST | `/api/pipeline/charts` | regenerate the static chart PNGs |
| GET | `/api/charts` / `/api/charts/{file}` | list / serve chart images |

Tested directly with `curl` during development — every endpoint above
returns real data from the 22,000-row dataset, including the exact
"Why did our European margins drop last quarter?" answer with its
product-line driver breakdown.

## The semantic layer — the whole point of the project
`backend/semantic_layer/metrics.py` defines every governed metric as
**one SQL aggregate expression** (e.g.
`gross_margin_pct = (SUM(revenue) - SUM(cost)) / NULLIF(SUM(revenue),0) * 100`),
executed against a DuckDB table (`backend/warehouse.py`) that stands in for
Snowflake/Databricks. Two enforcement points:

1. `resolve_metric()` maps natural language ("margin", "our margins") to
   exactly one metric key, or `None` if it's undefined — the orchestrator
   **must decline** rather than invent a formula.
2. `compute(warehouse, metric_key, filters)` is the only function allowed
   to build SQL. Filter dimensions are restricted to a fixed whitelist
   (`ALLOWED_DIMENSIONS`) and filter *values* are always parameterized —
   so even though the agent decides *which* metric and *which* filters,
   it can never inject SQL or invent a formula.

## The orchestrator (`backend/orchestrator.py`)
Ships with two interchangeable intent-extraction backends behind the same
`MetricMindOrchestrator` interface:

- **`RuleBasedIntentParser`** (default, always available): keyword/regex
  matching, zero API keys, fully deterministic — this is what runs unless
  you set `ANTHROPIC_API_KEY`.
- **`LLMIntentParser`** (optional): real tool-calling against the
  Anthropic API. Its *only* tool schema restricts `metric` to the governed
  metric keys and every dimension to `ALLOWED_DIMENSIONS` — so a real LLM
  here is boxed into the semantic layer exactly the same way the rule-based
  parser is by construction. Activate with:
  ```bash
  pip install anthropic
  export ANTHROPIC_API_KEY=sk-ant-...
  ```
  If the key isn't set, or a call fails for any reason, it transparently
  falls back to the rule-based parser — the app never depends on the API
  being up. **This path is written but not exercised in this build** (no
  API key was available in the environment that built this project) — the
  rule-based path is what's actually been tested.

For "why did X drop" questions, the agent decomposes the same governed
metric across `product_category` for both quarters, ranks the drivers,
and — for margin specifically — checks the cost-to-revenue ratio as a
secondary explanation.

## Frontend (`frontend/`)
A single-page app (vanilla JS, no build step, Plotly.js + a dark BI-style
CSS theme) with four tabs:
- **Chat** — ask questions, see the agent's answer plus a driver
  breakdown table for "why" questions
- **3D Dashboard** — live Plotly 3D scatter (Revenue × Region × Category ×
  Quarter) and 3D surface (Margin % × Region × Quarter), fetched fresh
  from the governed API on every load
- **Chart Gallery** — the static PNGs from `data_pipeline/charts.py`
- **Semantic Layer** — every governed metric, its unit, and its
  direction (higher/lower is better)

Stands in for the brief's Next.js + Tremor + ECharts interface. Porting to
Next.js: the `/api/*` routes are already a clean REST contract — move
`frontend/app.js`'s fetch calls into Next.js data-fetching, swap Plotly for
ECharts/Tremor components, same API underneath.

## Mapping to the target production architecture
| This project | Target enterprise stack |
|---|---|
| `backend/semantic_layer/metrics.py` | Cube.dev or dbt Semantic Layer |
| `backend/orchestrator.py` (`LLMIntentParser`) | LangChain tool-calling agent (Llama 3 / Claude) |
| `backend/warehouse.py` (DuckDB) | Snowflake / Databricks lakehouse |
| `frontend/` (vanilla JS + Plotly) | Next.js + Tremor chat UI rendering ECharts |

## Notes on the data
`data/raw/metricmind_enterprise_analytics_.csv` — 22,000 enterprise
transactions (2022–2026) across 5 regions, 5 product lines, 4 customer
segments, with revenue/cost/profit, KPI targets, CSAT, churn, and
agentic-query telemetry columns. Cleaning caps the top 0.5% of revenue
outliers and recomputes `profit` from `revenue - cost` rather than
trusting the raw column, so it can never silently drift from the
governed formula.
