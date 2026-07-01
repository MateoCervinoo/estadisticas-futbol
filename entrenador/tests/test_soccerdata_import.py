from __future__ import annotations

import importlib
import sys
import types
from datetime import datetime, timezone

import pandas as pd
from sqlmodel import Session, SQLModel, create_engine, select

from entrenador.features.advanced_features import add_advanced_features
from entrenador.models import Equipo, Partido, SourceCoverage, Torneo


alembic_module = types.ModuleType("alembic")
alembic_command = types.ModuleType("alembic.command")
alembic_config = types.ModuleType("alembic.config")
alembic_command.upgrade = lambda *args, **kwargs: None
alembic_config.Config = lambda *args, **kwargs: types.SimpleNamespace(set_main_option=lambda *a, **k: None)
sys.modules.setdefault("alembic", alembic_module)
sys.modules.setdefault("alembic.command", alembic_command)
sys.modules.setdefault("alembic.config", alembic_config)

importer = importlib.import_module("entrenador.03_import_soccerdata")


def _session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def test_find_partido_for_stat_matches_by_date_tournament_and_team_alias_when_hash_differs():
    session = _session()
    torneo = Torneo(nombre_canonico="Premier League", tipo="liga", categoria="club")
    local = Equipo(nombre_canonico="Manchester United", nombre_fbref="Manchester Utd", tipo="club")
    visitante = Equipo(nombre_canonico="Wolverhampton Wanderers", nombre_fbref="Wolves", tipo="club")
    session.add(torneo)
    session.add(local)
    session.add(visitante)
    session.flush()
    partido = Partido(
        fuente_origen="football_data",
        tipo_dato="api_sync",
        hash_dedupe="hash-local-distinto",
        fecha_utc=datetime(2024, 2, 1, 20, 0, tzinfo=timezone.utc),
        torneo_id=torneo.id,
        equipo_local_id=local.id,
        equipo_visitante_id=visitante.id,
        home_team="Manchester United FC",
        away_team="Wolverhampton Wanderers FC",
        goles_local=1,
        goles_visitante=0,
        estado="FT",
    )
    session.add(partido)
    session.commit()

    stat = {
        "hash_dedupe": "hash-fbref-distinto",
        "date": "2024-02-01",
        "home_team": "Manchester Utd",
        "away_team": "Wolves",
        "xg_local": 1.7,
        "xg_visitante": 0.4,
    }

    matched = importer._find_partido_for_stat(session, stat, torneo.id, "Premier League")

    assert matched is not None
    assert matched.id == partido.id


def test_upsert_coverage_updates_existing_row():
    session = _session()
    torneo = Torneo(nombre_canonico="La Liga", tipo="liga", categoria="club")
    session.add(torneo)
    session.flush()
    importer._upsert_coverage(session, "fbref", torneo.id, "2023-2024", 100, 80)
    session.commit()

    importer._upsert_coverage(session, "fbref", torneo.id, "2023-2024", 120, 110)
    session.commit()

    coverage = session.exec(select(SourceCoverage)).all()
    assert len(coverage) == 1
    assert coverage[0].total_partidos == 120
    assert coverage[0].partidos_con_stats == 110


def test_add_advanced_features_aligns_stats_by_partido_id_not_dataframe_index():
    partidos = pd.DataFrame([
        {"partido_id": 1, "fecha_utc": "2024-01-01", "local_name": "a", "visit_name": "b"},
        {"partido_id": 2, "fecha_utc": "2024-01-02", "local_name": "c", "visit_name": "d"},
    ])
    stats = pd.DataFrame([
        {"partido_id": 2, "xg_local": 2.0, "xg_visitante": 0.5},
    ])

    result = add_advanced_features(partidos, stats, windows=[5])

    by_id = result.set_index("partido_id")
    assert pd.isna(by_id.loc[1, "xg_local"])
    assert by_id.loc[2, "xg_local"] == 2.0
    assert by_id.loc[2, "xg_visitante"] == 0.5
