import datetime
import logging
from typing import Optional

from sqlalchemy import func, or_
from sqlmodel import Session, select


from ..models import Equipo, Partido, Torneo

logger = logging.getLogger(__name__)


def enrich_partido_item(p: Partido, session: Session) -> dict:
    item = p.model_dump()

    field_map = {
        "date": "fecha_utc",
        "home_score": "goles_local",
        "away_score": "goles_visitante",
        "status": "estado",
        "stage": "etapa",
        "group": "grupo",
        "matchday": "jornada",
        "ht_home_score": "goles_local_ht",
        "ht_away_score": "goles_visitante_ht",
    }
    for eng, spa in field_map.items():
        item[eng] = item.get(spa)

    try:
        if p.equipo_local_id:
            he = session.get(Equipo, p.equipo_local_id)
            if he:
                item["home_nombre_es"] = he.nombre_es
                item["home_codigo_bandera"] = he.codigo_bandera
                if not item.get("home_team"):
                    item["home_team"] = he.nombre_canonico
        if p.equipo_visitante_id:
            ae = session.get(Equipo, p.equipo_visitante_id)
            if ae:
                item["away_nombre_es"] = ae.nombre_es
                item["away_codigo_bandera"] = ae.codigo_bandera
                if not item.get("away_team"):
                    item["away_team"] = ae.nombre_canonico
    except Exception:
        logger.exception("Error enriqueciendo partido %s", p.id)

    return item


def dedupe_partido_items(items: list[dict]) -> list[dict]:
    by_key: dict[str, dict] = {}
    for item in items:
        key = partido_dedupe_key(item)
        if key is None:
            key = f"record:{item.get('id') or id(item)}"

        current = by_key.get(key)
        if current is None:
            by_key[key] = item
            continue

        if partido_dedupe_priority(item) > partido_dedupe_priority(current):
            by_key[key] = item

    return list(by_key.values())


def partido_dedupe_key(item: dict) -> str | None:
    raw_date = item.get("date") or item.get("fecha_utc") or ""
    date_key = str(raw_date)[:10]
    tournament = str(item.get("tournament") or "").strip().casefold()
    home = str(item.get("home_team") or item.get("home_nombre_es") or "").strip().casefold()
    away = str(item.get("away_team") or item.get("away_nombre_es") or "").strip().casefold()
    if not date_key or not home or not away or not tournament:
        return None
    return "|".join([date_key, home, away, tournament])


def partido_dedupe_priority(item: dict) -> tuple[int, int, int, int]:
    has_fixture = int(item.get("fixture_id") is not None)
    has_media = int(bool(item.get("home_crest_url") or item.get("away_crest_url")))
    has_score = int(item.get("home_score") is not None and item.get("away_score") is not None)
    record_id = int(item.get("id") or 0)
    return has_fixture, has_media, has_score, record_id


def season_bounds(
    season: Optional[str] = None,
    year: Optional[int] = None,
) -> tuple[Optional[datetime.datetime], Optional[datetime.datetime]]:
    if season:
        try:
            start_year = int(str(season).split("/")[0])
            return datetime.datetime(start_year, 7, 1), datetime.datetime(start_year + 1, 7, 1)
        except Exception:
            return None, None
    if year is not None:
        return datetime.datetime(year, 1, 1), datetime.datetime(year + 1, 1, 1)
    return None, None


def build_partido_filter_conditions(
    session: Session,
    mundial: bool = False,
    proximos: bool = False,
    year: Optional[int] = None,
    season: Optional[str] = None,
    torneo_id: Optional[int] = None,
    tournament: Optional[str] = None,
    stage: Optional[str] = None,
    group: Optional[str] = None,
    matchday: Optional[int] = None,
    date: Optional[str] = None,
) -> list:
    conditions = []

    if mundial:
        torneos = session.exec(
            select(Torneo).where(or_(Torneo.nombre_canonico.ilike("%world cup%"), Torneo.nombre_canonico.ilike("%mundial%")))
        ).all()
        torneo_ids = [t.id for t in torneos if t.id is not None]
        mundial_conditions = []
        if torneo_ids:
            mundial_conditions.append(Partido.torneo_id.in_(torneo_ids))
        mundial_conditions.append(Partido.tournament.ilike("%world cup%"))
        mundial_conditions.append(Partido.tournament.ilike("%mundial%"))
        conditions.append(or_(*mundial_conditions))

    if proximos:
        conditions.append(Partido.estado.in_(["NS", "TIMED"]))

    if year is not None:
        start, end = season_bounds(year=year)
        if start and end:
            conditions.extend([Partido.fecha_utc >= start, Partido.fecha_utc < end])

    if season:
        start, end = season_bounds(season=season)
        if start and end:
            conditions.extend([Partido.fecha_utc >= start, Partido.fecha_utc < end])

    if torneo_id is not None:
        conditions.append(Partido.torneo_id == torneo_id)
    if tournament:
        conditions.append(Partido.tournament == tournament)
    if stage:
        conditions.append(Partido.etapa == stage)
    if group:
        conditions.append(Partido.grupo == group)
    if matchday is not None:
        conditions.append(Partido.jornada == matchday)
    if date:
        conditions.append(func.date(Partido.fecha_utc) == date)

    return conditions


def season_label_for_match(match_date: datetime.datetime, tournament_type: str | None = None) -> str:
    if tournament_type == "mundial":
        return str(match_date.year)
    if match_date.month >= 7:
        return f"{match_date.year}/{str(match_date.year + 1)[-2:]}"
    return f"{match_date.year - 1}/{str(match_date.year)[-2:]}"


def is_finished_match(p: Partido) -> bool:
    if p.goles_local is None or p.goles_visitante is None:
        return False
    return str(p.estado or "").upper() in {"FT", "AET", "PEN", "FINISHED"}
