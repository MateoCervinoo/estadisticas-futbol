import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db
from .routers import analytics, equipos, health, notificaciones, partidos, torneos
from .services.sync_service import load_prediction_models

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def _cors_origins() -> list[str]:
    raw_origins = os.getenv("BACKEND_CORS_ORIGINS", "http://localhost:3000")
    return [origin.strip() for origin in raw_origins.split(",") if origin.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_db()
    except Exception:
        logger.exception("Fallo aplicando migraciones de base de datos durante startup; abortando servidor.")
        raise
    logger.info("Migraciones de base de datos aplicadas/confirmadas")

    load_prediction_models(app)

    notification_task = asyncio.create_task(notificaciones.broadcast_new_notifications())
    logger.info("Background notification broadcaster started")

    try:
        yield
    finally:
        notification_task.cancel()
        try:
            await notification_task
        except asyncio.CancelledError:
            logger.info("Background notification broadcaster stopped")


app = FastAPI(title="Estadisticas Futbol - Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(health.router)
app.include_router(partidos.router)
app.include_router(torneos.router)
app.include_router(equipos.router)
app.include_router(analytics.router)
app.include_router(notificaciones.router)
