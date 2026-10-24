"""Offline, chronological comparison of AuroraTime's three classifiers.

This deliberately imports AuroraTime's example builder so the benchmark uses
the identical T+24 target, leakage safeguards and 2024/2025/2026 partitions as
the website.  It never changes the API or the public model choices.

Run from backend/ after installing requirements-benchmark.txt:
    .venv/bin/python scripts/benchmark_xgboost.py --output ../docs/xgboost_benchmark_results.md
"""

import argparse
import csv
import sys
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, confusion_matrix, f1_score, precision_score, recall_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.aurora import FEATURES, chronological_partitions, make_examples

try:
    from xgboost import XGBClassifier
    XGBOOST_ERROR = None
except Exception as error:  # Missing package and missing macOS OpenMP are both setup errors.
    XGBClassifier = None
    XGBOOST_ERROR = error


DEFAULT_LOCATIONS = {
    'Tromsø': BACKEND_DIR / 'data/location_cache/69.6500_18.9600.csv',
    'Reykjavík': BACKEND_DIR / 'data/location_cache/64.1500_-21.9400.csv',
    'Oxford (optional local cache)': BACKEND_DIR / 'data/location_cache/51.7605_-1.2628.csv',
}
F1_THRESHOLDS = np.arange(0.05, 1.0, 0.05)
FALSE_POSITIVE_RATE_BUDGET = 0.01


def require_xgboost():
    if XGBClassifier is None:
        raise SystemExit(
            'XGBoost is unavailable. Run: python -m pip install -r requirements-benchmark.txt. '
            'On macOS, also run: brew install libomp. '
            f'Original error: {XGBOOST_ERROR}'
        )


def read_rows(path: Path):
    with path.open(encoding='utf-8', newline='') as source:
        return list(csv.DictReader(source))


def matrices(samples, feature_names):
    return (
        np.array([[sample['values'][feature] for feature in feature_names] for sample in samples]),
        np.array([sample['target'] for sample in samples]),
    )


def build_variants(name, train_positive_rate):
    """Two small, predeclared imbalance options per algorithm; no broad sweep."""
    if name == 'Logistic Regression':
        return {
            'unweighted': make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, random_state=42)),
            'balanced': make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, random_state=42, class_weight='balanced')),
        }
    if name == 'Random Forest':
        common = dict(n_estimators=200, min_samples_leaf=5, max_depth=8, random_state=42, n_jobs=1)
        return {
            'unweighted': RandomForestClassifier(**common),
            'balanced': RandomForestClassifier(**common, class_weight='balanced_subsample'),
        }
    # Square-root weighting is deliberately milder than the full imbalance ratio.
    require_xgboost()
    scale = float(np.sqrt((1 - train_positive_rate) / train_positive_rate))
    common = dict(n_estimators=200, max_depth=3, learning_rate=0.05, subsample=0.8,
                  colsample_bytree=0.8, reg_lambda=1.0, random_state=42, n_jobs=1,
                  eval_metric='logloss')
    return {
        'unweighted': XGBClassifier(**common, scale_pos_weight=1.0),
        'sqrt-balanced': XGBClassifier(**common, scale_pos_weight=scale),
    }


def metrics(y_true, probabilities, threshold):
    y_true = np.asarray(y_true)
    predicted = np.asarray(probabilities) >= threshold
    tn, fp, fn, tp = confusion_matrix(y_true, predicted, labels=[0, 1]).ravel()
    return {
        'precision': float(precision_score(y_true, predicted, zero_division=0)),
        'recall': float(recall_score(y_true, predicted, zero_division=0)),
        'f1': float(f1_score(y_true, predicted, zero_division=0)),
        'brier': float(brier_score_loss(y_true, probabilities)),
        'average_precision': float(average_precision_score(y_true, probabilities)),
        'true_positive': int(tp), 'false_positive': int(fp), 'false_negative': int(fn),
        'true_negative': int(tn),
    }


def f1_threshold(y_true, probabilities):
    scores = [f1_score(y_true, np.asarray(probabilities) >= threshold, zero_division=0) for threshold in F1_THRESHOLDS]
    return float(F1_THRESHOLDS[int(np.argmax(scores))])


