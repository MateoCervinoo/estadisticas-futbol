from __future__ import annotations
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from sqlmodel import Session, select

from .config import settings, LEAGUES_REGISTRY
from .database import get_engine, init_db
from .models import Partido, Torneo
from .utils.dedupe import generate_match_hash, normalize_team
from .utils.team_mapper import TeamMapper
from .sources.football_data import FootballDataClient

logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL))
logger = logging.getLogger("02_update_matches")

FINAL_STATUSES = {"FINISHED", "FT"}


def normalize_football_data_status(raw: str) -> str:
    r = str(raw).strip().upper()
    if r in ("FINISHED", "FT"):
        return "FT"
    if r in ("TIMED", "SCHEDULED"):
        return "NS"
    if r in ("IN_PLAY", "PAUSED", "LIVE"):
        return "IN_PLAY"
    if r in ("POSTPONED", "CANCELLED", "SUSPENDED"):
        return "POSTP"
    return "NS"


def update_from_football_data() -> int:
    client = FootballDataClient()
    if client.mock:
        logger.info("Modo MOCK — sin API key, saltando sincronización real")
        return 0

    engine = get_engine()
    init_db()
    total = 0

    with Session(engine) as session:
        mapper = TeamMapper(session)

        for league_config in LEAGUES_REGISTRY:
            if not league_config.sync_enabled or league_config.football_data_league_code is None:
                continue

            code = league_config.football_data_league_code
            logger.info("Sincronizando %s (%s) — temporadas %d a %d",
                        league_config.nombre_canonico, code,
                        settings.FOOTBALL_DATA_START_SEASON, settings.FOOTBALL_DATA_END_SEASON)
            try:
                matches = client.get_competition_matches_multi_season(
                    code,
                    settings.FOOTBALL_DATA_START_SEASON,
                    settings.FOOTBALL_DATA_END_SEASON,
                )
                processed = _process_matches(matches, "football_data", mapper, league_config, session)
                total += processed
                logger.info("  → %s: %d partidos procesados", league_config.nombre_canonico, processed)
            except Exception as e:
                logger.error("Error sincronizando %s: %s", league_config.nombre_canonico, e)
                session.rollback()
                continue

        session.commit()

    logger.info("Actualización Football-Data completada: %d partidos procesados en total", total)
    return total


def _resolve_torneo(session: Session, league_config) -> Optional[int]:
    if not league_config:
        return None
    torneo = session.exec(
        select(Torneo).where(Torneo.nombre_canonico == league_config.nombre_canonico)
    ).first()
    if not torneo:
        torneo = Torneo(
            nombre_canonico=league_config.nombre_canonico,
            nombre_api=league_config.nombre_football_data,
            nombre_fbref=league_config.nombre_fbref,
            tipo=league_config.tipo,
            categoria=league_config.categoria,
            nivel=league_config.nivel,
        )
        session.add(torneo)
        session.flush()
        logger.info("  Torneo creado desde API: %s", league_config.nombre_canonico)
    return torneo.id


def _process_matches(matches, fuente: str, mapper, league_config, session) -> int:
    processed = 0

    torneo_id = _resolve_torneo(session, league_config)

    for m in matches:
        date_str = m.get("date", "")
        home = (m.get("home_team") or "").strip()
        away = (m.get("away_team") or "").strip()
        if not home or not away:
            continue

        tournament = league_config.nombre_canonico if league_config else ""
        hash_dedupe = generate_match_hash(date_str[:10], home, away, tournament)
        fixture_id = m.get("fixture_id")
        stage = m.get("stage")
        group = m.get("group")
        ht_home = m.get("ht_goals_home")
        ht_away = m.get("ht_goals_away")
        home_crest = m.get("home_crest")
        away_crest = m.get("away_crest")

        home_id = mapper.resolve_or_create(home)
        away_id = mapper.resolve_or_create(away)

        existing = session.exec(
            select(Partido).where(Partido.hash_dedupe == hash_dedupe)
        ).first()

        status = normalize_football_data_status(m.get("status", ""))
        gl = m.get("goals_home")
        gv = m.get("goals_away")

        if existing:
            if existing.estado not in FINAL_STATUSES or status in FINAL_STATUSES:
                existing.goles_local = gl
                existing.goles_visitante = gv
                existing.goles_local_ht = ht_home
                existing.goles_visitante_ht = ht_away
                existing.estado = status
                existing.etapa = stage
                existing.grupo = group
                existing.home_crest_url = home_crest
                existing.away_crest_url = away_crest
                existing.torneo_id = torneo_id
                existing.fixture_id = fixture_id if isinstance(fixture_id, int) else existing.fixture_id
                existing.fixture_id_externo = str(fixture_id) if fixture_id else existing.fixture_id_externo
                existing.tipo_dato = "fixture" if status in {"NS", "TIMED"} else "api_sync"
                existing.updated_at = datetime.now(timezone.utc)
        else:
            partido = Partido(
                fixture_id=fixture_id if isinstance(fixture_id, int) else None,
                fixture_id_externo=str(fixture_id) if fixture_id else None,
                fuente_origen=fuente,
                tipo_dato="fixture" if status in {"NS", "TIMED"} else "api_sync",
                hash_dedupe=hash_dedupe,
                fecha_utc=_parse_date(date_str),
                torneo_id=torneo_id,
                etapa=stage,
                grupo=group,
                equipo_local_id=home_id,
                equipo_visitante_id=away_id,
                home_team=home,
                away_team=away,
                home_crest_url=home_crest,
                away_crest_url=away_crest,
                goles_local=gl,
                goles_visitante=gv,
                goles_local_ht=ht_home,
                goles_visitante_ht=ht_away,
                estado=status,
                neutral=False,
            )
            session.add(partido)

        processed += 1
        if processed % 100 == 0:
            session.commit()

    return processed


def _parse_date(date_str: str) -> datetime:
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except Exception:
        return datetime.now(timezone.utc)


def main():
    update_from_football_data()
    logger.info("✅ 02_update_matches completado")


if __name__ == "__main__":
    main()
