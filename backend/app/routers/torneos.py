from typing import Optional

from fastapi import APIRouter, HTTPException
from sqlalchemy import func
from sqlmodel import select

from ..db.session import Session, engine
from ..models import Equipo, Partido, Torneo
from ..services.tournament_service import is_finished_match, season_bounds, season_label_for_match

router = APIRouter()

STAGE_ORDER = {
    "LAST_32": 1,
    "ROUND_OF_32": 1,
    "LAST_16": 2,
    "ROUND_OF_16": 2,
    "QUARTER_FINALS": 3,
    "SEMI_FINALS": 4,
    "THIRD_PLACE": 5,
    "FINAL": 6,
}
STAGE_LABELS = {
    "LAST_32": "Dieciseisavos",
    "ROUND_OF_32": "Dieciseisavos",
    "LAST_16": "Octavos",
    "ROUND_OF_16": "Octavos",
    "QUARTER_FINALS": "Cuartos",
    "SEMI_FINALS": "Semifinales",
    "THIRD_PLACE": "Tercer Puesto",
    "FINAL": "Final",
}


def torneo_period_conditions(year: Optional[int] = None, season: Optional[str] = None) -> list:
    conditions = []
    start, end = season_bounds(season=season, year=year)
    if start and end:
        conditions.extend([Partido.fecha_utc >= start, Partido.fecha_utc < end])
    return conditions


def equipo_display_name(equipo: Equipo | None, fallback_id: int | None) -> str:
    if not equipo:
        return f"Equipo {fallback_id}"
    return equipo.nombre_canonico or equipo.nombre_es or equipo.nombre_csv or f"Equipo {fallback_id}"


def build_tabla_rows(session: Session, partidos: list[Partido]) -> list[dict]:
    stats: dict[int, dict] = {}
    for partido in partidos:
        for equipo_id in (partido.equipo_local_id, partido.equipo_visitante_id):
            if equipo_id and equipo_id not in stats:
                stats[equipo_id] = {"pj": 0, "pg": 0, "pe": 0, "pp": 0, "gf": 0, "gc": 0, "xg_favor": 0.0, "xg_contra": 0.0}

        if not is_finished_match(partido) or not partido.equipo_local_id or not partido.equipo_visitante_id:
            continue

        goles_local = partido.goles_local
        goles_visitante = partido.goles_visitante
        stats[partido.equipo_local_id]["pj"] += 1
        stats[partido.equipo_visitante_id]["pj"] += 1
        stats[partido.equipo_local_id]["gf"] += goles_local
        stats[partido.equipo_local_id]["gc"] += goles_visitante
        stats[partido.equipo_visitante_id]["gf"] += goles_visitante
        stats[partido.equipo_visitante_id]["gc"] += goles_local

        if partido.xg_local is not None:
            stats[partido.equipo_local_id]["xg_favor"] += float(partido.xg_local)
            stats[partido.equipo_visitante_id]["xg_contra"] += float(partido.xg_local)
        if partido.xg_visitante is not None:
            stats[partido.equipo_visitante_id]["xg_favor"] += float(partido.xg_visitante)
            stats[partido.equipo_local_id]["xg_contra"] += float(partido.xg_visitante)

        if goles_local > goles_visitante:
            stats[partido.equipo_local_id]["pg"] += 1
            stats[partido.equipo_visitante_id]["pp"] += 1
        elif goles_local < goles_visitante:
            stats[partido.equipo_visitante_id]["pg"] += 1
            stats[partido.equipo_local_id]["pp"] += 1
        else:
            stats[partido.equipo_local_id]["pe"] += 1
            stats[partido.equipo_visitante_id]["pe"] += 1

    equipos = {equipo.id: equipo for equipo in session.exec(select(Equipo).where(Equipo.id.in_(stats.keys()))).all()} if stats else {}
    rows = []
    for equipo_id, values in stats.items():
        equipo = equipos.get(equipo_id)
        rows.append({
            "equipo_id": equipo_id,
            "equipo": equipo_display_name(equipo, equipo_id),
            "codigo_bandera": equipo.codigo_bandera if equipo else None,
            "pj": values["pj"],
            "pg": values["pg"],
            "pe": values["pe"],
            "pp": values["pp"],
            "gf": values["gf"],
            "gc": values["gc"],
            "gd": values["gf"] - values["gc"],
            "pts": values["pg"] * 3 + values["pe"],
            "xg_favor": round(values["xg_favor"], 2),
            "xg_contra": round(values["xg_contra"], 2),
            "xg_diff": round(values["xg_favor"] - values["xg_contra"], 2),
        })

    rows.sort(key=lambda row: (-row["pts"], -row["gd"], -row["gf"], row["equipo"]))
    return rows


