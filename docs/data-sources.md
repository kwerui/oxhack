# Data sources & scientific boundaries

| Variable | Source | How it is used |
|---|---|---|
| Temperature, clouds, wind, MSL pressure | [Open-Meteo Historical Weather / ERA5](https://open-meteo.com/en/docs/historical-weather-api) | Historical hourly values for Tromsø and Reykjavík |
| Kp, solar wind speed, Bz (GSM) | [NASA OMNI2 hourly data](https://omniweb.gsfc.nasa.gov/html/ow_data.html) | Historical hourly records; Kp reflects three-hour periods |
| Latitude | Fixed city coordinates | Geographic, not geomagnetic latitude |
| Sun elevation, Moon phase/altitude | [Astral calculations](https://astral.readthedocs.io/) | Derived positions from UTC time/location; Moon illuminated fraction is approximate |
| Light pollution | Example Bortle classes 5 and 6 | **Assumptions only**, not measured values |

`backend/scripts/download_aurora_data.py` merges the sources at UTC hour resolution and writes `backend/data/aurora_hours.csv`. It will fail rather than generate fake replacement observations when external APIs are unavailable.

## Why evaluation is called a proxy

The outcome for T+3 is `Kp >= 4 AND cloud <= 40% AND Sun elevation <= -6 degrees`. Real aurora viewing additionally depends on the auroral oval, geomagnetic latitude, local horizon, moonlight, light pollution, atmospheric transparency, and more. A positive label is *not* evidence that aurora was seen.

Kp is a three-hour index (repeated across hourly OMNI records); its model input uses an earlier value to avoid using a period not yet complete at T. We compute the Sun and Moon positions **for T+3** because they can be known in advance. Historical hourly weather reanalysis is not the same as an actual forecast issued at time T.

The chronological train/test split avoids a random split that would expose later dates during training. Test metrics apply to the **selected city**. Because this dataset samples only two cities, adding latitude or constant assumed Bortle values can effectively encode city identity; do not claim this measures independent causal effects.

**Judges should see:** data provenance, feature choices, target definition, a held-out test score, baseline comparison, and caveats. We have not calculated real-world accuracy values in the offline packaging environment.
