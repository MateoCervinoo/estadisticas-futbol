from __future__ import annotations
import logging
import json
from typing import Dict, Any, List, Tuple
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sqlmodel import Session, select

from .config import settings
from .database import get_engine, init_db
from .models import Partido, Torneo
from .algos.dixon_coles import (
    fit_dixon_coles, fit_dixon_coles_xg,
    predict_match, predict_score_proba, save_model,
)
from .utils.dedupe import normalize_team

logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL))
logger = logging.getLogger("07_backtest")


def _load_backtest_data(engine, max_matches: int = None) -> pd.DataFrame:
    with Session(engine) as session:
        partidos = session.exec(
            select(Partido).where(
                Partido.estado == "FT",
                Partido.goles_local.isnot(None),
                Partido.goles_visitante.isnot(None),
            ).order_by(Partido.fecha_utc)
        ).all()

    rows = []
    from .models import Equipo, PartidoEstadisticas
    for p in partidos:
        with Session(engine) as s:
            local = s.get(Equipo, p.equipo_local_id)
            visit = s.get(Equipo, p.equipo_visitante_id)
            stats = s.exec(
                select(PartidoEstadisticas).where(
                    PartidoEstadisticas.partido_id == p.id,
                    PartidoEstadisticas.fuente == "fbref",
                )
            ).first()
            torneo = s.get(Torneo, p.torneo_id) if p.torneo_id else None

        categoria = torneo.categoria if torneo else "seleccion"
        xgl = float(stats.xg_local) if stats and stats.xg_local is not None else None
        xgv = float(stats.xg_visitante) if stats and stats.xg_visitante is not None else None

        rows.append({
            "partido_id": p.id,
            "local_name": normalize_team(local.nombre_canonico or local.nombre_csv or "") if local else f"team_{p.equipo_local_id}",
            "visit_name": normalize_team(visit.nombre_canonico or visit.nombre_csv or "") if visit else f"team_{p.equipo_visitante_id}",
            "goles_local": p.goles_local or 0,
            "goles_visitante": p.goles_visitante or 0,
            "xg_local": xgl,
            "xg_visitante": xgv,
            "xg_fuente": "fbref" if xgl is not None and xgv is not None else None,
            "fecha_utc": p.fecha_utc,
            "categoria": categoria,
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    df["goles_local"] = df["goles_local"].astype(int)
    df["goles_visitante"] = df["goles_visitante"].astype(int)

    if max_matches and len(df) > max_matches:
        df = df.tail(max_matches)

    return df


def _actual_probs(gl: int, gv: int, size: int = 6) -> np.ndarray:
    P = np.zeros((size, size), dtype=float)
    if gl < size and gv < size:
        P[gl, gv] = 1.0
    else:
        P[min(gl, size - 1), min(gv, size - 1)] = 1.0
    return P


def _log_loss(probs: np.ndarray, actual: np.ndarray, eps: float = 1e-15) -> float:
    p = np.clip(probs, eps, 1 - eps)
    return -float(np.nansum(actual * np.log(p)))


def _brier_score(probs: np.ndarray, actual: np.ndarray) -> float:
    return float(np.mean((probs - actual) ** 2))


def compute_metrics(df: pd.DataFrame, model: Dict[str, Any],
                    max_goals: int = 6) -> Dict[str, Any]:
    if df.empty:
        return {"n": 0}

    log_losses = []
    brier_scores = []
    home_acc = 0
    draw_acc = 0
    away_acc = 0
    total = 0
    correct = 0

    for _, r in df.iterrows():
        gl, gv = int(r["goles_local"]), int(r["goles_visitante"])
        actual_mat = _actual_probs(gl, gv, max_goals + 1)

        try:
            P = predict_match(r["local_name"], r["visit_name"], model,
                              max_goals=max_goals, neutral=True)
        except Exception as e:
            logger.warning("Error predicting %s vs %s: %s", r["local_name"], r["visit_name"], e)
            continue

        P_arr = np.array(P, dtype=float)

        ll = _log_loss(P_arr, actual_mat)
        bs = _brier_score(P_arr, actual_mat)
        log_losses.append(ll)
        brier_scores.append(bs)

        # Result accuracy
        if gl > gv:
            actual_res = "home"
        elif gl < gv:
            actual_res = "away"
        else:
            actual_res = "draw"

        probs = predict_score_proba(r["local_name"], r["visit_name"], model,
                                    max_goals=max_goals, neutral=True)
        pred_res = max(probs, key=probs.get)
        if pred_res == actual_res:
            correct += 1
        total += 1

    if total == 0:
        return {"n": 0}

    return {
        "n": total,
        "log_loss": float(np.mean(log_losses)) if log_losses else None,
        "brier_score": float(np.mean(brier_scores)) if brier_scores else None,
        "accuracy": correct / total if total > 0 else 0,
        "home_goals_avg": float(df["goles_local"].mean()),
        "away_goals_avg": float(df["goles_visitante"].mean()),
    }


def reliability_diagram(df: pd.DataFrame, model: Dict[str, Any],
                        max_goals: int = 6, n_bins: int = 10) -> Dict[str, Any]:
    probs_list = []
    outcomes = []

    for _, r in df.iterrows():
        gl, gv = int(r["goles_local"]), int(r["goles_visitante"])
        try:
            P = predict_match(r["local_name"], r["visit_name"], model,
                              max_goals=max_goals, neutral=True)
        except Exception:
            continue
        P_arr = np.array(P, dtype=float)
        for i in range(min(P_arr.shape[0], max_goals + 1)):
            for j in range(min(P_arr.shape[1], max_goals + 1)):
                probs_list.append(float(P_arr[i, j]))
                outcomes.append(1.0 if (i == gl and j == gv) else 0.0)

    if not probs_list:
        return {}

    probs_arr = np.array(probs_list)
    outcomes_arr = np.array(outcomes)

    bin_edges = np.linspace(0, 1, n_bins + 1)
    bin_centers = []
    bin_accs = []
    bin_counts = []

    for i in range(n_bins):
        mask = (probs_arr >= bin_edges[i]) & (probs_arr < bin_edges[i + 1])
        if i == n_bins - 1:
            mask = (probs_arr >= bin_edges[i]) & (probs_arr <= bin_edges[i + 1])
        count = int(mask.sum())
        if count > 0:
            bin_centers.append(float((bin_edges[i] + bin_edges[i + 1]) / 2))
            bin_accs.append(float(outcomes_arr[mask].mean()))
            bin_counts.append(count)
        else:
            bin_centers.append(float((bin_edges[i] + bin_edges[i + 1]) / 2))
            bin_accs.append(0.0)
            bin_counts.append(0)

    ece = sum(
        bc * abs(bp - bc) for bp, bc, bc2 in zip(bin_centers, bin_accs, bin_counts)
    ) / max(sum(bin_counts), 1)

    return {
        "bins": bin_centers,
        "observed_freqs": bin_accs,
        "counts": bin_counts,
        "ece": float(ece),
    }


def backtest():
    logger.info("Iniciando backtest...")
    engine = get_engine()
    init_db()

    df = _load_backtest_data(engine, max_matches=2000)
    if df.empty:
        logger.warning("No hay datos para backtest")
        return

    logger.info("Datos cargados: %d partidos", len(df))

    # Split by category
    df_sel = df[df["categoria"] == "seleccion"].copy()
    df_club = df[df["categoria"] == "club"].copy()

    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_matches": len(df),
    }

    # ---- Selecciones ----
    if not df_sel.empty:
        logger.info("--- Selecciones (%d partidos) ---", len(df_sel))
        model_sel_base = fit_dixon_coles(df_sel)
        model_sel_xg = fit_dixon_coles_xg(df_sel)

        metrics_base = compute_metrics(df_sel, model_sel_base)
        metrics_xg = compute_metrics(df_sel, model_sel_xg)
        reliab = reliability_diagram(df_sel, model_sel_xg)

        results["selecciones"] = {
            "n": len(df_sel),
            "xg_available": int(df_sel["xg_local"].notna().sum()),
            "base_model": metrics_base,
            "xg_model": metrics_xg,
            "reliability": reliab,
        }
        logger.info("  Base:  log_loss=%.4f  brier=%.4f  acc=%.2f%%",
                    metrics_base.get("log_loss", 0), metrics_base.get("brier_score", 0),
                    metrics_base.get("accuracy", 0) * 100)
        logger.info("  XG:    log_loss=%.4f  brier=%.4f  acc=%.2f%%",
                    metrics_xg.get("log_loss", 0), metrics_xg.get("brier_score", 0),
                    metrics_xg.get("accuracy", 0) * 100)
    else:
        results["selecciones"] = {"n": 0}

    # ---- Clubes ----
    if not df_club.empty:
        logger.info("--- Clubes (%d partidos) ---", len(df_club))
        model_club_base = fit_dixon_coles(df_club)
        model_club_xg = fit_dixon_coles_xg(df_club)

        metrics_base = compute_metrics(df_club, model_club_base)
        metrics_xg = compute_metrics(df_club, model_club_xg)
        reliab = reliability_diagram(df_club, model_club_xg)

        results["clubes"] = {
            "n": len(df_club),
            "xg_available": int(df_club["xg_local"].notna().sum()),
            "base_model": metrics_base,
            "xg_model": metrics_xg,
            "reliability": reliab,
        }
        logger.info("  Base:  log_loss=%.4f  brier=%.4f  acc=%.2f%%",
                    metrics_base.get("log_loss", 0), metrics_base.get("brier_score", 0),
                    metrics_base.get("accuracy", 0) * 100)
        logger.info("  XG:    log_loss=%.4f  brier=%.4f  acc=%.2f%%",
                    metrics_xg.get("log_loss", 0), metrics_xg.get("brier_score", 0),
                    metrics_xg.get("accuracy", 0) * 100)
    else:
        results["clubes"] = {"n": 0}

    # Save results
    output_path = Path(settings.MODEL_PARAMS_PATH).parent / "backtest_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    logger.info("Resultados guardados en %s", output_path)

    # Generate reliability plot data as CSV for external plotting
    for cat in ("selecciones", "clubes"):
        cat_data = results.get(cat, {})
        reliab = cat_data.get("reliability", {})
        if reliab and reliab.get("bins"):
            plot_df = pd.DataFrame({
                "bin_center": reliab["bins"],
                "observed_freq": reliab["observed_freqs"],
                "count": reliab["counts"],
            })
            plot_path = Path(settings.MODEL_PARAMS_PATH).parent / f"reliability_{cat}.csv"
            plot_df.to_csv(plot_path, index=False)
            logger.info("Datos de reliability guardados en %s", plot_path)

    return results


def main():
    backtest()
    logger.info("✅ 07_backtest completado")


if __name__ == "__main__":
    main()
