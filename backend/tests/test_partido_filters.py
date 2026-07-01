from datetime import datetime, timezone

from sqlmodel import Session

from app.db.session import engine
from app.models import Equipo, Partido, Torneo
from app.services.partido_service import dedupe_partido_items


def _create_match(
    session: Session,
    torneo: Torneo,
    home: Equipo,
    away: Equipo,
    fixture_id: int,
    fecha: datetime,
    stage: str,
    group: str | None,
    matchday: int | None,
    status: str = "NS",
) -> Partido:
    partido = Partido(
        fixture_id=fixture_id,
        fixture_id_externo=None,
        fuente_origen="api_football_data",
        tipo_dato="fixture",
        hash_dedupe=f"hash{fixture_id:028d}"[:32],
        fecha_utc=fecha,
        torneo_id=torneo.id,
        etapa=stage,
        grupo=group,
        jornada=matchday,
        equipo_local_id=home.id,
        equipo_visitante_id=away.id,
        home_team=home.nombre_canonico,
        away_team=away.nombre_canonico,
        tournament=torneo.nombre_canonico,
        estado=status,
    )
    session.add(partido)
    return partido


def test_partidos_and_metadata_share_filters(client):
    with Session(engine) as session:
        torneo = Torneo(nombre_canonico="Mundial Test", nombre_api="Mundial Test", tipo="mundial", categoria="seleccion")
        otro_torneo = Torneo(nombre_canonico="Copa Test", nombre_api="Copa Test", tipo="copa", categoria="seleccion")
        argentina = Equipo(nombre_canonico="Argentina Test", tipo="seleccion")
        brazil = Equipo(nombre_canonico="Brazil Test", tipo="seleccion")
        france = Equipo(nombre_canonico="France Test", tipo="seleccion")
        germany = Equipo(nombre_canonico="Germany Test", tipo="seleccion")
        session.add_all([torneo, otro_torneo, argentina, brazil, france, germany])
        session.flush()

        _create_match(session, torneo, argentina, brazil, 900001, datetime(2026, 6, 12, 18, tzinfo=timezone.utc), "GROUP_STAGE", "GROUP_A", 1)
        _create_match(session, torneo, france, germany, 900002, datetime(2026, 6, 13, 18, tzinfo=timezone.utc), "GROUP_STAGE", "GROUP_B", 1)
        _create_match(session, torneo, argentina, france, 900003, datetime(2026, 6, 20, 18, tzinfo=timezone.utc), "ROUND_OF_16", None, None)
        _create_match(session, otro_torneo, argentina, germany, 900004, datetime(2026, 6, 12, 18, tzinfo=timezone.utc), "GROUP_STAGE", "GROUP_A", 1)
        session.commit()
        torneo_id = torneo.id

    query = f"torneo_id={torneo_id}&year=2026&stage=GROUP_STAGE&group=GROUP_A&matchday=1&date=2026-06-12"
    partidos_response = client.get(f"/api/partidos?{query}")
    filtros_response = client.get(f"/api/partidos/filtros?{query}")

    assert partidos_response.status_code == 200
    assert filtros_response.status_code == 200

    partidos = partidos_response.json()
    filtros = filtros_response.json()
    assert len(partidos) == 1
    assert partidos[0]["fixture_id"] == 900001
    assert filtros["years"] == [2026]
    assert filtros["tournaments"] == ["Mundial Test"]
    assert filtros["stages"] == ["GROUP_STAGE"]
    assert filtros["groups"] == ["GROUP_A"]
    assert filtros["matchdays"] == [1]
    assert filtros["dates"] == ["2026-06-12"]


def test_partidos_filters_support_season(client):
    with Session(engine) as session:
        torneo = Torneo(nombre_canonico="Liga Test", nombre_api="Liga Test", tipo="liga", categoria="club")
        local = Equipo(nombre_canonico="Club Local Test", tipo="club")
        away = Equipo(nombre_canonico="Club Away Test", tipo="club")
        session.add_all([torneo, local, away])
        session.flush()

        _create_match(session, torneo, local, away, 910001, datetime(2024, 8, 1, 20, tzinfo=timezone.utc), "REGULAR", None, 1, status="FT")
        _create_match(session, torneo, away, local, 910002, datetime(2025, 5, 1, 20, tzinfo=timezone.utc), "REGULAR", None, 2, status="FT")
        _create_match(session, torneo, local, away, 910003, datetime(2025, 8, 1, 20, tzinfo=timezone.utc), "REGULAR", None, 1, status="FT")
        session.commit()
        torneo_id = torneo.id

    partidos_response = client.get(f"/api/partidos?torneo_id={torneo_id}&season=2024/25")
    filtros_response = client.get(f"/api/partidos/filtros?torneo_id={torneo_id}&season=2024/25")

    assert partidos_response.status_code == 200
    assert filtros_response.status_code == 200
    assert [p["fixture_id"] for p in partidos_response.json()] == [910001, 910002]
    assert filtros_response.json()["matchdays"] == [1, 2]
    assert filtros_response.json()["seasons"] == ["2024/25"]


