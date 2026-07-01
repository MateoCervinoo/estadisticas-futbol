from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlmodel import select

from backend.app.db.session import Session, engine
from backend.app.models import Partido, Torneo
from backend.app.services.tournament_service import season_label_for_match

PREMIER_EXPECTED_MATCHES = 380


def _norm(value: Any) -> str:
    return str(value or "").strip().casefold()


def _torneo_ids(torneos: list[Torneo], *needles: str) -> set[int]:
    ids: set[int] = set()
    for torneo in torneos:
        name = _norm(torneo.nombre_canonico)
        api_name = _norm(torneo.nombre_api)
        if any(needle in name or needle in api_name for needle in needles) and torneo.id is not None:
            ids.add(torneo.id)
    return ids


def _is_tournament(partido: Partido, torneo_ids: set[int], *needles: str) -> bool:
    tournament = _norm(partido.tournament)
    return partido.torneo_id in torneo_ids or any(needle in tournament for needle in needles)


def _year(value: datetime | None) -> int | None:
    return value.year if value else None


def build_tournament_counts_report_from_session(
    session: Session,
    world_cup_year: int = 2026,
    premier_expected: int = PREMIER_EXPECTED_MATCHES,
) -> dict[str, Any]:
    torneos = session.exec(select(Torneo)).all()
    partidos = session.exec(select(Partido)).all()
    world_cup_ids = _torneo_ids(torneos, "mundial", "world cup")
    premier_ids = _torneo_ids(torneos, "premier league", "eng-premier league", "epl")

    world_cup_matches = [
        partido
        for partido in partidos
        if _is_tournament(partido, world_cup_ids, "mundial", "world cup")
        and _year(partido.fecha_utc) == world_cup_year
    ]
    world_cup_by_stage = Counter((partido.etapa or "SIN_ETAPA") for partido in world_cup_matches)
    world_cup_by_status = Counter((partido.estado or "SIN_ESTADO") for partido in world_cup_matches)

    premier_by_season: dict[str, list[Partido]] = defaultdict(list)
    for partido in partidos:
        if not partido.fecha_utc or not _is_tournament(partido, premier_ids, "premier league", "eng-premier league", "epl"):
            continue
        premier_by_season[season_label_for_match(partido.fecha_utc, "liga")].append(partido)

    premier_seasons = []
    for season, rows in sorted(premier_by_season.items(), reverse=True):
        premier_seasons.append({
            "season": season,
            "total": len(rows),
            "expected_total": premier_expected,
            "missing_vs_expected": premier_expected - len(rows),
            "matches_expected_total": len(rows) == premier_expected,
        })

    return {
        "world_cup": {
            "year": world_cup_year,
            "total": len(world_cup_matches),
            "by_stage": dict(sorted(world_cup_by_stage.items())),
            "by_status": dict(sorted(world_cup_by_status.items())),
        },
        "premier_league": {
            "expected_total_per_season": premier_expected,
            "seasons": premier_seasons,
        },
    }


def build_tournament_counts_report(
    world_cup_year: int = 2026,
    premier_expected: int = PREMIER_EXPECTED_MATCHES,
) -> dict[str, Any]:
    with Session(engine) as session:
        return build_tournament_counts_report_from_session(
            session,
            world_cup_year=world_cup_year,
            premier_expected=premier_expected,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Audita conteos de partidos por torneo/temporada sin modificar datos.")
    parser.add_argument("--world-cup-year", type=int, default=2026)
    parser.add_argument("--premier-expected", type=int, default=PREMIER_EXPECTED_MATCHES)
    args = parser.parse_args()

    report = build_tournament_counts_report(
        world_cup_year=args.world_cup_year,
        premier_expected=args.premier_expected,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
