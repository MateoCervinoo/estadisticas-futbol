
from typing import List, Optional

import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select, SQLModel
from sqlalchemy import or_, and_

from .database import engine, ensure_partido_columns
from .models import Partido, Equipo, PartidoEstadisticas
from .dixoncoles import predict_match, predict_exact_score_matrix, load_model_json, select_model_for_match
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
                data_dir = os.path.join('/', 'app', 'data')
                alt_data_dir = os.path.join(os.path.dirname(__file__), 'data')

                def _resolve_path(filename):
                    fp = os.path.join(data_dir, filename)
                    if os.path.exists(fp):
                        return fp
                    fp = os.path.join(alt_data_dir, filename)
                    if os.path.exists(fp):
                        return fp
                    return None

                # Load selecciones model
                sel_path = _resolve_path("model_params.json")
                sel_model = load_model_json(sel_path) if sel_path else None
                if sel_model:
                    print(f"🚨 Modelo selecciones cargado. Llaves: {list(sel_model.keys())}")
                    logger.info("Cargado modelo selecciones desde %s", sel_path)
                else:
                    print("🚨 No se encontró model_params.json para selecciones")
                    sel_model = {
                        'teams': [], 'team_to_idx': {},
                        'attack': {}, 'defense': {},
                        'gamma': 1.0, 'rho': 1.0,
                    }

                # Load clubes model
                club_path = _resolve_path("model_params_clubes.json")
                club_model = load_model_json(club_path) if club_path else None
                if club_model:
                    print(f"🚨 Modelo clubes cargado. Llaves: {list(club_model.keys())}")
                    logger.info("Cargado modelo clubes desde %s", club_path)
                else:
                    club_model = None
                    logger.info("No se encontró modelo para clubes, se usará el de selecciones como fallback")

                app.state.sel_model = sel_model
                app.state.club_model = club_model
                app.state.model = sel_model  # keep backwards compat
            except Exception:
                logger.exception("No se pudo cargar model_params.json; usando neutrales en memoria")
                fallback = {
                    'teams': [], 'team_to_idx': {},
                    'attack': {}, 'defense': {},
                    'gamma': 1.0, 'rho': 1.0,
                }
                app.state.sel_model = fallback
                app.state.club_model = None
                app.state.model = fallback

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


def _enrich_partido_item(p: Partido, session: Session) -> dict:
    item = p.dict()

    # Mapear nombres de campos del modelo unificado (español) al frontend (inglés)
    FIELD_MAP = {
        "date": "fecha_utc",
        "home_score": "goles_local",
        "away_score": "goles_visitante",
        "status": "estado",
        "stage": "etapa",
        "group": "grupo",
        "ht_home_score": "goles_local_ht",
        "ht_away_score": "goles_visitante_ht",
    }
    for eng, spa in FIELD_MAP.items():
        item[eng] = item.get(spa)

    try:
        # Resolver nombre/localidad del equipo local
        if p.equipo_local_id:
            he = session.get(Equipo, p.equipo_local_id)
            if he:
                item["home_nombre_es"] = he.nombre_es
                item["home_codigo_bandera"] = he.codigo_bandera
                if not item.get("home_team"):
                    item["home_team"] = he.nombre_canonico
        # Resolver nombre/localidad del equipo visitante
        if p.equipo_visitante_id:
            ae = session.get(Equipo, p.equipo_visitante_id)
            if ae:
                item["away_nombre_es"] = ae.nombre_es
                item["away_codigo_bandera"] = ae.codigo_bandera
                if not item.get("away_team"):
                    item["away_team"] = ae.nombre_canonico
    except Exception:
        pass

    return item


@app.get("/api/partidos/anyos")
def api_list_anyos():
    """Devuelve los años disponibles en la base de datos (para el filtro de año)."""
    with Session(engine) as session:
        import datetime
        all_fechas = session.exec(select(Partido.fecha_utc)).all()
        years = sorted({dt.year for dt in all_fechas if dt is not None})
        return years


@app.get("/api/partidos")
def api_list_partidos(
    mundial: bool = False,
    proximos: bool = False,
    year: Optional[int] = None,
):
    """Devuelve partidos ordenados por fecha.
    - mundial=true: solo FIFA World Cup
    - proximos=true: solo estados NS/TIMED
    - year=AAAA: filtrar por año
    - sin parámetros: todos los partidos
    """
    with Session(engine) as session:
        stmt = select(Partido).order_by(Partido.fecha_utc)

        main_conditions = []
        if mundial:
            from .models import Torneo
            t = session.exec(
                select(Torneo).where(Torneo.nombre_canonico == "FIFA World Cup")
            ).first()
            if t:
                main_conditions.append(Partido.torneo_id == t.id)
        if proximos:
            main_conditions.append(Partido.estado.in_(["NS", "TIMED"]))

        all_conditions = []
        if main_conditions:
            all_conditions.append(or_(*main_conditions))
        if year is not None:
            from sqlalchemy import extract
            all_conditions.append(extract('year', Partido.fecha_utc) == year)

        if all_conditions:
            stmt = stmt.where(and_(*all_conditions))

        partidos: List[Partido] = session.exec(stmt).all()
        return [_enrich_partido_item(p, session) for p in partidos]


@app.get("/api/partidos/finalizados")
def api_list_partidos_finalizados():
    """Devuelve únicamente los partidos con estado 'FT' (finalizados)."""
    with Session(engine) as session:
        stmt = select(Partido).where(Partido.estado == "FT").order_by(Partido.fecha_utc)
        partidos: List[Partido] = session.exec(stmt).all()
        return [_enrich_partido_item(p, session) for p in partidos]


@app.get("/api/partidos/{partido_id}/estadisticas")
def api_partido_estadisticas(partido_id: int):
    """Devuelve estadísticas avanzadas para un partido."""
    with Session(engine) as session:
        partido = session.get(Partido, partido_id)
        if not partido:
            raise HTTPException(status_code=404, detail="Partido no encontrado")

        stats = session.exec(
            select(PartidoEstadisticas).where(PartidoEstadisticas.partido_id == partido_id)
        ).all()

        result = _enrich_partido_item(partido, session)
        result['estadisticas'] = [s.dict() for s in stats] if stats else []
        return result


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

    # Select model based on match category
    sel_model = getattr(app.state, 'sel_model', None)
    club_model = getattr(app.state, 'club_model', None)
    model = select_model_for_match(partido_id, engine, sel_model, club_model)
    if model is None:
        model = {
            'teams': [],
            'attack': {},
            'defense': {},
            'gamma': 1.0,
            'rho': 1.0,
        }

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
