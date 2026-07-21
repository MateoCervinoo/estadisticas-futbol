import pytest

from app.sync import _compute_xg_from_metrics


def test_compute_xg_returns_none_when_metrics_are_missing():
    metrics = {
        "shots_on_goal": {"home": None, "away": None},
        "shots_inside_box": {"home": None, "away": None},
        "shots_outside_box": {"home": None, "away": None},
    }

    assert _compute_xg_from_metrics(metrics) == (None, None)


def test_compute_xg_uses_complete_shot_metrics():
    metrics = {
        "shots_inside_box": {"home": 8, "away": 3},
        "shots_outside_box": {"home": 4, "away": 2},
    }

    home_xg, away_xg = _compute_xg_from_metrics(metrics)

    assert home_xg == pytest.approx(1.2)
    assert away_xg == pytest.approx(0.47)
