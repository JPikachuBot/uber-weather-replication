"""
opportunity_sizing.py — Phase 4: Annual margin opportunity from weather-responsive pricing at LGA.

Translates M1 regression coefficients into an annual dollar estimate with low/mid/high scenario bounds.
All monetary values in USD. All rates in per-mile or per-hour units.

Usage:
    python src/models/opportunity_sizing.py
    (or import and call run_all())

Outputs:
    outputs/tables/opportunity_sizing_scenarios.csv
    outputs/tables/sensitivity_analysis.csv
    outputs/charts/chart4_opportunity_estimate.png
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Any

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# ---------------------------------------------------------------------------
# Paths (relative to repo root)
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).parent.parent.parent
DATA_PATH = REPO_ROOT / "data" / "processed" / "fhvhv_lga_hourly_with_weather_2025.parquet"
OUT_TABLES = REPO_ROOT / "outputs" / "tables"
OUT_CHARTS = REPO_ROOT / "outputs" / "charts"

# ---------------------------------------------------------------------------
# Model coefficient constants — M1 all-season, heteroskedasticity-robust SEs
# Source: outputs/tables/baseline_model_coefficients.csv, Phase 3
# ---------------------------------------------------------------------------
LIGHT_RAIN_COEF_POINT: float = 0.073      # $/mile — point estimate
LIGHT_RAIN_COEF_SE: float = 0.0121        # $/mile — robust standard error
LIGHT_RAIN_COEF_CI_LOWER: float = 0.0494  # $/mile — 95% CI lower bound
LIGHT_RAIN_COEF_CI_UPPER: float = 0.0967  # $/mile — 95% CI upper bound

# ---------------------------------------------------------------------------
# Weather regime thresholds — match Phase 3 definitions exactly
# ---------------------------------------------------------------------------
LIGHT_RAIN_THRESHOLD_MM: float = 0.0   # precip_1h_mm_total > 0
HEAVY_RAIN_THRESHOLD_MM: float = 5.0   # precip_1h_mm_total >= 5

# ---------------------------------------------------------------------------
# Observation period
# ---------------------------------------------------------------------------
OBS_START: str = "2025-01-01"
OBS_END: str = "2025-08-27"
OBS_CALENDAR_DAYS: int = 238  # Jan 1 – Aug 27 inclusive

# ---------------------------------------------------------------------------
# Annualization factors — defined in business_case_frame.md (Phase 2)
# Basis: ratio of full calendar year (365 days) to observed period (238 days) = 1.533,
# adjusted for known NYC fall precipitation patterns:
#   Low  (1.40×): conservative — Sep–Dec not materially rainier than observed avg
#   Mid  (1.55×): baseline — day-ratio 365/238 ≈ 1.533, rounded up for modest fall premium
#   High (1.70×): optimistic — Sep–Nov estimated ~30% rainier than Jan–Aug average
# Source: NOAA LGA historical monthly rain-day frequency; see docs/business_case_frame.md §B4
# ---------------------------------------------------------------------------
ANN_LOW: float = 1.40
ANN_MID: float = 1.55
ANN_HIGH: float = 1.70


def load_data() -> pd.DataFrame:
    """Load the processed TLC + NOAA hourly dataset."""
    df = pd.read_parquet(DATA_PATH)
    return df


def assign_weather_regime(df: pd.DataFrame) -> pd.DataFrame:
    """Label each hour as no_rain / light_rain / heavy_rain."""
    df = df.copy()
    df["weather_regime"] = "no_rain"
    df.loc[df["precip_1h_mm_total"] > LIGHT_RAIN_THRESHOLD_MM, "weather_regime"] = "light_rain"
    df.loc[df["precip_1h_mm_total"] >= HEAVY_RAIN_THRESHOLD_MM, "weather_regime"] = "heavy_rain"
    return df


def get_volume_stats(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Compute per-regime trip volume and average trip miles.

    Returns a dict with four quantities Phase 4 needs:
      baseline_trips_per_hour  — avg trips/hr during no-rain hours
      rain_trips_per_hour      — avg trips/hr during light-rain hours
      baseline_trip_miles      — avg trip distance (miles) during no-rain hours
      rain_trip_miles          — avg trip distance (miles) during light-rain hours
    """
    no_rain = df[df["weather_regime"] == "no_rain"]
    light_rain = df[df["weather_regime"] == "light_rain"]

    return {
        "baseline_trips_per_hour": float(no_rain["request_count"].mean()),
        "rain_trips_per_hour": float(light_rain["request_count"].mean()),
        "baseline_trip_miles": float(no_rain["trip_miles_mean"].mean()),
        "rain_trip_miles": float(light_rain["trip_miles_mean"].mean()),
        "obs_light_rain_hours": int(len(light_rain)),
    }


