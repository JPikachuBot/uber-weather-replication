"""
Phase 3 — Baseline Regression Module
=====================================
Clean, importable version of the weather-margin regression analysis.

Design decisions vs original work:
- M1 uses temp_f_mean (available all hours) instead of wind_chill_f (cold hours only),
  enabling analysis on all 5,702 hourly observations rather than the original 2,205.
  This fixes Gap 3 identified in docs/audit.md.
- All models use HC3 heteroskedasticity-robust standard errors to address
  the confirmed heteroskedasticity (Breusch-Pagan p<0.001). Fixes Gap 2.
- Weather regime thresholds are named constants, not magic numbers.
"""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd
import statsmodels.api as sm
import patsy

# ---------------------------------------------------------------------------
# Weather regime thresholds — exact values from original analysis (audit.md)
# ---------------------------------------------------------------------------
LIGHT_RAIN_THRESHOLD_MM: float = 0.0   # rain_flag = 1 if precip_1h_mm_total > 0.0 mm
HEAVY_RAIN_THRESHOLD_MM: float = 5.0   # heavy_rain_flag = 1 if precip_1h_mm_total >= 5.0 mm

# ---------------------------------------------------------------------------
# Business-readable variable labels
# ---------------------------------------------------------------------------
VAR_LABELS: Dict[str, str] = {
    "const": "Intercept",
    "avg_trip_miles": "Average trip distance (miles)",
    "avg_trip_time_min": "Average trip duration (minutes)",
    "demand_resid_lag1": "Prior-hour demand pressure",
    "driver_pay_pct_of_base_fare": "Driver pay share of fare",
    "rain_flag": "Light rain (any precipitation)",
    "heavy_rain_flag": "Heavy rain (≥5 mm/hr)",
    "precip_1h_mm_total": "Precipitation amount (mm/hr)",
    "temp_f_mean": "Air temperature (°F)",
    "wind_chill_f": "Wind chill temperature (°F) [cold hours only]",
}


# ---------------------------------------------------------------------------
# Feature engineering
# ---------------------------------------------------------------------------

def add_calendar_features(df: pd.DataFrame, time_col: str = "datetime_hour") -> pd.DataFrame:
    """Add hour_of_week, month, and season columns from datetime."""
    out = df.copy()
    ts = pd.to_datetime(out[time_col])
    out["day_of_week"] = ts.dt.dayofweek
    out["hour"] = ts.dt.hour
    out["hour_of_week"] = out["day_of_week"] * 24 + out["hour"]
    out["month"] = ts.dt.month
    out["season"] = ts.dt.month.map(
        lambda m: "cold" if m in {10, 11, 12, 1, 2, 3, 4} else "warm"
    )
    return out


def add_trip_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Compute fare per mile, driver pay per mile, margin per mile, trip duration in minutes."""
    out = df.copy()
    miles_safe = out["trip_miles_sum"].where(out["trip_miles_sum"] > 0, other=np.nan)
    out["fare_per_mile"] = out["base_passenger_fare_sum"] / miles_safe
    out["driverpay_per_mile"] = out["driver_pay_sum"] / miles_safe
    out["margin_per_mile"] = out["fare_per_mile"] - out["driverpay_per_mile"]
    out["avg_trip_time_min"] = out["trip_time_mean"] / 60.0
    out["avg_trip_miles"] = out["trip_miles_mean"]
    return out


def add_weather_flags(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add binary weather regime flags using named threshold constants.

    Light rain: any precipitation > 0 mm/hr
    Heavy rain: precipitation >= 5.0 mm/hr (exact threshold from original analysis)
    """
    out = df.copy()
    out["rain_flag"] = (out["precip_1h_mm_total"] > LIGHT_RAIN_THRESHOLD_MM).astype(int)
    out["heavy_rain_flag"] = (out["precip_1h_mm_total"] >= HEAVY_RAIN_THRESHOLD_MM).astype(int)
    return out


