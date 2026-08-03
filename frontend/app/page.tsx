"use client";
// Step 6 — Conversational BI Interface (Next.js)
// Simple chat box that calls the FastAPI /ask endpoint and renders
// the plain-English answer alongside the Plotly chart JSON.

import { useState } from "react";
import dynamic from "next/dynamic";

const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

const API_URL = "http://localhost:8000";

export default function Home() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [chart, setChart] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  async function handleAsk() {
    setLoading(true);
    const res = await fetch(`${API_URL}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    const data = await res.json();
    setAnswer(data.answer);
    setChart(data.chart ? JSON.parse(data.chart) : null);
    setLoading(false);
  }

  return (
    <main style={{ maxWidth: 700, margin: "40px auto", fontFamily: "sans-serif" }}>
      <h1>MetricMind</h1>
      <p>Ask a business question — answers come only from the governed semantic layer.</p>

      <input
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        placeholder="Why did our European margins drop last quarter?"
        style={{ width: "100%", padding: 10 }}
      />
      <button onClick={handleAsk} disabled={loading} style={{ marginTop: 10, padding: "8px 16px" }}>
        {loading ? "Thinking..." : "Ask"}
      </button>

      {answer && <p style={{ marginTop: 20 }}><strong>Answer:</strong> {answer}</p>}
     {chart && (
  // @ts-ignore
  <Plot data={chart.data} layout={chart.layout} />
)}
    </main>
  );
}