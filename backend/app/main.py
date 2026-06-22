
from typing import List

import logging
from fastapi import FastAPI, HTTPException
from sqlmodel import Session, select, SQLModel

from .database import engine
from .models import Partido
from .dixoncoles import fit_dixon_coles, predict_exact_score_matrix
from .sync import sync_fixtures_and_metrics

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


app = FastAPI(title="Estadisticas Futbol - Backend")


@app.on_event("startup")
def on_startup():
    # Crear tablas en la base de datos (requerimiento explícito)
    try:
        SQLModel.metadata.create_all(engine)
        logger.info("Tablas creadas/confirmadas en la base de datos")
    except Exception:
        logger.exception("Fallo creando tablas en la base de datos al startup. Continuando...")

    # Ejecutar sincronización inicial, pero no provocar crash si falla
    try:
        logger.info("Iniciando sincronización de fixtures y métricas...")
        sync_summary = sync_fixtures_and_metrics()
        logger.info("Sincronización finalizada: %s", sync_summary)
    except Exception:
        logger.exception("Error durante la sincronización en startup. Continuando sin bloquear el servidor.")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/fixtures")
def list_fixtures():
    """Devuelve todos los partidos almacenados (para debugging/frontend)."""
    with Session(engine) as session:
        partidos: List[Partido] = session.exec(select(Partido)).all()
        # Convertir a dicts para serializar fácilmente
        return [p.dict() for p in partidos]


@app.get("/api/partidos/{fixture_id}/prediccion")
def partido_prediccion(fixture_id: int, max_goals: int = 5):
    """Endpoint de prueba que ajusta Dixon-Coles y devuelve la matriz de probabilidades.

    Nota: puede fallar si los nombres de equipo no existen en el dataset histórico.
    """
    with Session(engine) as session:
        partido = session.exec(select(Partido).where(Partido.fixture_id == fixture_id)).first()
        if not partido:
            raise HTTPException(status_code=404, detail="Partido no encontrado")

    # Entrenar/obtener modelo Dixon-Coles
    try:
        model = fit_dixon_coles()
    except Exception as e:
        logger.exception("Error entrenando Dixon-Coles: %s", e)
        raise HTTPException(status_code=500, detail=f"Error entrenando modelo: {e}")

    # Predecir matriz de probabilidades usando nombres de equipo
    try:
        matrix = predict_exact_score_matrix(partido.home_team, partido.away_team, model, max_goals=max_goals)
    except Exception as e:
        logger.exception("Error calculando predicción para fixture %s: %s", fixture_id, e)
        raise HTTPException(status_code=500, detail=f"Error calculando predicción: {e}")

    return {
        "fixture_id": fixture_id,
        "home_team": partido.home_team,
        "away_team": partido.away_team,
        "max_goals": max_goals,
        "prob_matrix": matrix,
        "model_summary": {"rho": model.get('rho'), "n_teams": len(model.get('teams', []))},
    }
