from datetime import datetime, timezone

from sqlmodel import Session

from app.db.session import engine
from app.models import Equipo, Partido, Torneo


def _team(session: Session, name: str, tipo: str = "seleccion") -> Equipo:
    equipo = Equipo(nombre_canonico=name, tipo=tipo)
    session.add(equipo)
    session.flush()
    return equipo


def _torneo(session: Session, name: str, tipo: str, categoria: str) -> Torneo:
    torneo = Torneo(nombre_canonico=name, nombre_api=name, tipo=tipo, categoria=categoria)
    session.add(torneo)
    session.flush()
    return torneo


def _partido(
    session: Session,
    torneo: Torneo,
    home: Equipo,
    away: Equipo,
    fixture_id: int,
    fecha: datetime,
    etapa: str,
    grupo: str | None = None,
    estado: str = "NS",
    goles_local: int | None = None,
    goles_visitante: int | None = None,
    xg_local: float | None = None,
    xg_visitante: float | None = None,
) -> Partido:
    partido = Partido(
        fixture_id=fixture_id,
        fixture_id_externo=None,
        fuente_origen="api_football_data",
        tipo_dato="api_sync" if estado == "FT" else "fixture",
        hash_dedupe=f"torneo{fixture_id:026d}"[:32],
        fecha_utc=fecha,
        torneo_id=torneo.id,
        etapa=etapa,
        grupo=grupo,
        equipo_local_id=home.id,
        equipo_visitante_id=away.id,
        home_team=home.nombre_canonico,
        away_team=away.nombre_canonico,
        tournament=torneo.nombre_canonico,
        estado=estado,
        goles_local=goles_local,
        goles_visitante=goles_visitante,
        xg_local=xg_local,
        xg_visitante=xg_visitante,
    )
    session.add(partido)
    return partido


def test_torneo_temporadas_uses_world_cup_years_and_league_seasons(client):
    with Session(engine) as session:
        mundial = _torneo(session, "Mundial Temporadas", "mundial", "seleccion")
        liga = _torneo(session, "Liga Temporadas", "liga", "club")
        a = _team(session, "Equipo A")
        b = _team(session, "Equipo B")
        club_a = _team(session, "Club A", "club")
        club_b = _team(session, "Club B", "club")

        _partido(session, mundial, a, b, 920001, datetime(2022, 11, 20, tzinfo=timezone.utc), "GROUP_STAGE")
        _partido(session, mundial, b, a, 920002, datetime(2026, 6, 12, tzinfo=timezone.utc), "GROUP_STAGE")
        _partido(session, liga, club_a, club_b, 920003, datetime(2024, 5, 1, tzinfo=timezone.utc), "REGULAR")
        _partido(session, liga, club_a, club_b, 920004, datetime(2024, 8, 1, tzinfo=timezone.utc), "REGULAR")
        _partido(session, liga, club_b, club_a, 920005, datetime(2025, 5, 1, tzinfo=timezone.utc), "REGULAR")
        session.commit()
        mundial_id = mundial.id
        liga_id = liga.id

    mundial_response = client.get(f"/api/torneos/{mundial_id}/temporadas")
    liga_response = client.get(f"/api/torneos/{liga_id}/temporadas")

    assert mundial_response.status_code == 200
    assert liga_response.status_code == 200
    assert mundial_response.json()["temporadas"] == ["2026", "2022"]
    assert liga_response.json()["temporadas"] == ["2024/25", "2023/24"]


def test_torneo_tabla_grouped_counts_only_finished_group_stage_matches(client):
    with Session(engine) as session:
        torneo = _torneo(session, "Mundial Tabla", "mundial", "seleccion")
        argentina = _team(session, "Argentina Tabla")
        brazil = _team(session, "Brazil Tabla")
        france = _team(session, "France Tabla")
        germany = _team(session, "Germany Tabla")

        _partido(session, torneo, argentina, brazil, 930001, datetime(2026, 6, 12, tzinfo=timezone.utc), "GROUP_STAGE", "GROUP_A", "FT", 2, 1, 1.4, 0.8)
        _partido(session, torneo, france, germany, 930002, datetime(2026, 6, 13, tzinfo=timezone.utc), "GROUP_STAGE", "GROUP_A", "NS")
        _partido(session, torneo, argentina, france, 930003, datetime(2026, 7, 1, tzinfo=timezone.utc), "ROUND_OF_16", None, "FT", 0, 1)
        session.commit()
        torneo_id = torneo.id

    response = client.get(f"/api/torneos/{torneo_id}/tabla-posiciones?year=2026&grouped=true")

    assert response.status_code == 200
    data = response.json()
    assert data["torneo"] == "Mundial Tabla"
    assert len(data["grupos"]) == 1
    rows = data["grupos"][0]["tabla"]
    by_team = {row["equipo"]: row for row in rows}

    assert by_team["Argentina Tabla"]["pj"] == 1
    assert by_team["Argentina Tabla"]["pg"] == 1
    assert by_team["Argentina Tabla"]["pts"] == 3
    assert by_team["Argentina Tabla"]["gf"] == 2
    assert by_team["Argentina Tabla"]["gc"] == 1
    assert by_team["Argentina Tabla"]["xg_favor"] == 1.4
    assert by_team["Brazil Tabla"]["pj"] == 1
    assert by_team["Brazil Tabla"]["pp"] == 1
    assert by_team["France Tabla"]["pj"] == 0
    assert by_team["Germany Tabla"]["pj"] == 0


def test_torneo_bracket_excludes_group_stage_and_filters_period(client):
    with Session(engine) as session:
        torneo = _torneo(session, "Mundial Bracket", "mundial", "seleccion")
        a = _team(session, "Bracket A")
        b = _team(session, "Bracket B")
        c = _team(session, "Bracket C")
        d = _team(session, "Bracket D")

        _partido(session, torneo, a, b, 940001, datetime(2026, 6, 12, tzinfo=timezone.utc), "GROUP_STAGE", "GROUP_A")
        _partido(session, torneo, a, c, 940002, datetime(2026, 7, 1, tzinfo=timezone.utc), "ROUND_OF_16")
        _partido(session, torneo, b, d, 940003, datetime(2026, 7, 8, tzinfo=timezone.utc), "QUARTER_FINALS")
        _partido(session, torneo, c, d, 940004, datetime(2022, 12, 18, tzinfo=timezone.utc), "FINAL")
        session.commit()
        torneo_id = torneo.id

    response = client.get(f"/api/torneos/{torneo_id}/bracket?year=2026")

    assert response.status_code == 200
    bracket = response.json()["bracket"]
    assert [round_data["stage"] for round_data in bracket] == ["ROUND_OF_16", "QUARTER_FINALS"]
    assert bracket[0]["matches"][0]["home_team"] == "Bracket A"
    assert bracket[1]["matches"][0]["away_team"] == "Bracket D"
