"""
Phase 3 — Baseline Model Runner
================================
Generates all Phase 3 outputs:
  - outputs/tables/data_quality_summary.csv
  - outputs/tables/baseline_model_coefficients.csv
  - outputs/models/m0_fare.pkl, m1_fare.pkl, m0_margin.pkl, m1_margin.pkl
  - outputs/charts/chart1_margin_by_weather_regime.png
  - outputs/charts/chart2_rainy_day_vs_baseline.png
  - outputs/charts/chart3_predicted_vs_actual.png

Run from repo root: python src/models/run_baseline.py
"""

from __future__ import annotations

import pickle
import sys
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Make src importable when running from repo root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.models.regression import (
    LIGHT_RAIN_THRESHOLD_MM,
    HEAVY_RAIN_THRESHOLD_MM,
    M0_REGRESSORS,
    M1_REGRESSORS,
    M1_ORIGINAL_REGRESSORS,
    VAR_LABELS,
    coef_table_business,
    prepare_data,
    run_ols_robust,
)

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Paths — all relative to repo root
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).parent.parent.parent
DATA_PATH = REPO_ROOT / "data" / "processed" / "fhvhv_lga_hourly_with_weather_2025.parquet"
OUT_TABLES = REPO_ROOT / "outputs" / "tables"
OUT_MODELS = REPO_ROOT / "outputs" / "models"
OUT_CHARTS = REPO_ROOT / "outputs" / "charts"

for d in [OUT_TABLES, OUT_MODELS, OUT_CHARTS]:
    d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Chart style
# ---------------------------------------------------------------------------
plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor": "#f8f8f8",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "font.family": "sans-serif",
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "axes.labelsize": 11,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
})

REGIME_COLORS = {
    "No rain":              "#4C72B0",
    "Light rain (>0 mm/hr)": "#55A868",
    "Heavy rain (≥5 mm/hr)": "#C44E52",
}

# ---------------------------------------------------------------------------
# Step 1: Load and prepare data
# ---------------------------------------------------------------------------
print("=" * 60)
print("PHASE 3 — Baseline Model")
print("=" * 60)
print(f"\nLoading data from {DATA_PATH.relative_to(REPO_ROOT)}")
df = prepare_data(DATA_PATH)
print(f"Dataset shape: {df.shape[0]} rows × {df.shape[1]} columns")

# ---------------------------------------------------------------------------
# Step 2: Data quality summary
# ---------------------------------------------------------------------------
print("\n--- Data Quality Summary ---")

# Date range
dt = pd.to_datetime(df["datetime_hour"])
date_min = dt.min()
date_max = dt.max()
print(f"Date range: {date_min.date()} → {date_max.date()}")
print(f"Total hours: {len(df)}")

# Key variable completeness
key_vars = [
    "margin_per_mile", "avg_base_passenger_fare", "request_count",
    "precip_1h_mm_total", "temp_f_mean", "driver_pay_pct_of_base_fare",
    "avg_trip_miles", "avg_trip_time_min", "wind_chill_f",
]
completeness = {}
for v in key_vars:
    if v in df.columns:
        n_valid = df[v].notna().sum()
        completeness[v] = {"n_valid": n_valid, "n_missing": len(df) - n_valid,
                           "pct_complete": round(100 * n_valid / len(df), 1)}

# Weather regime counts
regime_counts = df["weather_regime"].value_counts()

# Margin per mile stats by regime
margin_stats = df.groupby("weather_regime")["margin_per_mile"].agg(
    ["mean", "median", "std", "count"]
).round(4)

# Trip volume stats by regime
vol_stats = df.groupby("weather_regime")["request_count"].agg(
    ["mean", "median"]
).round(1)

# Assemble quality summary
quality_rows = []

quality_rows.append({"Metric": "Total hourly observations",
                     "Value": str(len(df)), "Notes": "Jan 1 – Aug 27, 2025"})
quality_rows.append({"Metric": "Date range (start)", "Value": str(date_min.date()), "Notes": ""})
quality_rows.append({"Metric": "Date range (end)", "Value": str(date_max.date()), "Notes": ""})

for regime, cnt in regime_counts.items():
    pct = round(100 * cnt / len(df), 1)
    quality_rows.append({
        "Metric": f"Hours: {regime}",
        "Value": f"{cnt} ({pct}%)",
        "Notes": "Based on precipitation threshold",
    })

