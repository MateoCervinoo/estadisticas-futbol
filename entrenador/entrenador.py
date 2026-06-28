from __future__ import annotations
"""
entrenador.py — Entry point legacy compatible.

Delega en el pipeline ETL modular.
Uso:
  python -m entrenador.entrenador               # full refresh
  python -m entrenador.05_train_model            # solo entrenar
  python -m entrenador.pipelines.run_incremental # diario
"""
from .pipelines.run_full_refresh import run_full_refresh


def main():
    run_full_refresh()


if __name__ == "__main__":
    main()
