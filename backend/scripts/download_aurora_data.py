"""Build reproducible UTC backtest data from NASA OMNI2 and Open-Meteo ERA5.

Run from backend/: ``.venv/bin/python scripts/download_aurora_data.py``.
This is retrospective backtesting data, never an operational forecast archive.
"""

import csv
from datetime import date, datetime, timedelta, timezone
import json
from math import cos, pi
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

YEARS = (2024, 2025, 2026)
DATA_DIR = Path(__file__).resolve().parents[1] / 'data'
DATA_PATH = DATA_DIR / 'aurora_hours.csv'
PROVENANCE_PATH = DATA_DIR / 'aurora_hours.provenance.json'
NASA_BASE_URL = 'https://cdaweb.gsfc.nasa.gov/pub/data/omni/low_res_omni'
OPEN_METEO_URL = 'https://archive-api.open-meteo.com/v1/archive'
WEATHER_FIELDS = ['temperature_2m', 'cloud_cover', 'wind_speed_10m', 'pressure_msl']

# Illustrative site assumptions, not light-pollution observations.
LOCATIONS = {
    'Tromsø': {'latitude': 69.65, 'longitude': 18.96, 'bortle_assumed': 5},
    'Reykjavík': {'latitude': 64.15, 'longitude': -21.94, 'bortle_assumed': 6},
}


def omni_url(year: int) -> str:
    return f'{NASA_BASE_URL}/omni2_{year}.dat'


def _parse_omni_line(line: str):
    """Parse verified 55-field OMNI2 records and supported 56/57-field variants.

    NASA's word positions remain fixed: GSM Bz=17, speed=25, Kp*10=39.
    """
    parts = line.split()
    if len(parts) not in (55, 56, 57):
        return None, 'unsupportedFieldCount'
    try:
        year, day, hour = (int(parts[index]) for index in range(3))
        bz, speed, kp10 = float(parts[16]), float(parts[24]), int(parts[38])
        if not (1 <= day <= 366 and 0 <= hour <= 23):
            return None, 'invalidTimestamp'
        # NASA ASCII fills: Bz=999.9, speed=9999, Kp*10=99.
        if abs(bz) >= 999:
            return None, 'bzFillValue'
        if speed <= 0 or speed >= 9999:
            return None, 'solarWindSpeedFillValue'
        if not (0 <= kp10 <= 90):
            return None, 'kpFillValue'
        timestamp = datetime(year, 1, 1, tzinfo=timezone.utc) + timedelta(days=day - 1, hours=hour)
        if timestamp.year != year:
            return None, 'invalidTimestamp'
        return (timestamp.strftime('%Y-%m-%dT%H:%M'), (kp10 / 10, speed, bz)), None
    except (ValueError, IndexError):
        return None, 'unparseableRecord'


def parse_omni_line(line: str):
    """Public parser retained for tests and callers that need valid records only."""
    return _parse_omni_line(line)[0]


