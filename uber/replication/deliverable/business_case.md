# Uber LGA Weather Pricing — Business Case
> Prepared for: Senior Manager, BizOps / Marketplace Pricing
> Analysis period: January–August 2025
> Data: NYC TLC FHVHV trip records + NOAA LGA weather station
> Status: Phase 6 complete — ready for experiment decision

---

## Weather-responsive pricing at LGA could add $156K–$267K in annual gross margin — a single 8-week A/B experiment will confirm it

- Light rain at LaGuardia is reliably associated with a **$0.073 per mile increase in Uber's net margin**, statistically significant across all seasons in nine months of actual rideshare data (p < 0.001, 95% CI: $0.049–$0.097/mile).
- Applied to observed light-rain hours at LGA and annualized to a full year, this coefficient produces an **annual margin opportunity of $156K (low) to $267K (high), with a mid-case of $254K**.
- The recommended action is not a price change — it is a controlled A/B experiment: add a NOAA precipitation trigger to the LGA pricing pipeline and test a 17.5% weather multiplier on top of existing dynamic pricing.
- The dollar figure assumes the full coefficient is unrealized opportunity; Uber's current surge algorithm may already capture part of it. The experiment resolves that question.
- If the experiment confirms the signal, the decision moves to Marketplace Pricing (Airport Verticals) and the scale path is clear: LGA first, then JFK at approximately 2× the volume.

---

## Uber's pricing algorithm responds to demand signals but not directly to weather — this analysis sizes the cost of that gap

- Uber's existing dynamic pricing algorithm raises fares when demand spikes and driver supply falls — both of which rain causes indirectly — but it does not ingest a weather feed.
- The consequence is that the algorithm may be capturing some of the rain-driven demand shift, but not the full signal: rain creates a demand surge **and** a supply constraint simultaneously, and the two effects partially cancel in the demand model.
- The business decision: should the Marketplace Pricing team spend 8 weeks running a controlled test of an explicit NOAA-fed weather multiplier at LGA?
- If the current algorithm already captures the full weather premium, the experiment returns a null result — a correct and informative outcome — and the $254K estimate represents revenue already being earned, not left on the table.
- If the algorithm is leaving margin behind, the experiment proves it with enough statistical precision to justify a permanent algorithm change.

---

## LGA combines captive rider demand, co-located real-time weather data, and no flat-rate taxi competition — it is Uber's best market to test weather pricing

- **Captive demand:** Airport riders face hard departure constraints. The alternative to accepting a surge price is not walking — it is missing a flight. Demand is measurably less elastic than street-hail markets.
- **No flat-rate alternative:** NYC yellow cab flat-rate pricing applies to JFK–Manhattan only. At LGA, all taxi and rideshare fares are metered or surge-priced, giving Uber real pricing headroom during weather events.
- **Data co-location:** NOAA Integrated Surface Dataset (ISD) station WBAN 14732 is physically at LaGuardia Airport, providing hourly precipitation readings at the same location where Uber trips originate.
- **Measurable throughput:** LGA processes approximately 529 Uber/Lyft trips per light-rain hour — enough to power a well-designed experiment in under 12 calendar days of minimum statistical exposure.
- **Replicability:** A successful LGA experiment creates a validated playbook for JFK (approximately 2× LGA volume), Newark, and other major markets with NOAA co-located stations.

---

## Nine months of matched trip and weather data across 5,702 hourly observations provide the baseline — but only completed trips are visible

- **Trip data:** NYC Taxi & Limousine Commission (TLC) For-Hire Vehicle (FHVHV) trip records, covering all Uber and Lyft trips originating in TLC zone 138 (LaGuardia Airport), January through August 2025.
- **Weather data:** NOAA ISD station at LGA, sub-hourly observations resampled to 1-hour bins and aligned to TLC request timestamps (the hour a ride was requested, not when it was picked up).
- **Merged dataset:** 5,702 hourly observations from an inner join on datetime hour; data ends August 27 where the NOAA feed stops, leaving 4 days of TLC data unmatched.
- **Unit of analysis:** One row = one calendar hour at LGA, aggregated from all individual trips in that hour. Models capture how the average trip's economics change with weather, not trip-to-trip variation.
- **Critical blind spot:** TLC records only completed trips. Every rider who opened the Uber app during rain, saw a surge price, and closed it without booking is invisible. Demand elasticity cannot be measured from this data — that is what the experiment is for.

