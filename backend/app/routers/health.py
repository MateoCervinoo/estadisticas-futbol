from typing import List

import os

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import text
from sqlmodel import select

from ..db.session import Session, engine
from ..models import Partido

router = APIRouter()


def require_debug_endpoints_enabled() -> None:
    if os.getenv("ENABLE_DEBUG_ENDPOINTS", "").lower() not in {"1", "true", "yes"}:
        raise HTTPException(status_code=404, detail="Not found")


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/health/db")
def health_db():
    try:
        with Session(engine) as session:
            session.exec(text("SELECT 1")).one()
    except Exception as exc:
        raise HTTPException(status_code=503, detail={"status": "unavailable"}) from exc
    return {"status": "ok"}


@router.get("/health/model")
def health_model(request: Request):
    status = getattr(request.app.state, "prediction_models_status", None)
    if status is None or not hasattr(request.app.state, "model"):
        raise HTTPException(status_code=503, detail={"status": "unavailable"})
    return status


@router.get("/fixtures")
def list_fixtures():
    """Devuelve todos los partidos almacenados (para debugging/frontend)."""
    require_debug_endpoints_enabled()
    with Session(engine) as session:
        partidos: List[Partido] = session.exec(select(Partido)).all()
        return [p.dict() for p in partidos]
