import logging
import os
import unicodedata
from typing import Any

import numpy as np
from fastapi import HTTPException
from sqlmodel import select

from ..db.session import Session, engine
from ..dixoncoles import predict_match
from ..models import Equipo, Partido, Torneo

logger = logging.getLogger(__name__)


def _norm(s: str) -> str:
    try:
        value = s.strip().casefold()
    except Exception:
        value = str(s).strip().casefold()
    return "".join(c for c in unicodedata.normalize("NFD", value) if unicodedata.category(c) != "Mn")


def _state(status: str, message: str, **extra: Any) -> dict:
    return {"status": status, "message": message, **extra}


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


def _model_version(model: dict | None) -> str | None:
    if not isinstance(model, dict):
        return None
    for key in ("version", "model_version", "trained_at", "created_at"):
        value = model.get(key)
        if value:
            return str(value)
    path = model.get("path")
    if path:
        return os.path.basename(str(path))
    return None


def _model_has_team(model: dict, team_name: str) -> bool:
    key = _norm(team_name)
    attack = model.get("attack")
    defense = model.get("defense")

    if isinstance(attack, dict) and isinstance(defense, dict):
        return key in {_norm(k) for k in attack} and key in {_norm(k) for k in defense}

    team_to_idx = model.get("team_to_idx")
    if isinstance(team_to_idx, dict) and (isinstance(attack, (list, tuple)) or isinstance(defense, (list, tuple))):
        return key in {_norm(k) for k in team_to_idx}

    teams = model.get("teams")
    if isinstance(teams, (list, tuple)):
        return key in {_norm(k) for k in teams}

    return False


def predict_partido(partido_id: int, sel_model: dict | None, club_model: dict | None) -> dict:
    max_goals = 4
    with Session(engine) as session:
        partido = session.exec(select(Partido).where(Partido.fixture_id == partido_id)).first()
        if not partido:
            raise HTTPException(status_code=404, detail="Partido no encontrado")

        torneo = session.get(Torneo, partido.torneo_id) if partido.torneo_id else None
        home_equipo = session.get(Equipo, partido.equipo_local_id) if partido.equipo_local_id else None
        away_equipo = session.get(Equipo, partido.equipo_visitante_id) if partido.equipo_visitante_id else None

    home_name_for_model = partido.home_team
    away_name_for_model = partido.away_team

    if home_equipo and home_equipo.nombre_csv:
        home_name_for_model = home_equipo.nombre_csv
    if away_equipo and away_equipo.nombre_csv:
        away_name_for_model = away_equipo.nombre_csv

    if not partido.fixture_id:
        return _state("insufficient_data", "El partido no tiene fixture_id asociado")
    if not home_name_for_model or not away_name_for_model:
        return _state("insufficient_data", "Faltan nombres de equipos para generar la predicción")

    model_type = "club" if torneo and torneo.categoria == "club" else "seleccion"
    if home_equipo and away_equipo and home_equipo.tipo != away_equipo.tipo:
        return _state(
            "team_not_supported",
            "No se puede predecir un cruce entre club y selección con los modelos actuales",
            model_type=model_type,
        )

    model = club_model if model_type == "club" else sel_model
    if not isinstance(model, dict) or not model:
        return _state(
            "model_not_loaded",
            f"Modelo de {model_type} no cargado",
            model_type=model_type,
        )

    if not _model_has_team(model, home_name_for_model) or not _model_has_team(model, away_name_for_model):
        return _state(
            "team_not_supported",
            "Uno o ambos equipos no están presentes en el modelo",
            model_type=model_type,
            home_team=home_name_for_model,
            away_team=away_name_for_model,
            model_version=_model_version(model),
        )

    neutral = True if model_type == "seleccion" else bool(partido.neutral)

    try:
        matrix_raw = predict_match(home_name_for_model, away_name_for_model, model, max_goals=max_goals, neutral=neutral)
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
            "model_type": model_type,
            "model_version": _model_version(model),
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
        "status": "ok",
        "model_type": model_type,
        "model_version": _model_version(model),
        "neutral": neutral,
        "home_win": round(home_win * 100, 2),
        "draw": round(draw * 100, 2),
        "away_win": round(away_win * 100, 2),
        "score_matrix": matrix,
        "score_matrix_flat": flat,
        "most_likely": most_likely,
    }
