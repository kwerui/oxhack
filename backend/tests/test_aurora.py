"""Small synthetic fixtures test program logic; never shown as scientific results."""

import csv
from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException

from app.aurora import FEATURES, ModelRequest, evaluate_model, make_examples, viewing_proxy
from scripts.download_aurora_data import parse_omni_line


def fixture_rows():
    rows = []
    for location, latitude, bortle in [('Tromsø', 69.65, 5), ('Reykjavík', 64.15, 6)]:
        for hour in range(1000):
            rows.append({
                'time': (datetime(2024, 1, 1) + timedelta(hours=hour)).isoformat(timespec='minutes'),
                'location': location,
                'latitude': latitude,
                'temperature': -6 + hour % 19,
                'cloud': hour * 11 % 100,
                'wind': 3 + hour % 22,
                'pressure': 1000 + hour % 40,
                'kp': 5.0 if hour % 13 < 7 else 2.0,
                'solar_speed': 380 + hour % 150,
                'bz': -5 if hour % 7 < 4 else 3,
                'sun_elevation': -18 if hour % 24 >= 17 or hour % 24 <= 5 else 15,
                'moon_phase': hour % 100,
                'moon_altitude': -20 + hour % 70,
                'light_pollution': bortle,
            })
    return rows


def write_fixture(tmp_path):
    path = tmp_path / 'hours.csv'
    rows = fixture_rows()
    with path.open('w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=['time', 'location', *FEATURES])
        writer.writeheader()
        writer.writerows(rows)
    return path


def test_proxy_uses_kp_clouds_and_sun():
    sky = {'kp': 5, 'cloud': 10, 'sun_elevation': -12}
    assert viewing_proxy(sky) == 1
    assert viewing_proxy({**sky, 'cloud': 90}) == 0
    assert viewing_proxy({**sky, 'sun_elevation': 15}) == 0
    assert viewing_proxy({**sky, 'kp': 1}) == 0


def test_features_do_not_use_future_weather(tmp_path):
    rows = fixture_rows()
    samples = make_examples(rows)
    first = next(sample for sample in samples if sample['location'] == 'Tromsø')
    assert first['time'] == '2024-01-01T03:00'
    assert first['futureTime'] == '2024-01-01T06:00'
    assert first['values']['cloud'] == float(rows[3]['cloud'])
    assert first['values']['kp'] == float(rows[0]['kp'])  # previous completed interval
    assert first['values']['sun_elevation'] == float(rows[6]['sun_elevation'])  # known astronomy
    assert first['target'] == viewing_proxy(rows[6])


def test_model_scores_unseen_hours_from_selected_city(tmp_path):
    result = evaluate_model(ModelRequest(features=['cloud', 'kp', 'bz', 'moon_altitude'], location='Tromsø'), write_fixture(tmp_path))
    assert result['trainCount'] > 100
    assert result['testCount'] > 50
    assert result['trainUntil'] < result['testFrom']
    assert result['features'] == ['cloud', 'kp', 'bz', 'moon_altitude']
    assert len(result['hours']) == 24
    assert 0 <= result['metrics']['brier'] <= 1
    assert 0 <= result['metrics']['baselineBrier'] <= 1


def test_every_variable_is_selectable(tmp_path):
    result = evaluate_model(ModelRequest(features=list(FEATURES), location='Reykjavík'), write_fixture(tmp_path))
    assert len(result['features']) == 12
    assert result['location'] == 'Reykjavík'


def test_unknown_variable_rejected(tmp_path):
    with pytest.raises(HTTPException) as error:
        evaluate_model(ModelRequest(features=['mystery']), write_fixture(tmp_path))
    assert error.value.status_code == 422


def test_omni_parses_both_supported_record_lengths():
    parts = ['0'] * 57
    parts[0:3] = ['2024', '1', '0']
    parts[16] = '-4.2'
    parts[24] = '440'
    parts[38] = '47'
    for length in (56, 57):
        record = parse_omni_line(' '.join(parts[:length]))
        assert record == ('2024-01-01T00:00', (4.7, 440.0, -4.2))
    parts[16] = '999.9'
    assert parse_omni_line(' '.join(parts)) is None
