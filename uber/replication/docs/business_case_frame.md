# Business Case Frame — Uber Weather Pricing at LGA

> Phase 2 output. This document must be read before running any regression or opportunity sizing analysis.
> Written before any new analysis is run. The recommendation is the last slide, written first.

---

## One-Sentence Recommendation

Uber should add real-time NOAA precipitation data as an explicit trigger input to its LGA dynamic pricing algorithm, applying a 15–20% fare increase during light rain events, validated through a controlled A/B experiment before deployment — because observed rideshare data shows a statistically significant margin uplift during light rain that current pricing does not appear to explicitly target.

---

## Falsifiable Hypothesis

**A 15–20% weather-triggered fare increase at LGA during NOAA-confirmed light rain (precipitation > 0 mm/hr) will increase Uber's net margin per mile by at least $0.04 per mile relative to control hours with standard pricing, without reducing trip completion volume by more than 5%, because LGA riders during rain face captive demand with no flat-rate ground alternative and demonstrated willingness to pay airport surge prices.**

Falsification criteria:
- **Confirmed** if: experiment treatment arm shows margin per mile increase ≥ $0.04 AND trip volume decline < 5%.
- **Rejected** if: margin per mile increase < $0.04, OR trip volume drops > 5% in the treatment arm.
- **Inconclusive** if: effect size is in range but confidence interval crosses zero at 95% level.

The hypothesis is directional, specifies the mechanism (captive demand), and names numeric thresholds that a live experiment can measure directly.

---

## Dollar Figure Methodology

> The dollar figure is not calculated in this phase. Phase 4 computes the actual numbers using Phase 3 model outputs and TLC volume data. This section defines the methodology that Phase 4 must follow.

### Inputs Required

| Input | Source | Phase |
|---|---|---|
| Observed light rain hours (Jan–Aug 2025) | NOAA processed weather data | Available now: 385 hours |
| Annualization factor | NOAA historical LGA rain frequency (Sep–Dec estimated) | Phase 4 |
| Average trips per light-rain hour at LGA | TLC processed data, split by weather regime | Phase 3/4 |
| Average trip miles per trip during light rain | TLC processed data | Phase 3/4 |
| Margin uplift per mile — light rain coefficient | M1 regression output, robust standard errors | Phase 3 |
| 95% confidence interval on light rain coefficient | M1 regression output, robust standard errors | Phase 3 |

### Calculation Structure

```
Annual Opportunity ($) =
    rain_hours_per_year
    × avg_trips_per_rain_hour
    × avg_trip_miles_per_trip
    × applicable_margin_uplift_per_mile
```

Where:

```
rain_hours_per_year = observed_light_rain_hours × annualization_factor
```

This calculation produces gross margin opportunity — the dollar value of the observed uplift applied forward. It does not account for any portion already captured by current dynamic pricing. That distinction is addressed in the "What This Is Not" section of the deliverable and quantified in the experiment.

### Scenario Bound Definitions

| Scenario | Margin Coefficient | Trip Volume | Annualization |
|---|---|---|---|
| **Low** | Lower bound of 95% CI on M1 light rain coefficient ($0.044/mile, pending robust SE rerun) | Baseline trips per hour (non-rain average) | 1.40× observed (conservative; assumes Sep–Dec not significantly rainier) |
| **Mid** | Point estimate of M1 light rain coefficient ($0.0847/mile, pending robust SE rerun) | Baseline trips per hour | 1.55× observed (day-ratio: 365 ÷ 239 days ≈ 1.53, rounded up slightly for known fall rain premium) |
| **High** | Point estimate of M1 light rain coefficient | Observed rain-period trip volume (may exceed baseline if rain increases LGA demand) | 1.70× observed (assumes Sep–Nov is ~30% rainier than observed Jan–Aug average) |

**Key caveat:** The M1 coefficient in the original work was estimated on cold-weather hours only (~Oct–Apr). Phase 3 will rerun M1 with all-season data and heteroskedasticity-robust standard errors. If the new coefficient differs materially from $0.0847, Phase 4 updates all scenarios accordingly before the dollar figure is finalized.

**What the scenarios do NOT vary:** The scenarios do not model a range for the share of the uplift already captured by current pricing. That is not a scenario — it is the central unknown that the experiment resolves. Until the experiment runs, all scenarios assume the full coefficient represents unrealized opportunity. This is the most optimistic framing; limitations are explicitly stated in Phase 4.

---

## Assumptions Table

