from sqlmodel import Session, select

from app.db.session import engine
from app.data_manager import ingest_historical_to_db
from app.models import Partido


def test_historical_load_leaves_expected_counts(tmp_path, monkeypatch):
    csv_path = tmp_path / "results.csv"
    csv_path.write_text(
        "date,home_team,away_team,home_score,away_score,neutral,tournament\n"
        "2024-01-10,Argentina,Brazil,2,1,true,FIFA World Cup\n"
        "2024-01-11,France,Germany,0,0,false,UEFA Euro\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CSV_DATA_PATH", str(csv_path))
    monkeypatch.setattr("app.data_manager.RESULTS_PATH", str(csv_path))

    ingest_historical_to_db(since_year=2024, batch_size=1)

    with Session(engine) as session:
        partidos = session.exec(select(Partido)).all()

    assert len(partidos) == 2
    assert {p.tipo_dato for p in partidos} == {"historico"}
    assert all(p.fixture_id is None for p in partidos)
    assert all(p.fixture_id_externo for p in partidos)
    assert all(p.hash_dedupe for p in partidos)
