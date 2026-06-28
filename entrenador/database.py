from __future__ import annotations
import logging
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy import text

from .config import settings

logger = logging.getLogger(__name__)

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        url = settings.database_url
        if settings.DB_ENGINE == "sqlite":
            # NUEVO: crear directorio si no existe
            import re
            from pathlib import Path
            m = re.match(r"sqlite:///(.+)", url)
            if m:
                db_path = Path(m.group(1))
                db_path.parent.mkdir(parents=True, exist_ok=True)
            _engine = create_engine(url, echo=False, connect_args={"check_same_thread": False})
        else:
            _engine = create_engine(url, echo=False)
    return _engine


def init_db():
    engine = get_engine()
    SQLModel.metadata.create_all(engine)
    logger.info("Tablas creadas/verificadas en %s", settings.DB_ENGINE)


def get_session():
    with Session(get_engine()) as session:
        yield session


def ensure_tables():
    from . import models
    init_db()


def get_or_create_session():
    return Session(get_engine())
