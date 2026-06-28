from __future__ import annotations
import logging
from datetime import datetime

import pandas as pd
from sqlmodel import Session, select

from .config import settings
from .database import get_engine, init_db
from .models import Partido, PartidoEstadisticas, EquipoElo, ModelFeatures
from .utils.dedupe import normalize_team
from .features.base_features import (
    compute_dixon_coles_strengths,
    add_dixon_coles_features,
    add_form_features,
)
from .features.advanced_features import add_advanced_features, add_elo_features
from .features.h2h_features import add_h2h_features
from .features.context_features import add_context_features, compute_completeness_score

logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL))
logger = logging.getLogger("04_feature_engineering")


def _load_partidos(session: Session) -> pd.DataFrame:
    partidos = session.exec(
        select(Partido).where(Partido.estado == "FT")
    ).all()

    rows = []
    for p in partidos:
        rows.append({
            "partido_id": p.id,
            "fecha_utc": p.fecha_utc,
            "equipo_local_id": p.equipo_local_id,
            "equipo_visitante_id": p.equipo_visitante_id,
            "local_name": _get_team_name(session, p.equipo_local_id),
            "visit_name": _get_team_name(session, p.equipo_visitante_id),
            "goles_local": p.goles_local or 0,
            "goles_visitante": p.goles_visitante or 0,
            "torneo_id": p.torneo_id,
            "neutral": p.neutral,
            "etapa": p.etapa or "",
        })
    return pd.DataFrame(rows)


def _get_team_name(session: Session, team_id: int) -> str:
    from .models import Equipo
    eq = session.get(Equipo, team_id)
    if eq:
        return eq.nombre_canonico or eq.nombre_csv or f"team_{team_id}"
    return f"team_{team_id}"


def _load_stats(session: Session, partido_ids: list) -> pd.DataFrame:
    stats = session.exec(
        select(PartidoEstadisticas).where(PartidoEstadisticas.partido_id.in_(partido_ids))
    ).all()

    rows = []
    for s in stats:
        rows.append({
            "partido_id": s.partido_id,
            "xg_local": float(s.xg_local) if s.xg_local else None,
            "xg_visitante": float(s.xg_visitante) if s.xg_visitante else None,
            "posesion_local": float(s.posesion_local) if s.posesion_local else None,
            "posesion_visitante": float(s.posesion_visitante) if s.posesion_visitante else None,
            "remates_local": s.remates_local,
            "remates_visitante": s.remates_visitante,
            "corners_local": s.corners_local,
            "corners_visitante": s.corners_visitante,
        })
    return pd.DataFrame(rows)


def _load_elo(session: Session) -> pd.DataFrame:
    elo_rows = session.exec(select(EquipoElo)).all()
    return pd.DataFrame([
        {"equipo_id": e.equipo_id, "fecha": e.fecha, "elo": e.elo}
        for e in elo_rows
    ])


def _save_features(session: Session, df: pd.DataFrame, version: str):
    inserted = 0
    for _, row in df.iterrows():
        existing = session.exec(
            select(ModelFeatures).where(
                ModelFeatures.partido_id == int(row["partido_id"]),
                ModelFeatures.version_features == version,
            )
        ).first()

        if existing:
            continue

        mf = ModelFeatures(
            partido_id=int(row["partido_id"]),
            version_features=version,
            resultado=(
                "H" if row["goles_local"] > row["goles_visitante"]
                else "A" if row["goles_local"] < row["goles_visitante"]
                else "D"
            ),
            goles_local=int(row["goles_local"]),
            goles_visitante=int(row["goles_visitante"]),
            total_goles=int(row["goles_local"] + row["goles_visitante"]),
            ambos_marcan=bool(row["goles_local"] > 0 and row["goles_visitante"] > 0),
            **{k: row[k] for k in [
                "attack_local", "defense_local", "attack_visitante", "defense_visitante",
                "home_advantage",
                "forma_local_5", "forma_visitante_5", "forma_local_10", "forma_visitante_10",
                "goles_favor_local_5", "goles_contra_local_5",
                "goles_favor_visitante_5", "goles_contra_visitante_5",
                "xg_diff_5", "xg_diff_10", "posesion_diff_5", "shots_diff_5", "corners_diff_5",
                "elo_diff", "ranking_fifa_diff",
                "dias_descanso_local", "dias_descanso_visitante",
                "neutral_field", "importancia_torneo", "fase_eliminatoria",
                "h2h_partidos", "h2h_victorias_local", "h2h_victorias_visitante",
                "h2h_goles_local", "h2h_goles_visitante",
            ] if k in row.index},
        )
        session.add(mf)
        inserted += 1
        if inserted % 500 == 0:
            session.commit()

    session.commit()
    logger.info("Features guardadas: %d", inserted)
    return inserted


def build_features():
    engine = get_engine()
    init_db()

    with Session(engine) as session:
        logger.info("Cargando partidos...")
        df = _load_partidos(session)
        if df.empty:
            logger.warning("No hay partidos finalizados para generar features")
            return

        df["fecha_utc"] = pd.to_datetime(df["fecha_utc"])
        logger.info("Partidos cargados: %d", len(df))

        stats_df = _load_stats(session, df["partido_id"].tolist())
        elo_df = _load_elo(session)

        logger.info("Generando features base (Dixon-Coles)...")
        strengths = compute_dixon_coles_strengths(df)
        df = add_dixon_coles_features(df, strengths, home_team_col="local_name", away_team_col="visit_name")

        logger.info("Generando features de forma reciente...")
        df = add_form_features(df)

        logger.info("Generando features H2H...")
        df = add_h2h_features(df)

        logger.info("Generando features de contexto...")
        df = add_context_features(df)

        logger.info("Generando features avanzadas...")
        df = add_advanced_features(df, stats_df)
        df = add_elo_features(df, elo_df)

        df["completeness"] = compute_completeness_score(df)

        logger.info("Guardando features en BD (versión %s)...", settings.FEATURES_VERSION)
        saved = _save_features(session, df, settings.FEATURES_VERSION)

    logger.info("Feature engineering completado: %d partidos, %d features", len(df), saved)
    return len(df)


def main():
    build_features()
    logger.info("✅ 04_feature_engineering completado")


if __name__ == "__main__":
    main()