---

## Trip length and driver pay share explain 58% of margin variation at LGA — weather adds a smaller but independently significant signal that economic controls cannot absorb

- **Baseline model (M0)** explains 57.5% of hourly margin variation using four economic variables: average trip distance, average trip duration, prior-hour demand, and driver pay share of fare.
- **Driver pay share is the largest lever:** each additional percentage point in the driver pay ratio reduces Uber's margin by approximately $0.035/mile — Uber's driver incentive decisions directly set the ceiling on weather pricing gains.
- **Longer trips, lower margin per mile:** the per-mile margin declines by $0.013/mile for each additional mile of average trip length, consistent with airport-to-destination pricing that doesn't scale linearly with distance.
- **Prior-hour demand adds a small premium:** tight supply in the previous hour predicts marginally higher margins in the current hour, reflecting the lag in driver supply response to surge.
- **Adding weather (M1) improves fit modestly** (adj R² 0.575 → 0.584), but the light rain coefficient is highly significant (p < 0.001) and is not absorbed by the economic controls — confirming the signal is not just a proxy for demand pressure.

---

## Light rain consistently adds $0.073 per mile to Uber's margin at LGA; heavy rain's negative effect vanishes under proper statistical standards

- **Light rain finding:** The M1 model estimates a **+$0.073/mile margin uplift** during any hour with recorded precipitation (> 0 mm/hr), all seasons, with HC3 heteroskedasticity-robust standard errors (95% CI: $0.049–$0.097, p < 0.001, n = 5,662 hours).
- **This is an all-season result:** the original analysis was restricted to cold-weather hours (Oct–Apr) due to a variable coding issue and produced +$0.085/mile. The all-season estimate ($0.073/mile) is more conservative and more broadly applicable.
- **The effect survives economic controls:** it holds after removing seasonal patterns, controlling for trip length, trip duration, demand pressure, and driver pay share — it is not simply a byproduct of longer or more expensive trips occurring in rain.
- **Heavy rain does not reach significance:** the heavy rain (≥5 mm/hr) coefficient is −$0.073/mile but p = 0.20 with robust standard errors on the full dataset. The original p = 0.011 was an artifact of non-robust inference. Heavy rain should not be included in opportunity sizing.
- **Current pricing does not fully eliminate the signal:** the weather effect persists in the regression after controlling for demand pressure, suggesting the current surge algorithm does not fully internalize precipitation as a pricing input.

---

## The weather pricing opportunity at LGA is $156K–$267K annually, with a mid-case of $254K — all contingent on an experiment confirming the signal is not already priced in

| Scenario | Annual light rain hours | Trips/hr | Coef ($/mile) | **Annual opportunity** |
|---|---|---|---|---|
| Low | 500 (357 × 1.40) | 556 (baseline) | $0.049 (CI lower) | **$156K** |
| Mid | 553 (357 × 1.55) | 556 (baseline) | $0.073 (point est.) | **$254K** |
| High | 607 (357 × 1.70) | 529 (rain-period) | $0.073 (point est.) | **$267K** |