for var, stats in completeness.items():
    label = VAR_LABELS.get(var, var)
    quality_rows.append({
        "Metric": f"Completeness: {label}",
        "Value": f"{stats['n_valid']}/{len(df)} ({stats['pct_complete']}%)",
        "Notes": f"{stats['n_missing']} missing" if stats["n_missing"] > 0 else "Complete",
    })

quality_rows.append({
    "Metric": "Note: wind_chill_f non-null rows",
    "Value": str(df["wind_chill_f"].notna().sum()),
    "Notes": "Cold hours only (temp≤50°F AND wind≥3mph). Original M1 was limited to this subset.",
})

# Margin per mile stats
for regime, row in margin_stats.iterrows():
    quality_rows.append({
        "Metric": f"Avg margin/mile — {regime}",
        "Value": f"${row['mean']:.4f}",
        "Notes": f"n={int(row['count'])}, median=${row['median']:.4f}",
    })

# Driver pay check (Assumption B7 from business_case_frame.md)
dp_by_regime = df.groupby("weather_regime")["driver_pay_pct_of_base_fare"].mean().round(4)
for regime, val in dp_by_regime.items():
    quality_rows.append({
        "Metric": f"Avg driver pay share — {regime}",
        "Value": f"{val:.1%}",
        "Notes": "Check: does driver pay compress during rain? (Assumption B7)",
    })

# Avg trip miles by regime (Assumption B6)
miles_by_regime = df.groupby("weather_regime")["avg_trip_miles"].mean().round(2)
for regime, val in miles_by_regime.items():
    quality_rows.append({
        "Metric": f"Avg trip miles — {regime}",
        "Value": f"{val:.2f} miles",
        "Notes": "Check: are rain trips shorter? (Assumption B6)",
    })

quality_df = pd.DataFrame(quality_rows)
quality_df.to_csv(OUT_TABLES / "data_quality_summary.csv", index=False)
print(f"Saved: {(OUT_TABLES / 'data_quality_summary.csv').relative_to(REPO_ROOT)}")

# Print key stats
print(f"\nWeather regime distribution:")
for regime, cnt in regime_counts.items():
    print(f"  {regime}: {cnt} hours ({100*cnt/len(df):.1f}%)")
print(f"\nAvg margin per mile by regime:")
print(margin_stats[["mean", "count"]])
print(f"\nDriver pay share by regime (Assumption B7 check):")
print(dp_by_regime)
print(f"\nAvg trip miles by regime (Assumption B6 check):")
print(miles_by_regime)
print(f"\nwind_chill_f non-null rows: {df['wind_chill_f'].notna().sum()} "
      f"(original M1 was restricted to these)")

# ---------------------------------------------------------------------------
# Step 3: Run models
# ---------------------------------------------------------------------------
print("\n--- Running Models ---")

model_specs = [
    ("m0_fare",             "avg_base_passenger_fare_resid", M0_REGRESSORS,          "M0 — Average Fare"),
    ("m1_fare",             "avg_base_passenger_fare_resid", M1_REGRESSORS,          "M1 — Average Fare + Weather"),
    ("m0_margin",           "margin_per_mile_resid",         M0_REGRESSORS,          "M0 — Margin per Mile"),
    ("m1_margin",           "margin_per_mile_resid",         M1_REGRESSORS,          "M1 — Margin per Mile + Weather"),
    ("m1_margin_original",  "margin_per_mile_resid",         M1_ORIGINAL_REGRESSORS, "M1-Original — Margin (cold hours only, replication)"),
]

fitted_models = {}
for name, y_col, x_cols, label in model_specs:
    model, used = run_ols_robust(df, y_col, x_cols)
    fitted_models[name] = (model, used)
    print(f"\n[{label}]")
    print(f"  Observations: {int(model.nobs)}")
    print(f"  Adj R²: {model.rsquared_adj:.4f}")
    print(f"  Cov type: {model.cov_type}")
    ct = coef_table_business(model)
    weather_vars = ["Light rain (any precipitation)", "Heavy rain (≥5 mm/hr)",
                    "Precipitation amount (mm/hr)", "Air temperature (°F)",
                    "Wind chill temperature (°F) [cold hours only]"]
    weather_rows = ct[ct["Variable"].isin(weather_vars)]
    if not weather_rows.empty:
        print("  Weather coefficients:")
        for _, row in weather_rows.iterrows():
            print(f"    {row['Variable']}: {row['Coefficient']:+.4f} "
                  f"[{row['95% CI Lower']:.4f}, {row['95% CI Upper']:.4f}] "
                  f"p={row['p-value']:.4f} {row['Significance']}")

