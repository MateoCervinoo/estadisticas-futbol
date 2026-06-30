import datetime
import logging
from typing import Optional

from sqlmodel import Session


from ..models import Equipo, Partido

logger = logging.getLogger(__name__)


def enrich_partido_item(p: Partido, session: Session) -> dict:
    item = p.dict()

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
        raw_date = item.get("date") or item.get("fecha_utc") or ""
        date_key = str(raw_date)[:10]
        tournament = str(item.get("tournament") or "").strip().casefold()
        home = str(item.get("home_team") or item.get("home_nombre_es") or "").strip().casefold()
        away = str(item.get("away_team") or item.get("away_nombre_es") or "").strip().casefold()
        key = "|".join([date_key, home, away, tournament])

        current = by_key.get(key)
        if current is None:
            by_key[key] = item
            continue

        current_has_fixture = current.get("fixture_id") is not None
        item_has_fixture = item.get("fixture_id") is not None
        current_has_media = bool(current.get("home_crest_url") or current.get("away_crest_url"))
        item_has_media = bool(item.get("home_crest_url") or item.get("away_crest_url"))
        if (item_has_fixture and not current_has_fixture) or (item_has_media and not current_has_media):
            by_key[key] = item

    return list(by_key.values())


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
