
from typing import List, Optional

import logging
import asyncio
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select, SQLModel
from sqlalchemy import or_, and_, func

from .database import engine, ensure_partido_columns
from .models import Partido, Equipo, PartidoEstadisticas, Notificacion, Torneo
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

# ──────────── WebSocket Connection Manager ────────────

class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, data: dict):
        for ws in self.active[:]:
            try:
                await ws.send_json(data)
            except Exception:
                self.disconnect(ws)

manager = ConnectionManager()
last_broadcasted_id = 0

async def broadcast_new_notifications():
    global last_broadcasted_id
    while True:
        try:
            def query():
                with Session(engine) as session:
                    stmt = select(Notificacion).where(Notificacion.id > last_broadcasted_id).order_by(Notificacion.id)
                    return session.exec(stmt).all()
            notifs = await asyncio.to_thread(query)
            for n in notifs:
                await manager.broadcast({
                    "type": "notification",
                    "data": {
                        "id": n.id,
                        "partido_id": n.partido_id,
                        "tipo": n.tipo,
                        "mensaje": n.mensaje,
                        "created_at": n.created_at.isoformat() if n.created_at else None,
                    }
                })
                last_broadcasted_id = n.id
        except Exception:
            pass
        await asyncio.sleep(5)


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

    # Background task for broadcasting notifications via WebSocket
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(broadcast_new_notifications())
        logger.info("Background notification broadcaster started")
    except Exception:
        logger.exception("No se pudo iniciar el broadcaster de notificaciones")

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
        "matchday": "jornada",
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


def _dedupe_partido_items(items: list[dict]) -> list[dict]:
    """Evita devolver dos fuentes del mismo partido en listados generales."""
    by_key: dict[str, dict] = {}
    for item in items:
        raw_date = item.get("date") or item.get("fecha_utc") or ""
        date_key = str(raw_date)[:10]
        tournament = str(item.get("tournament") or "").strip().casefold()
        home = str(item.get("home_team") or item.get("home_nombre_es") or "").strip().casefold()
        away = str(item.get("away_team") or item.get("away_nombre_es") or "").strip().casefold()
        key = "|".join([date_key, home, away, tournament])

        current = by_key.get(key)
        if current is None:
            by_key[key] = item
            continue

        current_has_fixture = current.get("fixture_id") is not None
        item_has_fixture = item.get("fixture_id") is not None
        current_has_media = bool(current.get("home_crest_url") or current.get("away_crest_url"))
        item_has_media = bool(item.get("home_crest_url") or item.get("away_crest_url"))
        if (item_has_fixture and not current_has_fixture) or (item_has_media and not current_has_media):
            by_key[key] = item

    return list(by_key.values())


def _season_bounds(season: Optional[str] = None, year: Optional[int] = None) -> tuple[Optional[datetime.datetime], Optional[datetime.datetime]]:
    if season:
        try:
            start_year = int(str(season).split("/")[0])
            return datetime.datetime(start_year, 7, 1), datetime.datetime(start_year + 1, 7, 1)
        except Exception:
            return None, None
    if year is not None:
        return datetime.datetime(year, 1, 1), datetime.datetime(year + 1, 1, 1)
    return None, None


def _season_label_for_match(match_date: datetime.datetime, tournament_type: str | None = None) -> str:
    if tournament_type == "mundial":
        return str(match_date.year)
    if match_date.month >= 7:
        return f"{match_date.year}/{str(match_date.year + 1)[-2:]}"
    return f"{match_date.year - 1}/{str(match_date.year)[-2:]}"


def _is_finished_match(p: Partido) -> bool:
    if p.goles_local is None or p.goles_visitante is None:
        return False
    return str(p.estado or "").upper() in {"FT", "AET", "PEN", "FINISHED"}


@app.get("/api/partidos/anyos")
def api_list_anyos():
    """Devuelve los años disponibles en la base de datos (para el filtro de año)."""
    with Session(engine) as session:
        import datetime
        all_fechas = session.exec(select(Partido.fecha_utc)).all()
        years = sorted({dt.year for dt in all_fechas if dt is not None})
        return years