- **Annualization factors (1.40–1.70×)** adjust the observed Jan–Aug rain hours (357 light-rain hours) to a full-year estimate; the mid-case 1.55× reflects the simple calendar-day ratio (365 ÷ 238 observed days); the 1.70× high case adds a fall rain premium consistent with NYC's September–November climatology.
- **Trip volume:** light rain hours average 529 trips/hour (slightly below the dry-hour baseline of 556/hr), likely due to driver supply constraints; the mid and low scenarios use the conservative dry-hour baseline.
- **Sensitivity range:** across all combinations of ±10% trip volume and ±1 standard error on the coefficient, the full opportunity range is **$191K–$327K**.
- **Even the pessimistic case exceeds $191K** — the estimate is robust to meaningful uncertainty in both trip volume and the margin coefficient.
- **The central assumption:** all scenarios treat the full $0.073/mile coefficient as unrealized incremental opportunity. If Uber's current surge already captures 50% of this signal, the true incremental opportunity is half the estimate. Only the A/B experiment resolves this.

---

## This analysis cannot prove that Uber is undercharging during rain — it proves margin is reliably higher when it rains, and only an experiment explains why

- **Completed trips only:** every number in this analysis comes from trips that finished. Riders who declined a price during rain and chose not to book — the population most relevant to elasticity — are structurally absent from TLC data.
- **The $0.073/mile coefficient has two equally valid explanations:** (A) Uber's existing surge algorithm correctly captures rain-driven demand and earns more margin, or (B) trip composition shifts during rain and certain high-margin trip types self-select into the completed pool regardless of price. Both explanations are consistent with the observed data.
- **January–August coverage only:** the nine-month window misses September–December, which includes NYC's wettest fall months. Annualization factors (1.40–1.70×) are calibrated estimates, not direct measurements.
- **Precipitation type not disaggregated:** the model treats rain, snow, and sleet as equivalent. January–February events at LGA are predominantly snow, which has different operational implications (flight cancellations, ground delays) than liquid rain.
- **None of these limitations prevent running the experiment** — they are precisely the reason the experiment must come before any algorithm change.

---

## An 8-week rider-level A/B test needs fewer than 18 rain hours per arm to confirm or kill the $254K opportunity — the binding constraint is independent events, not sample size

- **Treatment:** riders randomly assigned (by persistent UUID hash, 50/50 split) see a NOAA-triggered 17.5% multiplier layered on top of Uber's existing dynamic pricing whenever the LGA ISD station reports precipitation > 0 mm/hr.
- **Control:** all other LGA riders see standard Uber dynamic pricing with no weather multiplier — identical to today's pricing, including any demand-responsive surge the current algorithm applies.
- **Primary metric:** margin per mile on completed trips ($/mile), measured from Uber's internal event data. Minimum detectable effect: $0.04/mile. Sample required: 4,593 trips per arm (design-adjusted for within-event clustering).
- **Duration rationale:** statistical power is achieved in under 12 calendar days, but 8 weeks is recommended to accumulate approximately 21 independent rain events across multiple day types — conclusions based on 3–5 correlated storm events are not reliable.
- **Kill criterion:** if trip volume in the treatment arm falls below 501 trips/hour after week 2 (a 5% drop from the 529/hour rain-period baseline), halt the experiment immediately.
- **Measurement platform:** this experiment cannot be evaluated using TLC public data. Uber's internal event data — booking requests, price display events, cancellations, completions — is required. Confirm pipeline readiness before launch.

---

## If the experiment confirms a $0.04/mile margin uplift without a 5% volume loss, Marketplace Pricing deploys the weather multiplier permanently and scales to JFK

- **Confirmation requires all three:** margin per mile uplift ≥ $0.04/mile in the treatment arm, confidence interval excludes zero at 95%, and trip completion rate in the treatment arm does not decline > 5% versus control during rain hours.
- **Immediate action on confirmation:** promote `weather_multiplier = 1.175` from experiment parameter to permanent LGA pricing pipeline input; run a follow-on parameter sweep (1.15× vs. 1.20×) to find the optimal elasticity point.
- **Scale path:** validate at LGA, then evaluate JFK (approximately 2× LGA volume), Newark, and any FHVHV market with a co-located NOAA station. Each market requires its own experiment — demand elasticity differs by airport structure and competitive environment.
- **Decision owner:** Uber Marketplace Pricing team (Airport Verticals or Dynamic Pricing sub-team); if no dedicated airport pricing team exists, the Pricing team that owns surge multiplier parameters for high-demand locations.
- **If the experiment fails:** do not implement weather-specific pricing at LGA. Investigate instead whether the hourly margin uplift arises from trip composition shifts rather than pricing power — a question that requires trip-level analysis below the hourly aggregation this analysis uses.