| # | Assumption | Implication if Wrong | Validation Approach |
|---|---|---|---|
| B1 | The +$0.0847/mile margin uplift observed in M1 is not already being fully captured by Uber's current dynamic pricing — i.e., it represents incremental opportunity. | If current pricing already captures 100% of the weather signal, the incremental opportunity is $0 and the experiment will show no treatment effect. | This is the primary thing the A/B experiment tests. No pre-experiment data can resolve it. |
| B2 | The cold-weather rain coefficient from M1 (+$0.0847/mile) is representative of all-season rain events at LGA, not just cold-weather rain. | If warm-weather rain (May–Aug) has a weaker effect (different rider composition, more tourists), the mid- and high-scenario estimates overstate the annual opportunity by an unknown amount. | Phase 3 will attempt a season-stratified regression to test whether the coefficient differs between cold (Oct–Apr) and warm (May–Sep) months. |
| B3 | Rider demand at LGA is inelastic to a 15–20% fare increase during light rain — trip completion rate does not drop by more than 5%. | If demand is more elastic than assumed (e.g., riders cancel and wait for prices to drop), the volume assumption overstates the opportunity and the experiment secondary metrics will show elevated cancellation rates. | Measured directly in the A/B experiment via cancellation rate and surge acceptance rate. |
| B4 | The annualization factor (1.40–1.70×) adequately adjusts the Jan–Aug observed rain hours to a full-year estimate. | If September–December is significantly rainier than assumed (NOAA historical data suggests NYC fall is wet), the mid scenario underestimates; if drier, it overestimates. | Pull NOAA LGA historical monthly rain-day frequency for the past 5 years to derive a data-driven seasonal adjustment in Phase 4. |
| B5 | LGA riders face captive demand during rain — no competitive flat-rate ground alternatives materially constrain Uber's pricing power. | If NYC outer-borough car services, black cars, or airport shuttle pricing becomes more competitive during rain, Uber's effective pricing ceiling is lower than assumed. | Check TLC data for relative yellow cab and SHL (Superhero Livery) trip volumes at LGA during rain hours. If SHL volume rises in rain, competitive substitution is occurring. |
| B6 | Average trip miles during light rain hours are approximately equal to average trip miles during baseline (non-rain) hours. | If rain disproportionately affects short trips (e.g., terminal-to-parking, short-haul to Queens), average trip miles during rain fall, reducing total dollar opportunity even if the per-mile coefficient holds. | Compare avg_trip_miles across weather regimes in Phase 3 data quality review. |
| B7 | Driver pay percentage of base fare does not systematically increase during rain in ways that offset fare-side gains. | If Uber raises driver incentives during rain to maintain supply (fewer drivers willing to operate), the margin per mile gain from higher fares is partially or fully offset by higher driver pay per mile. | Check driver_pay_pct_of_base_fare across weather regimes in Phase 3. If the coefficient on driver_pay_pct is significantly different during rain hours, the net margin calculation must account for this. |

---

## "So What" — If the Hypothesis Is Confirmed

**Trigger condition:** A/B experiment shows margin per mile increases by ≥ $0.04 in the treatment arm AND trip completion volume decline < 5%.

**Specific action:** Uber Pricing/Marketplace team integrates NOAA LGA ISD feed into the real-time surge multiplier pipeline, setting a precipitation threshold of > 0 mm/hr to activate a 15–20% multiplier. The parameter should be tunable — initial deployment at 15%, with a ramp to 20% if trip volume holds.

**Decision owner:** Marketplace Pricing team (sub-team: Airport Verticals or Dynamic Pricing). If no dedicated airport pricing team exists, this falls to the Pricing team that owns surge multiplier parameters for high-demand locations.

**Scale criteria:** After validating at LGA, evaluate applicability to JFK (higher volume, roughly 2× LGA), Newark, and other major FHVHV markets with NOAA co-location. Each location requires its own experiment because demand elasticity and competitive structure differ by airport.

**If the hypothesis is rejected:** Do not implement weather-specific pricing at LGA based on this dataset. Instead, investigate whether trip composition (not pricing) is driving the observed margin signal — specifically whether rain disproportionately eliminates long, low-margin trips rather than increasing fares on existing trips. This distinction requires trip-level analysis that the hourly aggregation cannot resolve.

---

---

## Phase 4 Dollar Figures — Updated 2026-02-24

> Computed by `src/models/opportunity_sizing.py`. Full methodology and sensitivity in `outputs/tables/opportunity_sizing_scenarios.csv` and `outputs/tables/sensitivity_analysis.csv`.

### Coefficient Update

The Phase 2 frame anticipated the original cold-only M1 coefficient of $0.0847/mile. Phase 3 reran M1 with all-season data and HC3-robust standard errors, producing **$0.073/mile** (95% CI: $0.0494–$0.0967, p < 0.001, N = 5,662). Per the Phase 2 update rule ("if the new coefficient differs materially, Phase 4 updates all scenarios accordingly"), all scenarios below use $0.073/mile.

### Volume Note

Light rain hours at LGA have **lower** trip volume (528.6 trips/hr) than no-rain hours (555.6 trips/hr). Rain slightly suppresses trip count — likely driver supply constraints. The High scenario is elevated via annualization (1.70×), not via a volume premium. This is disclosed explicitly in the outputs.

### Scenario Results

| Scenario | Annual light rain hours | Trips/hr | Trip miles | Coef ($/mile) | **Annual opportunity (USD)** |
|---|---|---|---|---|---|
| **Low** | 499.8 (357 × 1.40) | 555.6 (baseline) | 11.337 | $0.0494 (CI lower) | **$155,533** |
| **Mid** | 553.4 (357 × 1.55) | 555.6 (baseline) | 11.337 | $0.073 (point est.) | **$254,461** |
| **High** | 606.9 (357 × 1.70) | 528.6 (rain-period) | 11.384 | $0.073 (point est.) | **$266,589** |

**Summary:** Weather-responsive pricing at LGA could add **$156K–$267K in annual gross margin** during light rain events (mid estimate: **$254K**), subject to elasticity validation via A/B experiment.

### Sensitivity (Mid anchor, ±10% volume, ±1 SE coefficient)

Full sensitivity table at `outputs/tables/sensitivity_analysis.csv`. Range across all combinations: **$191K–$327K**.

Even under pessimistic conditions (−10% volume, −1 SE on coefficient), the opportunity remains above **$191K** annually.

### Interpretation

The $0.073/mile coefficient is statistically significant and present in all-season data, not just cold months — strengthening the case for weather-responsive pricing year-round at LGA. The dollar estimate assumes the full coefficient represents unrealized opportunity; the A/B experiment (Phase 5) is the only mechanism to determine what share current surge pricing already captures. Until that experiment runs, treat these figures as the sizing of the prize, not a confirmed revenue projection.
