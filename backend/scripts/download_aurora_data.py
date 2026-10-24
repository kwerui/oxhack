"""Download REAL 2024 weather / NASA OMNI, then calculate astronomy features.

Run in backend/: python scripts/download_aurora_data.py
No keys required. We deliberately do not invent observations on download failures.
"""

import csv
from datetime import datetime, timedelta, timezone
import json
from math import cos, pi
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen


YEAR = 2024
DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "aurora_hours.csv"

# Bortle values below are ILLUSTRATIVE site assumptions, NOT measurements.
# Replace with a properly sourced sky-brightness dataset before making claims
# about the effect of light pollution.
LOCATIONS = {
    "Tromsø": {"latitude": 69.65, "longitude": 18.96, "bortle_assumed": 5},
    "Reykjavík": {"latitude": 64.15, "longitude": -21.94, "bortle_assumed": 6},
}
WEATHER_FIELDS = ["temperature_2m", "cloud_cover", "wind_speed_10m", "pressure_msl"]


def parse_omni_line(line):
    """Read NASA OMNI2 annual ASCII records (56 or 57 columns, by release).

    Word 17: GSM Bz; word 25: solar-wind speed; word 39: Kp*10.
    The later optional field does not change the column positions we need.
    """
    parts = line.split()
    if len(parts) not in (55, 56, 57):
        return None
    try:
        year, day, hour = int(parts[0]), int(parts[1]), int(parts[2])
        bz, speed, kp10 = float(parts[16]), float(parts[24]), int(parts[38])
        if not (1 <= day <= 366 and 0 <= hour <= 23):
            return None
        if abs(bz) >= 999 or not (0 < speed < 9999) or not (0 <= kp10 <= 90):
            return None
        timestamp = datetime(year, 1, 1, tzinfo=timezone.utc) + timedelta(days=day - 1, hours=hour)
        return timestamp.strftime("%Y-%m-%dT%H:%M"), (kp10 / 10, speed, bz)
    except (ValueError, IndexError):
        return None


def load_omni():
    url = f"https://cdaweb.gsfc.nasa.gov/pub/data/omni/low_res_omni/omni2_{YEAR}.dat"
    print("Downloading NASA OMNI2", url)
    with urlopen(url, timeout=120) as response:
        lines = response.read().decode("ascii").splitlines()
    readings = dict(record for line in lines if (record := parse_omni_line(line)) is not None)
    if len(readings) < 2000:
        raise RuntimeError("Not enough valid NASA hourly records. Check OMNI ASCII format and data availability.")
    return readings


def load_weather(latitude, longitude):
    params = {
        "latitude": latitude, "longitude": longitude,
        "start_date": f"{YEAR}-01-01", "end_date": f"{YEAR}-12-31",
        "hourly": ",".join(WEATHER_FIELDS), "timezone": "UTC", "models": "era5",
    }
    url = "https://archive-api.open-meteo.com/v1/archive?" + urlencode(params)
    print("Downloading Open-Meteo ERA5", latitude, longitude)
    with urlopen(url, timeout=120) as response:
        payload = json.load(response)
    if "hourly" not in payload:
        raise RuntimeError(f"Open-Meteo error: {payload}")
    hourly = payload["hourly"]
    return [
        {"time": time, **{field: hourly[field][index] for field in WEATHER_FIELDS}}
        for index, time in enumerate(hourly["time"])
    ]


def astronomy_at(time, latitude, longitude):
    """Sun/moon positions are deterministic calculations, not measured weather.

    Astral moon.phase is 0..28 (0=new moon; 14=full moon).
    We convert it to approximate illuminated percentage for readability.
    """
    # Imported here so parser tests can run without downloading packages.
    from astral import Observer
    from astral.moon import elevation as moon_elevation, phase as moon_phase
    from astral.sun import elevation as sun_elevation

    at = datetime.fromisoformat(time).replace(tzinfo=timezone.utc)
    observer = Observer(latitude=latitude, longitude=longitude)
    phase = moon_phase(at.date())
    illumination = 50 * (1 - cos(2 * pi * phase / 28))
    return {
        "sun_elevation": round(sun_elevation(observer, at), 2),
        "moon_phase": round(illumination, 1),
        "moon_altitude": round(moon_elevation(observer, at), 2),
    }


def main():
    omni = load_omni()
    rows = []
    for name, site in LOCATIONS.items():
        lat, lon = site["latitude"], site["longitude"]
        for hour in load_weather(lat, lon):
            values = omni.get(hour["time"])
            if values is None or any(hour[field] is None for field in WEATHER_FIELDS):
                continue
            kp, solar_speed, bz = values
            rows.append({
                "time": hour["time"], "location": name, "latitude": lat,
                "temperature": hour["temperature_2m"],
                "cloud": hour["cloud_cover"],
                "wind": hour["wind_speed_10m"],
                "pressure": hour["pressure_msl"],
                "kp": kp, "solar_speed": solar_speed, "bz": bz,
                **astronomy_at(hour["time"], lat, lon),
                "light_pollution": site["bortle_assumed"],
            })

    if len(rows) < 4000:
        raise RuntimeError("Too few combined observations; source/API problem. No synthetic fallback.")
    DATA_PATH.parent.mkdir(exist_ok=True)
    with DATA_PATH.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved {len(rows):,} records to {DATA_PATH}")
    print("Bortle estimates are manually assigned illustrative values, not observed light pollution.")
    print("Labels are a viewing-conditions proxy, NOT actual observed auroras.")


if __name__ == "__main__":
    main()
