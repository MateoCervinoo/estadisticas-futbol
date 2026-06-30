from typing import Optional

from fastapi import APIRouter
from sqlmodel import select

from ..database import engine
from ..db.session import Session
from ..models import Equipo, Partido
from ..services.analytics_service import team_display_name

router = APIRouter()


@router.get("/api/analytics/xg-vs-real")
def api_xg_vs_real(torneo_id: Optional[int] = None, tipo: Optional[str] = None):
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
            eq = session.get(Equipo, eid)
            if tipo in ("club", "seleccion") and eq and eq.tipo != tipo:
                continue
            nombre = team_display_name(eq, f"E{eid}")
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
