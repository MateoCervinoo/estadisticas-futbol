from __future__ import annotations

import importlib

import pandas as pd
import pytest


backtest = importlib.import_module("entrenador.07_backtest")


def test_calibration_ece_uses_confidence_not_bin_count():
    result = backtest.calibration_ece(
        confidences=[0.2, 0.8],
        outcomes=[0.0, 1.0],
        n_bins=2,
    )

    assert result["counts"] == [1, 1]
    assert result["observed_freqs"] == [0.0, 1.0]
    assert result["avg_confidences"] == [0.2, 0.8]
    assert result["ece"] == pytest.approx(0.2)


def test_compute_probability_metrics_for_1x2_predictions():
    df = pd.DataFrame(
        [
            {"local_name": "A", "visit_name": "B", "goles_local": 2, "goles_visitante": 0},
            {"local_name": "C", "visit_name": "D", "goles_local": 1, "goles_visitante": 1},
        ]
    )

    def predictor(row):
        if row["local_name"] == "A":
            return {"home": 0.7, "draw": 0.2, "away": 0.1}
        return {"home": 0.2, "draw": 0.6, "away": 0.2}

    metrics = backtest.compute_probability_metrics(df, predictor, n_bins=5)

    assert metrics["n"] == 2
    assert metrics["skipped"] == 0
    assert metrics["accuracy_1x2"] == 1.0
    assert metrics["log_loss"] > 0
    assert metrics["brier_score"] > 0
    assert metrics["calibration"]["ece"] is not None


def test_temporal_split_preserves_order_and_cutoff():
    df = pd.DataFrame(
        {
            "fecha_utc": pd.date_range("2024-01-01", periods=20, tz="UTC"),
            "goles_local": [1] * 20,
            "goles_visitante": [0] * 20,
        }
    )

    train_df, test_df, cutoff = backtest._temporal_split(df, test_fraction=0.25, min_train=10)

    assert len(train_df) == 15
    assert len(test_df) == 5
    assert train_df["fecha_utc"].max() < test_df["fecha_utc"].min()
    assert cutoff == test_df["fecha_utc"].min().isoformat()
