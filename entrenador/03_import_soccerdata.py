from __future__ import annotations
import logging
import math
from typing import Dict, Optional
from datetime import datetime, timezone, timedelta

from sqlmodel import Session, select

from .config import settings, LEAGUES_REGISTRY
from .database import get_engine, init_db
from .models import Partido, PartidoEstadisticas, EquipoElo, Torneo, SourceCoverage
from .sources.fbref import FBrefClient
from .sources.understat import UnderstatClient
from .sources.clubelo import ClubEloClient
from .utils.dedupe import generate_match_hash, normalize_team

logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL))
logger = logging.getLogger("03_import_soccerdata")

_STAT_META_KEYS = {"hash_dedupe", "fuente", "date", "home_team", "away_team", "league"}


def import_fbref_stats() -> int:
    if not settings.SOCCERDATA_FBREF:
        logger.info("FBref deshabilitado en config")
        return 0

    client = FBrefClient()
    engine = get_engine()
    init_db()
    total = 0

    with Session(engine) as session:
        for league_config in LEAGUES_REGISTRY:
            if league_config.categoria != "club":
                continue

            # Resolver torneo_id real desde el nombre_canonico
            torneo = session.exec(
                select(Torneo).where(Torneo.nombre_canonico == league_config.nombre_canonico)
            ).first()
            coverage_torneo_id = torneo.id if torneo else None

            fbref_name = league_config.nombre_fbref
            if not fbref_name:
                continue
            for season in (league_config.fbref_seasons or []):
                logger.info("Obteniendo FBref: %s %s", fbref_name, season)
                stats = client.get_match_stats(fbref_name, season)
                stats_with_xg = [s for s in stats if _has_real_xg(s)]

                updated = 0
                unmatched = 0
                for stat in stats_with_xg:
                    partido = _find_partido_for_stat(session, stat, coverage_torneo_id, league_config.nombre_canonico)
                    if not partido:
                        unmatched += 1
                        continue

                    _upsert_partido_estadisticas(session, partido.id, "fbref", stat)
                    updated += 1

                session.commit()
                total += updated
                logger.info("  → %d/%d partidos enriquecidos con FBref (%s %s); sin match local: %d",
                            updated, len(stats_with_xg), fbref_name, season, unmatched)

                _upsert_coverage(session, "fbref", coverage_torneo_id, season, len(stats_with_xg), updated)
                session.commit()

    logger.info("FBref completado: %d partidos enriquecidos", total)
    return total


def import_understat() -> int:
    if not settings.SOCCERDATA_UNDERSTAT:
        logger.info("Understat deshabilitado en config")
        return 0

    client = UnderstatClient()
    engine = get_engine()
    init_db()
    total = 0

    with Session(engine) as session:
        for league_config in LEAGUES_REGISTRY:
            if league_config.categoria != "club":
                continue

            torneo = session.exec(
                select(Torneo).where(Torneo.nombre_canonico == league_config.nombre_canonico)
            ).first()
            coverage_torneo_id = torneo.id if torneo else None

            understat_name = league_config.nombre_understat
            if not understat_name:
                continue
            for season in (league_config.understat_seasons or []):
                logger.info("Obteniendo Understat: %s %s", understat_name, season)
                stats = client.get_match_stats(understat_name, season)
                stats_with_xg = [s for s in stats if _has_real_xg(s)]

                updated = 0
                unmatched = 0
                for stat in stats_with_xg:
                    partido = _find_partido_for_stat(session, stat, coverage_torneo_id, league_config.nombre_canonico)
                    if not partido:
                        unmatched += 1
                        continue

                    _upsert_partido_estadisticas(session, partido.id, "understat", stat)
                    updated += 1

                session.commit()
                total += updated
                logger.info("  → %d/%d partidos enriquecidos con Understat (%s %s); sin match local: %d",
                            updated, len(stats_with_xg), understat_name, season, unmatched)

                _upsert_coverage(session, "understat", coverage_torneo_id, season, len(stats_with_xg), updated)
                session.commit()

    logger.info("Understat completado: %d partidos enriquecidos", total)
    return total


def _has_real_xg(stat: Dict) -> bool:
    return _is_real_number(stat.get("xg_local")) and _is_real_number(stat.get("xg_visitante"))


def _is_real_number(value) -> bool:
    if value is None:
        return False
    try:
        return not math.isnan(float(value))
    except (TypeError, ValueError):
        return False


def _stats_payload(stat: Dict) -> Dict:
    return {k: v for k, v in stat.items() if k not in _STAT_META_KEYS and v is not None}


def _upsert_partido_estadisticas(session: Session, partido_id: int, fuente: str, stat: Dict) -> None:
    existing_stats = session.exec(
        select(PartidoEstadisticas).where(
            PartidoEstadisticas.partido_id == partido_id,
            PartidoEstadisticas.fuente == fuente,
        )
    ).first()
    payload = _stats_payload(stat)

    if existing_stats:
        for key, value in payload.items():
            setattr(existing_stats, key, value)
        existing_stats.updated_at = datetime.now(timezone.utc)
    else:
        session.add(PartidoEstadisticas(partido_id=partido_id, fuente=fuente, **payload))


