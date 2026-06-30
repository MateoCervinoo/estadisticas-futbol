import logging
import os
from typing import List, Optional

import pandas as pd
from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import and_, func, or_
from sqlmodel import select

from ..database import engine
from ..db.session import Session
from ..models import Equipo, Partido, PartidoEstadisticas, Torneo
from ..services.partido_service import dedupe_partido_items, enrich_partido_item, season_bounds
from ..services.prediction_service import predict_partido

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/api/partidos/anyos")
def api_list_anyos():
    with Session(engine) as session:
        all_fechas = session.exec(select(Partido.fecha_utc)).all()
        return sorted({dt.year for dt in all_fechas if dt is not None})


@router.get("/api/partidos/filtros")
def api_partidos_filtros(
    tournament: Optional[str] = None,
    year: Optional[int] = None,
    season: Optional[str] = None,
    stage: Optional[str] = None,
):
    with Session(engine) as session:
        conditions = []
        if tournament:
            conditions.append(Partido.tournament == tournament)
        start, end = season_bounds(season=season, year=year)
        if start and end:
            conditions.extend([Partido.fecha_utc >= start, Partido.fecha_utc < end])

        stmt = select(Partido)
        if conditions:
            stmt = stmt.where(*conditions)
        partidos = session.exec(stmt).all()

        return {
            "years": sorted({p.fecha_utc.year for p in partidos if p.fecha_utc is not None}),
            "tournaments": sorted({p.tournament for p in partidos if p.tournament}),
            "stages": sorted({p.etapa for p in partidos if p.etapa}),
            "groups": [] if stage and stage not in ("Todos", "GROUP_STAGE") else sorted({p.grupo for p in partidos if p.grupo}),
            "matchdays": sorted({p.jornada for p in partidos if p.jornada is not None}),
            "dates": sorted({p.fecha_utc.date().isoformat() for p in partidos if p.fecha_utc is not None}),
        }


@router.get("/api/partidos")
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
    with Session(engine) as session:
        stmt = select(Partido).order_by(Partido.fecha_utc)

        main_conditions = []
        if mundial:
            torneos = session.exec(
                select(Torneo).where(or_(Torneo.nombre_canonico.ilike("%world cup%"), Torneo.nombre_canonico.ilike("%mundial%")))
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
            start, end = season_bounds(year=year)
            if start and end:
                all_conditions.extend([Partido.fecha_utc >= start, Partido.fecha_utc < end])
        if season:
            start, end = season_bounds(season=season)
            if start and end:
                all_conditions.extend([Partido.fecha_utc >= start, Partido.fecha_utc < end])
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
        items = [enrich_partido_item(p, session) for p in partidos]
        return dedupe_partido_items(items)


@router.get("/api/partidos/finalizados")
def api_list_partidos_finalizados():
    with Session(engine) as session:
        stmt = select(Partido).where(Partido.estado == "FT").order_by(Partido.fecha_utc)
        partidos: List[Partido] = session.exec(stmt).all()
        return [enrich_partido_item(p, session) for p in partidos]


@router.get("/api/partidos/{partido_id}/estadisticas")
def api_partido_estadisticas(partido_id: int):
    with Session(engine) as session:
        partido = session.get(Partido, partido_id)
        if not partido:
            raise HTTPException(status_code=404, detail="Partido no encontrado")
        stats = session.exec(select(PartidoEstadisticas).where(PartidoEstadisticas.partido_id == partido_id)).all()
        result = enrich_partido_item(partido, session)
        result["estadisticas"] = [s.dict() for s in stats] if stats else []
        return result


@router.get("/api/partidos/{partido_id}/prediccion")
def partido_prediccion_alt(partido_id: int, request: Request):
    return predict_partido(
        partido_id,
        getattr(request.app.state, "sel_model", None),
        getattr(request.app.state, "club_model", None),
    )


@router.get("/api/partidos/live")
def api_partidos_live():
    with Session(engine) as session:
        partidos = session.exec(select(Partido).where(Partido.estado == "IN_PLAY")).all()
        return [enrich_partido_item(p, session) for p in partidos]


@router.get("/api/debug/datos-corruptos")
def debug_datos_corruptos():
    bad_path = os.path.join(os.path.dirname(__file__), "..", "data", "bad_records.csv")
    alt_path = os.path.join("/", "app", "data", "bad_records.csv")
    chosen = bad_path if os.path.exists(bad_path) else alt_path if os.path.exists(alt_path) else None
    if not chosen:
        return {"warning": "No se encontró bad_records.csv"}
    try:
        df = pd.read_csv(chosen)
        records = df.to_dict(orient="records")
        return {"path": chosen, "count": len(records), "records": records}
    except Exception:
        logger.exception("Error leyendo %s", chosen)
        raise HTTPException(status_code=500, detail="No se pudo leer el archivo de registros corruptos")
