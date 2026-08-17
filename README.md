# MetricMind — Agentic Semantic BI Engine

An agentic Business Intelligence system that lets users ask business questions in plain English and get answers grounded in **governed, pre-defined metrics** — not hallucinated SQL.

## Problem

Giving an LLM raw access to a data warehouse for "Text-to-SQL" often ends badly — the AI hallucinates joins, ignores business logic, and generates numbers that don't match official reports. Finance and Sales end up with two different answers to the same question.

## Solution

MetricMind's agent never writes or sees raw SQL. It can only call two governed tools:
- `list_metrics` — returns the exact metrics/dimensions it's allowed to use
- `query_metric` — runs a query built from a fixed, pre-defined formula

The actual SQL is compiled by a single function (`build_query`) using formulas defined once in a `METRICS` dictionary — the semantic layer. This guarantees everyone gets the same number for "margin," no matter who asks or how they phrase the question.

## Architecture

| Component | Tool | File |
|---|---|---|
| Data layer | DuckDB | `backend/db.py` |
| Semantic layer | Python dict + governed query builder | `backend/semantic_layer.py` |
| Agentic orchestrator | LangChain + Groq (Llama 3.3) | `backend/agent/orchestrator.py`, `backend/agent/tools.py` |
| REST API | FastAPI | `backend/main.py` |
| Visualization | ECharts | `backend/charts.py` |
| Frontend | Next.js | `frontend/app/page.tsx` |

## Setup

### Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
cp .env.example .env         # add your GROQ_API_KEY (free at console.groq.com/keys)
uvicorn main:app --reload
```
Runs at `http://localhost:8000`. Without a Groq key, the agent automatically falls back to a rule-based keyword planner — the app still works end-to-end for free.

### Frontend
```bash
cd frontend
npm install
npm run dev
```
Runs at `http://localhost:3000`.

### Alternative: Streamlit deployment
A single-file version (`streamlit_app.py`) is available for one-click deployment to Streamlit Community Cloud — no separate frontend/backend needed. See deployment steps in that file's comments.

## Example questions
- "Why did our European margins drop last quarter?"
- "What is the churn rate by customer segment?"
- "Show me revenue trend by quarter"

## Dataset
`metricmind_enterprise_analytics_20k.csv` — 20,000 synthetic enterprise sales/analytics records (region, department, product, revenue, profit, churn, CSAT, KPI targets) spanning 2022–2026.

## Governed metrics
| Metric | Formula |
|---|---|
| revenue | `SUM(revenue)` |
| cost | `SUM(cost)` |
| profit | `SUM(profit)` |
| margin_pct | `SUM(profit) / SUM(revenue) * 100` |
| churn_rate | `AVG(churn_flag) * 100` |
| avg_csat | `AVG(csat_score)` |
| kpi_attainment | `SUM(kpi_actual) / SUM(kpi_target) * 100` |

## Skills demonstrated
Python · Pandas · SQL · DuckDB · FastAPI · LangChain · LLM Integration (Groq/Llama 3.3) · Semantic Layer Design · Business Intelligence · KPI Design · ECharts · Next.js · REST APIs · Data Visualization · Agentic AI

## Tooling substitutions
This build uses lightweight, local-first tools in place of enterprise infrastructure, so it runs entirely on a laptop with no paid cloud accounts:

| Brief calls for | This project uses | Why |
|---|---|---|
| Snowflake / Databricks | DuckDB | Same SQL execution model, zero setup |
| Cube.dev / dbt Semantic Layer | Python dict + governed query builder | Same governance principle, implemented in code |
| Tremor | Custom CSS | Same UI concept, no extra dependency |
