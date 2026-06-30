from __future__ import annotations
import logging
import re
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlmodel import create_engine, Session

from .config import settings

logger = logging.getLogger(__name__)

_engine = None
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_ROOT = PROJECT_ROOT / "backend"


def get_engine():
    global _engine
    if _engine is None:
        url = settings.database_url
        if settings.DB_ENGINE == "sqlite":
            m = re.match(r"sqlite:///(.+)", url)
            if m:
                db_path = Path(m.group(1))
                db_path.parent.mkdir(parents=True, exist_ok=True)
            _engine = create_engine(url, echo=False, connect_args={"check_same_thread": False})
        else:
            _engine = create_engine(url, echo=False)
    return _engine


def init_db():
    """Aplica las migraciones compartidas del backend."""
    get_engine()
    alembic_cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", settings.database_url)
    command.upgrade(alembic_cfg, "head")
    logger.info("Migraciones aplicadas/verificadas en %s", settings.DB_ENGINE)


def get_session():
    with Session(get_engine()) as session:
        yield session


def ensure_tables():
    from . import models
    init_db()


def get_or_create_session():
    return Session(get_engine())
