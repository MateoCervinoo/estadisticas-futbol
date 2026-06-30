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


def load_prediction_models(app: FastAPI) -> None:
    fallback = {
        "teams": [],
        "team_to_idx": {},
        "attack": {},
        "defense": {},
        "gamma": 1.0,
        "rho": 1.0,
    }

    try:
        sel_path = _resolve_data_path("model_params.json")
        sel_model = load_model_json(sel_path) if sel_path else None
        sel_available = bool(sel_model)
        if sel_model:
            logger.info("Cargado modelo selecciones desde %s", sel_path)
        else:
            logger.info("No se encontró model_params.json para selecciones")
            sel_model = fallback

        club_path = _resolve_data_path("model_params_clubes.json")
        club_model = load_model_json(club_path) if club_path else None
        club_available = bool(club_model)
        if club_model:
            logger.info("Cargado modelo clubes desde %s", club_path)
        else:
            logger.info("No se encontró modelo para clubes, se usará el de selecciones como fallback")

        app.state.sel_model = sel_model
        app.state.club_model = club_model
        app.state.model = sel_model
        app.state.prediction_models_status = {
            "status": "ok" if sel_available else "degraded",
            "selecciones": {"available": sel_available, "path": sel_path},
            "clubes": {"available": club_available, "path": club_path},
        }
    except Exception:
        logger.exception("No se pudo cargar model_params.json; usando neutrales en memoria")
        app.state.sel_model = fallback
        app.state.club_model = None
        app.state.model = fallback
        app.state.prediction_models_status = {
            "status": "degraded",
            "selecciones": {"available": False, "path": None},
            "clubes": {"available": False, "path": None},
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