def add_weather_regime_label(df: pd.DataFrame) -> pd.DataFrame:
    """Add a plain-English weather regime category (for charts and tables)."""
    out = df.copy()
    out["weather_regime"] = np.where(
        out["heavy_rain_flag"] == 1,
        "Heavy rain (≥5 mm/hr)",
        np.where(out["rain_flag"] == 1, "Light rain (>0 mm/hr)", "No rain"),
    )
    return out


# ---------------------------------------------------------------------------
# Residualization: remove hour-of-week and month fixed effects
# ---------------------------------------------------------------------------

def residualize(
    df: pd.DataFrame,
    metric: str,
) -> Tuple[pd.DataFrame, sm.regression.linear_model.RegressionResultsWrapper]:
    """
    Fit:  metric ~ C(hour_of_week) + C(month)

    Adds metric_resid and metric_fitted columns to df.
    Returns (updated_df, seasonality_model).

    This removes structured time patterns (flight schedules, seasonal effects)
    so that only within-schedule variation remains for regression analysis.
    """
    out = df.copy()
    sub = out[[metric, "hour_of_week", "month"]].dropna()
    formula = f"{metric} ~ C(hour_of_week) + C(month)"
    y, X = patsy.dmatrices(formula, data=sub, return_type="dataframe")
    model = sm.OLS(y, X).fit()
    out.loc[sub.index, f"{metric}_resid"] = model.resid
    out.loc[sub.index, f"{metric}_fitted"] = model.fittedvalues
    return out, model


# ---------------------------------------------------------------------------
# OLS with robust standard errors
# ---------------------------------------------------------------------------

def run_ols_robust(
    df: pd.DataFrame,
    y_col: str,
    x_cols: list[str],
    cov_type: str = "HC3",
) -> Tuple[sm.regression.linear_model.RegressionResultsWrapper, pd.DataFrame]:
    """
    Run OLS on non-null rows with heteroskedasticity-robust standard errors.

    Args:
        df: DataFrame containing all columns
        y_col: dependent variable column name
        x_cols: list of regressor column names
        cov_type: covariance estimator — HC3 by default (conservative, recommended for n>100)

    Returns:
        (fitted model with robust SEs, DataFrame of rows used in estimation)
    """
    cols = [y_col] + list(x_cols)
    sub = df[cols].dropna()
    X = sm.add_constant(sub[x_cols], has_constant="add")
    y = sub[y_col]
    model = sm.OLS(y, X).fit(cov_type=cov_type)
    return model, sub


# ---------------------------------------------------------------------------
# Business-readable output
# ---------------------------------------------------------------------------

def coef_table_business(
    model: sm.regression.linear_model.RegressionResultsWrapper,
    label_map: Dict[str, str] | None = None,
) -> pd.DataFrame:
    """
    Return a business-readable coefficient table with plain-English variable names,
    robust standard errors, and significance stars.
    """
    if label_map is None:
        label_map = VAR_LABELS

    conf = model.conf_int()
    rows = []
    for var in model.params.index:
        p = model.pvalues[var]
        stars = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
        rows.append({
            "Variable": label_map.get(var, var),
            "Coefficient": round(model.params[var], 4),
            "Std. Error (HC3)": round(model.bse[var], 4),
            "t-stat": round(model.tvalues[var], 3),
            "p-value": round(model.pvalues[var], 4),
            "95% CI Lower": round(conf.loc[var, 0], 4),
            "95% CI Upper": round(conf.loc[var, 1], 4),
            "Significance": stars,
        })

    out = pd.DataFrame(rows)
    out.attrs["n_obs"] = int(model.nobs)
    out.attrs["adj_r2"] = round(model.rsquared_adj, 4)
    out.attrs["cov_type"] = model.cov_type
    return out


# ---------------------------------------------------------------------------
# Full data preparation pipeline
# ---------------------------------------------------------------------------

