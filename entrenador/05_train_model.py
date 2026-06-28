from __future__ import annotations
import logging
from typing import Dict, Any, List
from datetime import datetime

import pandas as pd
from sqlmodel import Session, select

from .config import settings
from .database import get_engine, init_db
from .models import Partido, ModelFeatures
from .algos.dixon_coles import fit_dixon_coles, save_model
from .algos.poisson_regression import fit_poisson_regression
from .utils.dedupe import normalize_team, generate_match_hash

logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL))
logger = logging.getLogger("05_train_model")


def train_from_features() -> Dict[str, Any]:
    engine = get_engine()
    init_db()

    df = _load_training_data(engine)
    if df.empty:
        logger.warning("No hay datos de entrenamiento disponibles")
        return {}

    logger.info("Entrenando con %d partidos", len(df))

    model = fit_dixon_coles(df)
    save_model(model)
    logger.info("Modelo Dixon-Coles guardado en %s", settings.MODEL_PARAMS_PATH)

    if settings.ENABLE_ML_MODELS:
        try:
            logger.info("Entrenando Poisson Regression (baseline)...")
            poisson_model = fit_poisson_regression(df)
            logger.info("Poisson Regression converged: %s", poisson_model.get("converged", False))
        except Exception as e:
            logger.warning("Poisson Regression falló: %s", e)

    stats = {
        "n_partidos": len(df),
        "n_equipos": len(model.get("teams", [])),
        "gamma": model.get("gamma", 0),
        "rho": model.get("rho", 0),
        "trained_at": datetime.utcnow().isoformat(),
    }
    logger.info("Estadísticas entrenamiento: %s", stats)
    return stats


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
    for p in partidos:
        from .models import Equipo
        with Session(engine) as s:
            local = s.get(Equipo, p.equipo_local_id)
            visit = s.get(Equipo, p.equipo_visitante_id)

        rows.append({
            "local_name": normalize_team(local.nombre_canonico or local.nombre_csv or "") if local else f"team_{p.equipo_local_id}",
            "visit_name": normalize_team(visit.nombre_canonico or visit.nombre_csv or "") if visit else f"team_{p.equipo_visitante_id}",
            "goles_local": p.goles_local or 0,
            "goles_visitante": p.goles_visitante or 0,
            "fecha_utc": p.fecha_utc,
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    df = df[df["goles_local"] >= 0]
    df = df[df["goles_visitante"] >= 0]
    df["goles_local"] = df["goles_local"].astype(int)
    df["goles_visitante"] = df["goles_visitante"].astype(int)
    return df


def main():
    train_from_features()
    logger.info("✅ 05_train_model completado")


if __name__ == "__main__":
    main()
