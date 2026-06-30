from fastapi import FastAPI


def test_debug_endpoints_are_disabled_by_default(client):
    response = client.get("/api/debug/reporte-datos")

    assert response.status_code == 404


def test_startup_sync_is_disabled_by_default(monkeypatch):
    from app.services import sync_service

    called = False

    def fake_seed_equipos_if_empty():
        return None

    def fake_load_prediction_models(app):
        app.state.model_loaded = True

    def fake_sync_fixtures_and_metrics():
        nonlocal called
        called = True
        return {}

    monkeypatch.delenv("RUN_STARTUP_SYNC", raising=False)
    monkeypatch.setattr("app.data_manager.seed_equipos_if_empty", fake_seed_equipos_if_empty)
    monkeypatch.setattr(sync_service, "load_prediction_models", fake_load_prediction_models)
    monkeypatch.setattr(sync_service, "sync_fixtures_and_metrics", fake_sync_fixtures_and_metrics)

    app = FastAPI()
    sync_service.seed_and_sync_startup(app)

    assert app.state.model_loaded is True
    assert called is False


def test_startup_sync_can_be_enabled(monkeypatch):
    from app.services import sync_service

    called = False

    def fake_seed_equipos_if_empty():
        return None

    def fake_load_prediction_models(app):
        app.state.model_loaded = True

    def fake_sync_fixtures_and_metrics():
        nonlocal called
        called = True
        return {}

    monkeypatch.setenv("RUN_STARTUP_SYNC", "true")
    monkeypatch.setattr("app.data_manager.seed_equipos_if_empty", fake_seed_equipos_if_empty)
    monkeypatch.setattr(sync_service, "load_prediction_models", fake_load_prediction_models)
    monkeypatch.setattr(sync_service, "sync_fixtures_and_metrics", fake_sync_fixtures_and_metrics)

    app = FastAPI()
    sync_service.seed_and_sync_startup(app)

    assert app.state.model_loaded is True
    assert called is True