def prepare_data(raw_path: str | Path) -> pd.DataFrame:
    """
    Load and prepare the merged TLC + weather dataset for modeling.

    Steps:
    1. Load parquet
    2. Add calendar features
    3. Compute trip metrics (fare/mile, margin/mile)
    4. Add weather regime flags
    5. Residualize request_count, margin_per_mile, avg_base_passenger_fare
    6. Add demand_resid_lag1 (lagged demand residual)
    7. Add weather regime label for charts

    Returns: analysis-ready DataFrame
    """
    df = pd.read_parquet(raw_path)
    df = add_calendar_features(df)
    df = add_trip_metrics(df)
    df = add_weather_flags(df)

    # Residualize demand (for lagged demand regressor)
    df, _ = residualize(df, "request_count")
    df["demand_resid_lag1"] = df["request_count_resid"].shift(1)

    # Residualize primary modeling targets
    df, _ = residualize(df, "margin_per_mile")
    df, _ = residualize(df, "avg_base_passenger_fare")

    # Weather regime label
    df = add_weather_regime_label(df)

    return df


# ---------------------------------------------------------------------------
# Model specifications
# ---------------------------------------------------------------------------

M0_REGRESSORS: list[str] = [
    "avg_trip_miles",
    "avg_trip_time_min",
    "demand_resid_lag1",
    "driver_pay_pct_of_base_fare",
]

M1_REGRESSORS: list[str] = M0_REGRESSORS + [
    "rain_flag",
    "heavy_rain_flag",
    "precip_1h_mm_total",
    "temp_f_mean",          # replaces wind_chill_f to allow all-season estimation
]

# Original M1 spec — cold-season only due to wind_chill_f nulls
M1_ORIGINAL_REGRESSORS: list[str] = M0_REGRESSORS + [
    "rain_flag",
    "heavy_rain_flag",
    "precip_1h_mm_total",
    "wind_chill_f",         # non-null only when temp ≤ 50°F AND wind ≥ 3 mph
]


def run_all_models(
    df: pd.DataFrame,
    save_dir: str | Path | None = None,
) -> Dict[str, sm.regression.linear_model.RegressionResultsWrapper]:
    """
    Run all four primary models (M0 and M1 for fare and margin).

    Models:
        m0_fare:     Average fare per trip ~ economic controls
        m1_fare:     Average fare per trip ~ economic controls + weather (all seasons)
        m0_margin:   Margin per mile ~ economic controls
        m1_margin:   Margin per mile ~ economic controls + weather (all seasons)

    Also runs m1_margin_original for comparison with original work.

    Returns dict of model name → fitted model.
    Optionally saves model objects to save_dir as .pkl files.
    """
    models: Dict[str, sm.regression.linear_model.RegressionResultsWrapper] = {}

    model_specs = [
        ("m0_fare",             "avg_base_passenger_fare_resid", M0_REGRESSORS),
        ("m1_fare",             "avg_base_passenger_fare_resid", M1_REGRESSORS),
        ("m0_margin",           "margin_per_mile_resid",         M0_REGRESSORS),
        ("m1_margin",           "margin_per_mile_resid",         M1_REGRESSORS),
        ("m1_margin_original",  "margin_per_mile_resid",         M1_ORIGINAL_REGRESSORS),
    ]

    for name, y_col, x_cols in model_specs:
        model, used = run_ols_robust(df, y_col, x_cols)
        models[name] = model
        print(f"[{name}] n={int(model.nobs)}, adj_R²={model.rsquared_adj:.3f}, "
              f"cov_type={model.cov_type}")

    if save_dir is not None:
        save_dir = Path(save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)
        for name, model in models.items():
            if name == "m1_margin_original":
                continue  # save only the four primary models
            with open(save_dir / f"{name}.pkl", "wb") as f:
                pickle.dump(model, f)
        print(f"Models saved to {save_dir}")

    return models
