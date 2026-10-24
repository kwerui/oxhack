"""A small, explainable experiment: predict suitable aurora VIEWING CONDITIONS.

Use the observations available at hour T to estimate conditions at T + 3 hours.
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
from sklearn.metrics import brier_score_loss, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

DATA_PATH = Path(__file__).resolve().parents[1] / 'data' / 'aurora_hours.csv'
HOURS_AHEAD = 3
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

# The sun and moon positions three hours from now can be calculated TODAY,
# without knowing future weather. They are safe future-time inputs.
KNOWN_IN_ADVANCE = {'sun_elevation', 'moon_phase', 'moon_altitude'}


class ModelRequest(BaseModel):
    features: list[str] = Field(min_length=1, max_length=len(FEATURES))
    location: str = 'Tromsø'
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
    """Pair each hour T with T+3; NEVER feed future weather/Kp into the model."""
    lookup = {(row['location'], row['time']): row for row in rows}
    examples = []

    for row in rows:
        current_time = datetime.fromisoformat(row['time'])
        later_time = (current_time + timedelta(hours=HOURS_AHEAD)).isoformat(timespec='minutes')
        earlier_time = (current_time - timedelta(hours=3)).isoformat(timespec='minutes')
        later = lookup.get((row['location'], later_time))
        older = lookup.get((row['location'], earlier_time))
        if later is None or older is None:
            continue

        try:
            inputs = {feature: float(row[feature]) for feature in FEATURES}
            # Kp summarizes a completed three-hour interval, not an instant.
            # Use an earlier reading, avoiding the ongoing incomplete interval.
            inputs['kp'] = float(older['kp'])
            # Positions of the Sun and Moon at T+3 are predictable in advance.
            for feature in KNOWN_IN_ADVANCE:
                inputs[feature] = float(later[feature])
            target = viewing_proxy(later)
        except (ValueError, KeyError, TypeError):
            continue
        if not all(isfinite(number) for number in inputs.values()):
            continue
        examples.append({
            'time': row['time'],
            'futureTime': later_time,
            'location': row['location'],
            'values': inputs,
            'target': target,
        })
    return sorted(examples, key=lambda sample: (sample['time'], sample['location']))


def build_model(model_name):
    """Keep each algorithm definition short and reproducible."""
    if model_name == 'logistic_regression':
        # Scaling is fit only on the training hours inside this pipeline.
        return make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
    return RandomForestClassifier(n_estimators=120, min_samples_leaf=2, random_state=42, n_jobs=1)


def evaluate_run(model_name, x_train, y_train, x_test, y_test, test):
    """Fit one model and calculate metrics from the same held-out hours."""
    model = build_model(model_name)
    model.fit(x_train, y_train)
    probabilities = model.predict_proba(x_test)[:, 1]
    predicted_classes = (probabilities >= 0.5).astype(int)
    baseline = np.full(len(y_test), float(y_train.mean()))
    auc = float(roc_auc_score(y_test, probabilities)) if len(np.unique(y_test)) == 2 else None

    names = {
        'logistic_regression': 'Logistic Regression',
        'random_forest': 'Random Forest',
    }
    return {
        'key': model_name,
        'name': names[model_name],
        'metrics': {
            'brier': round(float(brier_score_loss(y_test, probabilities)), 4),
            'baselineBrier': round(float(brier_score_loss(y_test, baseline)), 4),
            'precision': round(float(precision_score(y_test, predicted_classes, zero_division=0)), 3),
            'recall': round(float(recall_score(y_test, predicted_classes, zero_division=0)), 3),
            'f1': round(float(f1_score(y_test, predicted_classes, zero_division=0)), 3),
            'auc': round(auc, 3) if auc is not None else None,
            'positiveRate': round(float(y_test.mean()) * 100, 1),
            'positiveCount': int(y_test.sum()),
            'negativeCount': int(len(y_test) - y_test.sum()),
        },
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


def evaluate_model(request: ModelRequest, data_path=DATA_PATH):
    chosen = list(dict.fromkeys(request.features))
    if any(feature not in FEATURES for feature in chosen):
        raise HTTPException(status_code=422, detail='Unknown input variable selected.')
    if request.location not in LOCATION_NAMES:
        raise HTTPException(status_code=422, detail='Choose Tromsø or Reykjavík.')

    # Location is fixed before splitting, so both models learn from the same city and hours.
    examples = [sample for sample in make_examples(read_observations(data_path))
                if sample['location'] == request.location]
    if len(examples) < 200:
        raise HTTPException(status_code=422, detail='Not enough historical hourly records for evaluation.')

    # Split by TIME, not at random: use the earlier 75% to train and later 25% to test.
    times = sorted({sample['time'] for sample in examples})
    cutoff = datetime.fromisoformat(times[int(0.75 * len(times))])
    gap = cutoff - timedelta(hours=HOURS_AHEAD)
    train = [sample for sample in examples if datetime.fromisoformat(sample['time']) < gap]
    test = [sample for sample in examples if datetime.fromisoformat(sample['time']) >= cutoff]
    if len(train) < 100 or len(test) < 50:
        raise HTTPException(status_code=422, detail='Not enough chronological test records.')

    x_train = np.array([[sample['values'][key] for key in chosen] for sample in train])
    y_train = np.array([sample['target'] for sample in train])
    x_test = np.array([[sample['values'][key] for key in chosen] for sample in test])
    y_test = np.array([sample['target'] for sample in test])
    if len(np.unique(y_train)) < 2:
        raise HTTPException(status_code=422, detail='Training data has only one outcome. Need more history.')

    selected_models = (
        ['logistic_regression', 'random_forest']
        if request.model == 'compare'
        else [request.model]
    )
    runs = [evaluate_run(name, x_train, y_train, x_test, y_test, test) for name in selected_models]
    primary = runs[0]

    return {
        'location': request.location,
        'features': chosen,
        'label': '3-hour viewing-conditions proxy: Kp ≥ 4, cloud ≤ 40%, Sun ≤ −6°',
        'model': primary['name'],
        'modelSelection': request.model,
        'trainCount': len(train),
        'testCount': len(test),
        'trainFrom': train[0]['time'],
        'trainUntil': gap.isoformat(timespec='minutes'),
        'testFrom': cutoff.isoformat(timespec='minutes'),
        'testUntil': test[-1]['time'],
        'metrics': primary['metrics'],
        'hours': primary['hours'],
        'modelRuns': runs,
        'comparisonExplanation': comparison_explanation(runs),
        'limitations': (
            'This is a historical test of a rule-defined conditions proxy, not confirmed aurora '
            'sightings or live forecasting. The target only uses Kp, cloud cover and Sun elevation. '
            'Moon, temperature and wind may influence viewing comfort; light pollution is an '
            'assumed Bortle class (not measured). Location is geographic rather than geomagnetic '
            'latitude. NASA hourly data and weather reanalysis are not real-time forecasts.'
        ),
    }
