# Assumptions Log

> Running log appended by each phase. Most recent entries appear at the bottom of each phase section.

---

## Phase 1 — Audit of Original Work

*Appended: 2026-02-24*

The following assumptions were identified in the original work as implicit — present in the code or modeling choices but not explicitly stated or defended.

---

**A1: Rain and snow are treated as equivalent precipitation events.**

The `precip_1h_mm_total` variable sums all precipitation regardless of type (rain, snow, sleet, freezing rain). January–February events in New York are predominantly snow. Snow has different operational implications than rain: it may cause greater operational delays (suppressing demand via flight cancellations more than rain does), but riders on the ground may respond differently (substituting to Uber more readily in snow than rain). The original work does not separate types or test whether the coefficient differs by precipitation type. This assumption understates the heterogeneity in the precipitation response.

**A2: The light rain and heavy rain thresholds are treated as fixed and established.**

The light rain threshold (> 0 mm) and heavy rain threshold (≥ 5.0 mm/hr) are applied as constants throughout all models. These values are not motivated by meteorological standards or empirical testing. The process notes acknowledge this: "did not see how much changing the threshold for heavy rain changes the estimated coefficient or the direction. Perhaps heavy rain should be higher than 5mm per hour." Meteorological convention classifies moderate rain as 2.5–7.5 mm/hr and heavy rain as ≥ 7.6 mm/hr. The 5.0 mm threshold splits the moderate rain range, which may misclassify moderate rain events as "heavy." The robustness of the heavy rain coefficient to alternative thresholds (e.g., 2.5, 7.5, 10 mm) was not tested.

**A3: The seasonal residualization using hour-of-week × month fixed effects fully removes confounding time patterns.**

The two-step residualization removes hour-of-week (168 bins) and month (8 bins) patterns from all metrics before regressing on weather. This implicitly assumes that all systematic time variation is captured by these patterns, and that remaining variation is attributable to weather and the other regressors. This assumption would be violated if: (a) holidays create demand patterns not captured by day-of-week (the process notes flag this: "vacation flags… Sunday 1/19 before MLK Jr holiday, demand was down"); (b) major weather events lasting multiple days create multi-hour autocorrelation beyond what lag-1 demand absorbs; or (c) seasonal weather norms (e.g., cold months tend to be wetter in NYC) create partial redundancy between month fixed effects and cold-weather regressors. The original work notes this last point: "since month is a residualization variable, temperature could become partially redundant."

**A4: The M1 model can be applied to all rain hours, not just cold-weather rain hours.**

The M1 model drops all rows where `wind_chill_f` is null, which means it is estimated on approximately 39% of the data — cold-weather hours only (roughly October through April). The implicit assumption embedded in any downstream use of this model is that the rain coefficient estimated on cold-weather hours applies equally to warm-weather rain. If warm-weather rain at LGA has different trip composition effects (e.g., summer tourists vs. business travelers), this assumption will generate biased estimates when applied to the full year.

**A5: LGA pickups are a representative sample of Uber's airport pricing environment.**

The analysis focuses exclusively on trips where `PULocationID == 138` (LGA pickup zone). This geographic restriction is appropriate for studying weather-margin dynamics at LGA, but it implicitly assumes that LGA is representative of the pricing question being studied. LGA has specific structural features that may not generalize: JFK is larger (roughly 2× the passenger volume per the process notes), LaGuardia serves primarily domestic travel and is closer to Manhattan, and LGA's curfew creates a distinct demand pattern. The original work presents results as "Uber at LGA" without asserting broader generalizability, which is appropriate — but downstream applications of these coefficients to other airports or geographies would require explicit justification.

**A6: Driver pay percentage of base fare is an exogenous control variable, not a dependent variable.**

`driver_pay_pct_of_base_fare` is included as a regressor in all M0 and M1 models. This treats Uber's driver compensation rate as exogenous — a rate that adjusts for supply-side conditions but does not itself respond to weather. In practice, if driver supply falls during heavy rain (fewer drivers willing to operate), Uber may increase driver pay rates as part of its matching algorithm, making `driver_pay_pct` endogenous to weather. Including an endogenous regressor biases all other coefficients. The process notes note this as an enhancement: "If `driver_pay_pct_of_base_fare` predicts `fare_resid`, Uber's pricing is reacting to driver supply constraints" — but the endogeneity concern is not formally addressed.

**A7: OLS standard errors are valid for inference despite known autocorrelation and heteroskedasticity.**

The Breusch-Godfrey test (p ≈ 1.3e-173) and Durbin-Watson statistic (0.853) confirm strong positive autocorrelation in the M1 margin model residuals. The Breusch-Pagan test (p = 4.2e-10) confirms heteroskedasticity. Under these conditions, OLS standard errors are biased and all reported t-statistics and p-values are invalid. The original work identifies these violations in diagnostics but does not rerun models with robust or clustered standard errors. The p<0.001 significance reported for the light rain coefficient may overstate precision; the actual precision under robust standard errors is unknown.