@router.get("/api/torneos")
def api_list_torneos():
    with Session(engine) as session:
        torneos = session.exec(select(Torneo)).all()
        result = []
        for t in torneos:
            total_partidos = session.exec(select(func.count(Partido.id)).where(Partido.torneo_id == t.id)).one()
            result.append({
                "id": t.id,
                "nombre_canonico": t.nombre_canonico,
                "tipo": t.tipo,
                "categoria": t.categoria,
                "nivel": t.nivel,
                "total_partidos": total_partidos,
            })
        return result


@router.get("/api/torneos/{torneo_id}/temporadas")
def api_torneo_temporadas(torneo_id: int):
    with Session(engine) as session:
        torneo = session.get(Torneo, torneo_id)
        if not torneo:
            raise HTTPException(404, "Torneo no encontrado")
        partidos = session.exec(select(Partido).where(Partido.torneo_id == torneo_id, Partido.fecha_utc.isnot(None))).all()
        labels = sorted({season_label_for_match(partido.fecha_utc, torneo.tipo) for partido in partidos if partido.fecha_utc}, reverse=True)
        return {"torneo_id": torneo_id, "temporadas": labels}


@router.get("/api/torneos/{torneo_id}/tabla-posiciones")
def api_torneo_tabla(torneo_id: int, year: Optional[int] = None, season: Optional[str] = None, grouped: bool = False):
    with Session(engine) as session:
        torneo = session.get(Torneo, torneo_id)
        if not torneo:
            raise HTTPException(404, "Torneo no encontrado")

        conditions = [Partido.torneo_id == torneo_id, *torneo_period_conditions(year=year, season=season)]
        if grouped or torneo.tipo == "mundial":
            conditions.append(Partido.etapa == "GROUP_STAGE")
        partidos = session.exec(select(Partido).where(*conditions)).all()

        response = {"torneo": torneo.nombre_canonico, "tipo": torneo.tipo, "tabla": build_tabla_rows(session, partidos)}
        if grouped or torneo.tipo == "mundial":
            groups: dict[str, list[Partido]] = {}
            for partido in partidos:
                groups.setdefault(partido.grupo or "Sin grupo", []).append(partido)
            response["grupos"] = [{"grupo": grupo, "tabla": build_tabla_rows(session, group_matches)} for grupo, group_matches in sorted(groups.items())]
        return response


@router.get("/api/torneos/{torneo_id}/bracket")
def api_torneo_bracket(torneo_id: int, year: Optional[int] = None, season: Optional[str] = None):
    with Session(engine) as session:
        torneo = session.get(Torneo, torneo_id)
        if not torneo:
            raise HTTPException(404, "Torneo no encontrado")
        conditions = [
            Partido.torneo_id == torneo_id,
            Partido.etapa.isnot(None),
            Partido.etapa != "",
            Partido.etapa != "GROUP_STAGE",
            *torneo_period_conditions(year=year, season=season),
        ]
        partidos = session.exec(select(Partido).where(*conditions).order_by(Partido.fecha_utc)).all()
        equipo_ids = {equipo_id for partido in partidos for equipo_id in (partido.equipo_local_id, partido.equipo_visitante_id) if equipo_id}
        equipos = {equipo.id: equipo for equipo in session.exec(select(Equipo).where(Equipo.id.in_(equipo_ids))).all()} if equipo_ids else {}

        rondas: dict[str, list] = {}
        for partido in partidos:
            etapa = partido.etapa.upper() if partido.etapa else ""
            rondas.setdefault(etapa, [])
            local = equipos.get(partido.equipo_local_id)
            visitante = equipos.get(partido.equipo_visitante_id)
            name_local = partido.home_team or equipo_display_name(local, partido.equipo_local_id)
            name_away = partido.away_team or equipo_display_name(visitante, partido.equipo_visitante_id)
            rondas[etapa].append({"partido_id": partido.id, "home_team": name_local, "away_team": name_away, "home_score": partido.goles_local, "away_score": partido.goles_visitante, "estado": partido.estado, "fecha": partido.fecha_utc.isoformat() if partido.fecha_utc else None, "grupo": partido.grupo})

        bracket = [{"stage": etapa, "label": STAGE_LABELS.get(etapa, etapa), "order": STAGE_ORDER.get(etapa, 99), "matches": rondas[etapa]} for etapa in sorted(rondas.keys(), key=lambda e: STAGE_ORDER.get(e, 99))]
        return {"torneo": torneo.nombre_canonico, "bracket": bracket}
