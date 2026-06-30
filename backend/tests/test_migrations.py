from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_db_migrates_from_zero(tmp_path, monkeypatch):
    db_path = tmp_path / "migrate_from_zero.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    backend_root = Path(__file__).resolve().parents[1]
    alembic_cfg = Config(str(backend_root / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(backend_root / "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")

    command.upgrade(alembic_cfg, "head")

    engine = create_engine(f"sqlite:///{db_path}")
    tables = set(inspect(engine).get_table_names())

    assert "partido" in tables
    assert "equipo" in tables
    assert "torneo" in tables
    assert "alembic_version" in tables
    partido_columns = {column["name"] for column in inspect(engine).get_columns("partido")}
    assert "tipo_dato" in partido_columns
