import os
import sys
from pathlib import Path

TEST_DB_PATH = Path("/tmp/estadisticas_backend_pytest.db")
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"
os.environ.setdefault("API_FOOTBALL_KEY", "")

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
for path in (str(PROJECT_ROOT), str(BACKEND_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

import pytest
from sqlmodel import SQLModel

from app.db.session import engine
from app.models import *  # noqa: F403 - ensure all SQLModel tables are registered


@pytest.fixture(autouse=True)
def reset_db():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    yield
    SQLModel.metadata.drop_all(engine)


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from app.main import app

    app.state.sel_model = {
        "teams": ["Argentina", "Brazil"],
        "team_to_idx": {},
        "attack": {"argentina": 1.0, "brazil": 1.0},
        "defense": {"argentina": 1.0, "brazil": 1.0},
        "gamma": 0.0,
        "rho": 0.0,
    }
    app.state.club_model = None
    app.state.model = app.state.sel_model
    app.state.prediction_models_status = {
        "status": "ok",
        "selecciones": {"available": True, "path": None, "version": None, "team_count": 2},
        "clubes": {"available": False, "path": None, "version": None, "team_count": None},
    }
    return TestClient(app)
