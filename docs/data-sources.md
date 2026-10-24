# Data sources & scientific boundaries

| Variable | Source | How it is used |
|---|---|---|
| Temperature, clouds, wind, MSL pressure | [Open-Meteo Historical Weather / ERA5](https://open-meteo.com/en/docs/historical-weather-api) | Historical hourly values for Tromsø and Reykjavík |
| Kp, solar wind speed, Bz (GSM) | [NASA OMNI2 hourly data](https://omniweb.gsfc.nasa.gov/html/ow_data.html) | Historical hourly records; Kp reflects three-hour periods |
| Latitude | Fixed city coordinates | Used for retrieval and astronomy; not an hourly model feature |
| Sun elevation, Moon phase/altitude | [Astral calculations](https://astral.readthedocs.io/) | Derived positions from UTC time/location; Moon illuminated fraction is approximate |
| Light pollution | No bundled measured worldwide source | Not evaluated; legacy assumed Bortle values are rejected |

`backend/scripts/download_aurora_data.py` merges the sources at UTC hour resolution and writes `backend/data/aurora_hours.csv`. Its accompanying provenance JSON records source URLs, download times, response metadata, accepted/rejected OMNI records, missing hours and per-city join losses. It reads verified 55-field OMNI annual records plus supported 56/57-field variants; Bz, speed and Kp use NASA words 17, 25 and 39 respectively.

## Why evaluation is called a proxy

The outcome for T+24 is `completed Kp interval >= 4 AND cloud <= 40% AND Sun elevation <= -6 degrees`. The target Kp comes from the `[T+21, T+24)` interval, so it is complete by the target time. Real aurora viewing additionally depends on the auroral oval, geomagnetic latitude, local horizon, moonlight, light pollution, atmospheric transparency, and more. A positive label is *not* evidence that aurora was seen.

Kp is a three-hour index (repeated across hourly OMNI records); its model input uses an earlier value to avoid using a period not yet complete at T. We compute the Sun and Moon positions **for T+24** because they can be known in advance. Historical hourly weather reanalysis is not the same as an actual forecast issued at time T.

The chronological protocol avoids random splitting: 2024 trains model weights, 2025 selects thresholds, and available 2026 data is held out for final evaluation. Examples whose T+24 target crosses a calendar boundary are excluded. Test metrics apply to the **selected city**. Geographic latitude is retained for location-specific data retrieval and astronomy but excluded from model features because it carries no hourly signal within a location. Light pollution is not evaluated without measured data.

**Judges should see:** data provenance, feature choices, target definition, a held-out test score, baseline comparison, and caveats. We have not calculated real-world accuracy values in the offline packaging environment.