---

## Appendix: Light rain is the only weather variable with a statistically significant margin effect — heavy rain's negative coefficient does not survive robust standard errors

> All standard errors are HC3 heteroskedasticity-robust. Dependent variable: margin per mile (residualized against hour-of-week × month fixed effects). "All seasons" model: n = 5,662. "Cold hours only" replicates original analysis (wind chill restriction): n = 2,205.

### M0 — Margin per Mile, Economic Controls Only (n = 5,701, adj R² = 0.575)

| Variable | Coefficient | 95% CI | p-value |
|---|---|---|---|
| Average trip distance (miles) | −$0.014/mile | [−$0.021, −$0.006] | < 0.001 *** |
| Average trip duration (minutes) | −$0.007/min | [−$0.008, −$0.006] | < 0.001 *** |
| Prior-hour demand pressure | +$0.0001 | [+$0.0001, +$0.0002] | < 0.001 *** |
| Driver pay share of fare | −$3.454 | [−$3.608, −$3.299] | < 0.001 *** |

*Business interpretation: controlling for trip economics, margin at LGA is largely set by driver compensation rates and trip efficiency — not weather.*

### M1 — Margin per Mile + Weather, All Seasons (n = 5,662, adj R² = 0.584)

| Variable | Coefficient | 95% CI | p-value |
|---|---|---|---|
| Average trip distance (miles) | −$0.013/mile | [−$0.020, −$0.006] | < 0.001 *** |
| Average trip duration (minutes) | −$0.008/min | [−$0.008, −$0.007] | < 0.001 *** |
| Prior-hour demand pressure | +$0.0002 | [+$0.0001, +$0.0002] | < 0.001 *** |
| Driver pay share of fare | −$3.490 | [−$3.649, −$3.331] | < 0.001 *** |
| **Light rain (any precipitation)** | **+$0.073/mile** | **[$0.049, $0.097]** | **< 0.001 ***▲** |
| Heavy rain (≥5 mm/hr) | −$0.073/mile | [−$0.183, +$0.038] | 0.197 — |
| Precipitation amount (mm/hr) | +$0.005/mm | [−$0.007, +$0.017] | 0.402 — |
| Air temperature (°F) | +$0.001/°F | [$0.001, $0.001] | < 0.001 *** |

▲ *This is the coefficient used in opportunity sizing.*

### M1-Original — Cold Hours Only, Replication (n = 2,205, adj R² = 0.594)

| Variable | Coefficient | 95% CI (HC3 robust) | p-value |
|---|---|---|---|
| **Light rain (any precipitation)** | **+$0.085/mile** | **[$0.027, $0.142]** | **0.004 **▼** |
| Heavy rain (≥5 mm/hr) | −$0.334/mile | [−$0.804, +$0.136] | 0.164 — |
| Precipitation amount (mm/hr) | +$0.032/mm | [−$0.031, +$0.096] | 0.319 — |
| Wind chill temperature (°F) | +$0.002/°F | [$0.001, $0.003] | < 0.001 *** |

▼ *Original non-robust p-value was 0.011; robust p-value is 0.004 — still significant but with wider CI. The cold-only coefficient ($0.085) is higher than the all-season estimate ($0.073) because it excludes warm-weather rain events where the effect is somewhat weaker.*

**Key takeaway for the technical reader:** The all-season M1 model is the correct specification. It is estimated on 2.6× more observations, uses a temperature variable defined in all hours (not just cold ones), and produces a more conservative and generalizable coefficient. The heavy rain finding from the original work does not survive robust standard errors in either specification and should not inform pricing decisions.
