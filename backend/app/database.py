import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlmodel import create_engine, Session

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@db:5432/estadisticas')
BACKEND_ROOT = Path(__file__).resolve().parents[1]

# Crear engine centralizado
engine = create_engine(DATABASE_URL, echo=False)


def get_session():
    """Yield a SQLModel Session. Use as dependency in FastAPI routes.

    Example:
        with get_session() as session:
            ...
    """
    with Session(engine) as session:
        yield session


def init_db():
    """Aplica migraciones Alembic hasta head."""
    alembic_cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", DATABASE_URL)
    command.upgrade(alembic_cfg, "head")
