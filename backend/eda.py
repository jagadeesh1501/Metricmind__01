"""
Step 0 — EDA (run this first, before building the semantic layer)
"""
import pandas as pd

df = pd.read_csv("metricmind_enterprise_analytics_20k.csv")
df["date"] = pd.to_datetime(df["date"])
df["quarter"] = df["date"].dt.to_period("Q")
df["margin_pct"] = df["profit"] / df["revenue"] * 100

print("Shape:", df.shape)
print("\nMissing values:\n", df.isnull().sum())
print("\nSummary stats:\n", df.describe())
print("\nRevenue by region:\n", df.groupby("region")["revenue"].sum().sort_values(ascending=False))
print("\nEurope margin by quarter:\n", df[df.region == "Europe"].groupby("quarter")["margin_pct"].mean())
print("\nChurn rate by segment:\n", df.groupby("customer_segment")["churn_flag"].mean())
print("\nKPI attainment by department:\n",
      df.groupby("department").apply(lambda g: g.kpi_actual.sum() / g.kpi_target.sum()))
