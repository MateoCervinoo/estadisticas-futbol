from typing import Optional

from fastapi import APIRouter, HTTPException
from sqlmodel import select

from ..database import engine
from ..db.session import Session
from ..models import Equipo, Partido, Torneo
from ..services.tournament_service import is_finished_match, season_bounds, season_label_for_match

router = APIRouter()


@router.get("/api/torneos")
def api_list_torneos():
    with Session(engine) as session:
        torneos = session.exec(select(Torneo)).all()
        result = []
        for t in torneos:
            count = session.exec(select(Partido).where(Partido.torneo_id == t.id)).all()
            result.append({
                "id": t.id,
                "nombre_canonico": t.nombre_canonico,
                "tipo": t.tipo,
                "categoria": t.categoria,
                "nivel": t.nivel,
                "total_partidos": len(count),
            })
        return result


@router.get("/api/torneos/{torneo_id}/temporadas")
def api_torneo_temporadas(torneo_id: int):
    with Session(engine) as session:
        torneo = session.get(Torneo, torneo_id)
        if not torneo:
            raise HTTPException(404, "Torneo no encontrado")
        partidos = session.exec(select(Partido).where(Partido.torneo_id == torneo_id, Partido.fecha_utc.isnot(None))).all()
        labels = sorted({season_label_for_match(p.fecha_utc, torneo.tipo) for p in partidos if p.fecha_utc}, reverse=True)
        return {"torneo_id": torneo_id, "temporadas": labels}


@router.get("/api/torneos/{torneo_id}/tabla-posiciones")
def api_torneo_tabla(torneo_id: int, year: Optional[int] = None, season: Optional[str] = None, grouped: bool = False):
    with Session(engine) as session:
        torneo = session.get(Torneo, torneo_id)
        if not torneo:
            raise HTTPException(404, "Torneo no encontrado")

        conditions = [Partido.torneo_id == torneo_id]
        start, end = season_bounds(season=season, year=year)
        if start and end:
            conditions.extend([Partido.fecha_utc >= start, Partido.fecha_utc < end])
        if grouped or torneo.tipo == "mundial":
            conditions.append(Partido.etapa == "GROUP_STAGE")
        partidos = session.exec(select(Partido).where(*conditions)).all()

    def build_rows(rows_partidos: list[Partido]) -> list[dict]:
        stats: dict[int, dict] = {}
        for p in rows_partidos:
            for eid in (p.equipo_local_id, p.equipo_visitante_id):
                if eid and eid not in stats:
                    stats[eid] = {"pj": 0, "pg": 0, "pe": 0, "pp": 0, "gf": 0, "gc": 0, "xg_favor": 0.0, "xg_contra": 0.0}
            if is_finished_match(p) and p.equipo_local_id and p.equipo_visitante_id:
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
                rows.append({
                    "equipo_id": eid,
                    "equipo": nombre,
                    "codigo_bandera": eq.codigo_bandera if eq else None,
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
        response["grupos"] = [{"grupo": grupo, "tabla": build_rows(group_matches)} for grupo, group_matches in sorted(groups.items())]
    return response


@router.get("/api/torneos/{torneo_id}/bracket")
def api_torneo_bracket(torneo_id: int, year: Optional[int] = None, season: Optional[str] = None):
    with Session(engine) as session:
        torneo = session.get(Torneo, torneo_id)
        if not torneo:
            raise HTTPException(404, "Torneo no encontrado")
        conditions = [Partido.torneo_id == torneo_id, Partido.etapa.isnot(None), Partido.etapa != ""]
        start, end = season_bounds(season=season, year=year)
        if start and end:
            conditions.extend([Partido.fecha_utc >= start, Partido.fecha_utc < end])
        partidos = session.exec(select(Partido).where(*conditions).order_by(Partido.fecha_utc)).all()

    stage_order = {"GROUP_STAGE": 0, "LAST_32": 1, "ROUND_OF_32": 1, "LAST_16": 2, "ROUND_OF_16": 2, "QUARTER_FINALS": 3, "SEMI_FINALS": 4, "THIRD_PLACE": 5, "FINAL": 6}
    stage_labels = {"GROUP_STAGE": "Fase de Grupos", "LAST_32": "Dieciseisavos", "ROUND_OF_32": "Dieciseisavos", "LAST_16": "Octavos", "ROUND_OF_16": "Octavos", "QUARTER_FINALS": "Cuartos", "SEMI_FINALS": "Semifinales", "THIRD_PLACE": "Tercer Puesto", "FINAL": "Final"}
    rondas: dict[str, list] = {}
    for p in partidos:
        etapa = p.etapa.upper() if p.etapa else ""
        rondas.setdefault(etapa, [])
        name_local = p.home_team or ""
        name_away = p.away_team or ""
        if not name_local or not name_away:
            with Session(engine) as session:
                if p.equipo_local_id:
                    eq = session.get(Equipo, p.equipo_local_id)
                    name_local = eq.nombre_canonico or eq.nombre_csv or f"E{p.equipo_local_id}" if eq else f"E{p.equipo_local_id}"
                if p.equipo_visitante_id:
                    eq = session.get(Equipo, p.equipo_visitante_id)
                    name_away = eq.nombre_canonico or eq.nombre_csv or f"E{p.equipo_visitante_id}" if eq else f"E{p.equipo_visitante_id}"
        rondas[etapa].append({"partido_id": p.id, "home_team": name_local, "away_team": name_away, "home_score": p.goles_local, "away_score": p.goles_visitante, "estado": p.estado, "fecha": p.fecha_utc.isoformat() if p.fecha_utc else None, "grupo": p.grupo})

    bracket = [{"stage": etapa, "label": stage_labels.get(etapa, etapa), "order": stage_order.get(etapa, 99), "matches": rondas[etapa]} for etapa in sorted(rondas.keys(), key=lambda e: stage_order.get(e, 99))]
    return {"torneo": torneo.nombre_canonico, "bracket": bracket}
