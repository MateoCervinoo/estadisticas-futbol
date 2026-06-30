import math
from collections import Counter
from typing import Optional

from fastapi import APIRouter, HTTPException
from sqlalchemy import or_
from sqlmodel import select

from ..database import engine
from ..db.session import Session
from ..models import Equipo, Partido

router = APIRouter()


@router.get("/api/equipos/search")
def api_equipos_search(q: str = "", tipo: Optional[str] = None):
    with Session(engine) as session:
        stmt = select(Equipo)
        if tipo in ("club", "seleccion"):
            stmt = stmt.where(Equipo.tipo == tipo)
        if q:
            like = f"%{q}%"
            stmt = stmt.where(or_(Equipo.nombre_canonico.ilike(like), Equipo.nombre_es.ilike(like), Equipo.nombre_api.ilike(like), Equipo.nombre_csv.ilike(like), Equipo.nombre_fbref.ilike(like), Equipo.nombre_understat.ilike(like)))
        equipos = session.exec(stmt.order_by(Equipo.nombre_canonico).limit(50)).all()
        return [{"id": e.id, "nombre": e.nombre_canonico or e.nombre_es or e.nombre_csv, "codigo_bandera": e.codigo_bandera} for e in equipos]


@router.get("/api/equipos/{equipo_id}/evolution")
def api_equipo_evolution(equipo_id: int):
    with Session(engine) as session:
        eq = session.get(Equipo, equipo_id)
        if not eq:
            raise HTTPException(404, "Equipo no encontrado")
        matches = session.exec(select(Partido).where(Partido.estado == "FT", Partido.goles_local.isnot(None), Partido.goles_visitante.isnot(None), (Partido.equipo_local_id == equipo_id) | (Partido.equipo_visitante_id == equipo_id)).order_by(Partido.fecha_utc)).all()
        if not matches:
            return {"equipo_id": equipo_id, "nombre": eq.nombre_canonico or "", "evolution": []}

        points = []
        for i, match in enumerate(matches):
            is_local = match.equipo_local_id == equipo_id
            gf = match.goles_local if is_local else match.goles_visitante
            gc = match.goles_visitante if is_local else match.goles_local
            xgf = float(match.xg_local) if is_local and match.xg_local else (float(match.xg_visitante) if not is_local and match.xg_visitante else None)
            xgc = float(match.xg_visitante) if is_local and match.xg_visitante else (float(match.xg_local) if not is_local and match.xg_local else None)
            window = matches[max(0, i - 4):i + 1]
            rolling_gf = sum((m.goles_local if m.equipo_local_id == equipo_id else m.goles_visitante) or 0 for m in window) / len(window)
            rolling_gc = sum((m.goles_visitante if m.equipo_local_id == equipo_id else m.goles_local) or 0 for m in window) / len(window)
            points.append({"match_index": i + 1, "fecha": match.fecha_utc.isoformat() if match.fecha_utc else None, "resultado": "H" if gf > gc else ("A" if gf < gc else "D"), "gf": gf or 0, "gc": gc or 0, "rolling_gf_avg": round(rolling_gf, 2), "rolling_gc_avg": round(rolling_gc, 2), "xg_favor": xgf, "xg_contra": xgc})
        return {"equipo_id": equipo_id, "nombre": eq.nombre_canonico or eq.nombre_es or eq.nombre_csv, "evolution": points}


