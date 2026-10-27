# AuroraTime

*Explore the past. Predict the night.*

**OxHack 2026 · Theme: Time · HRT: Data for Predictions & Decision Making**

*Which data actually helps us decide whether to plan an aurora-viewing trip 24 hours ahead?* Pick input variables, run a small machine-learning experiment, rewind and test a different combination.

This prototype intentionally does **not** claim to forecast real aurora sightings. It learns a historical **viewing-conditions proxy**: at the target hour, **Kp ≥ 4, cloud cover ≤ 40%, and solar elevation ≤ −6°**. These thresholds are illustrative, not a scientifically validated sighting label. Probability scores only estimate this proxy.

## What the visitor does

1. Choose a suggested **Tromsø** or **Reykjavík** location, search for another place, use browser location, or enter coordinates.
2. Select from **10 evaluated inputs**: temperature, cloud cover, wind speed, sea-level pressure, Kp, solar wind speed, IMF Bz, Sun elevation (darkness), Moon illumination and Moon altitude. Coordinates remain in use for location-specific data and astronomy, but latitude is not an hourly predictor. Light pollution is unavailable because a measured worldwide source is not bundled; it is never replaced with an assumption.
3. Choose **Logistic Regression**, **Random Forest**, or **Compare Both**, then click **Run experiment**. Each model trains on the same older historical hours and tests on the same later, unseen hours.
4. Inspect precision, recall, F1 and Brier score alongside hourly probabilities and detected, missed and false-alarm counts. Those classification metrics use a threshold selected on 2025 only: when several thresholds tie, it prefers the conventional 50% threshold (then the nearest candidate), before 2026 is evaluated.
5. Remove Bz or a weather variable and rerun. The resulting **Fork the Model** experiment can be compared against earlier versions without assuming that more inputs or a more complex model is better.

**Time** is central: predictions target **T + 24 hours**, evaluation respects calendar order, and each saved fork lets you change the information available at T.

## Start on macOS

You need Node.js, npm and Python. Open **two terminal tabs** from the `oxhack` repository root.

**Terminal A — Python:**

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/download_aurora_data.py
python -m uvicorn app.main:app --reload --port 8000
```

The data download fetches real **2024 training**, **2025 validation**, and all actually available **2026 held-out** observations. It records source URLs, download times, response metadata, accepted/rejected records and missing/joined-hour counts in `backend/data/aurora_hours.provenance.json`. Do not display or invent model scores when the download fails or a required period is unavailable.

Check `http://localhost:8000/health` for `{"status":"ok","dataReady":true}`.

**Terminal B — Next.js:**

```bash
cd frontend
npm install
npm run dev -- --hostname 0.0.0.0
```

Open **http://localhost:3000** on the host, or **http://&lt;host-ip&gt;:3000** from a teammate's device on the same network. Both terminals must remain running. The Next.js server forwards browser requests to `/api/v1/*` to the local Python service, so teammates only need the frontend URL; port 8000 is not exposed to their browser. In particular, `npm run dev -- --hostname 0.0.0.0` belongs in `frontend`, not the repository root.

### Tests

```bash
cd backend
python -m pytest -q
```

The test fixtures are **synthetic** to check the algorithm works; synthetic values are never shown as real-world results. With dependencies installed, you can also run `npm run typecheck` and `npm run build` from `frontend/`.

## Where data comes from

- **NASA OMNI2 hourly archive:** Kp, solar wind speed, IMF Bz (GSM). Verified 55-field annual records and supported 56/57-field variants are parsed. Kp is a three-hour index; an earlier completed interval is used as a model feature.
- **Open-Meteo Historical Weather (ERA5):** temperature, clouds, wind, pressure for two northern cities, joined on UTC hourly timestamps. ERA5 is retrospective reanalysis, not a forecast issued at the original decision time.
- **Astral library:** derived Sun elevation and approximate Moon illumination / altitude, calculated from timestamp and location. Future Sun/Moon positions are known in advance; they are *not* future-observed weather.
- **Light pollution:** unavailable as a model input. Legacy files may contain assumed Bortle values, but AuroraTime rejects and does not train on them because no measured worldwide source is bundled.

See [docs/data-sources.md](docs/data-sources.md) for source links and important limitations.

## How the model works

1. We read conditions at hour **T**; for example, cloud cover and a Kp interval completed by T. Sun and Moon locations for **T+24** can be computed in advance.
2. We compare against the retrospective rule outcome at **T+24**. Its Kp value is the completed three-hour interval ending at T+24, not an interval that extends beyond the target time.
3. We fit each model on 2024, choose its F1-maximising classification threshold on 2025, then refit on 2024–2025 and evaluate once on available 2026 data. If F1 ties, the policy prefers 50%; otherwise it chooses the tied candidate closest to 50% (lower one if still tied). Both models receive the same selected inputs and exactly the same rows.
4. **Logistic Regression** estimates a probability from a weighted combination of inputs. **Random Forest** averages many small decision trees, allowing it to learn more complex patterns. Neither is automatically better.
5. The held-out hours are scored using **precision** (how often predicted suitable periods met the rule), **recall** (how many suitable periods were found), **F1** (a balance of precision and recall), and **Brier score** (probability error; lower is better).
6. We also score a **naive baseline** that always predicts the training positive rate. This gives a reality check: adding more variables or model complexity does not automatically improve the result.

**Example:** Two forks might use `cloud + Kp + Sun elevation` versus the same inputs **plus Bz**. Compare their scores on the *same test period*. That is a test of predictive usefulness, not evidence of causation.


## Known limitations

- The outcome is **not verified aurora visibility**. To make that claim, we'd need trustworthy aurora observations/sighting labels, and likely a better target definition that includes geographic and geomagnetic factors.
- Sparse proxy positives are reported rather than turned into a model-winner claim. Geographic latitude is used for location data and astronomy, not as a model feature, because it is constant within a location. Light pollution is not evaluated without measured data.
- Favourable-condition labels are extremely rare. In the currently cached 2025 validation data for the tested seven-input Logistic Regression configurations, no positive score reached the implemented 0.05–0.95 threshold grid. The 0.5 fallback is therefore a documented F1-tie policy, **not** evidence of a validated useful alert threshold. Lower validation-only thresholds were tested, but unconstrained F1 optimisation produced excessive false alarms; a predeclared 1% validation false-positive-rate budget captured no positives in either Tromsø or Reykjavík.
- Thresholds are selected from scores produced by a model fitted on 2024, then that model is refit on combined 2024–2025 data before 2026 evaluation. Refit score calibration can change, so a selected numeric threshold is not automatically portable. AuroraTime is not an operationally reliable aurora-alert system.
- Kp and hourly reanalysis observations are **historical**, not guaranteed available instantly for real-life 24-hour-ahead decisions; operational forecasting would require truly available-at-issue-time inputs and realistic latency handling.
- Temperature and wind mainly relate to comfort and travel decisions. Moon and light pollution affect viewing, but are not part of this first rule-defined target, so selecting them cannot validate their real-world viewing impact.
- No AI agent, spatiotemporal heatmap, trading automation, or World Bank connection is included in this scoped version.