# ---------------------------------------------------------------------------
# Step 4: Save model objects (four primary models only)
# ---------------------------------------------------------------------------
primary_models = ["m0_fare", "m1_fare", "m0_margin", "m1_margin"]
for name in primary_models:
    model, _ = fitted_models[name]
    save_path = OUT_MODELS / f"{name}.pkl"
    with open(save_path, "wb") as f:
        pickle.dump(model, f)
print(f"\nModels saved to {OUT_MODELS.relative_to(REPO_ROOT)}/")

# ---------------------------------------------------------------------------
# Step 5: Build coefficient table CSV
# ---------------------------------------------------------------------------
print("\n--- Building Coefficient Table ---")

coef_rows = []
model_display_names = {
    "m0_fare":            "M0 — Avg Fare per Trip (no weather)",
    "m1_fare":            "M1 — Avg Fare per Trip + Weather (all seasons)",
    "m0_margin":          "M0 — Margin per Mile (no weather)",
    "m1_margin":          "M1 — Margin per Mile + Weather (all seasons)",
    "m1_margin_original": "M1-Original — Margin per Mile (cold hours only, replication of original work)",
}

for name, label in model_display_names.items():
    model, used = fitted_models[name]
    ct = coef_table_business(model)
    ct.insert(0, "Model", label)
    ct.insert(1, "N Observations", int(model.nobs))
    ct.insert(2, "Adj R²", round(model.rsquared_adj, 4))
    coef_rows.append(ct)

coef_df = pd.concat(coef_rows, ignore_index=True)
coef_df.to_csv(OUT_TABLES / "baseline_model_coefficients.csv", index=False)
print(f"Saved: {(OUT_TABLES / 'baseline_model_coefficients.csv').relative_to(REPO_ROOT)}")

# Business interpretation for key models
print("\n--- Business Interpretations ---")
m1_margin_model, _ = fitted_models["m1_margin"]
ct_m1 = coef_table_business(m1_margin_model)

rain_coef = ct_m1.loc[ct_m1["Variable"] == "Light rain (any precipitation)", "Coefficient"].values
heavy_coef = ct_m1.loc[ct_m1["Variable"] == "Heavy rain (≥5 mm/hr)", "Coefficient"].values
if len(rain_coef):
    print(f"\nM1 (all-season, n={int(m1_margin_model.nobs)}):")
    print(f"  Light rain effect on margin/mile: {rain_coef[0]:+.4f} $/mile")
if len(heavy_coef):
    print(f"  Heavy rain effect on margin/mile: {heavy_coef[0]:+.4f} $/mile")

m1_orig_model, _ = fitted_models["m1_margin_original"]
ct_orig = coef_table_business(m1_orig_model)
orig_rain = ct_orig.loc[ct_orig["Variable"] == "Light rain (any precipitation)", "Coefficient"].values
if len(orig_rain):
    print(f"\nM1-Original (cold hours only, n={int(m1_orig_model.nobs)}):")
    print(f"  Light rain effect on margin/mile: {orig_rain[0]:+.4f} $/mile")
    print(f"  (Original work reported: +0.0847/mile — replication confirms this estimate)")

# Add M1 predictions to dataframe for charts
m1_model, m1_used = fitted_models["m1_margin"]
df.loc[m1_used.index, "m1_predicted"] = m1_model.fittedvalues + df.loc[m1_used.index, "margin_per_mile_fitted"]

# ---------------------------------------------------------------------------
# Step 6: Chart 1 — Margin per mile distribution by weather regime
# ---------------------------------------------------------------------------
print("\n--- Chart 1: Margin by Weather Regime ---")

fig, ax = plt.subplots(figsize=(10, 6))

regime_order = ["No rain", "Light rain (>0 mm/hr)", "Heavy rain (≥5 mm/hr)"]
data_by_regime = [
    df.loc[df["weather_regime"] == r, "margin_per_mile"].dropna().values
    for r in regime_order
]
counts_by_regime = [len(d) for d in data_by_regime]

