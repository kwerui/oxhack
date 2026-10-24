# AuroraTime

*Explore the past. Predict the night.*

**OxHack 2026 · Theme: Time · HRT: Data for Predictions & Decision Making**

**Pitch:** *Which data actually helps us decide whether to plan an aurora-viewing trip three hours ahead?* Pick input variables, run a small machine-learning experiment, rewind and test a different combination.

This prototype intentionally does **not** claim to forecast real aurora sightings. It learns a historical **viewing-conditions proxy**: at the target hour, **Kp ≥ 4, cloud cover ≤ 40%, and solar elevation ≤ −6°**. These thresholds are illustrative, not a scientifically validated sighting label. Probability scores only estimate this proxy.

## What the visitor does

1. Choose **Tromsø** or **Reykjavík**.
2. Select from **12 inputs**: temperature, cloud cover, wind speed, sea-level pressure, Kp, solar wind speed, geographic latitude, IMF Bz, Sun elevation (darkness), Moon illumination, Moon altitude and assumed light pollution.
3. Click **Run experiment**. Python trains logistic regression on older historical hours and tests it on later, unseen hours.
4. Inspect hourly probabilities and whether a simple **GO / WAIT** decision (50% threshold) would have matched the proxy.
5. Remove Bz or a weather variable and rerun. The resulting **fork** can be compared against earlier versions using Brier score (lower is better), precision and recall.

**Time** is central: predictions target **T + 3 hours**, evaluation respects calendar order, and each saved fork lets you change the information available at T.

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

The data download fetches real **2024** historical observations and may take several minutes. It needs internet and can fail if either provider is unavailable. **Do not display or invent model accuracy scores when the download fails.** If your previous `.venv` was copied from another folder, rename/remove it before recreating it.

Check `http://localhost:8000/health` for `{"status":"ok","dataReady":true}`.

**Terminal B — Next.js:**

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:3000**. Both terminals must remain running. In particular, `npm run dev` belongs in `frontend`, not the repository root.

### Tests

```bash
cd backend
python -m pytest -q
```

The test fixtures are **synthetic** to check the algorithm works; synthetic values are never shown as real-world results. With dependencies installed, you can also run `npm run typecheck` and `npm run build` from `frontend/`.

## Where data comes from

- **NASA OMNI2 hourly archive:** Kp, solar wind speed, IMF Bz (GSM). Kp is a three-hour index; an earlier completed interval is used as a model feature.
- **Open-Meteo Historical Weather (ERA5):** temperature, clouds, wind, pressure for two northern cities, joined on UTC hourly timestamps.
- **Astral library:** derived Sun elevation and approximate Moon illumination / altitude, calculated from timestamp and location. Future Sun/Moon positions are known in advance; they are *not* future-observed weather.
- **Light pollution:** **assumed Bortle class** per city, not measured satellite data, so it cannot establish the effect of actual light pollution.

See [docs/data-sources.md](docs/data-sources.md) for source links and important limitations.

## How the model works (simple explanation)

1. We read conditions at hour **T**; for example, cloud cover and an earlier completed Kp measurement. Sun and Moon locations for **T+3** can be computed in advance.
2. We compare against the **observed rule outcome at T+3**, using real historical Kp, clouds and Sun position.
3. We train **logistic regression** on the earlier 75% of timestamps and leave a 3-hour gap before the held-out test period.
4. The selected city's held-out hours are scored using **Brier score**, **precision**, and **recall**. Brier score is the average squared difference between a predicted probability and a 0/1 actual proxy outcome; **lower is better**.
5. We also score a **naive baseline** that always predicts the training positive rate. This gives a reality check: adding more variables does not automatically improve the result.

**Example:** Two forks might use `cloud + Kp + Sun elevation` versus the same inputs **plus Bz**. Compare their scores on the *same test period*. That is a test of predictive usefulness, not evidence of causation.

## Files you should know for judging

| File | Purpose |
|---|---|
| `frontend/app/page.tsx` | Page, checkboxes, saved model forks and result display |
| `frontend/lib/aurora.ts` | Variable names, TypeScript types and one API request |
| `backend/app/main.py` | Three small FastAPI endpoints |
| `backend/app/aurora.py` | Input selection, hourly examples, training and scoring |
| `backend/scripts/download_aurora_data.py` | Fetches/joins NASA and Open-Meteo observations and computes astronomy |
| `backend/tests/test_aurora.py` | Tests model logic and the NASA file parser |

### 40-second technical explanation for judges

> AuroraTime is a model lab for experimenting with decisions over time. We load historical NASA space-weather data and ERA5 weather observations, then let users decide which of twelve variables a logistic-regression model is allowed to use. The prediction target is whether the sky meets an explicitly defined suitability rule three hours later. We train only on past dates, evaluate predictions on unseen later dates and compare against a simple baseline. When the user adds or removes a variable, **Fork the Model** creates a new fork so the results are easy to compare. This is a historical experiment with transparent limitations, not a live aurora-alert service.

## Known limitations

- The outcome is **not verified aurora visibility**. To make that claim, we'd need trustworthy aurora observations/sighting labels, and likely a better target definition that includes geographic and geomagnetic factors.
- Two locations and one historical year give limited evidence. City latitude and assumed Bortle class are confounded with location.
- Kp and hourly reanalysis observations are **historical**, not guaranteed available instantly for real-life 3-hour-ahead decisions; operational forecasting would require truly available-at-issue-time inputs and realistic latency handling.
- Temperature and wind mainly relate to comfort and travel decisions. Moon and light pollution affect viewing, but are not part of this first rule-defined target, so selecting them cannot validate their real-world viewing impact.
- No AI agent, spatiotemporal heatmap, trading automation, or World Bank connection is included in this scoped version.
