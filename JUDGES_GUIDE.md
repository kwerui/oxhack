# AuroraTime — Judges Guide

*Explore the past. Predict the night.*

AuroraTime is an explainable historical model lab for testing which inputs help predict favourable aurora-viewing conditions three hours ahead. It is not a live aurora-alert service and does not claim to predict verified aurora sightings.

## A short demo

1. Choose a location and select a set of weather, space-weather, astronomical, and environmental variables.
2. Choose Logistic Regression, Random Forest, or **Compare Both**, then run the experiment. Both algorithms use the same earlier training hours and later unseen test hours for the selected city.
3. Change the variables and use **Fork the Model** to compare the resulting configurations on the same evaluation protocol.
4. Review Brier score, precision, recall, F1, outcome counts, and the historical hourly outlook before interpreting the results.

## What makes it trustworthy

- Inputs selected in the interface are the only predictor variables sent to the model.
- The train/test split is chronological, with a three-hour gap to avoid future-label leakage.
- Metrics are calculated from held-out historical data; they are never invented or hardcoded.
- The target is an explicit viewing-conditions proxy: Kp ≥ 4, cloud cover ≤ 40%, and solar elevation ≤ −6° at the target hour.
- A simple baseline is displayed so a more complex configuration is not assumed to be better.

## Explaining the two models

- **Logistic Regression** makes a probability from a weighted combination of the selected inputs. It is a simple, explainable baseline.
- **Random Forest** combines many small decision trees, so it can represent more complicated patterns. It is not automatically more accurate or better calibrated.
- **Precision** says how often predicted suitable periods met the rule; **recall** says how many suitable periods were found; **F1** balances those two; **Brier score** measures probability error, where lower is better.

The comparison is about a rule-defined, three-hour-ahead historical proxy—not confirmed aurora sightings or a live forecast.

## Data and limitations

The prototype uses NASA OMNI2 space-weather records, Open-Meteo ERA5 weather observations, and calculated astronomical values. Light pollution is an assumption. See [README.md](README.md) and [docs/data-sources.md](docs/data-sources.md) for data sources and limitations.
