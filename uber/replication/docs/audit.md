# Phase 1 Audit — Original Work (Jackson Turnbull)

> Produced by replication repo, Phase 1. Read-only review of `/Users/jacksonbutler/Projects/uber/project`.
> No original code was executed. All findings are derived from reading source files, model summaries, and diagnostic reports.

---

## 1. Confirmed Data Sources, Time Period, and Geography

### TLC Rideshare Data
- **Source:** NYC Taxi & Limousine Commission (TLC) FHVHV (For-Hire Vehicle High-Volume) trip records
- **Coverage:** January 2025 through August 2025 (months 01–08 processed)
- **Geography:** LaGuardia Airport pickups only — TLC zone ID 138 (`PULocationID == 138`)
- **Carriers included:** All FHVHV carriers (primarily Uber and Lyft); yellow cabs are not in FHVHV data
- **Data access:** Monthly parquet files from TLC public dataset (`fhvhv_tripdata_2025-<mm>.parquet`)

### NOAA Weather Data
- **Source:** NOAA Integrated Surface Dataset (ISD), LGA station
- **Coverage:** December 31, 2024 through August 27, 2025 (data availability cutoff at time of analysis)
- **Resolution:** Sub-hourly observations, resampled to 1-hour bins keyed on local NYC time (UTC → America/New_York)
- **Known gap:** February 21–28 observations are missing due to upstream ISD outage

### Effective merged dataset range
- **January 1, 2025 00:00 → August 27, 2025 00:00** (inner join on hourly datetime)
- Data stops at August 27 because weather data ends there; TLC data extends through August 31

---

## 2. Unit of Analysis

**One row = one calendar hour at LGA, keyed on request datetime** (i.e., the hour in which the ride request was placed, not pickup time).

This choice is explicit in the process notes: "choose to look at request_hour buckets, not pickup, because we primarily want to measure demand from riders to measure weather impacts."

The merged dataset contains **5,702 hourly rows** covering Jan–Aug 2025.

---

## 3. Variable Inventory (Plain English)

### TLC Hourly Aggregation (`fhvhv_lga_hourly_agg_2025.parquet` — 5,820 rows)

