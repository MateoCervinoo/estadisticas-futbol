from datetime import datetime, timezone

from sqlmodel import Session

from app.database import engine
from app.models import Equipo, Partido, Torneo


def test_health_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_partidos_responds(client):
    response = client.get("/api/partidos")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_torneos_responds(client):
    response = client.get("/api/torneos")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_prediction_with_valid_teams_does_not_explode(client):
    with Session(engine) as session:
        torneo = Torneo(nombre_canonico="Mundial", nombre_api="FIFA World Cup", tipo="mundial", categoria="seleccion")
        argentina = Equipo(nombre_canonico="Argentina", nombre_api="Argentina", nombre_csv="Argentina", tipo="seleccion")
        brazil = Equipo(nombre_canonico="Brazil", nombre_api="Brazil", nombre_csv="Brazil", tipo="seleccion")
        session.add(torneo)
        session.add(argentina)
        session.add(brazil)
        session.flush()
        partido = Partido(
            fixture_id=123456,
            fixture_id_externo=None,
            fuente_origen="api_football_data",
            tipo_dato="fixture",
            hash_dedupe="predictiontest1234567890abcdef12",
            fecha_utc=datetime(2026, 6, 15, tzinfo=timezone.utc),
            torneo_id=torneo.id,
            equipo_local_id=argentina.id,
            equipo_visitante_id=brazil.id,
            home_team="Argentina",
            away_team="Brazil",
            tournament="Mundial",
            estado="NS",
        )
        session.add(partido)
        session.commit()

    response = client.get("/api/partidos/123456/prediccion")

    assert response.status_code == 200
    data = response.json()
    assert "home_win" in data
    assert "draw" in data
    assert "away_win" in data
    assert isinstance(data["score_matrix"], list)
