# Experiment Design — Weather-Triggered Pricing at LGA

> Phase 5 output. Converts the Phase 4 analytical finding into an operational A/B experiment.
> Audience: Uber Pricing / Marketplace team (Airport Verticals).
> Dollar figure under test: $155K–$267K annual margin opportunity (mid: $254K).

---

## Why an Experiment, Not a Price Change

The observational analysis (Phases 3–4) used NYC TLC rideshare data, which records **only completed trips**. A rider who opened the Uber app during rain, saw a surge price, and chose not to book is **invisible in the TLC dataset**. This is not a flaw in the analysis — it is a structural property of the data source.

The consequence is that the +$0.073/mile margin uplift during light rain cannot be attributed with certainty to pricing power. It could arise from two entirely different mechanisms:

- **Mechanism A (pricing power):** Rain increases demand relative to supply, Uber's existing surge algorithm lifts prices, and riders at LGA accept higher fares because they have no flat-rate alternative. The uplift reflects revenue Uber captures above baseline through surge.
- **Mechanism B (composition shift):** Rain selectively eliminates certain trip types from the completed pool — for example, recreational short-haul trips cancel while higher-margin airport-bound trips proceed regardless of price. The uplift is a statistical artifact of who shows up in the data, not evidence that any rider paid more than they would have on a dry day.

If Mechanism A dominates and current pricing already captures the full weather signal, the incremental opportunity from adding an **explicit** weather trigger is near zero. If Mechanism B dominates, a fare increase would reduce demand without adding margin. The experiment distinguishes between these mechanisms. It cannot be done on historical data.

---

## Treatment Definition

**What is being tested:**
A NOAA precipitation-triggered fare multiplier, applied as an explicit additional input to Uber's existing dynamic pricing pipeline at LGA.

**Specific change:**
When the NOAA LGA ISD real-time feed reports precipitation > 0 mm/hr, riders randomly assigned to the **treatment bucket** see their displayed fare calculated as:

```
treatment_fare = current_dynamic_fare × weather_multiplier
weather_multiplier = 1.175  (midpoint of the 1.15–1.20 range from the hypothesis)
```

The `current_dynamic_fare` is whatever Uber's standard algorithm — including any existing demand-responsive surge — would show at that moment. The weather multiplier is applied **on top of** the current price, not in place of it. It is not surge replacing surge; it is an additional explicit weather signal layered onto the demand signal.

**Trigger:**
NOAA Integrated Surface Database (ISD) station WBAN 14732 (LaGuardia Airport). Same data source used in the observational analysis. Update frequency: hourly. Activation threshold: `precip_1h_mm_total > 0`. This matches the M1 model's "light rain" indicator exactly, ensuring the experiment tests the same weather regime that produced the observed coefficient.

**Randomization unit:**
Individual rider, using a persistent hash of the rider's UUID. Each rider is assigned once to treatment or control for the duration of the experiment. Assignment is deterministic given the rider UUID — the same rider sees consistent pricing across all rain events during the test period.

Rider-level randomization is required because it allows treatment and control riders to **coexist at LGA during the same rain event**, facing identical weather, supply conditions, and time of day. Time-based alternation (e.g., odd hours = treatment) would confound pricing with naturally different weather intensity and demand levels across hours. Rider-level assignment eliminates that confound.

---

## Control Definition

**What control riders see:**
Standard Uber dynamic pricing — the same algorithm and parameterization currently deployed at LGA, with no weather multiplier added. This is the status quo: Uber's existing demand-responsive surge, which already partially incorporates rain-driven demand signals through elevated ride requests and reduced driver supply.

**Why this is the valid counterfactual:**
The control is not "no surge." It is "today's pricing." The experiment directly answers the business question: does adding an **explicit, real-time NOAA precipitation signal** to Uber's pricing pipeline generate incremental margin above what the current algorithm already extracts from weather-driven demand shifts?

This framing is conservative and correct. If the current algorithm is already capturing the full +$0.073/mile weather effect through organic surge, the treatment and control arms will show no difference — and the experiment will correctly return a null result. The $254K annual opportunity estimate would then represent pricing Uber already captures, not an incremental gain. This is an acceptable and informative outcome.

**Measurement platform:**
The experiment **cannot** be measured using TLC public data. TLC records only completed trips and does not capture: price display events, riders who declined the shown price, or booking attempts that did not result in a trip. All experiment metrics must be drawn from **Uber's internal event data**, specifically:

- `trip_request_event`: rider opens app at LGA
- `price_display_event`: fare screen shown, price recorded
- `booking_confirmation_event`: rider accepts the shown fare
- `booking_cancellation_event`: rider cancels after price shown but before driver dispatched
- `trip_completion_event`: trip completes, fare and driver pay recorded

The margin per mile is computed from internal trip completion data. The cancellation rate and acceptance rate are computed from the price display and booking events — neither of these metrics exists in TLC data.

---

## Metrics

### Primary Metric

**Margin per mile on completed trips** ($/mile)

