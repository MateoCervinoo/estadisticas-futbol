from datetime import datetime, timezone

from sqlmodel import Session

from app.db.session import engine
from app.models import Equipo, Partido, Torneo
from backend.scripts.audit_tournament_counts import build_tournament_counts_report_from_session


def _team(session: Session, name: str) -> Equipo:
    equipo = Equipo(nombre_canonico=name)
    session.add(equipo)
    session.flush()
    return equipo


def _torneo(session: Session, name: str, tipo: str) -> Torneo:
    torneo = Torneo(nombre_canonico=name, nombre_api=name, tipo=tipo, categoria="club")
    session.add(torneo)
    session.flush()
    return torneo


def _partido(session: Session, torneo: Torneo, home: Equipo, away: Equipo, fixture_id: int, fecha: datetime, etapa: str) -> None:
    session.add(Partido(
        fixture_id=fixture_id,
        fuente_origen="api_football_data",
        tipo_dato="fixture",
        hash_dedupe=f"audit{fixture_id:027d}"[:32],
        fecha_utc=fecha,
        torneo_id=torneo.id,
        tournament=torneo.nombre_canonico,
        etapa=etapa,
        equipo_local_id=home.id,
        equipo_visitante_id=away.id,
        home_team=home.nombre_canonico,
        away_team=away.nombre_canonico,
        estado="NS",
    ))


def test_audit_tournament_counts_reports_world_cup_stages_and_premier_expected_total():
    with Session(engine) as session:
        mundial = _torneo(session, "Mundial", "mundial")
        premier = _torneo(session, "Premier League", "liga")
        a = _team(session, "Audit A")
        b = _team(session, "Audit B")

        _partido(session, mundial, a, b, 950001, datetime(2026, 6, 12, tzinfo=timezone.utc), "GROUP_STAGE")
        _partido(session, mundial, b, a, 950002, datetime(2026, 7, 1, tzinfo=timezone.utc), "ROUND_OF_16")
        _partido(session, premier, a, b, 950003, datetime(2024, 8, 16, tzinfo=timezone.utc), "REGULAR")
        _partido(session, premier, b, a, 950004, datetime(2025, 5, 20, tzinfo=timezone.utc), "REGULAR")
        session.commit()

        report = build_tournament_counts_report_from_session(session, premier_expected=380)

    assert report["world_cup"]["total"] == 2
    assert report["world_cup"]["by_stage"] == {"GROUP_STAGE": 1, "ROUND_OF_16": 1}
    assert report["premier_league"]["seasons"] == [{
        "season": "2024/25",
        "total": 2,
        "expected_total": 380,
        "missing_vs_expected": 378,
        "matches_expected_total": False,
    }]
