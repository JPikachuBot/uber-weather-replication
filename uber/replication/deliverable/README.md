# Deliverable — Uber LGA Weather Pricing Business Case

## What This Document Answers

Uber charges surge prices when demand spikes — but its algorithm responds to demand signals, not directly to weather. This analysis asks: during light rain at LaGuardia Airport, does Uber leave measurable margin on the table by not incorporating an explicit precipitation signal into its pricing pipeline? Using nine months of actual NYC TLC rideshare trip data merged with hourly NOAA weather readings at LGA, the analysis finds that light rain is reliably associated with a $0.073/mile increase in Uber's net margin per trip, producing an estimated annual opportunity of $156K–$267K (mid-case: $254K). Because the data covers only completed trips, the analysis cannot determine whether this margin is already captured by the current surge algorithm or represents incremental opportunity — the document therefore closes with a specific, statistically powered A/B experiment design to resolve that question in 8 weeks.

## How to Use This Document

`business_case.md` is structured as 10 slides plus a technical appendix, intended for a Senior Manager on Uber's BizOps or Marketplace Pricing team. Read the slides in order: the first slide states the finding and the ask; slides 2–5 establish context and data; slides 6–7 present the core analytical finding and dollar sizing; slide 8 states the limitations plainly; slides 9–10 define the experiment and the decision path if it succeeds. The appendix contains the full regression coefficient tables for a technical reader or reviewer. Each slide headline is a complete finding — a reader who skims only the `##` headers will leave with the full argument. Supporting evidence files referenced throughout the business case are located at:

- Model coefficients: `outputs/tables/baseline_model_coefficients.csv`
- Opportunity scenarios: `outputs/tables/opportunity_sizing_scenarios.csv`
- Sensitivity analysis: `outputs/tables/sensitivity_analysis.csv`
- Experiment sample size: `outputs/tables/sample_size_calculation.csv`
- Charts: `outputs/charts/chart1_margin_by_weather_regime.png` through `chart4_opportunity_estimate.png`
- Methodology and assumptions: `docs/business_case_frame.md`, `docs/experiment_design.md`, `docs/assumptions_log.md`