@router.get("/api/equipos/{equipo_id}/distribucion")
def api_equipo_distribucion(equipo_id: int):
    with Session(engine) as session:
        eq = session.get(Equipo, equipo_id)
        if not eq:
            raise HTTPException(404, "Equipo no encontrado")
        matches = session.exec(select(Partido).where(Partido.estado == "FT", Partido.goles_local.isnot(None), Partido.goles_visitante.isnot(None), (Partido.equipo_local_id == equipo_id) | (Partido.equipo_visitante_id == equipo_id))).all()
        if not matches:
            return {"equipo_id": equipo_id, "nombre": eq.nombre_canonico or "", "total_partidos": 0, "avg_goles": 0, "distribucion": []}
        goals_scored = [p.goles_local if p.equipo_local_id == equipo_id else p.goles_visitante for p in matches]
        actual_dist = Counter(goals_scored)
        avg_goals = sum(goals_scored) / len(goals_scored)
        dist = []
        for goals in range(max(max(goals_scored), 5) + 1):
            poisson_prob = (avg_goals ** goals) * math.exp(-avg_goals) / math.factorial(goals)
            actual_count = actual_dist.get(goals, 0)
            dist.append({"goles": goals, "actual_pct": round((actual_count / len(goals_scored)) * 100, 1), "poisson_pct": round(poisson_prob * 100, 1), "actual_partidos": actual_count})
        return {"equipo_id": equipo_id, "nombre": eq.nombre_canonico or eq.nombre_es or eq.nombre_csv, "total_partidos": len(matches), "avg_goles": round(avg_goals, 2), "distribucion": dist}


@router.get("/api/equipos/{equipo_id}/perfil")
def api_equipo_perfil(equipo_id: int):
    with Session(engine) as session:
        eq = session.get(Equipo, equipo_id)
        if not eq:
            raise HTTPException(404, "Equipo no encontrado")
        ultimos = session.exec(select(Partido).where(Partido.estado == "FT", Partido.goles_local.isnot(None), Partido.goles_visitante.isnot(None), (Partido.equipo_local_id == equipo_id) | (Partido.equipo_visitante_id == equipo_id)).order_by(Partido.fecha_utc.desc()).limit(5)).all()
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
            forma.append({"partido_id": p.id, "resultado": resultado, "goles_favor": gl if p.equipo_local_id == equipo_id else gv, "goles_contra": gv if p.equipo_local_id == equipo_id else gl, "rival": rival.nombre_canonico or rival.nombre_csv if rival else f"E{rival_id}", "fecha": p.fecha_utc.isoformat() if p.fecha_utc else None})

        proximos = session.exec(select(Partido).where(Partido.estado.in_(["NS", "TIMED"]), (Partido.equipo_local_id == equipo_id) | (Partido.equipo_visitante_id == equipo_id)).order_by(Partido.fecha_utc).limit(5)).all()
        upcoming = []
        for p in proximos:
            is_local = p.equipo_local_id == equipo_id
            rival_id = p.equipo_visitante_id if is_local else p.equipo_local_id
            rival = session.get(Equipo, rival_id)
            upcoming.append({"partido_id": p.id, "fixture_id": p.fixture_id, "local": is_local, "rival": rival.nombre_canonico or rival.nombre_csv if rival else f"E{rival_id}", "fecha": p.fecha_utc.isoformat() if p.fecha_utc else None, "torneo_id": p.torneo_id, "home_team": p.home_team, "away_team": p.away_team})

        totales = session.exec(select(Partido).where(Partido.estado == "FT", Partido.goles_local.isnot(None), Partido.goles_visitante.isnot(None), (Partido.equipo_local_id == equipo_id) | (Partido.equipo_visitante_id == equipo_id))).all()
        pj = len(totales)
        pg = sum(1 for p in totales if (p.equipo_local_id == equipo_id and p.goles_local > p.goles_visitante) or (p.equipo_visitante_id == equipo_id and p.goles_visitante > p.goles_local))
        pe = sum(1 for p in totales if p.goles_local == p.goles_visitante)
        pp = pj - pg - pe
        gf = sum(p.goles_local for p in totales if p.equipo_local_id == equipo_id) + sum(p.goles_visitante for p in totales if p.equipo_visitante_id == equipo_id)
        gc = sum(p.goles_visitante for p in totales if p.equipo_local_id == equipo_id) + sum(p.goles_local for p in totales if p.equipo_visitante_id == equipo_id)
        return {"equipo_id": equipo_id, "nombre": eq.nombre_canonico or eq.nombre_es or eq.nombre_csv, "codigo_bandera": eq.codigo_bandera, "forma": forma, "proximos": upcoming, "stats": {"pj": pj, "pg": pg, "pe": pe, "pp": pp, "gf": gf, "gc": gc, "gd": gf - gc, "pts": pg * 3 + pe}}


