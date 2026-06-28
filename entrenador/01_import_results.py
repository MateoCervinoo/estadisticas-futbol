from __future__ import annotations
import logging
from datetime import datetime, timezone

import pandas as pd
from sqlmodel import Session, select

from .config import settings
from .database import get_engine, init_db
from .models import Equipo, Partido, Torneo
from .utils.dedupe import generate_match_hash
from .utils.validators import clean_dataframe
from .utils.team_mapper import TeamMapper

logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL))
logger = logging.getLogger("01_import_results")

MUNDIAL_2026_START = "2026-06-11"


def _create_torneos(session: Session, tournament_names: set):
    for name in sorted(tournament_names):
        if not name:
            continue
        existing = session.exec(
            select(Torneo).where(Torneo.nombre_canonico == name)
        ).first()
        if not existing:
            tipo = "mundial" if "world cup" in name.lower() or "mundial" in name.lower() else "otro"
            categoria = "seleccion"
            torneo = Torneo(nombre_canonico=name, tipo=tipo, categoria=categoria)
            session.add(torneo)
            logger.info("  Torneo creado: %s (%s)", name, tipo)
    session.commit()


def import_results_csv(csv_path: str = None) -> int:
    if csv_path is None:
        csv_path = settings.RESULTS_CSV

    logger.info("Importando histórico desde: %s", csv_path)
    df = pd.read_csv(csv_path)
    df["date"] = pd.to_datetime(df["date"])
    df = df[df["date"] >= f"{settings.SINCE_YEAR}-01-01"].copy()
    df = clean_dataframe(df)

    # Verificar si existe columna tournament
    has_tournament = "tournament" in df.columns

    # Filtrar partidos del Mundial 2026 (los trae la API con datos estructurados)
    if has_tournament:
        before = len(df)
        df = df[~((df["tournament"] == "FIFA World Cup") & (df["date"] >= MUNDIAL_2026_START))].copy()
        filtrados = before - len(df)
        if filtrados:
            logger.info("Partidos del Mundial 2026 filtrados (van por API): %d", filtrados)

    logger.info("Partidos a procesar: %d", len(df))
    if df.empty:
        logger.warning("No hay partidos para importar")
        return 0

    engine = get_engine()
    init_db()

    inserted = 0
    updated = 0

    with Session(engine) as session:
        mapper = TeamMapper(session)

        # Crear torneos automáticamente desde los nombres únicos del CSV
        if has_tournament:
            tournament_names = set(df["tournament"].dropna().unique())
            _create_torneos(session, tournament_names)

        # Cache de torneos para búsqueda rápida
        all_torneos = session.exec(select(Torneo)).all()
        torneo_cache = {t.nombre_canonico: t for t in all_torneos}

        for _, row in df.iterrows():
            date_str = row["date"].isoformat()[:19]
            home = str(row["home_team"]).strip()
            away = str(row["away_team"]).strip()
            tournament = str(row.get("tournament", "")).strip()
            neutral = bool(row.get("neutral", False))

            hash_dedupe = generate_match_hash(date_str[:10], home, away, tournament)
            fixture_id = f"csv_{hash_dedupe[:12]}"

            home_id = mapper.resolve_or_create(home, tipo="seleccion")
            away_id = mapper.resolve_or_create(away, tipo="seleccion")

            torneo = torneo_cache.get(tournament)
            torneo_id = torneo.id if torneo else None

            existing = session.exec(
                select(Partido).where(Partido.hash_dedupe == hash_dedupe)
            ).first()

            if existing:
                if existing.estado != "FT":
                    existing.goles_local = int(row["home_score"])
                    existing.goles_visitante = int(row["away_score"])
                    existing.estado = "FT"
                    existing.torneo_id = torneo_id
                    existing.updated_at = datetime.now(timezone.utc)
                    updated += 1
            else:
                partido = Partido(
                    fixture_id_externo=fixture_id,
                    fuente_origen="csv_historico",
                    hash_dedupe=hash_dedupe,
                    fecha_utc=row["date"],
                    torneo_id=torneo_id,
                    equipo_local_id=home_id,
                    equipo_visitante_id=away_id,
                    goles_local=int(row["home_score"]),
                    goles_visitante=int(row["away_score"]),
                    neutral=neutral,
                    estado="FT",
                )
                session.add(partido)
                inserted += 1

            if (inserted + updated) % 500 == 0:
                session.commit()
                logger.info("Procesados %d partidos...", inserted + updated)

        session.commit()

    logger.info("Importación completada: %d insertados, %d actualizados", inserted, updated)
    return inserted + updated


def main():
    import_results_csv()
    logger.info("✅ 01_import_results completado")


if __name__ == "__main__":
    main()
