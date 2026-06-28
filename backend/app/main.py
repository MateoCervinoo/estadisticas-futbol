
from typing import List

import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select, SQLModel

from .database import engine, ensure_partido_columns
from .models import Partido, Equipo
from .dixoncoles import predict_match, predict_exact_score_matrix
from .sync import sync_fixtures_and_metrics
import pandas as pd
import os
import json
import datetime
from typing import Any
import numpy as np

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


app = FastAPI(title="Estadisticas Futbol - Backend")


@app.on_event("startup")
def on_startup():
    # Crear tablas en la base de datos (requerimiento explícito)
    try:
        SQLModel.metadata.create_all(engine)
        ensure_partido_columns()
        logger.info("Tablas creadas/confirmadas en la base de datos")
    except Exception:
        logger.exception("Fallo creando tablas en la base de datos al startup. Continuando...")

    # Ejecutar sincronización inicial, pero no provocar crash si falla
    try:
        # Seedear la tabla Equipo para normalización si es necesario (no lee results.csv)
        try:
            from .data_manager import seed_equipos_if_empty
            seed_equipos_if_empty()
        except Exception:
            logger.exception("No se pudo seedear la tabla Equipo; continuando de todos modos.")

        # Cargar parámetros Dixon-Coles desde JSON (si existe). No entrenamos nada en el backend.
        try:
            logger.info("Cargando parámetros Dixon-Coles desde JSON (si existe)...")
            try:
                # Intentamos cargar y guardar en app.state.model; si no existe, dejamos neutrales
                app.state.model = None
                json_path = os.path.join('/', 'app', 'data', 'model_params.json')
                alt_path = os.path.join(os.path.dirname(__file__), 'data', 'model_params.json')
                model = None
                if os.path.exists(json_path):
                    with open(json_path, 'r') as fh:
                        model = json.load(fh)
                        # Diagnostic print requested
                        print(f"🚨 EXITO: JSON cargado correctamente. Llaves principales: {list(model.keys())}")
                        logger.info("Cargado modelo Dixon-Coles desde %s", json_path)
                elif os.path.exists(alt_path):
                    with open(alt_path, 'r') as fh:
                        model = json.load(fh)
                        # Diagnostic print requested
                        print(f"🚨 EXITO: JSON cargado correctamente. Llaves principales: {list(model.keys())}")
                        logger.info("Cargado modelo Dixon-Coles desde %s", alt_path)

                if model is None:
                    # Diagnostic: file not found in either location
                    print("🚨 ERROR FATAL: El archivo model_params.json no existe en el contenedor. Usando valores 1.0 por defecto.")
                    model = {
                        'teams': [],
                        'team_to_idx': {},
                        'attack': [],
                        'defense': [],
                        'gamma': 1.0,
                        'rho': 1.0,
                    }

                app.state.model = model
            except Exception:
                # If an error occurred reading the JSON, inform via print and keep neutrals
                print("🚨 ERROR FATAL: El archivo model_params.json no existe en el contenedor o no pudo leerse. Usando valores 1.0 por defecto.")
                logger.exception("No se pudo cargar model_params.json; usando neutrales en memoria")
                app.state.model = {
                    'teams': [],
                    'team_to_idx': {},
                    'attack': [],
                    'defense': [],
                    'gamma': 1.0,
                    'rho': 1.0,
                }

            # Ejecutar sincronización de fixtures y métricas (dentro del mismo try para capturar errores)
            logger.info("Iniciando sincronización de fixtures y métricas...")
            sync_summary = sync_fixtures_and_metrics()
            logger.info("Sincronización finalizada: %s", sync_summary)
        except Exception:
            logger.exception("Error durante la carga de parámetros/sincronización en startup. Continuando sin bloquear el servidor.")

    except Exception:
        # Catch-all for the outer startup try-block to ensure the function is syntactically correct
        logger.exception("Error inesperado en on_startup(); continuando sin bloquear el servidor.")

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