@router.get("/api/equipos/comparar")
def api_equipos_comparar(eq1: int, eq2: int):
    with Session(engine) as session:
        e1 = session.get(Equipo, eq1)
        e2 = session.get(Equipo, eq2)
        if not e1 or not e2:
            raise HTTPException(404, "Uno o ambos equipos no encontrados")

        def team_stats(eid: int):
            matches = session.exec(select(Partido).where(Partido.estado == "FT", Partido.goles_local.isnot(None), Partido.goles_visitante.isnot(None), (Partido.equipo_local_id == eid) | (Partido.equipo_visitante_id == eid))).all()
            pj = len(matches)
            pg = sum(1 for p in matches if (p.equipo_local_id == eid and p.goles_local > p.goles_visitante) or (p.equipo_visitante_id == eid and p.goles_visitante > p.goles_local))
            pe = sum(1 for p in matches if p.goles_local == p.goles_visitante)
            pp = pj - pg - pe
            gf = sum(p.goles_local for p in matches if p.equipo_local_id == eid) + sum(p.goles_visitante for p in matches if p.equipo_visitante_id == eid)
            gc = sum(p.goles_visitante for p in matches if p.equipo_local_id == eid) + sum(p.goles_local for p in matches if p.equipo_visitante_id == eid)
            xg_favor = sum(float(p.xg_local) for p in matches if p.equipo_local_id == eid and p.xg_local) + sum(float(p.xg_visitante) for p in matches if p.equipo_visitante_id == eid and p.xg_visitante)
            xg_contra = sum(float(p.xg_visitante) for p in matches if p.equipo_local_id == eid and p.xg_visitante) + sum(float(p.xg_local) for p in matches if p.equipo_visitante_id == eid and p.xg_local)
            return {"pj": pj, "pg": pg, "pe": pe, "pp": pp, "gf": gf, "gc": gc, "gd": gf - gc, "pts": pg * 3 + pe, "xg_favor": round(xg_favor, 2), "xg_contra": round(xg_contra, 2)}

        h2h_matches = session.exec(select(Partido).where(Partido.estado == "FT", Partido.goles_local.isnot(None), Partido.goles_visitante.isnot(None), ((Partido.equipo_local_id == eq1) & (Partido.equipo_visitante_id == eq2)) | ((Partido.equipo_local_id == eq2) & (Partido.equipo_visitante_id == eq1)))).all()
        h2h = {"eq1_wins": 0, "eq2_wins": 0, "draws": 0, "matches": []}
        for p in h2h_matches:
            g1, g2 = (p.goles_local, p.goles_visitante) if p.equipo_local_id == eq1 else (p.goles_visitante, p.goles_local)
            if g1 > g2:
                h2h["eq1_wins"] += 1
            elif g1 < g2:
                h2h["eq2_wins"] += 1
            else:
                h2h["draws"] += 1
            h2h["matches"].append({"eq1_goals": g1, "eq2_goals": g2, "fecha": p.fecha_utc.isoformat() if p.fecha_utc else None})

        return {"equipo1": {"id": e1.id, "nombre": e1.nombre_canonico or e1.nombre_es or e1.nombre_csv, "codigo_bandera": e1.codigo_bandera, "stats": team_stats(eq1)}, "equipo2": {"id": e2.id, "nombre": e2.nombre_canonico or e2.nombre_es or e2.nombre_csv, "codigo_bandera": e2.codigo_bandera, "stats": team_stats(eq2)}, "h2h": h2h}
