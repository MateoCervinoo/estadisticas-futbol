from __future__ import annotations
import logging
from typing import Dict, List, Set
from datetime import datetime, timezone

from sqlmodel import Session, select

from .config import settings, LEAGUES_REGISTRY
from .database import get_engine, init_db
from .models import Partido, PartidoEstadisticas, EquipoElo, Torneo, SourceCoverage
from .sources.fbref import FBrefClient
from .sources.clubelo import ClubEloClient

logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL))
logger = logging.getLogger("03_import_soccerdata")


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
                if not stats:
                    continue

                updated = 0
                for stat in stats:
                    hash_dedupe = stat.get("hash_dedupe")
                    if not hash_dedupe:
                        continue

                    partido = session.exec(
                        select(Partido).where(Partido.hash_dedupe == hash_dedupe)
                    ).first()
                    if not partido:
                        continue

                    existing_stats = session.exec(
                        select(PartidoEstadisticas).where(
                            PartidoEstadisticas.partido_id == partido.id,
                            PartidoEstadisticas.fuente == "fbref",
                        )
                    ).first()

                    if existing_stats:
                        for key, value in stat.items():
                            if key in ("hash_dedupe", "fuente") or value is None:
                                continue
                            setattr(existing_stats, key, value)
                        existing_stats.updated_at = datetime.now(timezone.utc)
                    else:
                        pe = PartidoEstadisticas(
                            partido_id=partido.id,
                            fuente="fbref",
                            **{k: v for k, v in stat.items() if k not in ("hash_dedupe", "fuente") and v is not None},
                        )
                        session.add(pe)

                    updated += 1

                session.commit()
                total += updated
                logger.info("  → %d partidos enriquecidos con FBref (%s %s)", updated,
                            fbref_name, season)

                coverage = session.exec(
                    select(SourceCoverage).where(
                        SourceCoverage.fuente == "fbref",
                        SourceCoverage.torneo_id == coverage_torneo_id,
                        SourceCoverage.temporada == season,
                    )
                ).first()
                if coverage:
                    coverage.partidos_con_stats = updated
                    coverage.ultima_sync = datetime.now(timezone.utc)
                else:
                    session.add(SourceCoverage(
                        fuente="fbref", torneo_id=coverage_torneo_id,
                        temporada=season, total_partidos=updated,
                        partidos_con_stats=updated, ultima_sync=datetime.now(timezone.utc),
                    ))
                session.commit()

    logger.info("FBref completado: %d partidos enriquecidos", total)
    return total


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
    import_clubelo()
    logger.info("✅ 03_import_soccerdata completado")


if __name__ == "__main__":
    main()
