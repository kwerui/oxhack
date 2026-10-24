# AuroraTime — Judges Guide

*Explore the past. Predict the night.*

AuroraTime is an explainable historical model lab for testing which inputs help predict favourable aurora-viewing conditions 24 hours ahead. It trains on 2024, selects thresholds on 2025, and evaluates once on available 2026 observations. It is not a live aurora-alert service and does not claim to predict verified aurora sightings.

## A short demo

1. Choose a location and select weather, space-weather, and calculated astronomical variables. Light pollution is not offered because no measured worldwide source is bundled.
2. Choose Logistic Regression, Random Forest, or **Compare Both**, then run the experiment. Both algorithms use the same earlier training hours and later unseen test hours for the selected location.
3. Change the variables and use **Fork the Model** to compare the resulting configurations on the same evaluation protocol.
4. Review Brier score, precision, recall, F1, outcome counts, and the historical hourly outlook before interpreting the results.

## What makes it trustworthy

- Inputs selected in the interface are the only predictor variables sent to the model.
- Calendar-year partitions prevent future-label leakage: each model trains on 2024, selects its F1 operating threshold on 2025, is refit on 2024–2025, and is evaluated on held-out 2026 hours.
- If several 2025 thresholds have the same F1, the deterministic policy prefers 50%, then the tied candidate closest to 50%. This affects only the alert operating point, not probability scores or Brier score.
- Metrics are calculated from held-out 2026 historical data; they are never invented or hardcoded. The provenance file records actual coverage and rejected records.
- The target is an explicit viewing-conditions proxy: Kp ≥ 4, cloud cover ≤ 40%, and solar elevation ≤ −6° at the target hour.
- A simple baseline is displayed so a more complex configuration is not assumed to be better.

## Explaining the two models

- **Logistic Regression** makes a probability from a weighted combination of the selected inputs. It is a simple, explainable baseline.
- **Random Forest** combines many small decision trees, so it can represent more complicated patterns. It is not automatically more accurate or better calibrated.
- **Precision** says how often predicted suitable periods met the rule; **recall** says how many suitable periods were found; **F1** balances those two; **Brier score** measures probability error, where lower is better.

The comparison is about a rule-defined, 24-hour-ahead historical proxy—not confirmed aurora sightings or a live forecast.

## Data and limitations

The prototype uses NASA OMNI2 space-weather records, Open-Meteo ERA5 weather reanalysis, and calculated astronomical values. Light pollution is **not** a model input: legacy files can contain assumed Bortle values, but the application rejects them rather than treating an assumption as measured data. ERA5 makes this a retrospective backtest, not a reconstruction of real-time forecast availability.

The downloader's provenance JSON records the exact available coverage, joins and rejected records. The interface calculates the current held-out metrics from the selected location and variables; it deliberately does not rely on a static score table. Those values are proxy-label results, not evidence of real aurora-visibility accuracy. Neither model is declared universally superior: inspect detections, missed periods, false alarms, precision, recall, F1 and Brier score for the selected experiment.

### Threshold caveat

Favourable-condition labels are extremely rare. In the currently cached 2025 validation data for the tested seven-input Logistic Regression configurations, every positive score was below the implemented 0.05–0.95 threshold grid. The 0.5 result is consequently a documented F1-tie policy, not a validated useful alert threshold. Lower thresholds were tested on validation only, but unconstrained F1 optimisation produced excessive false alarms; a predeclared 1% validation false-positive-rate budget captured no positives for either Tromsø or Reykjavík. Further, threshold selection uses 2024-fitted scores before the model is refit on combined 2024–2025 data, which can change score calibration. AuroraTime is a historical experiment, not an operationally reliable aurora-alert system.
