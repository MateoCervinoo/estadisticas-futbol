from __future__ import annotations
import logging
import json
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime, timezone

from sqlmodel import Session, select

from .config import settings
from .database import get_engine
from .models import Partido, Equipo
from .algos.dixon_coles import load_model, predict_score_proba, predict_match

logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL))
logger = logging.getLogger("06_predict")


def predict_upcoming_matches() -> List[Dict[str, Any]]:
    model = load_model()
    if not model:
        logger.error("No se encontró modelo entrenado en %s", settings.MODEL_PARAMS_PATH)
        return []

    engine = get_engine()
    predictions = []

    with Session(engine) as session:
        upcoming = session.exec(
            select(Partido).where(
                Partido.estado.in_(["NS", "TIMED"]),
                Partido.fecha_utc >= datetime.now(timezone.utc),
            )
        ).all()

        if not upcoming:
            logger.info("No hay partidos próximos para predecir")
            return []

        for partido in upcoming:
            home_name = ""
            away_name = ""

            if partido.equipo_local_id:
                local = session.get(Equipo, partido.equipo_local_id)
                if local:
                    home_name = local.nombre_canonico or local.nombre_csv or f"team_{partido.equipo_local_id}"
            if not home_name and partido.home_team:
                home_name = partido.home_team

            if partido.equipo_visitante_id:
                visit = session.get(Equipo, partido.equipo_visitante_id)
                if visit:
                    away_name = visit.nombre_canonico or visit.nombre_csv or f"team_{partido.equipo_visitante_id}"
            if not away_name and partido.away_team:
                away_name = partido.away_team

            if not home_name or not away_name:
                continue

            proba = predict_score_proba(
                home_name, away_name, model,
                max_goals=settings.PREDICT_MAX_GOALS,
                neutral=partido.neutral,
            )

            predictions.append({
                "fixture_id": partido.fixture_id or partido.fixture_id_externo or str(partido.id),
                "home_team": home_name,
                "away_team": away_name,
                "date": partido.fecha_utc.isoformat() if partido.fecha_utc else "",
                "prob_home": round(proba["home"], 4),
                "prob_draw": round(proba["draw"], 4),
                "prob_away": round(proba["away"], 4),
                "predicted_result": "H" if proba["home"] > proba["away"] and proba["home"] > proba["draw"]
                    else "A" if proba["away"] > proba["home"] and proba["away"] > proba["draw"]
                    else "D",
            })

    logger.info("Predicciones generadas: %d partidos", len(predictions))
    return predictions


def predict_custom(home_team: str, away_team: str, neutral: bool = True) -> Dict[str, Any]:
    model = load_model()
    if not model:
        return {"error": "No hay modelo entrenado"}

    proba = predict_score_proba(home_team, away_team, model, neutral=neutral)
    return {
        "home_team": home_team,
        "away_team": away_team,
        "prob_home": round(proba["home"], 4),
        "prob_draw": round(proba["draw"], 4),
        "prob_away": round(proba["away"], 4),
    }


def main():
    predictions = predict_upcoming_matches()
    if predictions:
        output_path = Path(settings.MODEL_PARAMS_PATH).parent / "predictions.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(predictions, f, ensure_ascii=False, indent=2)
        logger.info("Predicciones guardadas en %s", output_path)
        for p in predictions[:5]:
            logger.info("  %s vs %s → H:%.1f%% E:%.1f%% A:%.1f%%",
                        p["home_team"], p["away_team"],
                        p["prob_home"] * 100, p["prob_draw"] * 100, p["prob_away"] * 100)

    logger.info("✅ 06_predict completado")


if __name__ == "__main__":
    main()