def false_alarm_budget_threshold(y_true, probabilities, false_positive_rate):
    """Lowest validation threshold that stays within the negative-alert budget."""
    negatives = np.asarray(probabilities)[np.asarray(y_true) == 0]
    allowed = int(np.floor(len(negatives) * false_positive_rate))
    candidates = np.unique(negatives)
    valid = [threshold for threshold in candidates if np.sum(negatives >= threshold) <= allowed]
    return float(min(valid)) if valid else float(np.nextafter(np.max(negatives), np.inf))


def select_variant(name, x_train, y_train, x_validation, y_validation):
    """Use 2025 only: maximize PR-AUC, then prefer better-calibrated scores."""
    candidates = []
    for setting, model in build_variants(name, float(y_train.mean())).items():
        model.fit(x_train, y_train)
        probabilities = model.predict_proba(x_validation)[:, 1]
        candidates.append((
            float(average_precision_score(y_validation, probabilities)),
            -float(brier_score_loss(y_validation, probabilities)), setting,
        ))
    _, _, selected = max(candidates)
    return selected


def evaluate_model(name, x_train, y_train, x_validation, y_validation, x_test, y_test):
    setting = select_variant(name, x_train, y_train, x_validation, y_validation)
    selector = build_variants(name, float(y_train.mean()))[setting]
    selector.fit(x_train, y_train)
    validation_probabilities = selector.predict_proba(x_validation)[:, 1]
    selected_f1_threshold = f1_threshold(y_validation, validation_probabilities)
    budget_threshold = false_alarm_budget_threshold(y_validation, validation_probabilities, FALSE_POSITIVE_RATE_BUDGET)

    final_model = build_variants(name, float(np.concatenate((y_train, y_validation)).mean()))[setting]
    final_model.fit(np.vstack((x_train, x_validation)), np.concatenate((y_train, y_validation)))
    test_probabilities = final_model.predict_proba(x_test)[:, 1]
    matched_test_threshold = false_alarm_budget_threshold(y_test, test_probabilities, FALSE_POSITIVE_RATE_BUDGET)
    return {
        'model': name, 'setting': setting,
        'f1_threshold': selected_f1_threshold,
        'f1_metrics': metrics(y_test, test_probabilities, selected_f1_threshold),
        'validation_budget_threshold': budget_threshold,
        'validation_budget_metrics': metrics(y_test, test_probabilities, budget_threshold),
        # This uses test labels only to compare score rankings at an identical
        # observed alarm budget. It is descriptive, not a deployment threshold.
        'matched_test_threshold': matched_test_threshold,
        'matched_test_metrics': metrics(y_test, test_probabilities, matched_test_threshold),
    }


def baseline(y_train, y_test):
    prevalence = float(np.mean(y_train))
    score = np.full(len(y_test), prevalence)
    return {
        'model': 'Training-prevalence / always WAIT', 'setting': 'none',
        'f1_threshold': 1.0, 'f1_metrics': metrics(y_test, score, 1.0),
        'validation_budget_threshold': 1.0, 'validation_budget_metrics': metrics(y_test, score, 1.0),
        'matched_test_threshold': 1.0, 'matched_test_metrics': metrics(y_test, score, 1.0),
    }


