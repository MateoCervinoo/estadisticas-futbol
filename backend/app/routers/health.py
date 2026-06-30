from typing import List

from fastapi import APIRouter
from sqlmodel import select

from ..database import engine
from ..db.session import Session
from ..models import Partido

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/fixtures")
def list_fixtures():
    """Devuelve todos los partidos almacenados (para debugging/frontend)."""
    with Session(engine) as session:
        partidos: List[Partido] = session.exec(select(Partido)).all()
        return [p.dict() for p in partidos]
