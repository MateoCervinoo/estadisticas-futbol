from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy import text
import os

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@db:5432/estadisticas')

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
    """Inicializa las tablas (desarrollo)."""
    SQLModel.metadata.create_all(engine)


def ensure_partido_columns():
    """Garantiza columnas nuevas en tablas existentes sin usar migraciones externas."""
    statements = [
        "ALTER TABLE partido ADD COLUMN IF NOT EXISTS ht_home_score INTEGER",
        "ALTER TABLE partido ADD COLUMN IF NOT EXISTS ht_away_score INTEGER",
        "ALTER TABLE partido ADD COLUMN IF NOT EXISTS stage VARCHAR",
        "ALTER TABLE partido ADD COLUMN IF NOT EXISTS \"group\" VARCHAR",
        "ALTER TABLE partido ADD COLUMN IF NOT EXISTS home_crest_url VARCHAR",
        "ALTER TABLE partido ADD COLUMN IF NOT EXISTS away_crest_url VARCHAR",
    ]
    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))
