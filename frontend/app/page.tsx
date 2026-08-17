"use client";
// Step 6 — Conversational BI Interface (Next.js + ECharts)
// Dark "console" theme matching MetricMind's semantic-layer concept.

import { useState } from "react";
import dynamic from "next/dynamic";

const ReactECharts: any = dynamic(() => import("echarts-for-react"), { ssr: false });

const API_URL = "http://localhost:8000";

const SAMPLE_QUESTIONS = [
  "Why did our European margins drop last quarter?",
  "What is the churn rate by customer segment?",
  "Show me revenue trend by quarter",
];

export default function Home() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [toolCalls, setToolCalls] = useState<any[]>([]);
  const [chartOption, setChartOption] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleAsk(q?: string) {
    const finalQuestion = q ?? question;
    if (!finalQuestion.trim()) return;
    setLoading(true);
    setError("");
    setAnswer("");
    setChartOption(null);
    try {
      const res = await fetch(`${API_URL}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: finalQuestion }),
      });
      if (!res.ok) throw new Error(`API returned ${res.status}`);
      const data = await res.json();
      setAnswer(data.answer);
      setToolCalls(data.tool_calls || []);
      setChartOption(data.chart || null);
    } catch (e: any) {
      setError("Could not reach the backend. Is uvicorn running on port 8000?");
    } finally {
      setLoading(false);
    }
  }

  const chartTheme = chartOption
    ? {
        ...chartOption,
        backgroundColor: "transparent",
        textStyle: { fontFamily: "IBM Plex Mono, monospace", color: "#EDEFF2" },
        tooltip: {
          ...chartOption.tooltip,
          backgroundColor: "#171F29",
          borderColor: "#232C37",
          textStyle: { color: "#EDEFF2", fontFamily: "IBM Plex Mono, monospace", fontSize: 11 },
        },
        xAxis: {
          ...chartOption.xAxis,
          axisLine: { lineStyle: { color: "#232C37" } },
          axisLabel: { color: "#7C8794", fontFamily: "IBM Plex Mono, monospace", fontSize: 10.5 },
          splitLine: { lineStyle: { color: "#1a222c" } },
        },
        yAxis: {
          ...chartOption.yAxis,
          axisLine: { lineStyle: { color: "#232C37" } },
          axisLabel: { color: "#7C8794", fontFamily: "IBM Plex Mono, monospace", fontSize: 10.5 },
          splitLine: { lineStyle: { color: "#1a222c" } },
        },
        series: (chartOption.series || []).map((s: any) => ({
          ...s,
          lineStyle: { color: "#E8A33D", width: 2.5 },
          itemStyle: { color: s.type === "bar" ? "#E8A33D" : "#E8A33D" },
          areaStyle:
            s.type === "line"
              ? {
                  color: {
                    type: "linear",
                    x: 0, y: 0, x2: 0, y2: 1,
                    colorStops: [
                      { offset: 0, color: "rgba(232,163,61,0.18)" },
                      { offset: 1, color: "rgba(232,163,61,0)" },
                    ],
                  },
                }
              : undefined,
        })),
      }
    : null;

  return (
    <main style={styles.main}>
      <header style={styles.header}>
        <div style={styles.wordmarkRow}>
          <h1 style={styles.wordmark}>MetricMind</h1>
          <span style={styles.tag}>Semantic BI Console</span>
        </div>
        <div style={styles.statusPill}>
          <span style={styles.dot} /> Semantic layer <b style={{ color: "#EDEFF2" }}>online</b>
        </div>
      </header>

      <p style={styles.subline}>
        Ask a business question — answers come only from the governed semantic layer, never raw SQL.
      </p>

      <div style={styles.inputRow}>
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleAsk()}
          placeholder="Why did our European margins drop last quarter?"
          style={styles.input}
        />
        <button onClick={() => handleAsk()} disabled={loading} style={styles.button}>
          {loading ? "Thinking…" : "Ask"}
        </button>
      </div>

      <div style={styles.sampleRow}>
        {SAMPLE_QUESTIONS.map((q) => (
          <button key={q} style={styles.sampleChip} onClick={() => { setQuestion(q); handleAsk(q); }}>
            {q}
          </button>
        ))}
      </div>

      {error && <div style={styles.errorBox}>{error}</div>}

      {answer && (
        <div style={styles.panel}>
          <span style={styles.label}>Answer</span>
          <p style={styles.answerText}>{answer}</p>
        </div>
      )}

      {toolCalls.length > 0 && (
        <div style={styles.panel}>
          <span style={styles.label}>Tool Trail</span>
          {toolCalls.map((t, i) => (
            <div key={i} style={styles.toolRow}>
              <span style={styles.toolName}>{t.tool}</span>
              <span style={styles.toolInput}>{JSON.stringify(t.input)}</span>
            </div>
          ))}
        </div>
      )}

      {chartTheme && (
        <div style={styles.panel}>
          <span style={styles.label}>Visualization</span>
          <ReactECharts option={chartTheme} style={{ height: 340 }} />
        </div>
      )}
    </main>
  );
}

const styles: Record<string, React.CSSProperties> = {
  main: {
    maxWidth: 760,
    margin: "0 auto",
    padding: "40px 20px 80px",
    fontFamily: "Inter, sans-serif",
  },
  header: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    flexWrap: "wrap",
    gap: 12,
    borderBottom: "1px solid #232C37",
    paddingBottom: 18,
    marginBottom: 18,
  },
  wordmarkRow: { display: "flex", alignItems: "baseline", gap: 12 },
  wordmark: {
    fontFamily: "Space Grotesk, sans-serif",
    fontWeight: 700,
    fontSize: 30,
    letterSpacing: "-0.02em",
    margin: 0,
  },
  tag: {
    fontFamily: "IBM Plex Mono, monospace",
    fontSize: 11,
    color: "#7C8794",
    letterSpacing: "0.14em",
    textTransform: "uppercase",
  },
  statusPill: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    background: "#121820",
    border: "1px solid #232C37",
    borderRadius: 999,
    padding: "6px 14px",
    fontFamily: "IBM Plex Mono, monospace",
    fontSize: 12,
    color: "#7C8794",
  },
  dot: {
    width: 7,
    height: 7,
    borderRadius: "50%",
    background: "#3FB8AF",
    boxShadow: "0 0 8px #3FB8AF",
    display: "inline-block",
  },
  subline: { color: "#7C8794", fontSize: 14, marginBottom: 20, lineHeight: 1.5 },
  inputRow: { display: "flex", gap: 10 },
  input: {
    flex: 1,
    padding: "12px 14px",
    background: "#121820",
    border: "1px solid #232C37",
    borderRadius: 8,
    color: "#EDEFF2",
    fontFamily: "Inter, sans-serif",
    fontSize: 14,
    outline: "none",
  },
  button: {
    padding: "0 22px",
    background: "#E8A33D",
    border: "none",
    borderRadius: 8,
    color: "#0B0F14",
    fontFamily: "Space Grotesk, sans-serif",
    fontWeight: 600,
    fontSize: 14,
    cursor: "pointer",
  },
  sampleRow: { display: "flex", flexWrap: "wrap", gap: 8, marginTop: 12 },
  sampleChip: {
    background: "#121820",
    border: "1px solid #232C37",
    borderRadius: 999,
    color: "#7C8794",
    fontFamily: "IBM Plex Mono, monospace",
    fontSize: 11.5,
    padding: "6px 12px",
    cursor: "pointer",
  },
  errorBox: {
    marginTop: 20,
    padding: "12px 14px",
    background: "#1c1214",
    border: "1px solid #4a2a2a",
    borderRadius: 8,
    color: "#E2574C",
    fontFamily: "IBM Plex Mono, monospace",
    fontSize: 12.5,
  },
  panel: {
    marginTop: 20,
    background: "#121820",
    border: "1px solid #232C37",
    borderRadius: 12,
    padding: 18,
  },
  label: {
    fontFamily: "IBM Plex Mono, monospace",
    fontSize: 10.5,
    letterSpacing: "0.1em",
    textTransform: "uppercase",
    color: "#7C8794",
    display: "block",
    marginBottom: 10,
  },
  answerText: { fontSize: 14.5, lineHeight: 1.6, color: "#EDEFF2", margin: 0 },
  toolRow: {
    display: "flex",
    gap: 10,
    fontFamily: "IBM Plex Mono, monospace",
    fontSize: 12,
    padding: "6px 0",
    borderBottom: "1px dashed #1e2731",
  },
  toolName: { color: "#E8A33D", fontWeight: 600, minWidth: 110 },
  toolInput: { color: "#7C8794", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" },
};