# Configurar CORS para permitir peticiones desde el frontend en desarrollo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/partidos")
def api_list_partidos():
    """Devuelve todos los partidos ordenados por fecha."""
    with Session(engine) as session:
        # Hacer LEFT JOIN con Equipo para incluir nombres en español y códigos de bandera
        stmt = select(Partido).order_by(Partido.fecha_utc)
        partidos: List[Partido] = session.exec(stmt).all()

        out = []
        for p in partidos:
            item = p.dict()
            # Intentar anexar información de home/away desde tabla Equipo
            try:
                    if p.equipo_local_id:
                        he = session.get(Equipo, p.equipo_local_id)
                        if he:
                            item["home_nombre_es"] = he.nombre_es
                            item["home_codigo_bandera"] = he.codigo_bandera
                    if p.equipo_visitante_id:
                        ae = session.get(Equipo, p.equipo_visitante_id)
                        if ae:
                            item["away_nombre_es"] = ae.nombre_es
                            item["away_codigo_bandera"] = ae.codigo_bandera
            except Exception:
                pass
            out.append(item)

        return out


@app.get("/api/partidos/finalizados")
def api_list_partidos_finalizados():
    """Devuelve únicamente los partidos con estado 'FT' (finalizados)."""
    with Session(engine) as session:
        stmt = select(Partido).where(Partido.estado == "FT").order_by(Partido.fecha_utc)
        partidos: List[Partido] = session.exec(stmt).all()
        out = []
        for p in partidos:
            item = p.dict()
            try:
                if p.equipo_local_id:
                    he = session.get(Equipo, p.equipo_local_id)
                    if he:
                        item["home_nombre_es"] = he.nombre_es
                        item["home_codigo_bandera"] = he.codigo_bandera
                if p.equipo_visitante_id:
                    ae = session.get(Equipo, p.equipo_visitante_id)
                    if ae:
                        item["away_nombre_es"] = ae.nombre_es
                        item["away_codigo_bandera"] = ae.codigo_bandera
            except Exception:
                pass
            out.append(item)
        return out


# Endpoint /api/partidos/{partido_id}/prediccion implemented below. Kept only one route to avoid duplicates.