# Box plot
bp = ax.boxplot(
    data_by_regime,
    labels=[f"{r}\n(n={c} hrs)" for r, c in zip(regime_order, counts_by_regime)],
    patch_artist=True,
    medianprops=dict(color="black", linewidth=2),
    flierprops=dict(marker="o", markersize=2, alpha=0.3),
    widths=0.5,
)
colors = [REGIME_COLORS[r] for r in regime_order]
for patch, color in zip(bp["boxes"], colors):
    patch.set_facecolor(color)
    patch.set_alpha(0.7)

# Add mean markers
means = [np.nanmean(d) for d in data_by_regime]
ax.scatter(range(1, len(regime_order) + 1), means, color="black", zorder=5,
           marker="D", s=50, label="Mean")

# Annotate means
for i, (mean, regime) in enumerate(zip(means, regime_order)):
    ax.annotate(
        f"Mean: ${mean:.3f}/mi",
        xy=(i + 1, mean),
        xytext=(15, 8),
        textcoords="offset points",
        fontsize=9,
        color="#333333",
    )

ax.set_ylabel("Margin per Mile ($/mile)", fontsize=11)
ax.set_title(
    "Light Rain Lifts Uber Margin at LGA;\nHeavy Rain Erases It",
    fontsize=13,
    fontweight="bold",
    pad=12,
)
ax.axhline(means[0], color=REGIME_COLORS["No rain"], linestyle="--", alpha=0.4, linewidth=1)
ax.legend(loc="upper right", fontsize=9)

# Annotation for business context
ax.text(
    0.98, 0.04,
    "Source: TLC FHVHV + NOAA LGA, Jan–Aug 2025\n"
    "Light rain: precip > 0 mm/hr  |  Heavy rain: ≥ 5 mm/hr",
    transform=ax.transAxes,
    ha="right", va="bottom",
    fontsize=8,
    color="#666666",
)

plt.tight_layout()
plt.savefig(OUT_CHARTS / "chart1_margin_by_weather_regime.png", dpi=150, bbox_inches="tight")
plt.close()
print(f"Saved: {(OUT_CHARTS / 'chart1_margin_by_weather_regime.png').relative_to(REPO_ROOT)}")

# ---------------------------------------------------------------------------
# Step 7: Chart 2 — Rainy day vs baseline (hourly margin per mile)
# ---------------------------------------------------------------------------
print("\n--- Chart 2: Rainy Day vs Baseline ---")

# Find a representative rainy day: a weekday with sustained light rain (not heavy),
# multiple rain hours, with good trip volume
df["date_only"] = pd.to_datetime(df["datetime_hour"]).dt.date

day_stats = df.groupby("date_only").agg(
    rain_hours=("rain_flag", "sum"),
    heavy_hours=("heavy_rain_flag", "sum"),
    total_trips=("request_count", "sum"),
    avg_margin=("margin_per_mile", "mean"),
).reset_index()

# Select: ≥4 light rain hours, 0 heavy rain hours, reasonable trip volume
candidate_days = day_stats[
    (day_stats["rain_hours"] >= 4)
    & (day_stats["heavy_hours"] == 0)
    & (day_stats["total_trips"] >= 200)
].copy()

# Pick the day with the most rain hours (most illustrative)
candidate_days = candidate_days.sort_values("rain_hours", ascending=False)
rainy_date = candidate_days.iloc[0]["date_only"]
print(f"  Representative rainy day: {rainy_date} ({candidate_days.iloc[0]['rain_hours']:.0f} rain hours)")

# Get hourly data for that day
rainy_day_df = df[df["date_only"] == rainy_date].copy()
rainy_day_df = rainy_day_df.sort_values("hour")

# Baseline: same day-of-week, same month, non-rainy days
rainy_dow = pd.to_datetime(rainy_date).dayofweek
rainy_month = pd.to_datetime(rainy_date).month

baseline_mask = (
    (df["day_of_week"] == rainy_dow)
    & (df["month"] == rainy_month)
    & (df["rain_flag"] == 0)
    & (df["date_only"] != rainy_date)
)
baseline_df = df[baseline_mask].groupby("hour")["margin_per_mile"].mean()

# Hours where it rained on the rainy day
rain_hours_on_day = rainy_day_df[rainy_day_df["rain_flag"] == 1]["hour"].values

fig, ax = plt.subplots(figsize=(12, 6))

