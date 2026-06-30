import asyncio
import logging

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from sqlmodel import select

from ..database import engine
from ..db.session import Session
from ..models import Notificacion

logger = logging.getLogger(__name__)
router = APIRouter()


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
                    },
                })
                last_broadcasted_id = n.id
        except Exception:
            logger.exception("Error emitiendo notificaciones por WebSocket")
        await asyncio.sleep(5)


@router.websocket("/ws/matches")
async def ws_matches(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)


@router.get("/api/notificaciones")
def api_notificaciones(no_leidas: bool = False):
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


@router.get("/api/notificaciones/no-leidas")
def api_notificaciones_no_leidas_count():
    with Session(engine) as session:
        count = session.exec(select(Notificacion).where(Notificacion.leida == False)).all()
        return {"count": len(count)}


@router.post("/api/notificaciones/{notif_id}/leer")
def api_notificacion_leer(notif_id: int):
    with Session(engine) as session:
        n = session.get(Notificacion, notif_id)
        if not n:
            raise HTTPException(404, "Notificación no encontrada")
        n.leida = True
        session.add(n)
        session.commit()
        return {"ok": True}


@router.post("/api/notificaciones/leer-todas")
def api_notificaciones_leer_todas():
    with Session(engine) as session:
        notifs = session.exec(select(Notificacion).where(Notificacion.leida == False)).all()
        for n in notifs:
            n.leida = True
            session.add(n)
        session.commit()
        return {"ok": True, "marcadas": len(notifs)}
