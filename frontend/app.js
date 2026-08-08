const API = ""; // same-origin, FastAPI serves this file too

// ---------------- Tabs ----------------
document.querySelectorAll(".tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById("tab-" + btn.dataset.tab).classList.add("active");
    if (btn.dataset.tab === "dashboard") loadDashboard();
    if (btn.dataset.tab === "charts") loadCharts();
    if (btn.dataset.tab === "metrics") loadMetrics();
  });
});

// ---------------- Health check ----------------
async function checkHealth() {
  const badge = document.getElementById("health-badge");
  try {
    const r = await fetch(`${API}/api/health`);
    const data = await r.json();
    badge.textContent = `● ${data.rows_in_warehouse.toLocaleString()} rows · ${data.orchestrator_parser}`;
    badge.classList.add("ok");
  } catch (e) {
    badge.textContent = "● backend unreachable";
    badge.classList.add("err");
  }
}
checkHealth();

// ---------------- Chat ----------------
const chatLog = document.getElementById("chat-log");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");

function addUserMessage(text) {
  const div = document.createElement("div");
  div.className = "msg user";
  div.innerHTML = `<div class="bubble"></div>`;
  div.querySelector(".bubble").textContent = text;
  chatLog.appendChild(div);
  chatLog.scrollTop = chatLog.scrollHeight;
}

function addAgentMessage(result) {
  const div = document.createElement("div");
  div.className = "msg agent";
  const bubble = document.createElement("div");
  bubble.className = "bubble" + (result.metric === null ? " declined" : "");
  bubble.textContent = result.answer || "(no answer)";

  if (result.drivers && result.drivers.length) {
    const table = document.createElement("table");
    table.className = "driver-table";
    table.innerHTML = `<thead><tr><th>Product line</th><th>${result.prev_quarter}</th><th>${result.current_quarter}</th><th>Δ</th></tr></thead>`;
    const tbody = document.createElement("tbody");
    result.drivers.forEach(d => {
      const tr = document.createElement("tr");
      const cls = d.delta < 0 ? "down" : "up";
      tr.innerHTML = `<td>${d.category}</td><td>${d.prev.toLocaleString(undefined,{maximumFractionDigits:1})}</td>
        <td>${d.current.toLocaleString(undefined,{maximumFractionDigits:1})}</td>
        <td class="${cls}">${d.delta >= 0 ? "+" : ""}${d.delta.toLocaleString(undefined,{maximumFractionDigits:1})}</td>`;
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    bubble.appendChild(table);
  }

  div.appendChild(bubble);
  chatLog.appendChild(div);
  chatLog.scrollTop = chatLog.scrollHeight;
}

async function askAgent(question) {
  addUserMessage(question);
  const thinking = document.createElement("div");
  thinking.className = "msg agent";
  thinking.innerHTML = `<div class="bubble">thinking…</div>`;
  chatLog.appendChild(thinking);
  chatLog.scrollTop = chatLog.scrollHeight;

  try {
    const r = await fetch(`${API}/api/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    const data = await r.json();
    thinking.remove();
    addAgentMessage(data);
  } catch (e) {
    thinking.remove();
    addAgentMessage({ answer: "Backend request failed: " + e.message, metric: null });
  }
}

chatForm.addEventListener("submit", (e) => {
  e.preventDefault();
  const q = chatInput.value.trim();
  if (!q) return;
  chatInput.value = "";
  askAgent(q);
});

document.querySelectorAll(".suggestion").forEach(btn => {
  btn.addEventListener("click", () => askAgent(btn.dataset.q));
});

// ---------------- 3D Dashboard ----------------
let dashboardLoaded = false;
async function loadDashboard() {
  if (dashboardLoaded) return;
  dashboardLoaded = true;

  const cubeRes = await fetch(`${API}/api/dashboard/revenue-cube`).then(r => r.json());
  const regionIdx = Object.fromEntries(cubeRes.regions.map((r, i) => [r, i]));
  const catIdx = Object.fromEntries(cubeRes.categories.map((c, i) => [c, i]));
  const quarterIdx = Object.fromEntries(cubeRes.quarters.map((q, i) => [q, i]));

  const x = cubeRes.rows.map(r => regionIdx[r.region]);
  const y = cubeRes.rows.map(r => catIdx[r.category]);
  const z = cubeRes.rows.map(r => quarterIdx[r.quarter]);
  const val = cubeRes.rows.map(r => r.revenue);
  const text = cubeRes.rows.map(r => `${r.region} | ${r.category} | ${r.quarter}<br>Revenue: $${r.revenue.toLocaleString(undefined,{maximumFractionDigits:0})}`);

  Plotly.newPlot("plot-cube", [{
    type: "scatter3d", mode: "markers",
    x, y, z, text, hoverinfo: "text",
    marker: {
      size: val.map(v => (v / Math.max(...val)) * 20 + 4),
      color: val, colorscale: "Viridis", showscale: true,
      colorbar: { title: "Revenue" },
    },
  }], {
    scene: {
      xaxis: { title: "Region", tickvals: Object.values(regionIdx), ticktext: Object.keys(regionIdx) },
      yaxis: { title: "Category", tickvals: Object.values(catIdx), ticktext: Object.keys(catIdx) },
      zaxis: { title: "Quarter", tickvals: Object.values(quarterIdx), ticktext: Object.keys(quarterIdx) },
    },
    paper_bgcolor: "transparent", font: { color: "#e6edf7" },
    margin: { l: 0, r: 0, t: 10, b: 0 },
  }, { responsive: true });

  const surfRes = await fetch(`${API}/api/dashboard/margin-surface`).then(r => r.json());
  Plotly.newPlot("plot-surface", [{
    type: "surface", z: surfRes.z, x: surfRes.x, y: surfRes.y,
    colorscale: "RdYlGn", cmid: 52, colorbar: { title: "Margin %" },
  }], {
    scene: { xaxis: { title: "Region" }, yaxis: { title: "Quarter" }, zaxis: { title: "Margin %" } },
    paper_bgcolor: "transparent", font: { color: "#e6edf7" },
    margin: { l: 0, r: 0, t: 10, b: 0 },
  }, { responsive: true });
}

// ---------------- Chart gallery ----------------
let chartsLoaded = false;
async function loadCharts() {
  if (chartsLoaded) return;
  chartsLoaded = true;
  const gallery = document.getElementById("chart-gallery");
  try {
    const { charts } = await fetch(`${API}/api/charts`).then(r => r.json());
    if (!charts.length) {
      gallery.innerHTML = `<p>No charts yet — run <code>POST /api/pipeline/charts</code> first.</p>`;
      return;
    }
    charts.forEach(name => {
      const fig = document.createElement("figure");
      fig.innerHTML = `<img src="${API}/api/charts/${name}" alt="${name}" />
        <figcaption>${name}</figcaption>`;
      gallery.appendChild(fig);
    });
  } catch (e) {
    gallery.innerHTML = `<p>Could not load charts: ${e.message}</p>`;
  }
}

// ---------------- Semantic layer table ----------------
let metricsLoaded = false;
async function loadMetrics() {
  if (metricsLoaded) return;
  metricsLoaded = true;
  const tbody = document.querySelector("#metrics-table tbody");
  try {
    const { metrics } = await fetch(`${API}/api/metrics`).then(r => r.json());
    metrics.forEach(m => {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td><code>${m.key}</code></td><td>${m.unit}</td><td>${m.description}</td>
        <td>${m.higher_is_better ? "▲ higher is better" : "▼ lower is better"}</td>`;
      tbody.appendChild(tr);
    });
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="4">Could not load metrics: ${e.message}</td></tr>`;
  }
}
