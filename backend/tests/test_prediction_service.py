from datetime import datetime, timezone

from sqlmodel import Session

from app.db.session import engine
from app.models import Equipo, Partido, Torneo
from app.services import prediction_service


def _model(*teams: str) -> dict:
    return {
        "teams": list(teams),
        "team_to_idx": {},
        "attack": {team.casefold(): 1.0 for team in teams},
        "defense": {team.casefold(): 1.0 for team in teams},
        "gamma": 0.1,
        "rho": 0.0,
        "version": "test-v1",
    }


def _create_match(
    fixture_id: int | None = 9001,
    tournament_category: str = "seleccion",
    home_name: str = "Argentina",
    away_name: str = "Brazil",
    home_type: str = "seleccion",
    away_type: str = "seleccion",
) -> None:
    with Session(engine) as session:
        torneo = Torneo(
            nombre_canonico=f"Torneo {fixture_id}",
            nombre_api=f"Torneo {fixture_id}",
            tipo="test",
            categoria=tournament_category,
        )
        home = Equipo(
            nombre_canonico=f"{home_name} {fixture_id} local",
            nombre_api=home_name,
            nombre_csv=home_name,
            tipo=home_type,
        )
        away = Equipo(
            nombre_canonico=f"{away_name} {fixture_id} away",
            nombre_api=away_name,
            nombre_csv=away_name,
            tipo=away_type,
        )
        session.add(torneo)
        session.add(home)
        session.add(away)
        session.flush()
        session.add(
            Partido(
                fixture_id=fixture_id,
                fixture_id_externo=f"fixture-{fixture_id}",
                fuente_origen="test",
                tipo_dato="fixture",
                hash_dedupe=f"prediction{fixture_id or 0:022d}"[:32],
                fecha_utc=datetime(2026, 6, 15, tzinfo=timezone.utc),
                torneo_id=torneo.id,
                equipo_local_id=home.id,
                equipo_visitante_id=away.id,
                home_team=home_name,
                away_team=away_name,
                tournament=torneo.nombre_canonico,
                estado="NS",
            )
        )
        session.commit()


def test_predict_partido_valid_match_returns_ok():
    _create_match()

    data = prediction_service.predict_partido(9001, _model("Argentina", "Brazil"), None)

    assert data["status"] == "ok"
    assert data["model_type"] == "seleccion"
    assert data["model_version"] == "test-v1"
    assert data["neutral"] is True
    assert data["home_win"] >= 0
    assert data["draw"] >= 0
    assert data["away_win"] >= 0
    assert data["score_matrix"]


def test_predict_partido_without_loaded_model_is_explicit():
    _create_match(fixture_id=9002)

    data = prediction_service.predict_partido(9002, None, None)

    assert data["status"] == "model_not_loaded"
    assert data["model_type"] == "seleccion"
    assert "home_win" not in data


def test_predict_partido_without_fixture_id_is_insufficient_data():
    _create_match(fixture_id=None)

    data = prediction_service.predict_partido(None, _model("Argentina", "Brazil"), None)  # type: ignore[arg-type]

    assert data["status"] == "insufficient_data"
    assert "fixture_id" in data["message"]
    assert "home_win" not in data


def test_predict_partido_team_outside_model_is_not_predicted():
    _create_match(fixture_id=9003, away_name="Uruguay")

    data = prediction_service.predict_partido(9003, _model("Argentina", "Brazil"), None)

    assert data["status"] == "team_not_supported"
    assert data["away_team"] == "Uruguay"
    assert "score_matrix" not in data


def test_predict_partido_club_vs_selection_is_not_supported():
    _create_match(
        fixture_id=9004,
        tournament_category="club",
        home_name="River Plate",
        away_name="Argentina",
        home_type="club",
        away_type="seleccion",
    )

    data = prediction_service.predict_partido(9004, _model("Argentina"), _model("River Plate"))

    assert data["status"] == "team_not_supported"
    assert "club y selección" in data["message"]
    assert "home_win" not in data


def test_predict_partido_invalid_matrix_returns_insufficient_data(monkeypatch):
    _create_match(fixture_id=9005)

    def fake_predict_match(*args, **kwargs):
        return [[float("nan")]]

    monkeypatch.setattr(prediction_service, "predict_match", fake_predict_match)

    data = prediction_service.predict_partido(9005, _model("Argentina", "Brazil"), None)

    assert data["status"] == "insufficient_data"
    assert "score_matrix" not in data
