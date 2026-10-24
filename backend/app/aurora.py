"""A small, explainable experiment: predict suitable aurora VIEWING CONDITIONS.

Use the observations available at hour T to estimate conditions at T + 24 hours.
The outcome label is a transparent RULE, not a confirmed aurora sighting.
"""

import csv
from datetime import datetime, timedelta
from math import isfinite
from pathlib import Path
from typing import Literal

import numpy as np
from fastapi import HTTPException
from pydantic import BaseModel, Field
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import brier_score_loss, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .location_data import coordinate_label, historical_rows

DATA_PATH = Path(__file__).resolve().parents[1] / 'data' / 'aurora_hours.csv'
HOURS_AHEAD = 24
LOCATION_NAMES = {'Tromsø', 'Reykjavík'}

# Keys match the frontend checkboxes and columns of the downloaded CSV.
FEATURES = {
    'temperature': 'Temperature (°C)',
    'cloud': 'Cloud cover (%)',
    'wind': 'Wind speed (km/h)',
    'pressure': 'Sea-level pressure (hPa)',
    'kp': 'Geomagnetic Kp index',
    'solar_speed': 'Solar wind speed (km/s)',
    'latitude': 'Geographic latitude (°)',
    'bz': 'Interplanetary magnetic field Bz (nT)',
    'sun_elevation': 'Sun elevation (°)',
    'moon_phase': 'Moon illuminated fraction (%)',
    'moon_altitude': 'Moon altitude (°)',
    'light_pollution': 'Assumed Bortle class (1–9)',
}

# The sun and moon positions 24 hours from now can be calculated TODAY,
# without knowing future weather. They are safe future-time inputs.
KNOWN_IN_ADVANCE = {'sun_elevation', 'moon_phase', 'moon_altitude'}


class LocationRequest(BaseModel):
    location: str = 'Tromsø'
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class ModelRequest(LocationRequest):
    features: list[str] = Field(min_length=1, max_length=len(FEATURES))
    model: Literal['logistic_regression', 'random_forest', 'compare'] = 'logistic_regression'


def read_observations(path=DATA_PATH):
    if not path.exists():
        raise HTTPException(
            status_code=503,
            detail="Historical data missing. In backend/, run: python scripts/download_aurora_data.py",
        )
    with path.open(encoding='utf-8', newline='') as file:
        return list(csv.DictReader(file))


def viewing_proxy(row):
    """This tests an observable CONDITION, not an actual aurora sighting."""
    return int(
        float(row['kp']) >= 4
        and float(row['cloud']) <= 40
        and float(row['sun_elevation']) <= -6
    )


def make_examples(rows):
    """Pair T with T+24 without leaking future observations into inputs or labels."""
    lookup = {(row['location'], row['time']): row for row in rows}
    examples = []

    for row in rows:
        current_time = datetime.fromisoformat(row['time'])
        later_time = (current_time + timedelta(hours=HOURS_AHEAD)).isoformat(timespec='minutes')
        earlier_time = (current_time - timedelta(hours=3)).isoformat(timespec='minutes')
        target_kp_time = (current_time + timedelta(hours=HOURS_AHEAD - 3)).isoformat(timespec='minutes')
        later = lookup.get((row['location'], later_time))
        older = lookup.get((row['location'], earlier_time))
        completed_target_kp = lookup.get((row['location'], target_kp_time))
        if later is None or older is None or completed_target_kp is None:
            continue

        try:
            inputs = {feature: float(row[feature]) for feature in FEATURES}
            # Input Kp is the interval completed by T; it never uses an interval
            # still running at the prediction issue time.
            inputs['kp'] = float(older['kp'])
            # Positions of the Sun and Moon at T+24 are predictable in advance.
            for feature in KNOWN_IN_ADVANCE:
                inputs[feature] = float(later[feature])
            # The target Kp is the completed [T+21, T+24) block, not the block
            # beginning at T+24 and therefore extending beyond the target time.
            target = viewing_proxy({**later, 'kp': completed_target_kp['kp']})
        except (ValueError, KeyError, TypeError):
            continue
        if not all(isfinite(number) for number in inputs.values()):
            continue
        examples.append({
            'time': row['time'],
            'futureTime': later_time,
            'targetKpTime': target_kp_time,
            'location': row['location'],
            'values': inputs,
            'target': target,
        })
    return sorted(examples, key=lambda sample: (sample['time'], sample['location']))