def calculate_scenarios(stats: Dict[str, Any]) -> pd.DataFrame:
    """
    Build low / mid / high annual opportunity estimates.

    Formula:
        Annual Opportunity ($) =
            rain_hours_per_year
            × avg_trips_per_rain_hour
            × avg_trip_miles_per_trip
            × applicable_margin_uplift_per_mile

    Where rain_hours_per_year = obs_light_rain_hours × annualization_factor.

    Notes on trip volume:
      - Low/Mid use no-rain baseline volume (555.6 trips/hr) — optimistic for Low/Mid.
      - High uses observed rain-period volume (528.6 trips/hr), which is LOWER than
        baseline. Rain at LGA slightly suppresses trip count. The High scenario is
        elevated relative to Mid via the annualization factor (1.70× vs 1.55×), not
        via a volume premium. See business_case_frame.md for full scenario definitions.
    """
    obs_hours = stats["obs_light_rain_hours"]
    bt = stats["baseline_trips_per_hour"]
    rt = stats["rain_trips_per_hour"]
    bm = stats["baseline_trip_miles"]
    rm = stats["rain_trip_miles"]

    scenario_specs = [
        {
            "Scenario": "Low",
            "Coefficient ($/mile)": LIGHT_RAIN_COEF_CI_LOWER,
            "Coefficient basis": "95% CI lower bound",
            "Trips per rain hour": bt,
            "Trip volume basis": "Baseline (no-rain avg)",
            "Avg trip miles": bm,
            "Annualization factor": ANN_LOW,
            "Annualization basis": "Conservative: Sep–Dec ≈ Jan–Aug rain rate",
        },
        {
            "Scenario": "Mid",
            "Coefficient ($/mile)": LIGHT_RAIN_COEF_POINT,
            "Coefficient basis": "Point estimate",
            "Trips per rain hour": bt,
            "Trip volume basis": "Baseline (no-rain avg)",
            "Avg trip miles": bm,
            "Annualization factor": ANN_MID,
            "Annualization basis": "Day-ratio 365/238 = 1.533 + modest fall premium",
        },
        {
            "Scenario": "High",
            "Coefficient ($/mile)": LIGHT_RAIN_COEF_POINT,
            "Coefficient basis": "Point estimate",
            "Trips per rain hour": rt,
            "Trip volume basis": "Observed rain-period avg (lower than baseline)",
            "Avg trip miles": rm,
            "Annualization factor": ANN_HIGH,
            "Annualization basis": "Optimistic: Sep–Nov ~30% rainier than Jan–Aug avg",
        },
    ]

    rows = []
    for spec in scenario_specs:
        rain_hours_annual = obs_hours * spec["Annualization factor"]
        annual_opp = (
            rain_hours_annual
            * spec["Trips per rain hour"]
            * spec["Avg trip miles"]
            * spec["Coefficient ($/mile)"]
        )
        row = {
            "Scenario": spec["Scenario"],
            "Light rain hours observed (Jan–Aug)": obs_hours,
            "Annualization factor": spec["Annualization factor"],
            "Annualization basis": spec["Annualization basis"],
            "Estimated annual light rain hours": round(rain_hours_annual, 1),
            "Avg trips per rain hour": round(spec["Trips per rain hour"], 1),
            "Trip volume basis": spec["Trip volume basis"],
            "Avg trip miles": round(spec["Avg trip miles"], 3),
            "Margin uplift coefficient ($/mile)": spec["Coefficient ($/mile)"],
            "Coefficient basis": spec["Coefficient basis"],
            "Annual margin opportunity (USD)": round(annual_opp, 0),
        }
        rows.append(row)

    df_out = pd.DataFrame(rows)
    return df_out


def build_sensitivity_table(stats: Dict[str, Any]) -> pd.DataFrame:
    """
    Sensitivity of the Mid scenario annual opportunity to:
      - ±10% change in trip volume
      - ±1 standard error shift on the margin coefficient

    Anchored on Mid scenario inputs:
      annualization = ANN_MID, trip miles = baseline_trip_miles
    """
    base_trips = stats["baseline_trips_per_hour"]
    base_miles = stats["baseline_trip_miles"]
    obs_hours = stats["obs_light_rain_hours"]
    rain_hours_annual = obs_hours * ANN_MID

    vol_adjustments = [-0.10, 0.0, 0.10]
    se_adjustments = [-1, 0, 1]

    rows = []
    for vol_adj in vol_adjustments:
        for se_adj in se_adjustments:
            coef = LIGHT_RAIN_COEF_POINT + se_adj * LIGHT_RAIN_COEF_SE
            trips = base_trips * (1 + vol_adj)
            opp = rain_hours_annual * trips * base_miles * coef
            rows.append({
                "Trip volume adjustment": f"{'+' if vol_adj >= 0 else ''}{vol_adj * 100:.0f}%",
                "Coefficient adjustment": f"{'+' if se_adj >= 0 else ''}{se_adj} SE ({coef:.4f} $/mile)",
                "Effective coefficient ($/mile)": round(coef, 4),
                "Trips per rain hour": round(trips, 1),
                "Annual opportunity (USD)": round(opp, 0),
            })

    return pd.DataFrame(rows)