def markdown(results, features):
    lines = [
        '# AuroraTime XGBoost benchmark', '',
        '**Status:** exploratory comparison. The 2026 historical dataset had already been inspected before this benchmark, so it is not a fresh, unbiased final test.', '',
        '**Reproduce:** from `backend/`, install `python -m pip install -r requirements-benchmark.txt` (on macOS also `brew install libomp`), then run `python scripts/benchmark_xgboost.py --output ../docs/xgboost_benchmark_results.md`.', '',
        f'**Protocol:** 24-hour proxy from AuroraTime; 2024 train, 2025 validation, available 2026 test; variables: {", ".join(features)}.', '',
        'Settings are selected on 2025 from only two predeclared imbalance options per model by PR-AUC (Brier breaks ties). The displayed final models are then refit on 2024–2025. `F1 threshold` is selected only on 2025.', '',
    ]
    for location, result in results.items():
        lines += [f'## {location}', '',
                  f"Examples: train {result['counts']['train']} ({result['counts']['train_positive']} positive), validation {result['counts']['validation']} ({result['counts']['validation_positive']} positive), test {result['counts']['test']} ({result['counts']['test_positive']} positive).", '',
                  '### F1-selected operating point', '',
                  '| Model | 2025 setting | Threshold | Precision | Recall | F1 | Brier | PR-AUC | TP | FP | FN |',
                  '| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
        for run in result['runs']:
            value = run['f1_metrics']
            lines.append(f"| {run['model']} | {run['setting']} | {run['f1_threshold']:.3f} | {value['precision']:.3f} | {value['recall']:.3f} | {value['f1']:.3f} | {value['brier']:.4f} | {value['average_precision']:.3f} | {value['true_positive']} | {value['false_positive']} | {value['false_negative']} |")
        lines += ['', '### Matched observed false-alarm budget: at most 1% of 2026 negatives', '',
                  'Thresholds in this table are calculated from 2026 outcomes solely to compare ranking at the same measured false-alarm budget. They are descriptive, **not** deployable thresholds or a fresh test result.', '',
                  '| Model | Threshold | Precision | Recall | F1 | Brier | PR-AUC | TP | FP | FN |',
                  '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
        for run in result['runs']:
            value = run['matched_test_metrics']
            lines.append(f"| {run['model']} | {run['matched_test_threshold']:.3f} | {value['precision']:.3f} | {value['recall']:.3f} | {value['f1']:.3f} | {value['brier']:.4f} | {value['average_precision']:.3f} | {value['true_positive']} | {value['false_positive']} | {value['false_negative']} |")
        lines.append('')
    lines += ['## Reading the result', '',
              'Prefer a model only if it finds materially more true positives at the matched 1% false-positive-rate budget without materially worse precision or calibration. The prevalence/always-WAIT baseline has zero false alarms and zero detections; it is included to make the cost of alerts explicit. A practical deployment threshold must remain selected on validation data: in this run those validation thresholds did not transfer stably to 2026, another reason not to integrate yet. Do not use the 2026 comparison as a final model-selection claim: reserve a later, not-yet-inspected period or use rolling temporal backtests before integration.', '',
              '## Recommendation', '',
              'Keep the existing Logistic Regression and Random Forest models; **do not replace Random Forest with XGBoost**. XGBoost did not improve any location consistently: it found no Tromsø positives at the matched 1% false-alarm budget, trailed Logistic Regression in Reykjavík, and trailed or tied the existing models in Oxford. Its validation-selected operating points also produced many false alarms or zero detections. Revisit only with a new, uninspected period and operationally available predictors.', '']
    return '\n'.join(lines)


def run(location_paths, features):
    results = {}
    for location, path in location_paths.items():
        if not path.exists():
            continue
        partitions = chronological_partitions(make_examples(read_rows(path)))
        x_train, y_train = matrices(partitions['train'], features)
        x_validation, y_validation = matrices(partitions['validation'], features)
        x_test, y_test = matrices(partitions['test'], features)
        if any(len(np.unique(labels)) < 2 for labels in (y_train, y_validation, y_test)):
            raise ValueError(f'{location} lacks both target classes in every chronological partition.')
        runs = [baseline(y_train, y_test)]
        runs += [evaluate_model(name, x_train, y_train, x_validation, y_validation, x_test, y_test)
                 for name in ('Logistic Regression', 'Random Forest', 'XGBoost')]
        results[location] = {'counts': {
            'train': len(y_train), 'train_positive': int(y_train.sum()),
            'validation': len(y_validation), 'validation_positive': int(y_validation.sum()),
            'test': len(y_test), 'test_positive': int(y_test.sum()),
        }, 'runs': runs}
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--features', default=','.join(FEATURES), help='Comma-separated AuroraTime feature names.')
    parser.add_argument('--output', type=Path, help='Optional Markdown output path.')
    parser.add_argument('--skip-oxford', action='store_true', help='Benchmark only Tromsø and Reykjavík.')
    args = parser.parse_args()
    features = args.features.split(',')
    unknown = set(features) - set(FEATURES)
    if unknown:
        raise SystemExit(f'Unknown AuroraTime features: {", ".join(sorted(unknown))}')
    require_xgboost()
    paths = dict(DEFAULT_LOCATIONS)
    if args.skip_oxford:
        paths.pop('Oxford (optional local cache)')
    report = markdown(run(paths, features), features)
    print(report)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding='utf-8')


if __name__ == '__main__':
    main()