def chronological_partitions(examples):
    """Use calendar years and keep every T+24 target inside its own partition."""
    partitions = {'train': [], 'validation': [], 'test': []}
    year_to_partition = {2024: 'train', 2025: 'validation', 2026: 'test'}
    for sample in examples:
        source_year = datetime.fromisoformat(sample['time']).year
        target_year = datetime.fromisoformat(sample['futureTime']).year
        partition = year_to_partition.get(source_year)
        if partition and source_year == target_year:
            partitions[partition].append(sample)
    return partitions


def build_model(model_name):
    """Keep each algorithm definition short and reproducible."""
    if model_name == 'logistic_regression':
        # Scaling is fit only on the training hours inside this pipeline.
        return make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
    return RandomForestClassifier(n_estimators=120, min_samples_leaf=2, random_state=42, n_jobs=1)


def choose_threshold(y_true, probabilities):
    """Choose an F1 threshold only on validation data; retain 0.5 for a tie."""
    candidates = np.arange(0.05, 1.0, 0.05)
    scores = [f1_score(y_true, probabilities >= threshold, zero_division=0) for threshold in candidates]
    return float(candidates[int(np.argmax(scores))]) if len(candidates) else 0.5


def _metrics(y_true, probabilities, threshold, training_prevalence):
    predicted_classes = (probabilities >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, predicted_classes, labels=[0, 1]).ravel()
    baseline = np.full(len(y_true), training_prevalence)
    auc = float(roc_auc_score(y_true, probabilities)) if len(np.unique(y_true)) == 2 else None
    return {
        'threshold': round(float(threshold), 2),
        'brier': round(float(brier_score_loss(y_true, probabilities)), 4),
        'baselineBrier': round(float(brier_score_loss(y_true, baseline)), 4),
        'precision': round(float(precision_score(y_true, predicted_classes, zero_division=0)), 3),
        'recall': round(float(recall_score(y_true, predicted_classes, zero_division=0)), 3),
        'f1': round(float(f1_score(y_true, predicted_classes, zero_division=0)), 3),
        'auc': round(auc, 3) if auc is not None else None,
        'positiveRate': round(float(y_true.mean()) * 100, 3),
        'positiveCount': int(y_true.sum()), 'negativeCount': int(len(y_true) - y_true.sum()),
        'truePositive': int(tp), 'falsePositive': int(fp), 'trueNegative': int(tn), 'falseNegative': int(fn),
    }


def evaluate_run(model_name, x_train, y_train, x_validation, y_validation, x_test, y_test, test):
    """Select a threshold on 2025, then evaluate once on untouched 2026 hours."""
    model = build_model(model_name)
    model.fit(x_train, y_train)
    threshold = choose_threshold(y_validation, model.predict_proba(x_validation)[:, 1])
    # Validation labels may be used after selection to train the final fixed model.
    model.fit(np.vstack((x_train, x_validation)), np.concatenate((y_train, y_validation)))
    probabilities = model.predict_proba(x_test)[:, 1]

    names = {
        'logistic_regression': 'Logistic Regression',
        'random_forest': 'Random Forest',
    }
    return {
        'key': model_name,
        'name': names[model_name],
        'metrics': _metrics(y_test, probabilities, threshold, float(y_train.mean())),
        'hours': [
            {
                'hour': sample['futureTime'],
                'probability': round(float(probability) * 100, 1),
                'observedProxy': sample['target'],
            }
            for sample, probability in zip(test[-24:], probabilities[-24:])
        ],
    }


def comparison_explanation(runs):
    """Describe only measured differences; never declare a universal winner."""
    if len(runs) == 1:
        return 'These scores describe this model on later historical hours it did not train on.'

    logistic, forest = runs
    statements = []
    if forest['metrics']['recall'] > logistic['metrics']['recall']:
        statements.append('Random Forest found more suitable historical periods (higher recall).')
    elif logistic['metrics']['recall'] > forest['metrics']['recall']:
        statements.append('Logistic Regression found more suitable historical periods (higher recall).')
    if forest['metrics']['brier'] < logistic['metrics']['brier']:
        statements.append('Random Forest had lower probability error (Brier score).')
    elif logistic['metrics']['brier'] < forest['metrics']['brier']:
        statements.append('Logistic Regression had lower probability error (Brier score).')
    return ' '.join(statements) or 'The models had the same recall and probability error on this historical test.'


def location_rows(request: LocationRequest, data_path=DATA_PATH):
    """Resolve exactly the requested location; never substitute a preset city."""
    has_coordinates = request.latitude is not None or request.longitude is not None
    if has_coordinates and (request.latitude is None or request.longitude is None):
        raise HTTPException(status_code=422, detail='Enter both latitude and longitude.')
    if request.location not in LOCATION_NAMES and not has_coordinates:
        raise HTTPException(status_code=422, detail='Select a search result or enter both coordinates.')

    if has_coordinates:
        try:
            rows = historical_rows(request.location or coordinate_label(request.latitude, request.longitude), request.latitude, request.longitude, data_path)
        except (OSError, ValueError) as problem:
            raise HTTPException(status_code=503, detail=f'Could not prepare historical data for this location: {problem}') from problem
        location_name = request.location or coordinate_label(request.latitude, request.longitude)
    else:
        rows = [row for row in read_observations(data_path) if row['location'] == request.location]
        location_name = request.location
    return rows, location_name, has_coordinates


