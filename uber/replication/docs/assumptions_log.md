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