| Variable | Plain English |
|---|---|
| `datetime_hour` | Hour start timestamp (request time floored to hour) |
| `date` | Calendar date |
| `request_hour` | Hour of day (0–23) |
| `trip_miles_sum` | Total miles driven across all LGA pickups in the hour |
| `trip_miles_mean` | Average miles per trip |
| `trip_miles_median` | Median miles per trip |
| `trip_time_sum` | Total in-vehicle time across all trips (seconds) |
| `trip_time_mean` | Average in-vehicle time per trip (seconds) |
| `base_passenger_fare_sum` | Total passenger fare collected (excludes tips and fees) ($) |
| `avg_base_passenger_fare` | Average passenger fare per trip ($) |
| `subtotal_fare_sum` | Total fare including all fees and surcharges, excluding tips ($) |
| `avg_subtotal_fare` | Average subtotal fare per trip ($) |
| `rider_total_sum` | Total amount charged to riders including tips ($) |
| `driver_pay_sum` | Total driver earnings before tips ($) |
| `avg_driver_pay` | Average driver pay per trip ($) |
| `driver_pay_pct_of_base_fare` | Driver pay as a share of passenger fare (proxy for Uber's margin compression) |
| `request_count` | Number of ride requests in the hour |
| `pickup_count` | Number of pickups in the hour |
| `dropoff_count` | Number of dropoffs in the hour |
| `avg_speed_mph` | Average trip speed in miles per hour |
| `wait_time_sec_mean` | Average seconds between request and pickup |

### Weather Hourly Aggregation (`weather_lga_hourly_agg_2025_enhanced.parquet` — 5,717 rows)

| Variable | Plain English |
|---|---|
| `temp_f_mean` | Average temperature (°F) |
| `temp_f_min` / `temp_f_max` | Temperature range (°F) |
| `dewpoint_f_mean` | Average dewpoint (°F), used to compute humidity |
| `wind_speed_mph_mean` | Average wind speed (mph) |
| `precip_1h_mm_total` | Total precipitation in the hour (millimeters, rain + snow combined) |
| `relative_humidity` | Computed relative humidity (%) using Magnus approximation |
| `wind_chill_f` | NWS wind chill (°F). **Non-null only when temperature ≤ 50°F AND wind ≥ 3 mph.** Falls back to `temp_f_mean` on cold hours where wind is too low. |
| `heat_index_f` | NOAA heat index (°F). **Non-null only when temperature ≥ 80°F AND relative humidity ≥ 40%.** |

### Derived Modeling Variables (constructed in `revenue_models.py` and `weather_monetization_models.py`)

| Variable | Plain English |
|---|---|
| `fare_per_mile` | Total hourly fare divided by total hourly miles ($/mile), measures fare intensity |
| `driverpay_per_mile` | Total hourly driver pay divided by total miles ($/mile) |
| `margin_per_mile` | Fare per mile minus driver pay per mile ($/mile) — primary margin metric |
| `demand_resid` | Hourly request count after removing hour-of-week and month seasonal patterns |
| `rain_flag` | 1 if any precipitation this hour, 0 otherwise (threshold: > 0 mm) |
| `heavy_rain_flag` | 1 if heavy precipitation, 0 otherwise (threshold: ≥ 5.0 mm/hr) |
| `rain_flag_lag0`, `heavy_rain_flag_lag0` | Explicit aliases for current-hour rain flags |
| `rain_flag_lag1` | Whether it rained in the prior hour |
| `demand_resid_lag1` | Seasonal-adjusted demand from the prior hour (lagged demand pressure) |
| `wind_chill_diff` | Wind chill minus temperature (captures perceived cold beyond thermometer reading) |
| `heat_index_diff` | Heat index minus temperature (captures perceived heat beyond thermometer reading) |

---

## 4. Data Processing Pipeline

1. **Raw TLC files** → `tlc_processor.py`: Trim to allowed columns, fix DST error (March 9 2025), add derived metrics (wait time, fare/mile, flags), apply discard rules, filter to airport trips only → `data/interim/tlc/fhvhv_tripdata_2025-<mm>_clean.parquet`
2. **Interim TLC files** → `tlc_combine_cleaned.py`: Concatenate all months → `data/interim/tlc/fhvhv_tripdata_2025_all_clean.parquet`
3. **Combined TLC** → `tlc_aggregate_hourly.py`: Filter to LGA pickups (`is_lga_pickup == 1`), group by request hour, aggregate → `data/processed/tlc/fhvhv_lga_hourly_agg_2025.parquet`
4. **Raw NOAA ISD** → `weather_aggregate_hourly.py`: Resample to hourly bins, convert UTC → NYC time → `data/processed/weather_lga_hourly_agg_2025.parquet`
5. **Weather hourly** → `weather_variable_construction.py`: Compute relative humidity, wind chill, heat index → `data/processed/weather_lga_hourly_agg_2025_enhanced.parquet`
6. **TLC + weather** → `data_merge.py`: Inner join on datetime hour → `data/processed/fhvhv_lga_hourly_with_weather_2025.parquet`

### Discard rules applied to trip-level data (before aggregation)
Trips are discarded (flagged `discard = 1`) if they have:
- Negative or missing wait time (request → pickup)
- Invalid congestion surcharge (allowed values: $0, $0.75, $2.75)
- Invalid CBD congestion fee (allowed values: $0, $1.50)
- Negative driver pay
- Negative trip miles
- Negative trip time
- Negative tips
- Temporal ordering violations (request > pickup, pickup ≥ dropoff, or pickup before on-scene)

### Merge logic
Inner join on `datetime_hour` (TLC) to DatetimeIndex (weather), validated as 1:1. Result: **5,702 rows** (Jan 1 – Aug 27, 2025).

---

## 5. Model Specifications

### Seasonality residualization (pre-step for all models)
All dependent variables are first residualized by fitting:

```
metric ~ C(hour_of_week) + C(month)
```

where `hour_of_week = day_of_week × 24 + hour` (0–167). Residuals represent within-hour-of-week, within-month variation. This is equivalent to a two-way fixed effects model.

### M0 — Baseline economics, no weather
```
margin_per_mile_resid ~ avg_trip_miles + avg_trip_time_min + demand_resid_lag1 + driver_pay_pct_of_base_fare
```
Also run for: `avg_base_passenger_fare_resid` (same regressors).

**M0 results (margin):**
| Variable | Coefficient | p-value |
|---|---|---|
| Average trip distance | -0.0135 | < 0.001 |
| Average trip duration | -0.0067 | < 0.001 |
| Prior-hour demand | +0.0001 | < 0.001 |
| Driver pay share of fare | -3.4535 | < 0.001 |
| Observations | 5,701 | — |
| Adj. R² | 0.575 | — |

### M1 (E1 in original) — Baseline economics + weather block
```
margin_per_mile_resid ~ avg_trip_miles + avg_trip_time_min + demand_resid_lag1 + driver_pay_pct_of_base_fare
                      + rain_flag_lag0 + heavy_rain_flag_lag0 + precip_1h_mm_total + wind_chill_f
```
Also run for: `avg_base_passenger_fare_resid` (same regressors).

**M1 results (margin) — key weather coefficients:**
| Weather Variable | Coefficient | 95% CI | p-value | Interpretation |
|---|---|---|---|---|
| Any rain (binary) | **+0.0847** | [0.044, 0.125] | < 0.001 | Light rain associated with +$0.08/mile margin uplift |
| Heavy rain (binary) | **-0.3337** | [-0.592, -0.076] | 0.011 | Heavy rain associated with -$0.33/mile margin drop |
| Precipitation amount | +0.0322 | [0.006, 0.059] | 0.017 | Each additional mm/hr adds ~$0.03/mile |
| Wind chill | +0.0018 | [0.001, 0.003] | < 0.001 | Colder conditions modestly increase margin |
| **Observations** | **2,205** | — | — | ⚠️ Only cold-weather hours (see note below) |
| **Adj. R²** | **0.594** | — | — | — |

> **Critical observation:** M1 is estimated on 2,205 rows, not the full 5,702. This is because `wind_chill_f` is only non-null when temperature ≤ 50°F AND wind ≥ 3 mph. The model therefore fits only on cold-weather hours (approximately October–April). Rain effects are estimated exclusively from cold-weather rain events. This is labeled "cold-focused" in the code comments but is not explicitly stated in model outputs.

**REPLICATION.md vs actual model discrepancy:** The REPLICATION.md states the light rain coefficient is "+0.1 (p<0.001)." The actual model output is **+0.0847**, which rounds to +0.08, not +0.10. This is a minor discrepancy likely due to rounding or a different model run.

---

## 6. Weather Regime Threshold Values (Exact)

| Regime | Variable | Threshold |
|---|---|---|
| Light rain (any rain) | `precip_1h_mm_total` | **> 0 mm** |
| Heavy rain | `precip_1h_mm_total` | **≥ 5.0 mm/hr** |
| Wind chill valid domain | temperature | **≤ 50°F** AND wind ≥ 3 mph |
| Heat index valid domain | temperature | **≥ 80°F** AND relative humidity ≥ 40% |

**Observed rain frequencies in merged dataset:**
- Hours with any rain: **385 of 5,702** (6.8%)
- Hours with heavy rain: **28 of 5,702** (0.5%)
- Total precipitation: 695.9 mm (~27.4 inches over Jan–Aug)

---

## 7. Processed Data File Locations and Schemas

| File | Rows | Columns | Date Range | Description |
|---|---|---|---|---|
| `data/processed/fhvhv_lga_hourly_with_weather_2025.parquet` | 5,702 | 43 | Jan 1 – Aug 27, 2025 | **Primary analysis file.** Merged TLC + weather. |
| `data/processed/fhvhv_lga_hourly_with_weather_2025_with_preds.parquet` | ~5,702 | 43+ | Jan 1 – Aug 27, 2025 | Analysis file with model predictions appended. |
| `data/processed/tlc/fhvhv_lga_hourly_agg_2025.parquet` | 5,820 | 29 | Jan 1 – Aug 31, 2025 | TLC only, pre-merge. 118 extra rows vs merged (Aug 27–31 hours with no weather match). |
| `data/processed/weather_lga_hourly_agg_2025.parquet` | 5,717 | 13 | Dec 31, 2024 – Aug 27, 2025 | Basic weather. Includes 5 rows from Dec 2024. |
| `data/processed/weather_lga_hourly_agg_2025_enhanced.parquet` | 5,717 | 16 | Dec 31, 2024 – Aug 27, 2025 | Weather with wind chill, heat index, humidity added. |

**For replication:** Copy `fhvhv_lga_hourly_with_weather_2025.parquet` as the primary source. The weather_lga files are needed to rerun weather variable construction if required.

---

## 8. Top 3 Analytical Strengths

**Strength 1: Rigorous two-step residualization for seasonality control**

The original work correctly addresses the primary confounding threat in airport demand analysis: the strong, structured time patterns driven by flight schedules, business travel cycles, and seasonal variation. By residualizing both demand and all economic metrics against 168-bin hour-of-week × month fixed effects before regressing on weather, the model isolates within-schedule variation. This is methodologically sounder than a single regression with time controls, and the approach is consistently applied across all dependent variables.

**Strength 2: Comprehensive data quality pipeline with explicit discard rules**

The TLC data cleaning is unusually thorough for a solo project. Eight categories of discard rules are documented and applied with clear justification (DST error correction for March 9 is a particularly precise fix). The treatment of monetary anomalies (invalid congestion fees, negative driver pay) reflects genuine understanding of TLC data idiosyncrasies. Total precipitation cross-checked against NOAA daily summaries (695.9 mm computed vs 692.4 mm in daily summary) demonstrates genuine data verification effort.

**Strength 3: Diagnostic assessment of OLS assumptions**

The original work ran the full battery of OLS diagnostics (Breusch-Pagan for heteroskedasticity, Breusch-Godfrey for autocorrelation, Jarque-Bera for normality, Cook's distance, Durbin-Watson, VIF). These results are saved in `reports/model_diagnostics/`. Most projects at this stage skip diagnostics entirely. Identifying that all three major OLS assumptions are violated (DW=0.853 indicates strong positive autocorrelation; BP p<0.001 indicates heteroskedasticity; JB p≈0 indicates non-normal residuals) is a meaningful finding, even if the remediation was incomplete.

---

## 9. Top 3 Gaps vs. Business Case Standard

**Gap 1: No dollar figure produced — the central business question is left unanswered**

The analysis establishes that light rain is associated with a +$0.0847/mile margin uplift in the M1 model. It never translates this into an annual dollar estimate. A business case requires: (coefficient) × (average trip miles per hour) × (rainy hours per year) × (annualization factor). This calculation was not performed. The REPLICATION.md correctly identifies this as "the primary gap."

The compounding issue: the process notes conclude that "Uber probably can't improve pricing in rainy, cold weather" because "Uber already appears to be internalizing most of the weather effect." This conclusion is stated informally in process notes and never rigorously tested. A proper business case requires distinguishing between (a) current pricing already capturing weather uplift vs. (b) structural undercapture that an experiment could exploit.

**Gap 2: Standard errors are not heteroskedasticity-robust despite known violations**

The model summaries explicitly state `Covariance Type: nonrobust`, and the Breusch-Pagan test (p = 4.2e-10) confirms significant heteroskedasticity in E1 margin. This means all standard errors, confidence intervals, and p-values are biased. Reported significance stars (p<0.001 for the light rain coefficient) may overstate precision. Business recommendations based on these standard errors cannot be defended. The replication must use HC3 or HC1 robust standard errors.

**Gap 3: The M1 model is estimated only on cold-weather hours, but this restriction is not stated in model outputs**

`wind_chill_f` is non-null only when temperature ≤ 50°F and wind ≥ 3 mph. When OLS drops rows with any null regressor, M1 is silently estimated on 2,205 of 5,702 available hourly observations — approximately 39% of the dataset. These are disproportionately winter and early spring observations. Rain during warm months (May–August) is excluded from the coefficient estimate entirely. The rain coefficient therefore measures the effect of cold-weather rain, not rain in general. This selection bias is labeled "cold-focused" in a code comment but never appears in model output or any summary document. A business case that applies the cold-rain coefficient to all rain hours will overstate or mischaracterize the opportunity.

---

## 10. Supplemental Notes

### Curfew hours
LGA has a curfew from midnight to 6am. Process notes indicate awareness of this: "drop 2-6 hours, which is all rides after 1:59:59 and before 07:00:00." However, reviewing the tlc_aggregate_hourly code, no explicit curfew filter is applied before aggregation. Hours 0–6 are present in the dataset. If modeled hours include curfew hours, the request_count residualization will absorb these as a pattern, but their presence could distort the fixed effects.

### Precipitation type
The `precip_1h_mm_total` variable sums all precipitation regardless of type (rain + snow + sleet). The process notes acknowledge this: "looked at general precipitation, not separating rain and snow." January and February rain events may predominantly be snow, which has different operational impacts on Uber demand. The original model does not distinguish.

### Heavy rain sample size
28 hours of heavy rain (≥ 5 mm/hr) in the dataset is a very small sample for a binary regression coefficient. The wide confidence interval on the heavy rain coefficient [-0.592, -0.076] reflects this. The original notes flag this explicitly: "Rain intensity is sparse; heavy-rain regressions rely on low sample."

### The "pricing already captures weather" conclusion
The process notes conclude that Uber may already be internalizing the weather effect. This conclusion rests on a case study of one date (2025-03-20) where the E1 model fit was better than E0 but margin was not substantially higher than the seasonality baseline. This is not a statistical test of whether current pricing fully captures weather elasticity; it is a qualitative observation. The replication should frame this differently: the margin uplift is observable, but whether it results from Uber's dynamic pricing or from trip composition changes (shorter, higher-margin trips during rain) is not identified in this data.