def _upsert_coverage(session: Session, fuente: str, torneo_id: Optional[int], temporada: str,
                     total_partidos: int, partidos_con_stats: int) -> None:
    coverage = session.exec(
        select(SourceCoverage).where(
            SourceCoverage.fuente == fuente,
            SourceCoverage.torneo_id == torneo_id,
            SourceCoverage.temporada == temporada,
        )
    ).first()
    now = datetime.now(timezone.utc)
    if coverage:
        coverage.total_partidos = total_partidos
        coverage.partidos_con_stats = partidos_con_stats
        coverage.ultima_sync = now
    else:
        session.add(SourceCoverage(
            fuente=fuente,
            torneo_id=torneo_id,
            temporada=temporada,
            total_partidos=total_partidos,
            partidos_con_stats=partidos_con_stats,
            ultima_sync=now,
        ))


def _find_partido_for_stat(session: Session, stat: Dict, torneo_id: Optional[int], tournament: str) -> Optional[Partido]:
    hash_dedupe = stat.get("hash_dedupe")
    if hash_dedupe:
        partido = session.exec(select(Partido).where(Partido.hash_dedupe == hash_dedupe)).first()
        if partido and (torneo_id is None or partido.torneo_id == torneo_id):
            return partido

    date_str = str(stat.get("date") or "")[:10]
    home = (stat.get("home_team") or "").strip()
    away = (stat.get("away_team") or "").strip()
    if not date_str or not home or not away:
        return None

    alternate_hash = generate_match_hash(date_str, home, away, tournament)
    partido = session.exec(select(Partido).where(Partido.hash_dedupe == alternate_hash)).first()
    if partido and (torneo_id is None or partido.torneo_id == torneo_id):
        return partido

    match_date = _parse_stat_date(date_str)
    if match_date is None:
        return None

    start = match_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=2)
    query = select(Partido).where(Partido.fecha_utc >= start, Partido.fecha_utc < end)
    if torneo_id is not None:
        query = query.where(Partido.torneo_id == torneo_id)

    home_norm = normalize_team(home)
    away_norm = normalize_team(away)
    candidates = session.exec(query).all()
    exact_name_match = None
    for candidate in candidates:
        if _candidate_matches_teams(session, candidate, home_norm, away_norm):
            if exact_name_match is not None:
                logger.warning("Match ambiguo para stats %s %s vs %s", date_str, home, away)
                return None
            exact_name_match = candidate
    return exact_name_match


def _candidate_matches_teams(session: Session, partido: Partido, home_norm: str, away_norm: str) -> bool:
    home_names = _team_names_for_match(session, partido.equipo_local_id, partido.home_team)
    away_names = _team_names_for_match(session, partido.equipo_visitante_id, partido.away_team)
    return home_norm in home_names and away_norm in away_names


def _team_names_for_match(session: Session, equipo_id: Optional[int], legacy_name: Optional[str]) -> set[str]:
    names = set()
    if legacy_name:
        names.add(normalize_team(legacy_name))
    if equipo_id is not None:
        from .models import Equipo
        equipo = session.get(Equipo, equipo_id)
        if equipo:
            for attr in ("nombre_canonico", "nombre_api", "nombre_csv", "nombre_fbref", "nombre_understat", "nombre_es"):
                value = getattr(equipo, attr, None)
                if value:
                    names.add(normalize_team(value))
    return names


def _parse_stat_date(date_str: str) -> Optional[datetime]:
    try:
        parsed = datetime.fromisoformat(date_str[:10])
        return parsed.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def import_clubelo() -> int:
    if not settings.SOCCERDATA_CLUBELO:
        logger.info("ClubElo deshabilitado en config")
        return 0

    client = ClubEloClient()
    engine = get_engine()
    init_db()
    total = 0

    with Session(engine) as session:
        from .utils.team_mapper import TeamMapper
        mapper = TeamMapper(session)

        elo_data = client.get_elo_for_date()
        if not elo_data:
            logger.warning("No se obtuvieron datos de ClubElo")
            return 0

        for entry in elo_data:
            team_name = entry.get("team", "")
            equipo_id = mapper.resolve(team_name)
            if equipo_id is None:
                continue

            existing = session.exec(
                select(EquipoElo).where(
                    EquipoElo.equipo_id == equipo_id,
                    EquipoElo.fecha == entry["date"],
                    EquipoElo.fuente == "clubelo",
                )
            ).first()

            if not existing:
                ee = EquipoElo(
                    equipo_id=equipo_id,
                    fecha=entry["date"],
                    elo=entry["elo"],
                    ranking_fifa=entry.get("rank"),
                    fuente="clubelo",
                )
                session.add(ee)
                total += 1

        session.commit()

    logger.info("ClubElo completado: %d registros insertados", total)
    return total


def main():
    import_fbref_stats()
    import_understat()
    import_clubelo()
    logger.info("✅ 03_import_soccerdata completado")


if __name__ == "__main__":
    main()
