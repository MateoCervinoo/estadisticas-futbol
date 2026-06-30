import logging
from typing import Any

import numpy as np
from fastapi import HTTPException
from sqlmodel import Session, select

from ..database import engine
from ..dixoncoles import predict_match, select_model_for_match
from ..models import Equipo, Partido

logger = logging.getLogger(__name__)


def _norm(s: str) -> str:
    try:
        return s.strip().casefold()
    except Exception:
        return str(s).strip().casefold()


def _is_valid_matrix(mat: Any) -> bool:
    try:
        if not isinstance(mat, (list, tuple)) or len(mat) == 0:
            return False
        row_len = None
        total = 0.0
        for row in mat:
            if not isinstance(row, (list, tuple)):
                return False
            if row_len is None:
                row_len = len(row)
                if row_len == 0:
                    return False
            elif len(row) != row_len:
                return False
            for value in row:
                fv = float(value)
                if not np.isfinite(fv):
                    return False
                total += fv
        return bool(np.isfinite(total) and total > 0.0)
    except Exception:
        return False


def predict_partido(partido_id: int, sel_model: dict | None, club_model: dict | None) -> dict:
    max_goals = 4
    with Session(engine) as session:
        partido = session.exec(select(Partido).where(Partido.fixture_id == partido_id)).first()
        if not partido:
            raise HTTPException(status_code=404, detail="Partido no encontrado")

    home_name_for_model = partido.home_team
    away_name_for_model = partido.away_team

    try:
        with Session(engine) as session:
            if partido.equipo_local_id:
                he = session.get(Equipo, partido.equipo_local_id)
                if he and he.nombre_csv:
                    home_name_for_model = he.nombre_csv
            if partido.equipo_visitante_id:
                ae = session.get(Equipo, partido.equipo_visitante_id)
                if ae and ae.nombre_csv:
                    away_name_for_model = ae.nombre_csv
    except Exception:
        logger.exception("Error resolviendo Equipo para partido %s; usando nombres sin normalizar", partido.fixture_id)

    model = select_model_for_match(partido.id if partido else partido_id, engine, sel_model, club_model)
    if model is None:
        model = {"teams": [], "attack": {}, "defense": {}, "gamma": 1.0, "rho": 1.0}

    hkey = _norm(home_name_for_model)
    akey = _norm(away_name_for_model)
    attack_param = model.get("attack") if isinstance(model, dict) else None
    defense_param = model.get("defense") if isinstance(model, dict) else None

    if isinstance(attack_param, dict) and isinstance(defense_param, dict):
        model_for_pred = model
    else:
        gamma = float(model.get("gamma", 1.0)) if isinstance(model, dict) else 1.0
        rho = float(model.get("rho", 1.0)) if isinstance(model, dict) else 1.0
        model_for_pred = {
            "teams": [home_name_for_model, away_name_for_model],
            "attack": {hkey: 1.0, akey: 1.0},
            "defense": {hkey: 1.0, akey: 1.0},
            "gamma": gamma,
            "rho": rho,
        }

    try:
        matrix_raw = predict_match(home_name_for_model, away_name_for_model, model_for_pred, max_goals=max_goals, neutral=True)
    except Exception:
        logger.exception(
            "Error generando predicción matemática para partido %s (%s vs %s)",
            partido.fixture_id,
            home_name_for_model,
            away_name_for_model,
        )
        matrix_raw = None

    if matrix_raw is None or not _is_valid_matrix(matrix_raw):
        logger.warning("Predicción no válida para partido %s: matriz vacía o con valores no finitos", partido.fixture_id)
        return {
            "status": "insufficient_data",
            "message": "Predicción en curso o datos insuficientes para generar probabilidades",
        }

    home_win = 0.0
    draw = 0.0
    away_win = 0.0
    matrix = []
    flat = []
    max_prob = -1.0
    most_likely = {"home": 0, "away": 0}
    for i, raw_row in enumerate(matrix_raw):
        row = []
        for j, value in enumerate(raw_row):
            p = float(value)
            if p > max_prob:
                max_prob = p
                most_likely = {"home": i, "away": j}
            pct = round(p * 100, 2)
            row.append(pct)
            flat.append({"home": i, "away": j, "prob": pct})
            if i > j:
                home_win += p
            elif i == j:
                draw += p
            else:
                away_win += p
        matrix.append(row)

    return {
        "home_win": round(home_win * 100, 2),
        "draw": round(draw * 100, 2),
        "away_win": round(away_win * 100, 2),
        "score_matrix": matrix,
        "score_matrix_flat": flat,
        "most_likely": most_likely,
    }
