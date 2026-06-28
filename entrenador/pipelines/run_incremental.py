from __future__ import annotations
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ..config import settings
from ..database import init_db

logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL))
logger = logging.getLogger("run_incremental")


def run_incremental():
    logger.info("=" * 60)
    logger.info("INICIANDO PIPELINE INCREMENTAL")
    logger.info("=" * 60)

    start = time.time()

    init_db()

    steps = [
        ("02 - Actualizar desde Football-Data", lambda: _run_script("02_update_matches")),
        ("03 - Importar soccerdata (nuevos)", lambda: _run_script("03_import_soccerdata")),
        ("04 - Feature engineering", lambda: _run_script("04_feature_engineering")),
        ("05 - Re-entrenar modelo", lambda: _run_script("05_train_model")),
        ("06 - Predecir próximos", lambda: _run_script("06_predict")),
    ]

    for step_name, step_fn in steps:
        logger.info("▶ %s", step_name)
        try:
            step_fn()
            logger.info("✓ %s completado", step_name)
        except Exception as e:
            logger.error("✗ %s falló: %s", step_name, e)

    elapsed = time.time() - start
    logger.info("=" * 60)
    logger.info("PIPELINE INCREMENTAL COMPLETADO en %.1f segundos", elapsed)
    logger.info("=" * 60)


def _run_script(module_name: str):
    import importlib
    mod = importlib.import_module(f"..{module_name}", package="entrenador.pipelines")
    if hasattr(mod, "main"):
        mod.main()


if __name__ == "__main__":
    run_incremental()
