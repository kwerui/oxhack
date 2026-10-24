"""Location-specific historical inputs for AuroraTime experiments."""

import csv
import json
from datetime import datetime, timezone
from functools import lru_cache
from math import cos, pi
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

DATA_DIR = Path(__file__).resolve().parents[1] / 'data'
CACHE_DIR = DATA_DIR / 'location_cache'
WEATHER_FIELDS = ['temperature_2m', 'cloud_cover', 'wind_speed_10m', 'pressure_msl']
EVALUATION_YEARS = (2024, 2025, 2026)


def coordinate_label(latitude: float, longitude: float) -> str:
    north_south = 'N' if latitude >= 0 else 'S'
    east_west = 'E' if longitude >= 0 else 'W'
    return f'{abs(latitude):.2f}° {north_south}, {abs(longitude):.2f}° {east_west}'


def cache_path_for(latitude: float, longitude: float, cache_dir: Path = CACHE_DIR) -> Path:
    return cache_dir / f'{latitude:.4f}_{longitude:.4f}.csv'


def cache_provenance_path(cache_path: Path) -> Path:
    return cache_path.with_suffix('.provenance.json')


def _astronomy_at(time: str, latitude: float, longitude: float) -> dict[str, float]:
    from astral import Observer
    from astral.moon import elevation as moon_elevation, phase as moon_phase
    from astral.sun import elevation as sun_elevation

    at = datetime.fromisoformat(time).replace(tzinfo=timezone.utc)
    observer = Observer(latitude=latitude, longitude=longitude)
    phase = moon_phase(at.date())
    return {
        'sun_elevation': round(sun_elevation(observer, at), 2),
        'moon_phase': round(50 * (1 - cos(2 * pi * phase / 28)), 1),
        'moon_altitude': round(moon_elevation(observer, at), 2),
    }


def _read_cache(path: Path) -> list[dict[str, str]]:
    with path.open(encoding='utf-8', newline='') as file:
        return list(csv.DictReader(file))


def _write_cache(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


@lru_cache(maxsize=1)
def _omni_by_time(data_path: str) -> dict[str, tuple[str, str, str]]:
    with Path(data_path).open(encoding='utf-8', newline='') as file:
        return {row['time']: (row['kp'], row['solar_speed'], row['bz']) for row in csv.DictReader(file)}


def _weather(latitude: float, longitude: float, year: int, end_date: str) -> list[dict[str, object]]:
    params = {'latitude': latitude, 'longitude': longitude, 'start_date': f'{year}-01-01', 'end_date': end_date, 'hourly': ','.join(WEATHER_FIELDS), 'timezone': 'UTC', 'models': 'era5'}
    with urlopen('https://archive-api.open-meteo.com/v1/archive?' + urlencode(params), timeout=60) as response:
        payload = json.load(response)
    hourly = payload.get('hourly')
    if not isinstance(hourly, dict) or not isinstance(hourly.get('time'), list):
        raise ValueError('Open-Meteo did not return hourly historical weather for this location.')
    return [{'time': time, **{field: hourly[field][index] for field in WEATHER_FIELDS}} for index, time in enumerate(hourly['time']) if all(field in hourly and hourly[field][index] is not None for field in WEATHER_FIELDS)]


def historical_rows(location: str, latitude: float, longitude: float, source_path: Path) -> list[dict[str, object]]:
    """Fetch/cache matching weather for every year required by the fixed protocol."""
    cache_path = cache_path_for(latitude, longitude)
    provenance_path = cache_provenance_path(cache_path)
    if cache_path.exists() and provenance_path.exists():
        return _read_cache(cache_path)
    omni = _omni_by_time(str(source_path))
    source_years = {datetime.fromisoformat(time).year for time in omni}
    if not set(EVALUATION_YEARS).issubset(source_years):
        raise ValueError('Source data must contain 2024 training, 2025 validation and available 2026 observations; cached 2024-only data is not used.')
    rows = []
    for year in EVALUATION_YEARS:
        year_times = [time for time in omni if datetime.fromisoformat(time).year == year]
        # A partial 2026 OMNI archive bounds the matching weather request too.
        end_date = max(year_times)[:10]
        for hour in _weather(latitude, longitude, year, end_date):
            values = omni.get(str(hour['time']))
            if values is None:
                continue
            kp, solar_speed, bz = values
            rows.append({'time': hour['time'], 'location': location, 'latitude': latitude, 'temperature': hour['temperature_2m'], 'cloud': hour['cloud_cover'], 'wind': hour['wind_speed_10m'], 'pressure': hour['pressure_msl'], 'kp': kp, 'solar_speed': solar_speed, 'bz': bz, **_astronomy_at(str(hour['time']), latitude, longitude), 'light_pollution': 0})
    if len(rows) < 500:
        raise ValueError('Too little matching historical data was available for this location.')
    _write_cache(cache_path, rows)
    with cache_provenance_path(cache_path).open('w', encoding='utf-8') as file:
        json.dump({'createdAt': datetime.now(timezone.utc).isoformat(), 'sourcePath': str(source_path),
                   'years': EVALUATION_YEARS, 'rows': len(rows), 'weatherModel': 'ERA5',
                   'timestampConvention': 'UTC'}, file, indent=2, sort_keys=True)
    return rows