def prepare_location(request: LocationRequest, data_path=DATA_PATH):
    """Warm/verify a location dataset before a model run so UI states are honest."""
    rows, location_name, has_coordinates = location_rows(request, data_path)
    if not rows:
        raise HTTPException(status_code=503, detail='No matching historical observations were available for the requested location.')
    return {
        'location': location_name,
        'coordinates': {'latitude': request.latitude, 'longitude': request.longitude} if has_coordinates else None,
        'historicalRowCount': len(rows),
    }


def evaluate_model(request: ModelRequest, data_path=DATA_PATH):
    chosen = list(dict.fromkeys(request.features))
    if any(feature not in FEATURES for feature in chosen):
        raise HTTPException(status_code=422, detail='Unknown input variable selected.')

    rows, location_name, has_coordinates = location_rows(request, data_path)

    # Location is fixed before splitting, so both models learn from the same place and hours.
    examples = make_examples(rows)
    partitions = chronological_partitions(examples)
    train, validation, test = partitions['train'], partitions['validation'], partitions['test']
    if min(len(train), len(validation), len(test)) < 50:
        raise HTTPException(status_code=422, detail='Need matching 2024 training, 2025 validation and available 2026 test data. Run the multi-year downloader; no old-data fallback is used.')

    x_train = np.array([[sample['values'][key] for key in chosen] for sample in train])
    y_train = np.array([sample['target'] for sample in train])
    x_validation = np.array([[sample['values'][key] for key in chosen] for sample in validation])
    y_validation = np.array([sample['target'] for sample in validation])
    x_test = np.array([[sample['values'][key] for key in chosen] for sample in test])
    y_test = np.array([sample['target'] for sample in test])
    if len(np.unique(y_train)) < 2 or len(np.unique(y_validation)) < 2:
        raise HTTPException(status_code=422, detail='Training data has only one outcome. Need more history.')

    selected_models = (
        ['logistic_regression', 'random_forest']
        if request.model == 'compare'
        else [request.model]
    )
    runs = [evaluate_run(name, x_train, y_train, x_validation, y_validation, x_test, y_test, test) for name in selected_models]
    primary = runs[0]
    warnings = []
    if 'latitude' in chosen or 'light_pollution' in chosen:
        warnings.append('Latitude and assumed light pollution are constants within one location, so they cannot explain hourly variation.')
    if min(int(y_train.sum()), int(y_validation.sum()), int(y_test.sum())) < 25:
        warnings.append('At least one period has fewer than 25 positive proxy labels; precision, recall and threshold estimates are unstable.')

    return {
        'location': location_name,
        'coordinates': {'latitude': request.latitude, 'longitude': request.longitude} if has_coordinates else None,
        'features': chosen,
        'horizonHours': HOURS_AHEAD,
        'label': '24-hour viewing-conditions proxy: completed Kp interval ≥ 4, cloud ≤ 40%, Sun ≤ −6°',
        'model': primary['name'],
        'modelSelection': request.model,
        'trainCount': len(train),
        'validationCount': len(validation),
        'testCount': len(test),
        'trainFrom': train[0]['time'],
        'trainUntil': train[-1]['futureTime'],
        'validationFrom': validation[0]['time'],
        'validationUntil': validation[-1]['futureTime'],
        'testFrom': test[0]['time'],
        'testUntil': test[-1]['time'],
        'metrics': primary['metrics'],
        'hours': primary['hours'],
        'modelRuns': runs,
        'comparisonExplanation': comparison_explanation(runs),
        'warnings': warnings + (['This location uses a freshly assembled, location-specific multi-year backtest. Light pollution is not included because no measured worldwide source is bundled.'] if has_coordinates else []),
        'limitations': (
            'This is a historical test of a rule-defined conditions proxy, not confirmed aurora '
            'sightings or live forecasting. The target only uses Kp, cloud cover and Sun elevation. '
            'Thresholds are selected on 2025 and 2026 is evaluated once. Moon, temperature and wind may influence viewing comfort; light pollution is an '
            'assumed Bortle class (not measured). Location is geographic rather than geomagnetic '
            'latitude. NASA hourly data and weather reanalysis are not real-time forecasts.'
        ),
    }