def validate_omni_readings(readings: dict[str, tuple[float, float, float]], year: int) -> dict[str, object]:
    """Calculate actual annual coverage rather than assuming a published file is full."""
    start, end = datetime(year, 1, 1), datetime(year + 1, 1, 1)
    expected = int((end - start).total_seconds() // 3600)
    expected_times = {(start + timedelta(hours=hour)).strftime('%Y-%m-%dT%H:%M') for hour in range(expected)}
    missing = sorted(expected_times - set(readings))
    available = sorted(readings)
    last = available[-1] if available else None
    first = available[0] if available else None
    within_available = [time for time in missing if last is None or time <= last]
    return {'expectedHours': expected, 'acceptedHours': len(readings), 'missingHours': len(missing),
            'firstAvailableHour': first, 'lastAvailableHour': last,
            'missingWithinAvailableRange': len(within_available),
            'firstMissingHour': missing[0] if missing else None}


def _headers(response) -> dict[str, str]:
    return {key: response.headers[key] for key in ('Last-Modified', 'ETag', 'Content-Length') if response.headers.get(key)}


def load_omni(year: int) -> tuple[dict[str, tuple[float, float, float]], dict[str, object]]:
    url = omni_url(year)
    downloaded_at = datetime.now(timezone.utc).isoformat()
    with urlopen(url, timeout=120) as response:
        headers, lines = _headers(response), response.read().decode('ascii').splitlines()
    readings, rejected = {}, 0
    rejected_by_reason = {}
    for line in lines:
        record, reason = _parse_omni_line(line)
        if record is None:
            rejected += 1
            rejected_by_reason[reason] = rejected_by_reason.get(reason, 0) + 1
        else:
            readings[record[0]] = record[1]
    report = validate_omni_readings(readings, year)
    report.update({'source': url, 'downloadedAt': downloaded_at, 'sourceMetadata': headers,
                   'rawRecords': len(lines), 'rejectedRecords': rejected,
                   'rejectedByReason': rejected_by_reason})
    return readings, report


def _year_end(year: int) -> date:
    today = datetime.now(timezone.utc).date()
    return min(date(year, 12, 31), today) if year == today.year else date(year, 12, 31)


def load_weather(latitude: float, longitude: float, year: int, end_date: date | None = None) -> tuple[dict[str, dict[str, object]], dict[str, object]]:
    end = end_date or _year_end(year)
    params = {'latitude': latitude, 'longitude': longitude, 'start_date': f'{year}-01-01',
              'end_date': end.isoformat(), 'hourly': ','.join(WEATHER_FIELDS),
              'timezone': 'UTC', 'models': 'era5'}
    url = OPEN_METEO_URL + '?' + urlencode(params)
    downloaded_at = datetime.now(timezone.utc).isoformat()
    with urlopen(url, timeout=120) as response:
        headers, payload = _headers(response), json.load(response)
    hourly = payload.get('hourly')
    if not isinstance(hourly, dict) or not isinstance(hourly.get('time'), list):
        raise RuntimeError(f'Open-Meteo did not return hourly data: {payload}')
    records, rejected = {}, 0
    for index, timestamp in enumerate(hourly['time']):
        try:
            values = {field: hourly[field][index] for field in WEATHER_FIELDS}
        except (KeyError, IndexError):
            rejected += 1
            continue
        if any(value is None for value in values.values()):
            rejected += 1
            continue
        records[timestamp] = values
    return records, {'source': url, 'downloadedAt': downloaded_at, 'sourceMetadata': headers,
                     'requestedStart': f'{year}-01-01', 'requestedEnd': end.isoformat(),
                     'rawHours': len(hourly['time']), 'acceptedHours': len(records),
                     'rejectedHours': rejected, 'units': payload.get('hourly_units', {}), 'model': 'ERA5'}


def astronomy_at(time: str, latitude: float, longitude: float) -> dict[str, float]:
    from astral import Observer
    from astral.moon import elevation as moon_elevation, phase as moon_phase
    from astral.sun import elevation as sun_elevation

    at = datetime.fromisoformat(time).replace(tzinfo=timezone.utc)
    observer = Observer(latitude=latitude, longitude=longitude)
    phase = moon_phase(at.date())
    return {'sun_elevation': round(sun_elevation(observer, at), 2),
            'moon_phase': round(50 * (1 - cos(2 * pi * phase / 28)), 1),
            'moon_altitude': round(moon_elevation(observer, at), 2)}


def main():
    omni_by_year, omni_reports = {}, {}
    for year in YEARS:
        print(f'Downloading NASA OMNI2 {year}')
        omni_by_year[year], omni_reports[str(year)] = load_omni(year)

    rows, location_reports = [], {}
    for name, site in LOCATIONS.items():
        location_reports[name] = {}
        for year in YEARS:
            print(f'Downloading Open-Meteo ERA5 {name} {year}')
            omni = omni_by_year[year]
            # Do not request weather later than the last hour where all required
            # NASA features survived validation (especially important for 2026).
            last_omni_date = date.fromisoformat(omni_reports[str(year)]['lastAvailableHour'][:10])
            weather, weather_report = load_weather(site['latitude'], site['longitude'], year, last_omni_date)
            common = sorted(set(weather) & set(omni))
            location_reports[name][str(year)] = {
                'weather': weather_report, 'joinedHours': len(common),
                'missingBecauseOmniUnavailable': len(set(weather) - set(omni)),
                'missingBecauseWeatherUnavailable': len(set(omni) - set(weather)),
            }
            for time in common:
                kp, solar_speed, bz = omni[time]
                hour = weather[time]
                rows.append({'time': time, 'location': name, 'latitude': site['latitude'],
                             'temperature': hour['temperature_2m'], 'cloud': hour['cloud_cover'],
                             'wind': hour['wind_speed_10m'], 'pressure': hour['pressure_msl'],
                             'kp': kp, 'solar_speed': solar_speed, 'bz': bz,
                             **astronomy_at(time, site['latitude'], site['longitude']),
                             'light_pollution': site['bortle_assumed']})
    if not rows:
        raise RuntimeError('No matching observations downloaded; existing data was not replaced.')
    DATA_DIR.mkdir(exist_ok=True)
    with DATA_PATH.open('w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with PROVENANCE_PATH.open('w', encoding='utf-8') as file:
        json.dump({'createdAt': datetime.now(timezone.utc).isoformat(), 'yearsRequested': YEARS,
                   'timestampConvention': 'UTC hour start; OMNI Kp labels a three-hour interval',
                   'omni': omni_reports, 'locations': location_reports, 'outputRows': len(rows)},
                  file, indent=2, sort_keys=True)
    print(f'Saved {len(rows):,} records and provenance to {DATA_DIR}')


if __name__ == '__main__':
    main()
