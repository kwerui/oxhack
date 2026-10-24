# AuroraTime XGBoost benchmark

**Status:** exploratory comparison. The 2026 historical dataset had already been inspected before this benchmark, so it is not a fresh, unbiased final test.

**Reproduce:** from `backend/`, install `python -m pip install -r requirements-benchmark.txt` (on macOS also `brew install libomp`), then run `python scripts/benchmark_xgboost.py --output ../docs/xgboost_benchmark_results.md`.

**Protocol:** 24-hour proxy from AuroraTime; 2024 train, 2025 validation, available 2026 test; variables: temperature, cloud, wind, pressure, kp, solar_speed, bz, sun_elevation, moon_phase, moon_altitude.

Settings are selected on 2025 from only two predeclared imbalance options per model by PR-AUC (Brier breaks ties). The displayed final models are then refit on 2024–2025. `F1 threshold` is selected only on 2025.

## Tromsø

Examples: train 8186 (30 positive), validation 8499 (65 positive), test 5807 (72 positive).

### F1-selected operating point

| Model | 2025 setting | Threshold | Precision | Recall | F1 | Brier | PR-AUC | TP | FP | FN |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Training-prevalence / always WAIT | none | 1.000 | 0.000 | 0.000 | 0.000 | 0.0123 | 0.012 | 0 | 0 | 72 |
| Logistic Regression | unweighted | 0.050 | 0.480 | 0.167 | 0.247 | 0.0119 | 0.163 | 12 | 13 | 60 |
| Random Forest | unweighted | 0.050 | 0.177 | 0.236 | 0.202 | 0.0118 | 0.136 | 17 | 79 | 55 |
| XGBoost | sqrt-balanced | 0.250 | 0.000 | 0.000 | 0.000 | 0.0141 | 0.039 | 0 | 60 | 72 |

### Matched observed false-alarm budget: at most 1% of 2026 negatives

Thresholds in this table are calculated from 2026 outcomes solely to compare ranking at the same measured false-alarm budget. They are descriptive, **not** deployable thresholds or a fresh test result.

| Model | Threshold | Precision | Recall | F1 | Brier | PR-AUC | TP | FP | FN |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Training-prevalence / always WAIT | 1.000 | 0.000 | 0.000 | 0.000 | 0.0123 | 0.012 | 0 | 0 | 72 |
| Logistic Regression | 0.029 | 0.230 | 0.236 | 0.233 | 0.0119 | 0.163 | 17 | 57 | 55 |
| Random Forest | 0.060 | 0.149 | 0.139 | 0.144 | 0.0118 | 0.136 | 10 | 57 | 62 |
| XGBoost | 0.254 | 0.000 | 0.000 | 0.000 | 0.0141 | 0.039 | 0 | 57 | 72 |

## Reykjavík

Examples: train 8186 (72 positive), validation 8499 (98 positive), test 5807 (87 positive).

### F1-selected operating point

| Model | 2025 setting | Threshold | Precision | Recall | F1 | Brier | PR-AUC | TP | FP | FN |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Training-prevalence / always WAIT | none | 1.000 | 0.000 | 0.000 | 0.000 | 0.0148 | 0.015 | 0 | 0 | 87 |
| Logistic Regression | balanced | 0.650 | 0.062 | 0.483 | 0.110 | 0.1269 | 0.067 | 42 | 635 | 45 |
| Random Forest | balanced | 0.150 | 0.037 | 0.448 | 0.069 | 0.0535 | 0.036 | 39 | 1009 | 48 |
| XGBoost | sqrt-balanced | 0.050 | 0.027 | 0.299 | 0.050 | 0.0207 | 0.044 | 26 | 923 | 61 |

### Matched observed false-alarm budget: at most 1% of 2026 negatives

Thresholds in this table are calculated from 2026 outcomes solely to compare ranking at the same measured false-alarm budget. They are descriptive, **not** deployable thresholds or a fresh test result.

| Model | Threshold | Precision | Recall | F1 | Brier | PR-AUC | TP | FP | FN |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Training-prevalence / always WAIT | 1.000 | 0.000 | 0.000 | 0.000 | 0.0148 | 0.015 | 0 | 0 | 87 |
| Logistic Regression | 0.949 | 0.109 | 0.080 | 0.093 | 0.1269 | 0.067 | 7 | 57 | 80 |
| Random Forest | 0.847 | 0.017 | 0.011 | 0.014 | 0.0535 | 0.036 | 1 | 57 | 86 |
| XGBoost | 0.450 | 0.050 | 0.034 | 0.041 | 0.0207 | 0.044 | 3 | 57 | 84 |

## Oxford (optional local cache)

Examples: train 8186 (103 positive), validation 8499 (222 positive), test 5807 (69 positive).

### F1-selected operating point

| Model | 2025 setting | Threshold | Precision | Recall | F1 | Brier | PR-AUC | TP | FP | FN |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Training-prevalence / always WAIT | none | 1.000 | 0.000 | 0.000 | 0.000 | 0.0117 | 0.012 | 0 | 0 | 69 |
| Logistic Regression | balanced | 0.850 | 0.049 | 0.188 | 0.078 | 0.1573 | 0.035 | 13 | 250 | 56 |
| Random Forest | balanced | 0.250 | 0.026 | 0.681 | 0.051 | 0.0737 | 0.030 | 47 | 1745 | 22 |
| XGBoost | sqrt-balanced | 0.150 | 0.030 | 0.493 | 0.056 | 0.0280 | 0.028 | 34 | 1114 | 35 |

### Matched observed false-alarm budget: at most 1% of 2026 negatives

Thresholds in this table are calculated from 2026 outcomes solely to compare ranking at the same measured false-alarm budget. They are descriptive, **not** deployable thresholds or a fresh test result.

| Model | Threshold | Precision | Recall | F1 | Brier | PR-AUC | TP | FP | FN |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Training-prevalence / always WAIT | 1.000 | 0.000 | 0.000 | 0.000 | 0.0117 | 0.012 | 0 | 0 | 69 |
| Logistic Regression | 0.942 | 0.050 | 0.043 | 0.047 | 0.1573 | 0.035 | 3 | 57 | 66 |
| Random Forest | 0.734 | 0.050 | 0.043 | 0.047 | 0.0737 | 0.030 | 3 | 57 | 66 |
| XGBoost | 0.516 | 0.017 | 0.014 | 0.016 | 0.0280 | 0.028 | 1 | 57 | 68 |

## Reading the result

Prefer a model only if it finds materially more true positives at the matched 1% false-positive-rate budget without materially worse precision or calibration. The prevalence/always-WAIT baseline has zero false alarms and zero detections; it is included to make the cost of alerts explicit. A practical deployment threshold must remain selected on validation data: in this run those validation thresholds did not transfer stably to 2026, another reason not to integrate yet. Do not use the 2026 comparison as a final model-selection claim: reserve a later, not-yet-inspected period or use rolling temporal backtests before integration.

## Recommendation

Keep the existing Logistic Regression and Random Forest models; **do not replace Random Forest with XGBoost**. XGBoost did not improve any location consistently: it found no Tromsø positives at the matched 1% false-alarm budget, trailed Logistic Regression in Reykjavík, and trailed or tied the existing models in Oxford. Its validation-selected operating points also produced many false alarms or zero detections. Revisit only with a new, uninspected period and operationally available predictors.
