from __future__ import annotations

import argparse
import sys
import unicodedata
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlmodel import Session, select

from backend.app.database import engine
from backend.app.models import Equipo, Partido, PartidoEstadisticas, Torneo

WORLD_CUP_2026_START = date(2026, 6, 11)
FINAL_STATUSES = {"FT", "AET", "PEN", "FINISHED"}
API_SOURCES = {"api_football_data", "football_data", "api"}


def _as_date(value: datetime | date | None) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    return value


def _norm(value: Any) -> str:
    return str(value or "").strip().casefold()


def _team_norm(value: Any) -> str:
    text = _norm(value)
    text = "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")
    text = text.replace("-", " ").replace("_", " ").replace(".", "").replace("'", " ")
    return " ".join(text.split())


def _is_api_row(partido: Partido) -> bool:
    return partido.fixture_id is not None or _norm(partido.fuente_origen) in API_SOURCES


def _is_csv_row(partido: Partido) -> bool:
    return _norm(partido.fuente_origen).startswith("csv") or partido.fixture_id_externo is not None


def _is_finished(partido: Partido) -> bool:
    return _norm(partido.estado).upper() in FINAL_STATUSES


def _team_key(team_id: int | None, fallback: str | None, team_names: dict[int, str]) -> str:
    if team_id is not None and team_id in team_names:
        return _team_norm(team_names[team_id])
    return _team_norm(fallback)


def _match_key(partido: Partido, team_names: dict[int, str]) -> tuple[str, str, str]:
    match_date = _as_date(partido.fecha_utc)
    return (
        match_date.isoformat() if match_date else "",
        _team_key(partido.equipo_local_id, partido.home_team, team_names),
        _team_key(partido.equipo_visitante_id, partido.away_team, team_names),
    )


def _richness_score(partido: Partido) -> tuple[int, int, int, int, int]:
    return (
        1 if _is_api_row(partido) else 0,
        1 if partido.fixture_id is not None else 0,
        1 if partido.etapa else 0,
        1 if partido.grupo else 0,
        1 if partido.home_crest_url or partido.away_crest_url else 0,
    )


def _world_cup_torneo_ids(session: Session) -> set[int]:
    torneos = session.exec(select(Torneo)).all()
    ids: set[int] = set()
    for torneo in torneos:
        name = _norm(torneo.nombre_canonico)
        if "world cup" in name or "mundial" in name:
            if torneo.id is not None:
                ids.add(torneo.id)
    return ids


def _team_names(session: Session) -> dict[int, str]:
    equipos = session.exec(select(Equipo)).all()
    names: dict[int, str] = {}
    for equipo in equipos:
        if equipo.id is None:
            continue
        names[equipo.id] = (
            equipo.nombre_csv
            or equipo.nombre_api
            or equipo.nombre_canonico
            or equipo.nombre_es
            or str(equipo.id)
        )
    return names


def _is_world_cup_2026(partido: Partido, torneo_ids: set[int]) -> bool:
    match_date = _as_date(partido.fecha_utc)
    if not match_date or match_date.year != 2026:
        return False
    tournament = _norm(partido.tournament)
    return (
        partido.torneo_id in torneo_ids
        or "world cup" in tournament
        or "mundial" in tournament
    )


def _delete_partido(session: Session, partido: Partido) -> None:
    stats = session.exec(
        select(PartidoEstadisticas).where(PartidoEstadisticas.partido_id == partido.id)
    ).all()
    for stat in stats:
        session.delete(stat)
    session.delete(partido)


def cleanup_worldcup_2026(apply: bool = False) -> dict[str, Any]:
    report: dict[str, Any] = {
        "mode": "apply" if apply else "dry-run",
        "world_cup_rows": 0,
        "duplicate_groups": 0,
        "delete_ids": [],
        "normalize_ids": [],
    }

    with Session(engine) as session:
        torneo_ids = _world_cup_torneo_ids(session)
        team_names = _team_names(session)
        partidos = session.exec(select(Partido).order_by(Partido.fecha_utc, Partido.id)).all()
        world_cup = [p for p in partidos if _is_world_cup_2026(p, torneo_ids)]
        report["world_cup_rows"] = len(world_cup)

        by_key: dict[tuple[str, str, str], list[Partido]] = defaultdict(list)
        delete_ids: set[int] = set()
        for partido in world_cup:
            match_date = _as_date(partido.fecha_utc)
            if match_date and match_date >= WORLD_CUP_2026_START:
                by_key[_match_key(partido, team_names)].append(partido)
                if partido.id is not None and _is_csv_row(partido):
                    delete_ids.add(partido.id)

            if not _is_finished(partido):
                score_placeholder = partido.goles_local == 0 and partido.goles_visitante == 0
                xg_placeholder = partido.xg_local == 0 or partido.xg_visitante == 0
                if score_placeholder or xg_placeholder:
                    report["normalize_ids"].append(partido.id)
                    if apply:
                        if score_placeholder:
                            partido.goles_local = None
                            partido.goles_visitante = None
                        if xg_placeholder:
                            if partido.xg_local == 0:
                                partido.xg_local = None
                            if partido.xg_visitante == 0:
                                partido.xg_visitante = None
                        partido.updated_at = datetime.now(timezone.utc)
                        session.add(partido)

        for group in by_key.values():
            if len(group) <= 1:
                continue
            report["duplicate_groups"] += 1
            keep = max(group, key=_richness_score)
            for partido in group:
                if partido.id == keep.id:
                    continue
                if _is_csv_row(partido) or _richness_score(partido) < _richness_score(keep):
                    if partido.id is not None:
                        delete_ids.add(partido.id)

        report["delete_ids"] = sorted(delete_ids)
        if apply and delete_ids:
            for partido in world_cup:
                if partido.id in delete_ids:
                    _delete_partido(session, partido)

        if apply:
            session.commit()
        else:
            session.rollback()

    report["delete_count"] = len(report["delete_ids"])
    report["normalize_count"] = len(report["normalize_ids"])
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audita y limpia duplicados del Mundial 2026. Por defecto no modifica datos."
    )
    parser.add_argument("--apply", action="store_true", help="Aplica borrados/correcciones. Sin esto solo reporta.")
    args = parser.parse_args()

    report = cleanup_worldcup_2026(apply=args.apply)
    print(f"Modo: {report['mode']}")
    print(f"Filas Mundial 2026 encontradas: {report['world_cup_rows']}")
    print(f"Grupos duplicados: {report['duplicate_groups']}")
    print(f"Partidos a borrar: {report['delete_count']} -> {report['delete_ids']}")
    print(f"Partidos a normalizar: {report['normalize_count']} -> {report['normalize_ids']}")


if __name__ == "__main__":
    main()