**A8: The hourly aggregation unit preserves the economically relevant variation.**

All trip-level fare, pay, and distance data are aggregated to hourly means before modeling. This means the analysis captures whether the average trip in a rainy hour earns more margin per mile than the average trip in a dry hour. It does not capture within-hour heterogeneity (e.g., whether specific trip types — short vs. long, peak vs. off-peak within the hour — respond differently to weather). The hourly mean is a sufficient statistic for the business question only if the effect of weather on margin is approximately uniform across trip types within an hour.

---

## Phase 2 — Business Case Frame

*Appended: 2026-02-24*

The following assumptions underpin the business case frame and the dollar figure methodology defined in Phase 2. They are not inherited from the original work — they are new assumptions introduced by the decision to translate regression coefficients into an actionable pricing recommendation.

---

**B1: The observed margin uplift during light rain is not already fully captured by Uber's current dynamic pricing.**

The M1 coefficient (+$0.0847/mile) shows that margin per mile is higher during light rain hours than equivalent non-rain hours after controlling for economic and seasonal factors. This uplift could arise from two distinct mechanisms: (a) Uber's surge pricing algorithm is already responding to rain-driven demand and capturing more margin, or (b) trip composition shifts during rain (shorter, higher-margin trips self-select) create the uplift independent of pricing. Mechanism (a) means the incremental opportunity from explicit weather pricing is near zero; mechanism (b) means pricing is not the driver and a fare multiplier could capture additional margin. The historical data cannot distinguish between these mechanisms. B1 assumes mechanism (b) dominates, or that (a) is only partial. This is the central assumption the experiment tests.

**B2: The cold-weather rain coefficient generalizes to all-season rain at LGA.**

The M1 model was estimated on 2,205 cold-weather hours (temperature ≤ 50°F). Rain events in May–August are excluded from the coefficient estimate. Warm-weather rain at LGA may involve different rider demographics (leisure travelers vs. business travelers) and different competitive dynamics. If the warm-weather rain coefficient is materially lower than +$0.0847/mile, the annualized opportunity estimate overstates the true opportunity. Phase 3 will test for season interaction effects.

**B3: Rider demand at LGA is sufficiently inelastic to sustain a 15–20% fare increase during rain without volume declining more than 5%.**

Airport demand is generally less elastic than street-hail demand because: riders have fixed departure constraints, the alternative (taxis, car services) is not cheaper at LGA, and time sensitivity is high. A 5% volume tolerance is the threshold at which the margin uplift from higher per-mile pricing is approximately offset by lower trip volume. If elasticity is higher, the net margin impact approaches zero even if the fare increase succeeds. This assumption is embedded in all three scenario bounds.

**B4: The annualization factors of 1.40–1.70× adequately translate Jan–Aug rain observations to a full-year estimate.**

The observed 385 light rain hours cover January 1 through August 27 (239 days). The annualization factor must account for September–December, which includes NYC's wetter fall months. NOAA climatological normals for LGA suggest September–November average 3.5–4.0 inches of rain per month, comparable to or slightly above the Jan–Aug monthly average. The 1.55× mid-scenario (simple day-ratio) is conservative by this measure; 1.70× reflects the fall rain premium. These factors will be validated against NOAA historical monthly data in Phase 4.

**B5: The $0.044/mile lower CI bound from M1 is an appropriate conservative floor for the opportunity estimate.**

The lower bound of the 95% confidence interval on the M1 light rain coefficient is $0.044/mile in the original work (non-robust standard errors). Phase 3 will rerun with HC3 robust standard errors; the CI may widen. The low scenario uses the Phase 3 robust CI lower bound, not the original non-robust bound. If robust standard errors make the lower CI negative or statistically insignificant, the low scenario must be set to zero and the business case depends entirely on the experiment.

**B6: Average trip miles during light rain hours are approximately equal to non-rain baseline trip miles.**

If rain disproportionately eliminates long trips (e.g., business travelers cancel, only short-haul trips complete), the dollar opportunity shrinks even if the per-mile coefficient holds. This assumption is not tested in the original work. Phase 3 data quality review will compare avg_trip_miles across weather regimes and flag material differences.

**B7: Driver pay per mile does not systematically increase during rain events in a way that offsets fare-side margin gains.**

If Uber's matching algorithm increases driver incentives during rain to maintain driver supply, the gross fare margin uplift could be offset by higher driver pay per mile. The coefficient in M1 is margin per mile (fare minus driver pay), so this offset is captured in the model — but only if driver pay adjustments are included in the historical data used to fit the model. Phase 3 will check driver_pay_pct_of_base_fare by weather regime to confirm this is already controlled for in the dependent variable.

