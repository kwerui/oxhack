"""Small guardrails for the offline XGBoost benchmark helpers."""

import subprocess
import sys
from pathlib import Path

from scripts.benchmark_xgboost import false_alarm_budget_threshold, metrics


def test_budget_threshold_limits_validation_negative_alert_rate():
    # Two of four negative examples may alert at a 50% false-positive budget.
    threshold = false_alarm_budget_threshold(
        y_true=[0, 0, 0, 0, 1],
        probabilities=[0.1, 0.2, 0.8, 0.9, 0.95],
        false_positive_rate=0.5,
    )
    result = metrics(
        y_true=[0, 0, 0, 0, 1],
        probabilities=[0.1, 0.2, 0.8, 0.9, 0.95],
        threshold=threshold,
    )

    assert result['false_positive'] <= 2
    assert result['true_positive'] == 1


def test_script_runs_from_backend_directory():
    backend = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, 'scripts/benchmark_xgboost.py', '--help'],
        cwd=backend, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0
    assert 'Offline, chronological comparison' in result.stdout
