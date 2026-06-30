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
        # Columnas del modelo unificado shared/models.py
        "ALTER TABLE partido ADD COLUMN IF NOT EXISTS fixture_id INTEGER",
        "ALTER TABLE partido ADD COLUMN IF NOT EXISTS fixture_id_externo VARCHAR",
        "ALTER TABLE partido ADD COLUMN IF NOT EXISTS hash_dedupe VARCHAR",
        "ALTER TABLE partido ADD COLUMN IF NOT EXISTS fecha_utc TIMESTAMP",
        "ALTER TABLE partido ADD COLUMN IF NOT EXISTS torneo_id INTEGER",
        "ALTER TABLE partido ADD COLUMN IF NOT EXISTS etapa VARCHAR",
        "ALTER TABLE partido ADD COLUMN IF NOT EXISTS grupo VARCHAR",
        "ALTER TABLE partido ADD COLUMN IF NOT EXISTS jornada INTEGER",
        "ALTER TABLE partido ADD COLUMN IF NOT EXISTS home_team VARCHAR",
        "ALTER TABLE partido ADD COLUMN IF NOT EXISTS away_team VARCHAR",
        "ALTER TABLE partido ADD COLUMN IF NOT EXISTS tournament VARCHAR",
        "ALTER TABLE partido ADD COLUMN IF NOT EXISTS home_crest_url VARCHAR",
        "ALTER TABLE partido ADD COLUMN IF NOT EXISTS away_crest_url VARCHAR",
        "ALTER TABLE partido ADD COLUMN IF NOT EXISTS goles_local_ht INTEGER",
        "ALTER TABLE partido ADD COLUMN IF NOT EXISTS goles_visitante_ht INTEGER",
        "ALTER TABLE partido ADD COLUMN IF NOT EXISTS xg_local REAL",
        "ALTER TABLE partido ADD COLUMN IF NOT EXISTS xg_visitante REAL",
        "ALTER TABLE partido ADD COLUMN IF NOT EXISTS created_at TIMESTAMP",
        "ALTER TABLE partido ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP",
    ]
    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))
