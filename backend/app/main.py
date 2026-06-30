import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db
from .routers import analytics, equipos, health, notificaciones, partidos, torneos
from .services.sync_service import seed_and_sync_startup

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Estadisticas Futbol - Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    try:
        init_db()
        logger.info("Migraciones de base de datos aplicadas/confirmadas")
    except Exception:
        logger.exception("Fallo creando tablas en la base de datos al startup. Continuando...")

    try:
        loop = asyncio.get_event_loop()
        loop.create_task(notificaciones.broadcast_new_notifications())
        logger.info("Background notification broadcaster started")
    except Exception:
        logger.exception("No se pudo iniciar el broadcaster de notificaciones")

    try:
        seed_and_sync_startup(app)
    except Exception:
        logger.exception("Error inesperado en on_startup(); continuando sin bloquear el servidor.")


app.include_router(health.router)
app.include_router(partidos.router)
app.include_router(torneos.router)
app.include_router(equipos.router)
app.include_router(analytics.router)
app.include_router(notificaciones.router)
