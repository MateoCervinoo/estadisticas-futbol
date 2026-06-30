import logging
import os

from fastapi import FastAPI

from ..dixoncoles import load_model_json
from ..sync import sync_fixtures_and_metrics

logger = logging.getLogger(__name__)


def _resolve_data_path(filename: str) -> str | None:
    for data_dir in (os.path.join("/", "app", "data"), os.path.join(os.path.dirname(__file__), "..", "data")):
        fp = os.path.abspath(os.path.join(data_dir, filename))
        if os.path.exists(fp):
            return fp
    return None


def _model_version(model: dict | None) -> str | None:
    if not isinstance(model, dict):
        return None
    for key in ("version", "model_version", "trained_at", "created_at"):
        value = model.get(key)
        if value:
            return str(value)
    path = model.get("path")
    return os.path.basename(str(path)) if path else None


def _model_team_count(model: dict | None) -> int | None:
    if not isinstance(model, dict):
        return None
    teams = model.get("teams")
    if isinstance(teams, (list, tuple, set)):
        return len(teams)
    team_to_idx = model.get("team_to_idx")
    if isinstance(team_to_idx, dict):
        return len(team_to_idx)
    attack = model.get("attack")
    if isinstance(attack, dict):
        return len(attack)
    return None


def _model_status(model: dict | None, path: str | None) -> dict:
    available = bool(model)
    return {
        "available": available,
        "path": path,
        "version": _model_version(model),
        "team_count": _model_team_count(model),
    }


def load_prediction_models(app: FastAPI) -> None:
    try:
        sel_path = _resolve_data_path("model_params.json")
        sel_model = load_model_json(sel_path) if sel_path else None
        sel_available = bool(sel_model)
        if sel_model:
            sel_model.setdefault("path", sel_path)
            logger.info("Cargado modelo selecciones desde %s", sel_path)
        else:
            logger.info("No se encontró model_params.json para selecciones")

        club_path = _resolve_data_path("model_params_clubes.json")
        club_model = load_model_json(club_path) if club_path else None
        club_available = bool(club_model)
        if club_model:
            club_model.setdefault("path", club_path)
            logger.info("Cargado modelo clubes desde %s", club_path)
        else:
            logger.info("No se encontró modelo para clubes")

        app.state.sel_model = sel_model
        app.state.club_model = club_model
        app.state.model = sel_model
        app.state.prediction_models_status = {
            "status": "ok" if sel_available else "degraded",
            "selecciones": _model_status(sel_model, sel_path),
            "clubes": _model_status(club_model, club_path),
        }
    except Exception:
        logger.exception("No se pudieron cargar modelos de predicción")
        app.state.sel_model = None
        app.state.club_model = None
        app.state.model = None
        app.state.prediction_models_status = {
            "status": "degraded",
            "selecciones": _model_status(None, None),
            "clubes": _model_status(None, None),
        }


def seed_and_sync_startup(app: FastAPI) -> None:
    try:
        from ..data_manager import seed_equipos_if_empty

        seed_equipos_if_empty()
    except Exception:
        logger.exception("No se pudo seedear la tabla Equipo; continuando de todos modos.")

    load_prediction_models(app)

    if os.getenv("RUN_STARTUP_SYNC", "").lower() not in {"1", "true", "yes"}:
        logger.info("Sincronización en startup desactivada; usar sync_worker o RUN_STARTUP_SYNC=true.")
        return

    try:
        logger.info("Iniciando sincronización de fixtures y métricas...")
        sync_summary = sync_fixtures_and_metrics()
        logger.info("Sincronización finalizada: %s", sync_summary)
    except Exception:
        logger.exception("Error durante la sincronización en startup. Continuando sin bloquear el servidor.")
