"""
MetricMind - run the full pipeline end to end:
cleaning -> EDA -> charts -> agent demo -> 3D dashboard

Usage: python3 run_all.py
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STEPS = [
    "scripts/01_data_cleaning.py",
    "scripts/02_eda.py",
    "scripts/03_charts.py",
    "scripts/04_ai_agent.py",
    "scripts/05_dashboard_3d.py",
]

for step in STEPS:
    print(f"\n{'='*70}\nRUNNING {step}\n{'='*70}")
    result = subprocess.run([sys.executable, str(ROOT / step)], cwd=ROOT)
    if result.returncode != 0:
        print(f"[FAILED] {step}")
        sys.exit(1)

print("\nAll steps completed. See outputs/ for charts, eda_report.txt, and dashboard/.")