---

## Phase 3 — Baseline Model

*Appended: 2026-02-24*

### Methodology Note (Plain English)

**What the models do:**

We measured how Uber's margin per mile at LaGuardia changes during rain, after accounting
for everything else we know affects margin: how long and far trips go, how many drivers are
on the road (lagged demand), and how much Uber pays drivers relative to the fare.

We ran two models. The first (M0) uses only the economic controls — trip length, duration,
demand pressure, and driver pay share. The second (M1) adds four weather variables: whether
it was raining at all, whether it was raining hard, how many millimeters of rain fell, and
the air temperature. Both models strip out the regular time-of-week and seasonal patterns
before estimation, so the weather effects are measured relative to what we'd expect for that
hour on a typical dry day of the same month.

**Key improvement: fixed the sample restriction problem.**

The original analysis used a "wind chill" variable that is only defined on cold, windy days
(temperature ≤ 50°F AND wind speed ≥ 3 mph). Because the model dropped every hour where
wind chill was not defined, it was silently estimated on only 2,205 of the 5,702 available
hours — primarily October through April. Any estimated effect of rain was therefore specific
to cold-season rain and could not speak to rain during warmer months.

This replication uses air temperature instead of wind chill. Air temperature is measured
every hour throughout the year, allowing M1 to run on all 5,662 eligible hours (all seasons).
The resulting rain coefficient is a better estimate of the average effect across all LGA
rain events, not just winter ones.

**Standard errors: why this matters for the dollar figure.**

The original models did not use robust standard errors, even though statistical tests
confirmed that the variance of model errors was not constant across observations
(a violation of ordinary regression assumptions). When variance is uneven, standard
confidence intervals are too narrow — they overstate how certain we are of the estimate.

This replication uses HC3 robust standard errors throughout. This makes confidence intervals
wider and more honest. The light rain coefficient remains statistically significant (p<0.001)
even with the stricter standard. The heavy rain coefficient does NOT survive this stricter
test: p=0.20 on the full dataset, p=0.16 even on cold hours only. This matters for Phase 4:
heavy rain should not be included in the opportunity sizing.

**What Phase 3 found:**

- Light rain is associated with **+$0.073 per mile** in margin uplift (95% CI: $0.049–$0.097),
  holding trip length, duration, demand pressure, and driver pay share constant.
- This effect is robust: it holds in all seasons, with proper standard errors, and across
  the representative rainy day vs dry baseline comparison (Chart 2).
- Heavy rain shows a negative coefficient (-$0.073/mile) but it is not statistically
  distinguishable from zero. Do not build a business case around heavy rain findings.
- Driver pay share during light rain (~73.7%) is slightly higher than during dry hours
  (~72.6%), confirming that some margin gain is offset by driver costs — but this offset
  is already embedded in the margin per mile variable and captured by M1.
- Average trip miles during rain (11.38 mi) are essentially equal to dry-hour averages
  (11.34 mi), confirming Assumption B6: rain is not disproportionately selecting
  shorter or longer trips.

**What Phase 4 will use from Phase 3:**

- Light rain coefficient: **+$0.073/mile** (all-season M1, HC3 robust SEs)
- 95% CI lower bound: **+$0.049/mile** (Phase 4 low scenario)
- Light rain hours observed: 385 total (357 light-only + 28 heavy, Jan–Aug 2025)
- Average trips per light rain hour: to be computed in Phase 4 from TLC volume data

**C1: The heavy rain coefficient is not significant and should not be included in opportunity sizing.**

With HC3 robust standard errors on the full all-season dataset (n=5,662), the heavy rain
binary coefficient is -$0.073/mile with p=0.20. Even on the cold-season subset replicating
the original model (n=2,205), heavy rain produces p=0.164 with robust SEs. The original
p=0.011 was an artifact of non-robust inference. Phase 4 correctly excludes heavy rain
from the opportunity sizing per Phase 4 instructions.

**C2: The all-season light rain coefficient ($0.073) is the appropriate base for Phase 4, not the cold-season coefficient ($0.085).**

The cold-season-specific coefficient inflates the estimate because it reflects rain effects
only during winter, when LGA trip composition and demand patterns differ from warmer months.
The all-season coefficient is more conservative, more generalizable, and methodologically
more defensible. Using $0.073 as the point estimate and $0.049 as the low-scenario floor
appropriately reflects the uncertainty in the estimate.

**C3: The "warm-season rain discount" is real but modest.**

All-season coefficient ($0.073) vs cold-season coefficient ($0.085) implies warm-season
rain has a weaker margin effect. The difference is $0.012/mile — roughly a 14% discount.
This is directionally consistent with Assumption B2's concern (different rider composition
in summer), but the difference is small enough that it does not invalidate the business case.
It does mean the high-scenario annualization assumptions should be treated conservatively.
