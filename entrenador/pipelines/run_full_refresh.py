from __future__ import annotations
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ..config import settings
from ..database import init_db

logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL))
logger = logging.getLogger("run_full_refresh")


def run_full_refresh():
    logger.info("=" * 60)
    logger.info("INICIANDO FULL REFRESH — Pipeline ETL completa")
    logger.info("=" * 60)

    start = time.time()

    init_db()
    logger.info("Base de datos inicializada")

    steps = [
        ("01 - Importar histórico CSV", lambda: _run_script("01_import_results")),
        ("02 - Actualizar desde Football-Data", lambda: _run_script("02_update_matches")),
        ("03 - Importar soccerdata", lambda: _run_script("03_import_soccerdata")),
        ("04 - Feature engineering", lambda: _run_script("04_feature_engineering")),
        ("05 - Entrenar modelo", lambda: _run_script("05_train_model")),
        ("06 - Predecir", lambda: _run_script("06_predict")),
    ]

    for step_name, step_fn in steps:
        logger.info("▶ %s", step_name)
        try:
            step_fn()
            logger.info("✓ %s completado", step_name)
        except Exception as e:
            logger.error("✗ %s falló: %s", step_name, e)
            raise

    elapsed = time.time() - start
    logger.info("=" * 60)
    logger.info("FULL REFRESH COMPLETADO en %.1f segundos", elapsed)
    logger.info("=" * 60)


def _run_script(module_name: str):
    import importlib
    mod = importlib.import_module(f"..{module_name}", package="entrenador.pipelines")
    if hasattr(mod, "main"):
        mod.main()


if __name__ == "__main__":
    run_full_refresh()
