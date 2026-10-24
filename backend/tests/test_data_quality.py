"""Regression tests for source parsing, provenance and chronological evaluation."""

from datetime import datetime, timedelta
import csv

from app.aurora import chronological_partitions, make_examples
from app import location_data
from scripts.download_aurora_data import parse_omni_line, validate_omni_readings


def _omni_line(length: int, *, bz: str = '-4.2', speed: str = '440', kp10: str = '47') -> str:
    parts = ['0'] * length
    parts[0:3] = ['2024', '1', '0']
    parts[16], parts[24], parts[38] = bz, speed, kp10
    return ' '.join(parts)


def test_omni_parser_supports_verified_55_and_extended_layouts():
    expected = ('2024-01-01T00:00', (4.7, 440.0, -4.2))
    assert parse_omni_line(_omni_line(55)) == expected
    assert parse_omni_line(_omni_line(56)) == expected
    assert parse_omni_line(_omni_line(57)) == expected


def test_omni_parser_drops_documented_fill_values():
    assert parse_omni_line(_omni_line(55, bz='999.9')) is None
    assert parse_omni_line(_omni_line(55, speed='9999')) is None
    assert parse_omni_line(_omni_line(55, kp10='99')) is None


def test_omni_coverage_records_missing_hours_without_assuming_completeness():
    readings = {
        '2024-01-01T00:00': (1.0, 400.0, -2.0),
        '2024-01-01T02:00': (1.3, 410.0, -3.0),
    }
    report = validate_omni_readings(readings, 2024)
    assert report['expectedHours'] == 8784
    assert report['acceptedHours'] == 2
    assert report['missingHours'] == 8782
    assert report['firstMissingHour'] == '2024-01-01T01:00'


def _row(at: datetime):
    return {
        'time': at.isoformat(timespec='minutes'), 'location': 'test', 'latitude': 60,
        'temperature': 0, 'cloud': 20, 'wind': 5, 'pressure': 1000, 'kp': 5,
        'solar_speed': 400, 'bz': -2, 'sun_elevation': -10, 'moon_phase': 50,
        'moon_altitude': 10, 'light_pollution': 3,
    }


def test_chronological_partitions_keep_target_timestamps_out_of_later_sets():
    rows = []
    for year in (2024, 2025, 2026):
        start = datetime(year, 1, 1)
        rows.extend(_row(start + timedelta(hours=hour)) for hour in range(250))
    partitions = chronological_partitions(make_examples(rows))
    assert {sample['time'][:4] for sample in partitions['train']} == {'2024'}
    assert {sample['time'][:4] for sample in partitions['validation']} == {'2025'}
    assert {sample['time'][:4] for sample in partitions['test']} == {'2026'}
    assert max(sample['futureTime'] for sample in partitions['train']) < '2025-01-01T00:00'
    assert max(sample['futureTime'] for sample in partitions['validation']) < '2026-01-01T00:00'


def test_location_cache_requires_provenance_before_reuse(tmp_path, monkeypatch):
    source = tmp_path / 'omni.csv'
    cache = tmp_path / 'location.csv'
    rows = []
    for year in (2024, 2025, 2026):
        for hour in range(200):
            rows.append({'time': (datetime(year, 1, 1) + timedelta(hours=hour)).isoformat(timespec='minutes'),
                         'kp': '3', 'solar_speed': '400', 'bz': '-2'})
    with source.open('w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    weather = [{'time': row['time'], 'temperature_2m': 0, 'cloud_cover': 10,
                'wind_speed_10m': 5, 'pressure_msl': 1000} for row in rows]
    monkeypatch.setattr(location_data, 'cache_path_for', lambda *_: cache)
    monkeypatch.setattr(location_data, '_weather', lambda _lat, _lon, year, _end: [row for row in weather if row['time'].startswith(str(year))])
    # A legacy CSV without matching provenance must not be silently reused.
    cache.write_text('time,location\n2024-01-01T00:00,stale\n', encoding='utf-8')
    result = location_data.historical_rows('test', 60, 10, source)
    assert len(result) == 600
    assert location_data.cache_provenance_path(cache).exists()
    monkeypatch.setattr(location_data, '_weather', lambda *_: (_ for _ in ()).throw(AssertionError('cache miss')))
    assert len(location_data.historical_rows('test', 60, 10, source)) == 600