@app.get("/api/partidos/filtros")
def api_partidos_filtros(
    tournament: Optional[str] = None,
    year: Optional[int] = None,
    season: Optional[str] = None,
    stage: Optional[str] = None,
):
    """Metadata liviana para armar filtros sin descargar todos los partidos."""
    with Session(engine) as session:
        conditions = []
        if tournament:
            conditions.append(Partido.tournament == tournament)
        start, end = _season_bounds(season=season, year=year)
        if start and end:
            conditions.extend([Partido.fecha_utc >= start, Partido.fecha_utc < end])

        stmt = select(Partido)
        if conditions:
            stmt = stmt.where(*conditions)
        partidos = session.exec(stmt).all()

        tournaments = sorted({p.tournament for p in partidos if p.tournament})
        stages = sorted({p.etapa for p in partidos if p.etapa})
        if stage and stage not in ("Todos", "GROUP_STAGE"):
            groups = []
        else:
            groups = sorted({p.grupo for p in partidos if p.grupo})
        matchdays = sorted({p.jornada for p in partidos if p.jornada is not None})
        dates = sorted({p.fecha_utc.date().isoformat() for p in partidos if p.fecha_utc is not None})
        years = sorted({p.fecha_utc.year for p in partidos if p.fecha_utc is not None})

        return {
            "years": years,
            "tournaments": tournaments,
            "stages": stages,
            "groups": groups,
            "matchdays": matchdays,
            "dates": dates,
        }


@app.get("/api/partidos")
def api_list_partidos(
    mundial: bool = False,
    proximos: bool = False,
    year: Optional[int] = None,
    season: Optional[str] = None,
    torneo_id: Optional[int] = None,
    tournament: Optional[str] = None,
    stage: Optional[str] = None,
    group: Optional[str] = None,
    matchday: Optional[int] = None,
    date: Optional[str] = None,
):
    """Devuelve partidos ordenados por fecha.
    - mundial=true: solo FIFA World Cup
    - proximos=true: solo estados NS/TIMED
    - year=AAAA: filtrar por año
    - season=2025/26: temporada de clubes
    - torneo_id/tournament/stage/group/date: filtros exactos
    - sin parámetros: todos los partidos
    """
    with Session(engine) as session:
        stmt = select(Partido).order_by(Partido.fecha_utc)

        main_conditions = []
        if mundial:
            from .models import Torneo
            torneos = session.exec(
                select(Torneo).where(or_(
                    Torneo.nombre_canonico.ilike("%world cup%"),
                    Torneo.nombre_canonico.ilike("%mundial%"),
                ))
            ).all()
            torneo_ids = [t.id for t in torneos if t.id is not None]
            conditions = []
            if torneo_ids:
                conditions.append(Partido.torneo_id.in_(torneo_ids))
            conditions.append(Partido.tournament.ilike("%world cup%"))
            conditions.append(Partido.tournament.ilike("%mundial%"))
            main_conditions.append(or_(*conditions))
        if proximos:
            main_conditions.append(Partido.estado.in_(["NS", "TIMED"]))

        all_conditions = []
        if main_conditions:
            all_conditions.append(or_(*main_conditions))
        if year is not None:
            start, end = _season_bounds(year=year)
            if start and end:
                all_conditions.append(Partido.fecha_utc >= start)
                all_conditions.append(Partido.fecha_utc < end)
        if season:
            start, end = _season_bounds(season=season)
            if start and end:
                all_conditions.append(Partido.fecha_utc >= start)
                all_conditions.append(Partido.fecha_utc < end)
        if torneo_id is not None:
            all_conditions.append(Partido.torneo_id == torneo_id)
        if tournament:
            all_conditions.append(Partido.tournament == tournament)
        if stage:
            all_conditions.append(Partido.etapa == stage)
        if group:
            all_conditions.append(Partido.grupo == group)
        if matchday is not None:
            all_conditions.append(Partido.jornada == matchday)
        if date:
            all_conditions.append(func.date(Partido.fecha_utc) == date)

        if all_conditions:
            stmt = stmt.where(and_(*all_conditions))

        partidos: List[Partido] = session.exec(stmt).all()
        items = [_enrich_partido_item(p, session) for p in partidos]
        return _dedupe_partido_items(items)


@app.get("/api/torneos/{torneo_id}/temporadas")
def api_torneo_temporadas(torneo_id: int):
    """Devuelve temporadas disponibles para un torneo."""
    with Session(engine) as session:
        torneo = session.get(Torneo, torneo_id)
        if not torneo:
            raise HTTPException(404, "Torneo no encontrado")
        partidos = session.exec(
            select(Partido).where(Partido.torneo_id == torneo_id, Partido.fecha_utc.isnot(None))
        ).all()
        labels = sorted(
            {_season_label_for_match(p.fecha_utc, torneo.tipo) for p in partidos if p.fecha_utc},
            reverse=True,
        )
        return {"torneo_id": torneo_id, "temporadas": labels}


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
    model = select_model_for_match(partido.id if partido else partido_id, engine, sel_model, club_model)
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