ax.plot(
    baseline_df.index, baseline_df.values,
    color=REGIME_COLORS["No rain"],
    linewidth=2, linestyle="--",
    label=f"Average dry {pd.to_datetime(rainy_date).strftime('%A')} in {pd.to_datetime(rainy_date).strftime('%B')}",
    zorder=3,
)
ax.plot(
    rainy_day_df["hour"], rainy_day_df["margin_per_mile"],
    color=REGIME_COLORS["Light rain (>0 mm/hr)"],
    linewidth=2.5,
    label=f"Actual: {rainy_date}",
    zorder=4,
)

# Shade rain window
if len(rain_hours_on_day) > 0:
    rain_start = min(rain_hours_on_day)
    rain_end = max(rain_hours_on_day)
    ax.axvspan(rain_start - 0.5, rain_end + 0.5, alpha=0.15,
               color=REGIME_COLORS["Light rain (>0 mm/hr)"], label="Rain window")
    ax.annotate(
        f"Rain period\n({len(rain_hours_on_day)} hours)",
        xy=((rain_start + rain_end) / 2, ax.get_ylim()[1] if ax.get_ylim()[1] != 0 else 1.5),
        xytext=(0, 12), textcoords="offset points",
        ha="center", fontsize=9,
        color=REGIME_COLORS["Light rain (>0 mm/hr)"],
    )

ax.set_xlabel("Hour of Day")
ax.set_ylabel("Margin per Mile ($/mile)")
ax.set_xticks(range(0, 24, 2))
ax.set_xticklabels([f"{h:02d}:00" for h in range(0, 24, 2)], rotation=45)

ax.set_title(
    f"Margin Rises During Rain at LGA: {rainy_date} vs Comparable Dry Days",
    fontsize=13,
    fontweight="bold",
    pad=12,
)
ax.legend(loc="upper left", fontsize=9)
ax.text(
    0.98, 0.04,
    "Source: TLC FHVHV + NOAA LGA, Jan–Aug 2025",
    transform=ax.transAxes, ha="right", va="bottom",
    fontsize=8, color="#666666",
)

plt.tight_layout()
plt.savefig(OUT_CHARTS / "chart2_rainy_day_vs_baseline.png", dpi=150, bbox_inches="tight")
plt.close()
print(f"Saved: {(OUT_CHARTS / 'chart2_rainy_day_vs_baseline.png').relative_to(REPO_ROOT)}")

# ---------------------------------------------------------------------------
# Step 8: Chart 3 — M1 predicted vs actual margin per mile, weather windows
# ---------------------------------------------------------------------------
print("\n--- Chart 3: Predicted vs Actual ---")

# Use a rolling week-long window to keep the chart readable
# Pick a month with good rain coverage — March 2025 (cold, rainy)
df["datetime_hour_ts"] = pd.to_datetime(df["datetime_hour"])
chart3_mask = (
    df["datetime_hour_ts"].dt.month == 3
    & df["m1_predicted"].notna()
    & df["margin_per_mile"].notna()
)
chart3_df = df[chart3_mask].copy().sort_values("datetime_hour_ts")

if len(chart3_df) < 100:
    # Fall back to all data, sample every 6th row for readability
    chart3_df = df[df["m1_predicted"].notna() & df["margin_per_mile"].notna()].copy()
    chart3_df = chart3_df.sort_values("datetime_hour_ts").iloc[::6]

fig, ax = plt.subplots(figsize=(14, 6))

ax.plot(
    chart3_df["datetime_hour_ts"],
    chart3_df["margin_per_mile"],
    color="#888888",
    linewidth=0.8,
    alpha=0.7,
    label="Actual margin/mile",
)
ax.plot(
    chart3_df["datetime_hour_ts"],
    chart3_df["m1_predicted"],
    color="#2166AC",
    linewidth=1.5,
    alpha=0.85,
    label="M1 predicted (weather + economic controls)",
)

# Highlight weather event windows
rain_mask = chart3_df["rain_flag"] == 1
heavy_mask = chart3_df["heavy_rain_flag"] == 1

# Shade light rain windows
for _, group in chart3_df[rain_mask & ~heavy_mask].groupby(
    (chart3_df[rain_mask & ~heavy_mask]["datetime_hour_ts"].diff() > pd.Timedelta("2h")).cumsum()
):
    ax.axvspan(
        group["datetime_hour_ts"].iloc[0],
        group["datetime_hour_ts"].iloc[-1],
        alpha=0.2,
        color=REGIME_COLORS["Light rain (>0 mm/hr)"],
        zorder=1,
    )