Defined as: `(base_passenger_fare − driver_pay) / trip_distance_miles`, computed per completed trip and averaged across the treatment or control arm during rain hours.

This matches the dependent variable in the M1 regression model and is the metric for which the $0.073/mile coefficient was estimated. It is the right metric because the business question is about Uber's net capture on each mile driven — not gross revenue, not fare, not driver pay in isolation.

### Secondary Metrics

1. **Trip completion rate during rain** — trips completed per open-app request during rain hours, by arm. The key demand elasticity indicator. A drop > 5% in the treatment arm triggers the kill criterion (see Stopping Criteria).

2. **Price screen cancellation rate** — riders who viewed the fare screen and did not book, by arm. This directly measures price sensitivity at the fare display step, which is invisible in TLC data and the primary source of demand-side elasticity information the experiment provides.

3. **Driver utilization rate** — driver-hours dispatched per rain hour at LGA, by arm. Measures whether the weather multiplier affects driver supply allocation. If treatment-arm higher fares attract more drivers to LGA (supply response), this could bias the comparison by giving treatment riders shorter wait times.

---

## Minimum Detectable Effect and Sample Size

### Parameters

| Parameter | Value | Source |
|---|---|---|
| Significance level (α) | 0.05 (two-sided) | Standard |
| Statistical power (1−β) | 0.80 | Standard |
| Minimum detectable effect (MDE) | $0.04/mile | Hypothesis confirmation threshold |
| Trip-level SD of margin per mile (σ) | $0.60/mile | Conservative estimate; LGA airport rides range ~$0.50–$2.50/mile |
| Design effect (DEFF) | 1.3 | Within-event clustering adjustment (trips within the same rain event are correlated) |

### Sample Size

Using the standard two-sample t-test formula:

```
n_naive = 2 × σ² × (z_{α/2} + z_{β})² / δ²
        = 2 × (0.60)² × (1.96 + 0.842)² / (0.04)²
        = 2 × 0.36 × 7.851 / 0.0016
        = 3,533 trips per arm
```

Adjusted for within-rain-event clustering:

```
n_adjusted = 3,533 × 1.3 = 4,593 trips per arm
Total required = 9,186 trips across both arms
```

### Rain Volume at LGA

From the baseline data (Jan–Aug 2025, n = 5,702 hourly observations):
- Light rain hours: 357 out of 5,702 total = **6.3% of calendar hours**
- Average trips per light-rain hour (all riders): 528.6 trips/hr
- Per arm (50/50 split): **264 trips per arm per rain hour**

### Duration Estimate

Rain hours needed per arm to reach sample size:
```
17.4 rain hours per arm  (= 4,593 / 264)
```

Statistical minimum calendar duration:
```
17.4 hours ÷ 0.063 = 276 calendar hours = 11.5 calendar days
```

**Recommended test duration: 8 weeks (56 calendar days)**

Statistical power alone is achieved in under 2 weeks. The 8-week recommendation is driven by three factors that sample size math does not capture:

1. **Independent rain events:** The statistical minimum (~12 days) would accumulate observations within perhaps 3–5 rain events. Inference is unreliable when estimates rest on a handful of correlated events. Eight weeks yields approximately 21 independent rain events at LGA's observed frequency — enough to average across variation in rain intensity, time-of-day, and day-of-week.

2. **Weekday/weekend coverage:** Airport pricing dynamics differ substantially between weekday business travel and weekend leisure travel. A minimum of 8 weeks ensures multiple iterations of each day-type during rain events.

3. **Implementation buffer:** Weather-based triggers require real-time NOAA feed integration into the pricing pipeline. Testing and validation of the trigger latency should occur before experiment start. The 8-week timeline assumes a clean launch; any integration issues that delay start should not compress the experiment duration.

**Expected data accumulation over 8 weeks:**

| Metric | Value |
|---|---|
| Expected rain hours | 84 hours (8 wk × 7 days × 24 hr × 6.3%) |
| Expected trips per arm | 22,200 trips |
| Statistical safety margin | 4.8× the required 4,593 trips |
| Expected independent rain events | ~21 events |

The experiment is substantially overpowered relative to the sample size requirement. The binding constraint is independent-event coverage, not raw sample size.

---

## Stopping Criteria

### Confirmation (hypothesis supported)

Proceed to full deployment if **all three** of the following hold after the full 8-week run:

1. **Margin per mile uplift ≥ $0.04/mile** in the treatment arm relative to control, during rain hours.
2. **Treatment-arm confidence interval does not cross zero** at the 95% level (two-sided).
3. **Trip completion rate in treatment arm does not decline by more than 5%** relative to control during rain hours.

If confirmed, the recommended action is to promote `weather_multiplier = 1.175` from experiment parameter to permanent pricing pipeline input for LGA, with a tuning window to test 1.15 vs. 1.20 at the follow-on stage.

### Kill (hypothesis rejected)

Stop and do not deploy if **either** of the following occurs:

1. **Trip volume in the treatment arm declines by more than 5%** relative to control at any interim check after week 2 (early harm stop). Operationally: if the treatment arm's trips-per-rain-hour falls below 501 (528.6 × 0.95 = 502.2 → threshold 501) relative to the control arm, halt.

2. **No margin uplift after the full 8-week run**: treatment margin per mile < $0.02/mile above control (well below the $0.04 MDE) AND confidence interval does not overlap $0.04.

### Inconclusive

Treat as inconclusive — extend by 4 weeks — if:
- Point estimate is in range ($0.02–$0.05) but the confidence interval crosses zero at the 95% level after 8 weeks.
- Proceed with 12-week run before declaring a result.

---

## Threats to Experiment Validity

### Threat 1: Control Group Contamination from Existing Surge

Uber's standard dynamic algorithm already responds to rain indirectly — rain increases ride requests and reduces driver supply, which its surge model detects. During rain events, the control group's price may already be elevated above dry-day baseline by the standard algorithm. This means:

- The treatment effect is measured **relative to a control that is already partially weather-adjusted**, not relative to flat pricing.
- The experiment will underestimate the gross opportunity from weather-responsive pricing and correctly estimate the **incremental** opportunity from making weather an explicit input.
- This is a feature, not a bug — the incremental estimate is the right number for the business question. But it must be documented clearly: experiment results will not match the Phase 4 sizing, which assumed zero prior capture.

**Mitigation:** Log the control arm's average surge multiplier during rain hours. If control-arm surge is substantially above dry-day baseline, estimate what fraction of the Phase 4 opportunity is already being captured.

### Threat 2: SUTVA Violation — Treatment Spills Over to Control via Supply

If treatment-arm riders cancel because of higher prices, drivers who would have served those riders are now available to control-arm riders. This increases supply availability for the control group, potentially improving their experience (shorter waits) and deflating the observed margin difference between arms. The Standard Unit Treatment Value Assumption (SUTVA) requires that one unit's treatment not affect another's outcome — a requirement violated in a two-sided marketplace.

**Mitigation:** Monitor driver wait time and driver utilization separately by arm. If driver wait time in the control arm is materially shorter than in the treatment arm, SUTVA is likely violated. This would cause the experiment to **underestimate** the treatment effect. The true effect could be larger than the measured treatment-control difference.

### Threat 3: Novelty Effect in the Treatment Arm

Riders who have never seen an explicit weather label on their Uber fare display may respond differently in the first few weeks of the experiment than they will in steady state. If weather-labeled pricing triggers cancellations during the test but riders habituate over time, the short-term experiment result will overstate the long-run demand reduction. Conversely, if the weather label reduces rider cancellations (by providing a transparent explanation for the elevated fare), the short-run result will understate the steady-state effect.

**Mitigation:** Segment the cancellation rate by week within the experiment. If cancellation rates are declining week-over-week in the treatment arm, extend the experiment to 12 weeks to observe steady-state behavior before drawing conclusions.

---

## Recommended Action If Hypothesis Confirmed

**Decision owner:** Uber Marketplace Pricing team (Airport Verticals or Dynamic Pricing sub-team).

**Immediate next step:** Promote `weather_multiplier = 1.175` to permanent LGA pricing pipeline. Instrument a parameter sweep (1.15 vs. 1.20) as the follow-on experiment at LGA before considering rollout to JFK.

**Scale path:** After validating at LGA, evaluate applicability to JFK (approximately 2× LGA volume), Newark, and other major FHVHV markets where NOAA co-located weather data is available. Each market requires its own experiment — demand elasticity and competitive structure differ by airport.

**If rejected:** Do not implement weather-specific pricing at LGA. Investigate whether the observed hourly margin uplift arises from trip composition changes (long-haul business trips completing during rain while recreational trips cancel) rather than pricing effects. This requires trip-level analysis below the hourly aggregation used in the baseline model.

---

## Summary Table

| Element | Value |
|---|---|
| Treatment | NOAA-triggered weather multiplier (1.175×) layered on existing LGA dynamic pricing |
| Control | Uber's current standard dynamic pricing (status quo; no weather multiplier) |
| Trigger | NOAA LGA ISD station: precip > 0 mm/hr |
| Randomization unit | Individual rider (persistent UUID hash; 50/50 split) |
| Primary metric | Margin per mile on completed trips ($/mile) |
| Secondary metrics | Trip completion rate; price-screen cancellation rate; driver utilization |
| MDE | $0.04/mile |
| Required sample (per arm) | 4,593 trips (design-adjusted) |
| Required rain hours (per arm) | 17.4 hours |
| Statistical minimum duration | 12 calendar days |
| Recommended duration | 8 weeks |
| Confirmation threshold | Margin uplift ≥ $0.04/mile AND volume drop < 5% AND CI excludes 0 |
| Kill threshold | Volume drop > 5% after 2 weeks OR no uplift after 8 weeks |
| Measurement platform | Uber internal event data (NOT TLC public data) |
| Decision owner | Marketplace Pricing — Airport Verticals |
| Dollar figure under test | $155K–$267K annually (mid: $254K) |
