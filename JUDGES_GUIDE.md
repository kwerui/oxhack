# AuroraTime — Judges Guide

*Explore the past. Predict the night.*

AuroraTime is an explainable historical model lab for testing which inputs help predict favourable aurora-viewing conditions 24 hours ahead. It trains on 2024, selects thresholds on 2025, and evaluates once on available 2026 observations. It is not a live aurora-alert service and does not claim to predict verified aurora sightings.

## A short demo

1. Choose a location and select a set of weather, space-weather, astronomical, and environmental variables.
2. Choose Logistic Regression, Random Forest, or **Compare Both**, then run the experiment. Both algorithms use the same earlier training hours and later unseen test hours for the selected city.
3. Change the variables and use **Fork the Model** to compare the resulting configurations on the same evaluation protocol.
4. Review Brier score, precision, recall, F1, outcome counts, and the historical hourly outlook before interpreting the results.

## What makes it trustworthy

- Inputs selected in the interface are the only predictor variables sent to the model.
- Calendar-year partitions prevent future-label leakage: 2024 trains, 2025 validates, and 2026 is held out.
- Metrics are calculated from held-out 2026 historical data; they are never invented or hardcoded. The provenance file records actual coverage and rejected records.
- The target is an explicit viewing-conditions proxy: Kp ≥ 4, cloud cover ≤ 40%, and solar elevation ≤ −6° at the target hour.
- A simple baseline is displayed so a more complex configuration is not assumed to be better.

## Explaining the two models

- **Logistic Regression** makes a probability from a weighted combination of the selected inputs. It is a simple, explainable baseline.
- **Random Forest** combines many small decision trees, so it can represent more complicated patterns. It is not automatically more accurate or better calibrated.
- **Precision** says how often predicted suitable periods met the rule; **recall** says how many suitable periods were found; **F1** balances those two; **Brier score** measures probability error, where lower is better.

The comparison is about a rule-defined, 24-hour-ahead historical proxy—not confirmed aurora sightings or a live forecast.

## Data and limitations

The prototype uses NASA OMNI2 space-weather records, Open-Meteo ERA5 weather reanalysis, and calculated astronomical values. Light pollution is an assumption. ERA5 makes this a retrospective backtest, not a reconstruction of real-time forecast availability. See [README.md](README.md) and [docs/data-sources.md](docs/data-sources.md) for data sources and limitations.

### Reproducible local data run (24 October 2026 UTC)

The downloader joined 8,570 hours per city in 2024, 8,687 in 2025 and 6,187 through **2026-09-30 01:00 UTC**. After requiring both the completed input Kp interval and a T+24 target with a completed target Kp interval, the partitions contain 8,186 / 8,499 / 5,807 examples respectively. The exact source response metadata and rejection counts are in the locally generated provenance JSON. Newer OMNI rows were not safely usable because IMF Bz was a documented fill value; the merged feature set is intentionally stopped rather than partially backfilled.

Using weather, OMNI and astronomical features (excluding constant latitude and assumed Bortle class), the held-out 2026 results were:

| Location / model | Positives | Precision | Recall | F1 | Brier | FP / FN |
|---|---:|---:|---:|---:|---:|---:|
| Tromsø / Logistic Regression | 72 | 0.480 | 0.167 | 0.247 | 0.0119 | 13 / 60 |
| Tromsø / Random Forest | 72 | 0.078 | 0.139 | 0.100 | 0.0120 | 119 / 62 |
| Reykjavík / Logistic Regression | 87 | 0.077 | 0.149 | 0.102 | 0.0145 | 156 / 74 |
| Reykjavík / Random Forest | 87 | 0.048 | 0.023 | 0.031 | 0.0151 | 40 / 85 |

These are proxy-label results, not evidence of real aurora-visibility accuracy. Neither model is declared universally superior: the trade-off differs by metric and location.
