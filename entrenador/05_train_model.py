from __future__ import annotations
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sqlmodel import Session, select

from .config import settings
from .database import get_engine, init_db
from .models import Partido, PartidoEstadisticas, Torneo, ModelFeatures
from .algos.dixon_coles import fit_dixon_coles_xg, fit_dixon_coles, save_model
from .algos.poisson_regression import fit_poisson_regression
from .utils.dedupe import normalize_team, generate_match_hash

logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL))
logger = logging.getLogger("05_train_model")

CLUB_CATEGORIES = {"club", "liga", "copa"}
SELECCION_CATEGORIES = {"seleccion", "mundial", "continental", "clasificatorias", "amistoso"}


def train_from_features() -> Dict[str, Any]:
    engine = get_engine()
    init_db()

    df = _load_training_data(engine)
    if df.empty:
        logger.warning("No hay datos de entrenamiento disponibles")
        return {}

    # Attach xG stats
    df = _attach_xg_stats(engine, df)

    # Separate selecciones vs clubes
    df_sel = df[df["categoria"] == "seleccion"].copy()
    df_club = df[df["categoria"] == "club"].copy()

    stats_all = {"trained_at": datetime.now(timezone.utc).isoformat()}

    # --- Selecciones model ---
    if not df_sel.empty:
        logger.info("Entrenando selecciones con %d partidos (xg: %d con datos)", len(df_sel), df_sel["xg_local"].notna().sum())
        model_sel = fit_dixon_coles_xg(df_sel)
        model_sel["model_type"] = "selecciones"
        save_model(model_sel, settings.MODEL_PARAMS_PATH)
        logger.info("Modelo selecciones guardado en %s", settings.MODEL_PARAMS_PATH)
        stats_all.update({
            "n_partidos_sel": len(df_sel),
            "n_equipos_sel": len(model_sel.get("teams", [])),
            "gamma_sel": model_sel.get("gamma", 0),
            "rho_sel": model_sel.get("rho", 0),
            "rho_xg_sel": model_sel.get("rho_xg", 0),
        })
    else:
        logger.warning("No hay partidos de selecciones para entrenar")

    # --- Clubes model ---
    if not df_club.empty:
        logger.info("Entrenando clubes con %d partidos (xg: %d con datos)", len(df_club), df_club["xg_local"].notna().sum())
        model_club = fit_dixon_coles_xg(df_club)
        model_club["model_type"] = "clubes"
        club_path = _club_model_path()
        save_model(model_club, club_path)
        logger.info("Modelo clubes guardado en %s", club_path)
        stats_all.update({
            "n_partidos_club": len(df_club),
            "n_equipos_club": len(model_club.get("teams", [])),
            "gamma_club": model_club.get("gamma", 0),
            "rho_club": model_club.get("rho", 0),
            "rho_xg_club": model_club.get("rho_xg", 0),
        })
    else:
        logger.warning("No hay partidos de clubes para entrenar")

    # Fallback: if only one category has data, train a combined model
    if df_sel.empty and not df.empty:
        logger.info("Entrenando modelo combinado (solo hay %d partidos)", len(df))
        model = fit_dixon_coles_xg(df)
        model["model_type"] = "combinado"
        save_model(model, settings.MODEL_PARAMS_PATH)

    if settings.ENABLE_ML_MODELS:
        try:
            logger.info("Entrenando Poisson Regression (baseline)...")
            poisson_model = fit_poisson_regression(df)
            logger.info("Poisson Regression converged: %s", poisson_model.get("converged", False))
        except Exception as e:
            logger.warning("Poisson Regression falló: %s", e)

    logger.info("Estadísticas entrenamiento: %s", stats_all)
    return stats_all


def _club_model_path() -> str:
    base = Path(settings.MODEL_PARAMS_PATH)
    return str(base.parent / "model_params_clubes.json")


def _get_categoria_from_partido(engine, partido) -> str:
    if partido.torneo_id:
        with Session(engine) as s:
            torneo = s.get(Torneo, partido.torneo_id)
            if torneo:
                return torneo.categoria
    return "seleccion"


def _load_training_data(engine) -> pd.DataFrame:
    with Session(engine) as session:
        partidos = session.exec(
            select(Partido).where(
                Partido.estado == "FT",
                Partido.goles_local.isnot(None),
                Partido.goles_visitante.isnot(None),
            )
        ).all()

    rows = []
    from .models import Equipo
    for p in partidos:
        with Session(engine) as s:
            local = s.get(Equipo, p.equipo_local_id)
            visit = s.get(Equipo, p.equipo_visitante_id)

        categoria = _get_categoria_from_partido(engine, p)
        rows.append({
            "local_name": normalize_team(local.nombre_canonico or local.nombre_csv or "") if local else f"team_{p.equipo_local_id}",
            "visit_name": normalize_team(visit.nombre_canonico or visit.nombre_csv or "") if visit else f"team_{p.equipo_visitante_id}",
            "goles_local": p.goles_local or 0,
            "goles_visitante": p.goles_visitante or 0,
            "fecha_utc": p.fecha_utc,
            "partido_id": p.id,
            "categoria": categoria,
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    df = df[df["goles_local"] >= 0]
    df = df[df["goles_visitante"] >= 0]
    df["goles_local"] = df["goles_local"].astype(int)
    df["goles_visitante"] = df["goles_visitante"].astype(int)
    return df


def _attach_xg_stats(engine, df: pd.DataFrame) -> pd.DataFrame:
    partido_ids = df["partido_id"].tolist()
    if not partido_ids:
        df["xg_local"] = None
        df["xg_visitante"] = None
        return df

    with Session(engine) as session:
        stats = session.exec(
            select(PartidoEstadisticas).where(
                PartidoEstadisticas.partido_id.in_(partido_ids),
                PartidoEstadisticas.fuente == "fbref",
            )
        ).all()

    xg_map = {}
    for s in stats:
        xg_map[s.partido_id] = {
            "xg_local": float(s.xg_local) if s.xg_local is not None else None,
            "xg_visitante": float(s.xg_visitante) if s.xg_visitante is not None else None,
        }

    # Also fallback to Partido.xg_local/xg_visitante (from sync)
    with Session(engine) as session:
        partidos = session.exec(
            select(Partido).where(Partido.id.in_(partido_ids))
        ).all()
    for p in partidos:
        if p.id not in xg_map:
            xgl = float(p.xg_local) if p.xg_local is not None else None
            xgv = float(p.xg_visitante) if p.xg_visitante is not None else None
            if xgl is not None or xgv is not None:
                xg_map[p.id] = {"xg_local": xgl, "xg_visitante": xgv}

    df["xg_local"] = df["partido_id"].map(lambda pid: xg_map.get(pid, {}).get("xg_local"))
    df["xg_visitante"] = df["partido_id"].map(lambda pid: xg_map.get(pid, {}).get("xg_visitante"))

    return df


def main():
    train_from_features()
    logger.info("✅ 05_train_model completado")


if __name__ == "__main__":
    main()