@app.get("/api/partidos/{partido_id}/prediccion")
def partido_prediccion_alt(partido_id: int):
    """Endpoint compatible con el frontend: devuelve probabilidades agregadas y
    una lista aplanada de score_matrix con campos {home, away, prob} (porcentaje).
    Genera una matriz de 0..4 goles por equipo.
    """
    max_goals = 4
    with Session(engine) as session:
        partido = session.exec(select(Partido).where(Partido.fixture_id == partido_id)).first()
        if not partido:
            raise HTTPException(status_code=404, detail="Partido no encontrado")

    # Resolver nombres canónicos a pasar al modelo: preferir nombre_csv de Equipo si existe
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
        # No bloquear; usaremos los nombres originales como fallback
        logger.exception("Error resolviendo Equipo para partido %s; usando nombres sin normalizar", partido.fixture_id)

    # Local helper to load params safely at request time from /app/data/model_params.json
    def get_params():
        try:
            model = getattr(app.state, 'model', None)
            if model is not None:
                return model
            json_path = os.path.join('/', 'app', 'data', 'model_params.json')
            alt_json = os.path.join(os.path.dirname(__file__), 'data', 'model_params.json')
            if os.path.exists(json_path):
                with open(json_path, 'r') as fh:
                    return json.load(fh)
            if os.path.exists(alt_json):
                with open(alt_json, 'r') as fh:
                    return json.load(fh)
        except Exception:
            logger.exception("Error leyendo model_params.json en get_params(); usando neutrales")

        # Fallback neutrales (attack/defense como dicts)
        return {
            'teams': [],
            'attack': {},
            'defense': {},
            'gamma': 1.0,
            'rho': 1.0,
        }

    model = get_params()

    # Construir modelo mínimo si el mapping por nombre no incluye los equipos solicitados
    def _norm(s: str) -> str:
        try:
            return s.strip().casefold()
        except Exception:
            return str(s).strip().casefold()

    hkey = _norm(home_name_for_model)
    akey = _norm(away_name_for_model)

    # If model already uses dicts keyed by normalized names, use it directly
    attack_param = model.get('attack') if isinstance(model, dict) else None
    defense_param = model.get('defense') if isinstance(model, dict) else None

    if isinstance(attack_param, dict) and isinstance(defense_param, dict):
        model_for_pred = model
    else:
        # fallback minimal dicts keyed by normalized names
        gamma = float(model.get('gamma', 1.0)) if isinstance(model, dict) else 1.0
        rho = float(model.get('rho', 1.0)) if isinstance(model, dict) else 1.0
        model_for_pred = {
            'teams': [home_name_for_model, away_name_for_model],
            'attack': {hkey: 1.0, akey: 1.0},
            'defense': {hkey: 1.0, akey: 1.0},
            'gamma': gamma,
            'rho': rho,
        }

    # Llamada matemática pura e instantánea a la función de predicción
    try:
        P = predict_match(home_name_for_model, away_name_for_model, model_for_pred, max_goals=max_goals, neutral=True)
    except Exception:
        logger.exception("Error generando predicción matemática para partido %s (%s vs %s)", partido.fixture_id, home_name_for_model, away_name_for_model)
        P = None

    # Validate matrix P: ensure it is a List[List[float]] and well-formed. Otherwise replace with 5x5 safe matrix.
    import numpy as np

    def _is_valid_matrix(mat):
        # Must be a sequence of sequences (list of lists) of numbers with finite values and positive sum
        try:
            if not isinstance(mat, (list, tuple)):
                return False
            # Ensure each row is a list/tuple and all rows have same length
            if len(mat) == 0:
                return False
            row_len = None
            total = 0.0
            for r in mat:
                if not isinstance(r, (list, tuple)):
                    return False
                if row_len is None:
                    row_len = len(r)
                    if row_len == 0:
                        return False
                elif len(r) != row_len:
                    return False
                for v in r:
                    # Allow ints/floats castable to float
                    fv = float(v)
                    if not np.isfinite(fv):
                        return False
                    total += fv
            if not np.isfinite(total) or total <= 0.0:
                return False
            return True
        except Exception:
            return False

    # If P is None or structurally invalid, do not attempt to serialize a broken matrix.
    # Return a friendly JSON indicating that prediction is in progress or data is insufficient.
    if P is None or not _is_valid_matrix(P):
        logger.warning("Predicción no válida para partido %s: matriz vacía o con valores no finitos", partido.fixture_id)
        return {
            "status": "insufficient_data",
            "message": "Predicción en curso o datos insuficientes para generar probabilidades",
        }

    # Convertir a porcentajes y preparar matrix 2D y flattened list
    n = len(P)
    home_win = 0.0
    draw = 0.0
    away_win = 0.0
    matrix = []
    flat = []
    max_prob = -1.0
    most_likely = {"home": 0, "away": 0}
    for i in range(n):
        row = []
        for j in range(n):
            p = float(P[i][j])
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

    # Return the shape expected by the frontend: flattened score_matrix list of dicts
    return {
        "home_win": round(home_win * 100, 2),
        "draw": round(draw * 100, 2),
        "away_win": round(away_win * 100, 2),
        # Provide both formats: 2D matrix for frontend rendering and flattened list
        "score_matrix": matrix,
        "score_matrix_flat": flat,
        "most_likely": most_likely,
    }


@app.get("/api/debug/datos-corruptos")
def debug_datos_corruptos():
    """Devuelve el contenido de /app/data/bad_records.csv si existe para facilitar auditoría desde el navegador."""
    bad_path = os.path.join(os.path.dirname(__file__), "data", "bad_records.csv")
    # También comprobar la ruta del contenedor /app/data/bad_records.csv
    alt_path = os.path.join('/', 'app', 'data', 'bad_records.csv')
    chosen = None
    if os.path.exists(bad_path):
        chosen = bad_path
    elif os.path.exists(alt_path):
        chosen = alt_path

    if not chosen:
        return {"warning": "No se encontró bad_records.csv"}

    try:
        df = pd.read_csv(chosen)
        # Devolver como lista de registros JSON serializables
        records = df.to_dict(orient='records')
        return {"path": chosen, "count": len(records), "records": records}
    except Exception:
        logger.exception("Error leyendo %s", chosen)
        raise HTTPException(status_code=500, detail="No se pudo leer el archivo de registros corruptos")