def test_partidos_metadata_exposes_league_seasons(client):
    with Session(engine) as session:
        torneo = Torneo(nombre_canonico="Liga Season Test", nombre_api="Liga Season Test", tipo="liga", categoria="club")
        local = Equipo(nombre_canonico="Season Local Test", tipo="club")
        away = Equipo(nombre_canonico="Season Away Test", tipo="club")
        session.add_all([torneo, local, away])
        session.flush()

        _create_match(session, torneo, local, away, 920001, datetime(2025, 8, 1, 20, tzinfo=timezone.utc), "REGULAR", None, 1, status="FT")
        _create_match(session, torneo, away, local, 920002, datetime(2026, 5, 1, 20, tzinfo=timezone.utc), "REGULAR", None, 2, status="FT")
        session.commit()

    response = client.get("/api/partidos/filtros?tournament=Liga%20Season%20Test")

    assert response.status_code == 200
    assert response.json()["years"] == [2025, 2026]
    assert response.json()["seasons"] == ["2025/26"]


def test_dedupe_partido_items_prefers_api_fixture_with_media():
    csv_item = {
        "id": 1,
        "date": "2026-06-12T18:00:00",
        "home_team": "Argentina",
        "away_team": "Brazil",
        "tournament": "Mundial",
        "fixture_id": None,
    }
    api_item = {
        "id": 2,
        "date": "2026-06-12T18:00:00",
        "home_team": "Argentina",
        "away_team": "Brazil",
        "tournament": "Mundial",
        "fixture_id": 123,
        "home_crest_url": "https://example.com/arg.png",
    }

    result = dedupe_partido_items([csv_item, api_item])

    assert len(result) == 1
    assert result[0]["id"] == 2


def test_dedupe_partido_items_priority_is_order_independent():
    csv_item = {
        "id": 10,
        "date": "2026-06-12T18:00:00",
        "home_team": "Argentina",
        "away_team": "Brazil",
        "tournament": "Mundial",
        "fixture_id": None,
        "home_score": 1,
        "away_score": 0,
    }
    api_item = {
        "id": 9,
        "date": "2026-06-12T18:00:00",
        "home_team": "Argentina",
        "away_team": "Brazil",
        "tournament": "Mundial",
        "fixture_id": 123,
    }

    assert dedupe_partido_items([csv_item, api_item])[0]["id"] == 9
    assert dedupe_partido_items([api_item, csv_item])[0]["id"] == 9


def test_dedupe_partido_items_keeps_distinct_matches():
    base_item = {
        "id": 1,
        "date": "2026-06-12T18:00:00",
        "home_team": "Argentina",
        "away_team": "Brazil",
        "tournament": "Mundial",
        "fixture_id": 123,
    }
    different_date = {**base_item, "id": 2, "date": "2026-06-13T18:00:00"}
    different_tournament = {**base_item, "id": 3, "tournament": "Copa America"}
    reversed_teams = {**base_item, "id": 4, "home_team": "Brazil", "away_team": "Argentina"}

    result = dedupe_partido_items([base_item, different_date, different_tournament, reversed_teams])

    assert [item["id"] for item in result] == [1, 2, 3, 4]


def test_dedupe_partido_items_does_not_merge_incomplete_identity():
    missing_tournament = {
        "id": 1,
        "date": "2026-06-12T18:00:00",
        "home_team": "Argentina",
        "away_team": "Brazil",
        "fixture_id": 123,
    }
    also_missing_tournament = {
        "id": 2,
        "date": "2026-06-12T18:00:00",
        "home_team": "Argentina",
        "away_team": "Brazil",
        "fixture_id": 124,
    }

    result = dedupe_partido_items([missing_tournament, also_missing_tournament])

    assert [item["id"] for item in result] == [1, 2]