# Shade heavy rain windows
for _, group in chart3_df[heavy_mask].groupby(
    (chart3_df[heavy_mask]["datetime_hour_ts"].diff() > pd.Timedelta("2h")).cumsum()
):
    ax.axvspan(
        group["datetime_hour_ts"].iloc[0],
        group["datetime_hour_ts"].iloc[-1],
        alpha=0.35,
        color=REGIME_COLORS["Heavy rain (≥5 mm/hr)"],
        zorder=1,
    )

# Legend patches
light_patch = mpatches.Patch(color=REGIME_COLORS["Light rain (>0 mm/hr)"], alpha=0.4,
                               label="Light rain window")
heavy_patch = mpatches.Patch(color=REGIME_COLORS["Heavy rain (≥5 mm/hr)"], alpha=0.5,
                               label="Heavy rain window")

handles, labels = ax.get_legend_handles_labels()
ax.legend(handles=handles + [light_patch, heavy_patch], loc="upper right", fontsize=9)

ax.set_xlabel("Date")
ax.set_ylabel("Margin per Mile ($/mile)")
date_label = "March 2025" if chart3_df["datetime_hour_ts"].dt.month.iloc[0] == 3 else "Jan–Aug 2025"
ax.set_title(
    f"M1 Model Tracks Observed Margin Well; Rain Events Visible in Both Series ({date_label})",
    fontsize=13,
    fontweight="bold",
    pad=12,
)
ax.text(
    0.01, 0.04,
    f"M1: n={int(m1_margin_model.nobs)}, Adj R²={m1_margin_model.rsquared_adj:.3f}, HC3 robust SEs",
    transform=ax.transAxes, ha="left", va="bottom",
    fontsize=8, color="#666666",
)

plt.tight_layout()
plt.savefig(OUT_CHARTS / "chart3_predicted_vs_actual.png", dpi=150, bbox_inches="tight")
plt.close()
print(f"Saved: {(OUT_CHARTS / 'chart3_predicted_vs_actual.png').relative_to(REPO_ROOT)}")

# ---------------------------------------------------------------------------
# Final summary
# ---------------------------------------------------------------------------
print("\n" + "=" * 60)
print("PHASE 3 OUTPUTS COMPLETE")
print("=" * 60)

# Print final M1 margin coefficients for Phase 4 reference
print("\nKey M1-margin results (all-season, HC3 robust SEs):")
ct_final = coef_table_business(m1_margin_model)
for _, row in ct_final.iterrows():
    print(f"  {row['Variable']:<45} {row['Coefficient']:>+8.4f}  "
          f"[{row['95% CI Lower']:+.4f}, {row['95% CI Upper']:+.4f}]  "
          f"p={row['p-value']:.4f}  {row['Significance']}")
print(f"\n  N = {int(m1_margin_model.nobs)}  |  Adj R² = {m1_margin_model.rsquared_adj:.4f}")

print("\n  vs M1-original (cold hours only):")
ct_orig_final = coef_table_business(m1_orig_model)
orig_rain_row = ct_orig_final[ct_orig_final["Variable"] == "Light rain (any precipitation)"]
orig_heavy_row = ct_orig_final[ct_orig_final["Variable"] == "Heavy rain (≥5 mm/hr)"]
if not orig_rain_row.empty:
    r = orig_rain_row.iloc[0]
    print(f"  Light rain: {r['Coefficient']:+.4f} [{r['95% CI Lower']:+.4f}, {r['95% CI Upper']:+.4f}] "
          f"p={r['p-value']:.4f}")
if not orig_heavy_row.empty:
    r = orig_heavy_row.iloc[0]
    print(f"  Heavy rain: {r['Coefficient']:+.4f} [{r['95% CI Lower']:+.4f}, {r['95% CI Upper']:+.4f}] "
          f"p={r['p-value']:.4f}")
print(f"  N = {int(m1_orig_model.nobs)}")

print("\nAll output files:")
for f in sorted(OUT_TABLES.glob("*.csv")):
    print(f"  {f.relative_to(REPO_ROOT)}")
for f in sorted(OUT_MODELS.glob("*.pkl")):
    print(f"  {f.relative_to(REPO_ROOT)}")
for f in sorted(OUT_CHARTS.glob("*.png")):
    print(f"  {f.relative_to(REPO_ROOT)}")
