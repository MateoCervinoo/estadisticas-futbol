
from fastapi import FastAPI, HTTPException
from sqlmodel import Session

from .models import Partido
from .dixoncoles import fit_dixon_coles, predict_exact_score_matrix
from .database import init_db


app = FastAPI(title="Estadisticas Futbol - Backend")


@app.on_event("startup")
def on_startup():
    # Inicializar DB (crea tablas si no existen)
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/partidos/{partido_id}/prediccion")
def partido_prediccion(partido_id: int, max_goals: int = 5):
    # Verificar que el partido existe y está programado
    with Session(engine) as session:
        partido = session.get(Partido, partido_id)
        if not partido:
            raise HTTPException(status_code=404, detail="Partido no encontrado")
        if partido.estado != "programado":
            raise HTTPException(status_code=400, detail="Predicciones solo para partidos programados")

    # Ajustar modelo Dixon-Coles con partidos finalizados
    try:
        model = fit_dixon_coles()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error entrenando modelo: {e}")

    try:
        matrix = predict_exact_score_matrix(partido.local_id, partido.visitante_id, model, max_goals=max_goals)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculando predicción: {e}")

    return {
        "partido_id": partido_id,
        "local_id": partido.local_id,
        "visitante_id": partido.visitante_id,
        "max_goals": max_goals,
        "prob_matrix": matrix,
        "model_summary": {"rho": model.get('rho'), "n_teams": len(model.get('teams', []))}
    }