# ──────────────────────────────────────────────
# FASE 6 — Live Alerts + Notifications
# ──────────────────────────────────────────────

@app.websocket("/ws/matches")
async def ws_matches(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)


@app.get("/api/notificaciones")
def api_notificaciones(no_leidas: bool = False):
    """Lista de notificaciones. Pasá no_leidas=true para solo las no leídas."""
    with Session(engine) as session:
        stmt = select(Notificacion).order_by(Notificacion.id.desc()).limit(50)
        if no_leidas:
            stmt = stmt.where(Notificacion.leida == False)
        notifs = session.exec(stmt).all()
        return [
            {
                "id": n.id,
                "partido_id": n.partido_id,
                "tipo": n.tipo,
                "mensaje": n.mensaje,
                "leida": n.leida,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in notifs
        ]


@app.get("/api/notificaciones/no-leidas")
def api_notificaciones_no_leidas_count():
    """Cantidad de notificaciones no leídas."""
    with Session(engine) as session:
        count = session.exec(
            select(Notificacion).where(Notificacion.leida == False)
        ).all()
        return {"count": len(count)}


@app.post("/api/notificaciones/{notif_id}/leer")
def api_notificacion_leer(notif_id: int):
    """Marca una notificación como leída."""
    with Session(engine) as session:
        n = session.get(Notificacion, notif_id)
        if not n:
            raise HTTPException(404, "Notificación no encontrada")
        n.leida = True
        session.add(n)
        session.commit()
        return {"ok": True}


@app.post("/api/notificaciones/leer-todas")
def api_notificaciones_leer_todas():
    """Marca todas las notificaciones como leídas."""
    with Session(engine) as session:
        notifs = session.exec(select(Notificacion).where(Notificacion.leida == False)).all()
        for n in notifs:
            n.leida = True
            session.add(n)
        session.commit()
        return {"ok": True, "marcadas": len(notifs)}


@app.get("/api/partidos/live")
def api_partidos_live():
    """Devuelve partidos actualmente en vivo (estado IN_PLAY)."""
    with Session(engine) as session:
        partidos = session.exec(
            select(Partido).where(Partido.estado == "IN_PLAY")
        ).all()
        return [_enrich_partido_item(p, session) for p in partidos]


# ──────────────────────────────────────────────
# FASE 7 — Análisis Avanzado + Dashboard
# ──────────────────────────────────────────────


import math
from collections import Counter


@app.get("/api/equipos/{equipo_id}/evolution")
def api_equipo_evolution(equipo_id: int):
    """Evolución de ataque/defensa (rolling avg) de un equipo en el tiempo."""
    from .models import Equipo as EqModel
    with Session(engine) as session:
        eq = session.get(EqModel, equipo_id)
        if not eq:
            raise HTTPException(404, "Equipo no encontrado")
        matches = session.exec(
            select(Partido).where(
                Partido.estado == "FT",
                Partido.goles_local.isnot(None),
                Partido.goles_visitante.isnot(None),
                (Partido.equipo_local_id == equipo_id) | (Partido.equipo_visitante_id == equipo_id),
            ).order_by(Partido.fecha_utc)
        ).all()
        if not matches:
            return {"equipo_id": equipo_id, "nombre": eq.nombre_canonico or "", "evolution": []}

        points = []
        for i in range(len(matches)):
            is_local = matches[i].equipo_local_id == equipo_id
            gf = matches[i].goles_local if is_local else matches[i].goles_visitante
            gc = matches[i].goles_visitante if is_local else matches[i].goles_local
            xgf = float(matches[i].xg_local) if is_local and matches[i].xg_local else (float(matches[i].xg_visitante) if not is_local and matches[i].xg_visitante else None)
            xgc = float(matches[i].xg_visitante) if is_local and matches[i].xg_visitante else (float(matches[i].xg_local) if not is_local and matches[i].xg_local else None)
            window = matches[max(0, i - 4):i + 1]
            rolling_gf = sum(
                (m.goles_local if m.equipo_local_id == equipo_id else m.goles_visitante) or 0
                for m in window
            ) / len(window)
            rolling_gc = sum(
                (m.goles_visitante if m.equipo_local_id == equipo_id else m.goles_local) or 0
                for m in window
            ) / len(window)
            points.append({
                "match_index": i + 1,
                "fecha": matches[i].fecha_utc.isoformat() if matches[i].fecha_utc else None,
                "resultado": "H" if gf > gc else ("A" if gf < gc else "D"),
                "gf": gf or 0,
                "gc": gc or 0,
                "rolling_gf_avg": round(rolling_gf, 2),
                "rolling_gc_avg": round(rolling_gc, 2),
                "xg_favor": xgf,
                "xg_contra": xgc,
            })
        return {"equipo_id": equipo_id, "nombre": eq.nombre_canonico or eq.nombre_es or eq.nombre_csv, "evolution": points}


@app.get("/api/equipos/{equipo_id}/distribucion")
def api_equipo_distribucion(equipo_id: int):
    """Distribución real de goles vs Poisson esperada para un equipo."""
    from .models import Equipo as EqModel
    with Session(engine) as session:
        eq = session.get(EqModel, equipo_id)
        if not eq:
            raise HTTPException(404, "Equipo no encontrado")
        matches = session.exec(
            select(Partido).where(
                Partido.estado == "FT",
                Partido.goles_local.isnot(None),
                Partido.goles_visitante.isnot(None),
                (Partido.equipo_local_id == equipo_id) | (Partido.equipo_visitante_id == equipo_id),
            )
        ).all()
        if not matches:
            return {"equipo_id": equipo_id, "nombre": eq.nombre_canonico or "", "total_partidos": 0, "avg_goles": 0, "distribucion": []}

        goals_scored = []
        for p in matches:
            goals_scored.append(p.goles_local if p.equipo_local_id == equipo_id else p.goles_visitante)

        actual_dist = Counter(goals_scored)
        avg_goals = sum(goals_scored) / len(goals_scored)
        max_goals = max(max(goals_scored), 5)
        dist = []
        for g in range(max_goals + 1):
            poisson_prob = (avg_goals ** g) * math.exp(-avg_goals) / math.factorial(g)
            actual_count = actual_dist.get(g, 0)
            actual_pct = (actual_count / len(goals_scored)) * 100
            dist.append({
                "goles": g,
                "actual_pct": round(actual_pct, 1),
                "poisson_pct": round(poisson_prob * 100, 1),
                "actual_partidos": actual_count,
            })
        return {
            "equipo_id": equipo_id,
            "nombre": eq.nombre_canonico or eq.nombre_es or eq.nombre_csv,
            "total_partidos": len(matches),
            "avg_goles": round(avg_goals, 2),
            "distribucion": dist,
        }


@app.get("/api/analytics/xg-vs-real")
def api_xg_vs_real(torneo_id: Optional[int] = None, tipo: Optional[str] = None):
    """Comparación xG vs goles reales por equipo (opcional filtrado por torneo)."""
    from .models import Equipo as EqModel
    with Session(engine) as session:
        stmt = select(Partido).where(
            Partido.estado == "FT",
            Partido.goles_local.isnot(None),
            Partido.goles_visitante.isnot(None),
        )
        if torneo_id is not None:
            stmt = stmt.where(Partido.torneo_id == torneo_id)
        matches = session.exec(stmt).all()

        team_stats: dict = {}
        for p in matches:
            for eid, is_local in [(p.equipo_local_id, True), (p.equipo_visitante_id, False)]:
                if eid is None:
                    continue
                if eid not in team_stats:
                    team_stats[eid] = {"pj": 0, "goles": 0, "xg": 0.0, "xga": 0.0}
                team_stats[eid]["pj"] += 1
                if is_local:
                    team_stats[eid]["goles"] += p.goles_local or 0
                    if p.xg_local is not None:
                        team_stats[eid]["xg"] += float(p.xg_local)
                    if p.xg_visitante is not None:
                        team_stats[eid]["xga"] += float(p.xg_visitante)
                else:
                    team_stats[eid]["goles"] += p.goles_visitante or 0
                    if p.xg_visitante is not None:
                        team_stats[eid]["xg"] += float(p.xg_visitante)
                    if p.xg_local is not None:
                        team_stats[eid]["xga"] += float(p.xg_local)

        result = []
        for eid, stats in team_stats.items():
            eq = session.get(EqModel, eid)
            if tipo in ("club", "seleccion") and eq and eq.tipo != tipo:
                continue
            nombre = eq.nombre_canonico or eq.nombre_es or eq.nombre_csv if eq else f"E{eid}"
            result.append({
                "equipo_id": eid,
                "nombre": nombre,
                "codigo_bandera": eq.codigo_bandera if eq else None,
                "pj": stats["pj"],
                "goles": stats["goles"],
                "xg": round(stats["xg"], 2),
                "xga": round(stats["xga"], 2),
                "diferencia": round(stats["goles"] - stats["xg"], 2),
                "xg_diff": round(stats["xg"] - stats["xga"], 2),
                "goles_p90": round(stats["goles"] / stats["pj"], 2) if stats["pj"] else 0,
                "xg_p90": round(stats["xg"] / stats["pj"], 2) if stats["pj"] else 0,
                "xga_p90": round(stats["xga"] / stats["pj"], 2) if stats["pj"] else 0,
            })
        result.sort(key=lambda r: -r["goles"])
        return result


@app.get("/api/equipos/search")
def api_equipos_search(q: str = "", tipo: Optional[str] = None):
    """Busca equipos por nombre."""
    from .models import Equipo as EqModel
    with Session(engine) as session:
        stmt = select(EqModel)
        if tipo in ("club", "seleccion"):
            stmt = stmt.where(EqModel.tipo == tipo)
        if q:
            like = f"%{q}%"
            stmt = stmt.where(or_(
                EqModel.nombre_canonico.ilike(like),
                EqModel.nombre_es.ilike(like),
                EqModel.nombre_api.ilike(like),
                EqModel.nombre_csv.ilike(like),
                EqModel.nombre_fbref.ilike(like),
                EqModel.nombre_understat.ilike(like),
            ))
        stmt = stmt.order_by(EqModel.nombre_canonico).limit(50)
        equipos = session.exec(stmt).all()
        return [
            {
                "id": e.id,
                "nombre": e.nombre_canonico or e.nombre_es or e.nombre_csv,
                "codigo_bandera": e.codigo_bandera,
            }
            for e in equipos
        ]


# ──────────────────────────────────────────────
# FASE 5 — Posiciones, Bracket, Perfil, Comparador
# ──────────────────────────────────────────────


@app.get("/api/torneos")
def api_list_torneos():
    """Devuelve todos los torneos con conteo de partidos."""
    from .models import Torneo as TorneoModel
    with Session(engine) as session:
        torneos = session.exec(select(TorneoModel)).all()
        result = []
        for t in torneos:
            count = session.exec(
                select(Partido).where(Partido.torneo_id == t.id)
            ).all()
            result.append({
                "id": t.id,
                "nombre_canonico": t.nombre_canonico,
                "tipo": t.tipo,
                "categoria": t.categoria,
                "nivel": t.nivel,
                "total_partidos": len(count),
            })
        return result


@app.get("/api/torneos/{torneo_id}/tabla-posiciones")
def api_torneo_tabla(
    torneo_id: int,
    year: Optional[int] = None,
    season: Optional[str] = None,
    grouped: bool = False,
):
    """Calcula tabla de posiciones para un torneo, con soporte de temporada y grupos."""
    from .models import Torneo as TorneoModel, Equipo as EquipoModel
    with Session(engine) as session:
        torneo = session.get(TorneoModel, torneo_id)
        if not torneo:
            raise HTTPException(404, "Torneo no encontrado")

        conditions = [Partido.torneo_id == torneo_id]
        start, end = _season_bounds(season=season, year=year)
        if start and end:
            conditions.append(Partido.fecha_utc >= start)
            conditions.append(Partido.fecha_utc < end)
        if grouped or torneo.tipo == "mundial":
            conditions.append(Partido.etapa == "GROUP_STAGE")

        partidos = session.exec(select(Partido).where(*conditions)).all()

    def build_rows(rows_partidos: list[Partido]) -> list[dict]:
        stats: dict[int, dict] = {}
        for p in rows_partidos:
            for eid in (p.equipo_local_id, p.equipo_visitante_id):
                if eid and eid not in stats:
                    stats[eid] = {"pj": 0, "pg": 0, "pe": 0, "pp": 0, "gf": 0, "gc": 0, "xg_favor": 0.0, "xg_contra": 0.0}

            if _is_finished_match(p) and p.equipo_local_id and p.equipo_visitante_id:
                gl, gv = p.goles_local, p.goles_visitante
                stats[p.equipo_local_id]["pj"] += 1
                stats[p.equipo_visitante_id]["pj"] += 1
                stats[p.equipo_local_id]["gf"] += gl
                stats[p.equipo_local_id]["gc"] += gv
                stats[p.equipo_visitante_id]["gf"] += gv
                stats[p.equipo_visitante_id]["gc"] += gl

                if p.xg_local is not None:
                    stats[p.equipo_local_id]["xg_favor"] += float(p.xg_local)
                    stats[p.equipo_visitante_id]["xg_contra"] += float(p.xg_local)
                if p.xg_visitante is not None:
                    stats[p.equipo_visitante_id]["xg_favor"] += float(p.xg_visitante)
                    stats[p.equipo_local_id]["xg_contra"] += float(p.xg_visitante)

                if gl > gv:
                    stats[p.equipo_local_id]["pg"] += 1
                    stats[p.equipo_visitante_id]["pp"] += 1
                elif gl < gv:
                    stats[p.equipo_visitante_id]["pg"] += 1
                    stats[p.equipo_local_id]["pp"] += 1
                else:
                    stats[p.equipo_local_id]["pe"] += 1
                    stats[p.equipo_visitante_id]["pe"] += 1

        rows = []
        with Session(engine) as session:
            for eid, s in stats.items():
                eq = session.get(Equipo, eid)
                nombre = eq.nombre_canonico or eq.nombre_es or eq.nombre_csv or f"Equipo {eid}" if eq else f"Equipo {eid}"
                codigo = eq.codigo_bandera if eq else None
                rows.append({
                    "equipo_id": eid,
                    "equipo": nombre,
                    "codigo_bandera": codigo,
                    "pj": s["pj"],
                    "pg": s["pg"],
                    "pe": s["pe"],
                    "pp": s["pp"],
                    "gf": s["gf"],
                    "gc": s["gc"],
                    "gd": s["gf"] - s["gc"],
                    "pts": s["pg"] * 3 + s["pe"],
                    "xg_favor": round(s["xg_favor"], 2),
                    "xg_contra": round(s["xg_contra"], 2),
                    "xg_diff": round(s["xg_favor"] - s["xg_contra"], 2),
                })

        rows.sort(key=lambda r: (-r["pts"], -r["gd"], -r["gf"]))
        return rows

    response = {"torneo": torneo.nombre_canonico, "tipo": torneo.tipo, "tabla": build_rows(partidos)}
    if grouped or torneo.tipo == "mundial":
        groups: dict[str, list[Partido]] = {}
        for p in partidos:
            groups.setdefault(p.grupo or "Sin grupo", []).append(p)
        response["grupos"] = [
            {"grupo": grupo, "tabla": build_rows(group_matches)}
            for grupo, group_matches in sorted(groups.items())
        ]
    return response


@app.get("/api/torneos/{torneo_id}/bracket")
def api_torneo_bracket(torneo_id: int, year: Optional[int] = None, season: Optional[str] = None):
    """Devuelve estructura eliminatoria (bracket) para un torneo."""
    with Session(engine) as session:
        torneo = session.get(Torneo, torneo_id)
        if not torneo:
            raise HTTPException(404, "Torneo no encontrado")

        conditions = [
            Partido.torneo_id == torneo_id,
            Partido.etapa.isnot(None),
            Partido.etapa != "",
        ]
        start, end = _season_bounds(season=season, year=year)
        if start and end:
            conditions.append(Partido.fecha_utc >= start)
            conditions.append(Partido.fecha_utc < end)
        partidos = session.exec(select(Partido).where(*conditions).order_by(Partido.fecha_utc)).all()

    STAGE_ORDER = {
        "GROUP_STAGE": 0, "LAST_32": 1, "ROUND_OF_32": 1, "LAST_16": 2, "ROUND_OF_16": 2,
        "QUARTER_FINALS": 3, "SEMI_FINALS": 4, "THIRD_PLACE": 5, "FINAL": 6,
    }
    STAGE_LABELS = {
        "GROUP_STAGE": "Fase de Grupos", "LAST_32": "Dieciseisavos", "ROUND_OF_32": "Dieciseisavos",
        "LAST_16": "Octavos", "ROUND_OF_16": "Octavos",
        "QUARTER_FINALS": "Cuartos", "SEMI_FINALS": "Semifinales",
        "THIRD_PLACE": "Tercer Puesto", "FINAL": "Final",
    }

    rondas: dict[str, list] = {}
    for p in partidos:
        etapa = p.etapa.upper() if p.etapa else ""
        if etapa not in rondas:
            rondas[etapa] = []
        name_local = p.home_team or ""
        name_away = p.away_team or ""
        if not name_local or not name_away:
            with Session(engine) as s:
                if p.equipo_local_id:
                    eq = s.get(Equipo, p.equipo_local_id)
                    name_local = eq.nombre_canonico or eq.nombre_csv or f"E{p.equipo_local_id}" if eq else f"E{p.equipo_local_id}"
                if p.equipo_visitante_id:
                    eq = s.get(Equipo, p.equipo_visitante_id)
                    name_away = eq.nombre_canonico or eq.nombre_csv or f"E{p.equipo_visitante_id}" if eq else f"E{p.equipo_visitante_id}"

        rondas[etapa].append({
            "partido_id": p.id,
            "home_team": name_local,
            "away_team": name_away,
            "home_score": p.goles_local,
            "away_score": p.goles_visitante,
            "estado": p.estado,
            "fecha": p.fecha_utc.isoformat() if p.fecha_utc else None,
            "grupo": p.grupo,
        })

    bracket = []
    for etapa in sorted(rondas.keys(), key=lambda e: STAGE_ORDER.get(e, 99)):
        bracket.append({
            "stage": etapa,
            "label": STAGE_LABELS.get(etapa, etapa),
            "order": STAGE_ORDER.get(etapa, 99),
            "matches": rondas[etapa],
        })

    return {"torneo": torneo.nombre_canonico, "bracket": bracket}


@app.get("/api/equipos/{equipo_id}/perfil")
def api_equipo_perfil(equipo_id: int):
    """Perfil de equipo: forma última 5, estadísticas, próximos partidos."""
    with Session(engine) as session:
        eq = session.get(Equipo, equipo_id)
        if not eq:
            raise HTTPException(404, "Equipo no encontrado")

        # Últimos 5 partidos
        ultimos = session.exec(
            select(Partido).where(
                Partido.estado == "FT",
                Partido.goles_local.isnot(None),
                Partido.goles_visitante.isnot(None),
                (Partido.equipo_local_id == equipo_id) | (Partido.equipo_visitante_id == equipo_id),
            ).order_by(Partido.fecha_utc.desc()).limit(5)
        ).all()

        forma = []
        for p in reversed(ultimos):
            gl, gv = p.goles_local, p.goles_visitante
            if p.equipo_local_id == equipo_id:
                resultado = "H" if gl > gv else "A" if gl < gv else "D"
                rival_id = p.equipo_visitante_id
            else:
                resultado = "A" if gl > gv else "H" if gl < gv else "D"
                rival_id = p.equipo_local_id
            rival = session.get(Equipo, rival_id)
            forma.append({
                "partido_id": p.id,
                "resultado": resultado,
                "goles_favor": gl if p.equipo_local_id == equipo_id else gv,
                "goles_contra": gv if p.equipo_local_id == equipo_id else gl,
                "rival": rival.nombre_canonico or rival.nombre_csv if rival else f"E{rival_id}",
                "fecha": p.fecha_utc.isoformat() if p.fecha_utc else None,
            })

        # Próximos partidos
        proximos = session.exec(
            select(Partido).where(
                Partido.estado.in_(["NS", "TIMED"]),
                (Partido.equipo_local_id == equipo_id) | (Partido.equipo_visitante_id == equipo_id),
            ).order_by(Partido.fecha_utc).limit(5)
        ).all()

        upcoming = []
        for p in proximos:
            is_local = p.equipo_local_id == equipo_id
            rival_id = p.equipo_visitante_id if is_local else p.equipo_local_id
            rival = session.get(Equipo, rival_id)
            upcoming.append({
                "partido_id": p.id,
                "fixture_id": p.fixture_id,
                "local": is_local,
                "rival": rival.nombre_canonico or rival.nombre_csv if rival else f"E{rival_id}",
                "fecha": p.fecha_utc.isoformat() if p.fecha_utc else None,
                "torneo_id": p.torneo_id,
                "home_team": p.home_team,
                "away_team": p.away_team,
            })

        # Estadísticas totales del equipo en todos los partidos
        totales = session.exec(
            select(Partido).where(
                Partido.estado == "FT",
                Partido.goles_local.isnot(None),
                Partido.goles_visitante.isnot(None),
                (Partido.equipo_local_id == equipo_id) | (Partido.equipo_visitante_id == equipo_id),
            )
        ).all()

        pj = len(totales)
        pg = sum(1 for p in totales if (p.equipo_local_id == equipo_id and p.goles_local > p.goles_visitante) or (p.equipo_visitante_id == equipo_id and p.goles_visitante > p.goles_local))
        pe = sum(1 for p in totales if p.goles_local == p.goles_visitante)
        pp = pj - pg - pe
        gf = sum(p.goles_local for p in totales if p.equipo_local_id == equipo_id) + sum(p.goles_visitante for p in totales if p.equipo_visitante_id == equipo_id)
        gc = sum(p.goles_visitante for p in totales if p.equipo_local_id == equipo_id) + sum(p.goles_local for p in totales if p.equipo_visitante_id == equipo_id)

        return {
            "equipo_id": equipo_id,
            "nombre": eq.nombre_canonico or eq.nombre_es or eq.nombre_csv,
            "codigo_bandera": eq.codigo_bandera,
            "forma": forma,
            "proximos": upcoming,
            "stats": {"pj": pj, "pg": pg, "pe": pe, "pp": pp, "gf": gf, "gc": gc, "gd": gf - gc, "pts": pg * 3 + pe},
        }


@app.get("/api/equipos/comparar")
def api_equipos_comparar(eq1: int, eq2: int):
    """Comparación lado a lado entre dos equipos."""
    with Session(engine) as session:
        e1 = session.get(Equipo, eq1)
        e2 = session.get(Equipo, eq2)
        if not e1 or not e2:
            raise HTTPException(404, "Uno o ambos equipos no encontrados")

        def _team_stats(eid: int):
            matches = session.exec(
                select(Partido).where(
                    Partido.estado == "FT",
                    Partido.goles_local.isnot(None),
                    Partido.goles_visitante.isnot(None),
                    (Partido.equipo_local_id == eid) | (Partido.equipo_visitante_id == eid),
                )
            ).all()
            pj = len(matches)
            pg = sum(1 for p in matches if (p.equipo_local_id == eid and p.goles_local > p.goles_visitante) or (p.equipo_visitante_id == eid and p.goles_visitante > p.goles_local))
            pe = sum(1 for p in matches if p.goles_local == p.goles_visitante)
            pp = pj - pg - pe
            gf = sum(p.goles_local for p in matches if p.equipo_local_id == eid) + sum(p.goles_visitante for p in matches if p.equipo_visitante_id == eid)
            gc = sum(p.goles_visitante for p in matches if p.equipo_local_id == eid) + sum(p.goles_local for p in matches if p.equipo_visitante_id == eid)
            xg_favor = sum(float(p.xg_local) for p in matches if p.equipo_local_id == eid and p.xg_local) + sum(float(p.xg_visitante) for p in matches if p.equipo_visitante_id == eid and p.xg_visitante)
            xg_contra = sum(float(p.xg_visitante) for p in matches if p.equipo_local_id == eid and p.xg_visitante) + sum(float(p.xg_local) for p in matches if p.equipo_visitante_id == eid and p.xg_local)
            return {"pj": pj, "pg": pg, "pe": pe, "pp": pp, "gf": gf, "gc": gc, "gd": gf - gc, "pts": pg * 3 + pe, "xg_favor": round(xg_favor, 2), "xg_contra": round(xg_contra, 2)}

        stats1 = _team_stats(eq1)
        stats2 = _team_stats(eq2)

        # H2H directo
        h2h_matches = session.exec(
            select(Partido).where(
                Partido.estado == "FT",
                Partido.goles_local.isnot(None),
                Partido.goles_visitante.isnot(None),
                ((Partido.equipo_local_id == eq1) & (Partido.equipo_visitante_id == eq2)) |
                ((Partido.equipo_local_id == eq2) & (Partido.equipo_visitante_id == eq1)),
            )
        ).all()

        h2h = {"eq1_wins": 0, "eq2_wins": 0, "draws": 0, "matches": []}
        for p in h2h_matches:
            if p.equipo_local_id == eq1:
                g1, g2 = p.goles_local, p.goles_visitante
            else:
                g1, g2 = p.goles_visitante, p.goles_local
            if g1 > g2:
                h2h["eq1_wins"] += 1
            elif g1 < g2:
                h2h["eq2_wins"] += 1
            else:
                h2h["draws"] += 1
            h2h["matches"].append({"eq1_goals": g1, "eq2_goals": g2, "fecha": p.fecha_utc.isoformat() if p.fecha_utc else None})

        return {
            "equipo1": {"id": e1.id, "nombre": e1.nombre_canonico or e1.nombre_es or e1.nombre_csv, "codigo_bandera": e1.codigo_bandera, "stats": stats1},
            "equipo2": {"id": e2.id, "nombre": e2.nombre_canonico or e2.nombre_es or e2.nombre_csv, "codigo_bandera": e2.codigo_bandera, "stats": stats2},
            "h2h": h2h,
        }