def generate_chart(scenarios_df: pd.DataFrame, out_path: Path) -> None:
    """
    Bar chart: Low / Mid / High annual margin opportunity.
    Headline states the finding and the dollar range.
    """
    low_val = float(scenarios_df.loc[scenarios_df["Scenario"] == "Low", "Annual margin opportunity (USD)"].iloc[0])
    mid_val = float(scenarios_df.loc[scenarios_df["Scenario"] == "Mid", "Annual margin opportunity (USD)"].iloc[0])
    high_val = float(scenarios_df.loc[scenarios_df["Scenario"] == "High", "Annual margin opportunity (USD)"].iloc[0])

    fig, ax = plt.subplots(figsize=(8, 5))
    fig.patch.set_facecolor("#FAFAFA")
    ax.set_facecolor("#FAFAFA")

    scenarios = ["Low", "Mid", "High"]
    values = [low_val, mid_val, high_val]
    colors = ["#A8C7E8", "#2166AC", "#4393C3"]

    bars = ax.bar(scenarios, values, color=colors, width=0.5, edgecolor="white", linewidth=1.2)

    # Value labels on bars
    for bar, val in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 3_000,
            f"${val / 1_000:.0f}K",
            ha="center",
            va="bottom",
            fontsize=13,
            fontweight="bold",
            color="#1A1A1A",
        )

    # Axis formatting
    ax.set_ylim(0, max(values) * 1.25)
    ax.yaxis.set_major_formatter(
        matplotlib.ticker.FuncFormatter(lambda x, _: f"${x/1_000:.0f}K")
    )
    ax.set_ylabel("Annual margin opportunity (USD)", fontsize=10)
    ax.set_xlabel("")
    ax.tick_params(labelsize=11)
    ax.spines[["top", "right"]].set_visible(False)

    # Scenario annotation boxes
    annot = [
        f"CI lower\ncoefficient\n($0.0494/mi)\nBaseline volume\n1.40× annualization",
        f"Point estimate\ncoefficient\n($0.073/mi)\nBaseline volume\n1.55× annualization",
        f"Point estimate\ncoefficient\n($0.073/mi)\nRain-period volume\n1.70× annualization",
    ]
    for i, txt in enumerate(annot):
        ax.text(
            i, max(values) * 0.08,
            txt,
            ha="center", va="bottom",
            fontsize=7, color="#444",
            linespacing=1.4,
        )

    # Title = finding
    ax.set_title(
        f"Weather-Responsive Pricing Could Add ${low_val/1_000:.0f}K–${high_val/1_000:.0f}K\n"
        "in Annual Margin at LGA Under Light Rain",
        fontsize=13, fontweight="bold", color="#1A1A1A", pad=14,
    )

    fig.text(
        0.5, -0.04,
        "Assumes full coefficient represents unrealized opportunity. Requires A/B experiment to validate.\n"
        "Source: TLC rideshare data Jan–Aug 2025, NOAA LGA weather station. M1 regression, HC3 robust SEs.",
        ha="center", fontsize=7, color="#666", style="italic",
    )

    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Chart saved: {out_path}")


