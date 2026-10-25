# AuroraTime — Demo Specification

## Purpose

AuroraTime is a local historical model lab, not a live alert service. It compares Logistic Regression and Random Forest for a transparent 24-hour-ahead viewing-conditions proxy. The proxy is positive only when the target hour has a completed Kp interval of at least 4, cloud cover at most 40%, and Sun elevation at most −6°. It is not a confirmed aurora sighting or scientifically validated visibility label.

## User workflow

1. Select Tromsø, Reykjavík, a searched place, browser location, or exact coordinates.
2. Select weather, NASA space-weather, and calculated Sun/Moon inputs; latitude is used only to retrieve history and calculate astronomy.
3. Run Logistic Regression, Random Forest, or both. Save results as forks and compare their stored configuration and metrics.
4. Read detected periods, missed periods, false alarms, precision, recall, F1, Brier score and the training-prevalence Brier baseline.

No measured worldwide light-pollution dataset is bundled. Light pollution and assumed Bortle values are deliberately excluded from selectable model inputs.

## Historical protocol

- Examples use information available at hour T to target the proxy at T + 24 hours. Input Kp is an earlier completed interval; Sun and Moon positions at the future target are calculated astronomy, not future-observed weather.
- 2024 is the training partition. 2025 selects the F1-maximising classification threshold. The chosen model is then refit on 2024–2025 and evaluated once on available 2026 hours.
- Threshold candidates run from 0.05 to 0.95. If F1 is tied, choose 0.50 when it is tied; otherwise choose the F1-optimal candidate closest to 0.50, then the lower candidate if still tied.
- Location-specific history is assembled at the requested coordinates. The frontend rejects a backend response whose coordinates differ from the selection.

## Boundaries and limitations

- NASA OMNI2 and Open-Meteo ERA5 are historical data. ERA5 reanalysis and archived space-weather inputs do not establish what would have been available in real time.
- The target omits viewing factors such as measured light pollution and does not prove that any selected predictor causes visibility.
- Sparse positives and one held-out calendar period mean metrics can be unstable. Do not claim a universal winner or operational forecasting performance.
- XGBoost exists only in the offline benchmark script and documentation. It is not an API choice, frontend option, or production model.

## Local checks

```sh
cd backend && .venv/bin/python -m pytest -q
cd frontend && npm run test && npm run lint && npm run typecheck && npm run build
```

See [README.md](README.md) for setup for a concise demo walkthrough.
