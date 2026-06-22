from sqlmodel import SQLModel, create_engine, Session
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