def print_interpretation(scenarios_df: pd.DataFrame) -> str:
    """Return the two-paragraph plain-English interpretation."""
    low_val = float(scenarios_df.loc[scenarios_df["Scenario"] == "Low", "Annual margin opportunity (USD)"].iloc[0])
    mid_val = float(scenarios_df.loc[scenarios_df["Scenario"] == "Mid", "Annual margin opportunity (USD)"].iloc[0])
    high_val = float(scenarios_df.loc[scenarios_df["Scenario"] == "High", "Annual margin opportunity (USD)"].iloc[0])

    text = (
        f"## What the number means\n\n"
        f"The regression shows that for every mile driven during a light rain hour at LGA, "
        f"Uber earns approximately $0.073 more in gross margin than during dry hours — a "
        f"statistically significant effect (p < 0.001, N = 5,662 hours). Applied to the "
        f"observed 357 light rain hours in the Jan–Aug 2025 dataset and scaled to a full "
        f"year using an explicit seasonal adjustment, this coefficient implies an annual "
        f"margin gap of **${low_val:,.0f}–${high_val:,.0f}** (mid estimate: **${mid_val:,.0f}**) "
        f"relative to what would be earned if the weather signal were fully priced in. "
        f"The range reflects uncertainty in seasonal rainfall coverage (how many more rain "
        f"hours occur in Sep–Dec) and in which scenario bound on the coefficient applies.\n\n"
        f"## What the number does not mean — and what must be true to realize it\n\n"
        f"This estimate assumes that the entire $0.073/mile coefficient represents "
        f"*unrealized* pricing opportunity — margin that Uber's current algorithm does not "
        f"already capture. If current surge pricing already incorporates weather signals "
        f"(even implicitly, via real-time demand), the realized incremental gain from "
        f"weather-specific pricing would be smaller, potentially zero. The number also "
        f"assumes that applying a 15–20% weather fare premium does not reduce trip completion "
        f"volume by more than 5% — an elasticity claim that cannot be proven from completed-"
        f"trip data alone, because riders who declined surge prices are not in the dataset. "
        f"For the opportunity to be realized, three things must hold: (1) the A/B experiment "
        f"confirms a statistically significant margin uplift in the treatment arm; (2) trip "
        f"completion rate in the treatment arm does not fall below the 5% threshold defined "
        f"in the hypothesis; and (3) Uber's Pricing team integrates the NOAA LGA real-time "
        f"precipitation feed into the surge multiplier pipeline. Until the experiment runs, "
        f"treat this as a sizing estimate of the prize, not a confirmed revenue projection."
    )
    return text


def run_all() -> Dict[str, Any]:
    """Execute the full Phase 4 opportunity sizing pipeline."""
    print("=== Phase 4: Opportunity Sizing ===\n")

    # 1. Load data
    print("Loading processed data...")
    df = load_data()
    df = assign_weather_regime(df)

    # 2. Volume stats
    stats = get_volume_stats(df)
    print(f"Observed light rain hours (Jan–Aug 2025): {stats['obs_light_rain_hours']}")
    print(f"  → Seasonal coverage gap: dataset ends Aug 27; Sep–Dec rain not observed.")
    print(f"  → Annualization factors applied: Low={ANN_LOW}×, Mid={ANN_MID}×, High={ANN_HIGH}×")
    print(f"No-rain avg trips/hr (baseline volume): {stats['baseline_trips_per_hour']:.1f}")
    print(f"Light-rain avg trips/hr: {stats['rain_trips_per_hour']:.1f}")
    print(f"  *** Note: rain-period volume is LOWER than baseline by "
          f"{stats['baseline_trips_per_hour'] - stats['rain_trips_per_hour']:.1f} trips/hr.")
    print(f"  *** The High scenario is elevated via annualization (1.70×), not via volume uplift.")
    print(f"No-rain avg trip miles: {stats['baseline_trip_miles']:.3f}")
    print(f"Light-rain avg trip miles: {stats['rain_trip_miles']:.3f}")
    print()

    # 3. Scenario calculations
    scenarios_df = calculate_scenarios(stats)
    print("=== Scenarios ===")
    print(scenarios_df[["Scenario", "Estimated annual light rain hours",
                          "Avg trips per rain hour", "Avg trip miles",
                          "Margin uplift coefficient ($/mile)",
                          "Annual margin opportunity (USD)"]].to_string(index=False))
    print()

    # 4. Sensitivity table
    sensitivity_df = build_sensitivity_table(stats)
    print("=== Sensitivity (Mid scenario anchor) ===")
    print(sensitivity_df.to_string(index=False))
    print()

    # 5. Save CSVs
    OUT_TABLES.mkdir(parents=True, exist_ok=True)
    scenarios_path = OUT_TABLES / "opportunity_sizing_scenarios.csv"
    sensitivity_path = OUT_TABLES / "sensitivity_analysis.csv"
    scenarios_df.to_csv(scenarios_path, index=False)
    sensitivity_df.to_csv(sensitivity_path, index=False)
    print(f"Saved: {scenarios_path}")
    print(f"Saved: {sensitivity_path}")
    print()

    # 6. Chart
    OUT_CHARTS.mkdir(parents=True, exist_ok=True)
    chart_path = OUT_CHARTS / "chart4_opportunity_estimate.png"
    generate_chart(scenarios_df, chart_path)

    # 7. Print interpretation
    interp = print_interpretation(scenarios_df)
    print()
    print(interp)

    return {
        "scenarios": scenarios_df,
        "sensitivity": sensitivity_df,
        "stats": stats,
        "interpretation": interp,
    }


if __name__ == "__main__":
    results = run_all()
