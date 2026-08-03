<<<<<<< HEAD
# MetricMind — Agentic Semantic BI Engine

## Folder structure
```
metricmind/
├── backend/
│   ├── metricmind_enterprise_analytics_20k.csv   # your data
│   ├── eda.py              # Step 0: EDA (Pandas)
│   ├── db.py                # Step 1: Data Lakehouse (DuckDB)
│   ├── semantic_layer.py    # Step 2: Semantic Layer (governed metrics)
│   ├── agent.py              # Step 3: Agentic Orchestrator (LangChain/LLM)
│   ├── charts.py             # Step 4: Data Visualization (Plotly)
│   ├── main.py                # Step 5: REST API (FastAPI)
│   └── requirements.txt
└── frontend/
    ├── package.json
    └── app/page.tsx          # Step 6: Conversational BI UI (Next.js)
```

## How to run

### 1. Backend
```bash
cd backend
pip install -r requirements.txt
python eda.py                      # sanity-check the data first
uvicorn main:app --reload          # starts API at http://localhost:8000
```
Test it:
```bash
curl http://localhost:8000/
curl -X POST http://localhost:8000/ask -H "Content-Type: application/json" \
  -d "{\"question\":\"Why did our European margins drop last quarter?\"}"
```

Without an `OPENAI_API_KEY` set, the agent uses a rule-based keyword planner
(no cost, fully runnable). Set the key to switch on real LLM planning:
```bash
export OPENAI_API_KEY=sk-...
```

### 2. Frontend
```bash
cd frontend
npm install
npm run dev          # http://localhost:3000
```

## Skills demonstrated → file mapping
| Skill | File |
|---|---|
| Pandas / EDA | `eda.py` |
| SQL | `semantic_layer.py`, `db.py` |
| DuckDB | `db.py` |
| Semantic Layer Concepts | `semantic_layer.py` |
| Agentic AI / LangChain / LLM Integration | `agent.py` |
| Business Intelligence / KPI Design | `semantic_layer.py` (METRICS dict) |
| FastAPI / REST APIs | `main.py` |
| Plotly / Data Visualization | `charts.py` |
| Next.js / Conversational BI UI | `frontend/app/page.tsx` |

## The core guardrail (why this satisfies the brief)
The LLM in `agent.py` never writes SQL. It only returns a JSON plan
(`{"metric": "margin_pct", "filters": {"region": "Europe"}}`). The actual SQL
is compiled by `semantic_layer.build_query()`, which only allows metrics and
dimensions defined in the `METRICS`/`DIMENSIONS` dictionaries. This is what
prevents hallucinated joins or invented formulas — Finance and Sales always
get the same number for "margin," no matter who asks.
=======
# Metricmind__01
Agentic Semantic BI engine — translates natural language questions into governed SQL via a semantic layer, preventing LLM metric hallucination. Built with FastAPI, DuckDB, LangChain + Groq (Llama 3.3), and a Next.js + ECharts conversational UI.
>>>>>>> 39ab0cc059652f2caa699eb56393f278f5dcc0bb
