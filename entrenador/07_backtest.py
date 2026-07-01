from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sqlmodel import Session, select

from .algos.dixon_coles import fit_dixon_coles, fit_dixon_coles_xg, predict_score_proba
from .config import settings
from .database import get_engine, init_db
from .models import Equipo, ModelFeatures, Partido, PartidoEstadisticas, Torneo
from .utils.dedupe import normalize_team

try:
    from scipy.optimize import minimize
except Exception:  # pragma: no cover - scipy is optional at import time
    minimize = None


logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL))
logger = logging.getLogger("07_backtest")

RESULT_KEYS = ("home", "draw", "away")
# Keep this list conservative: only use stored features that are generated from
# prior matches or match context, avoiding global-strength fallbacks with leakage.
TABULAR_CANDIDATE_FEATURES = (
    "forma_local_5",
    "forma_visitante_5",
    "forma_local_10",
    "forma_visitante_10",
    "goles_favor_local_5",
    "goles_contra_local_5",
    "goles_favor_visitante_5",
    "goles_contra_visitante_5",
    "dias_descanso_local",
    "dias_descanso_visitante",
    "neutral_field",
    "importancia_torneo",
    "fase_eliminatoria",
    "h2h_partidos",
    "h2h_victorias_local",
    "h2h_victorias_visitante",
    "h2h_goles_local",
    "h2h_goles_visitante",
)


def _load_backtest_data(engine, max_matches: Optional[int] = None) -> pd.DataFrame:
    with Session(engine) as session:
        partidos = session.exec(
            select(Partido).where(
                Partido.estado == "FT",
                Partido.goles_local.isnot(None),
                Partido.goles_visitante.isnot(None),
            ).order_by(Partido.fecha_utc)
        ).all()

        rows = []
        for p in partidos:
            local = session.get(Equipo, p.equipo_local_id)
            visit = session.get(Equipo, p.equipo_visitante_id)
            stats = session.exec(
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

    if feature_rows:
        feature_data = []
        for f in feature_rows:
            row = {"partido_id": f.partido_id}
            for col in TABULAR_CANDIDATE_FEATURES:
                row[col] = getattr(f, col, None)
            feature_data.append(row)
        df = df.merge(pd.DataFrame(feature_data), on="partido_id", how="left")

    df["fecha_utc"] = pd.to_datetime(df["fecha_utc"], utc=True, errors="coerce")
    df = df.dropna(subset=["fecha_utc"])
    df = df[df["goles_local"] >= 0]
    df = df[df["goles_visitante"] >= 0]
    df["goles_local"] = df["goles_local"].astype(int)
    df["goles_visitante"] = df["goles_visitante"].astype(int)
    df = df.sort_values("fecha_utc")

    if max_matches and len(df) > max_matches:
        df = df.tail(max_matches)

    return df.reset_index(drop=True)


def _actual_result(row: pd.Series) -> str:
    if int(row["goles_local"]) > int(row["goles_visitante"]):
        return "home"
    if int(row["goles_local"]) < int(row["goles_visitante"]):
        return "away"
    return "draw"


def _normalize_probs(probs: Dict[str, float], eps: float = 1e-15) -> Dict[str, float]:
    clipped = {k: max(float(probs.get(k, 0.0)), eps) for k in RESULT_KEYS}
    total = sum(clipped.values())
    if total <= 0 or not np.isfinite(total):
        return {k: 1.0 / len(RESULT_KEYS) for k in RESULT_KEYS}
    return {k: clipped[k] / total for k in RESULT_KEYS}


def _log_loss_result(probs: Dict[str, float], actual: str, eps: float = 1e-15) -> float:
    p = _normalize_probs(probs, eps)[actual]
    return -float(np.log(np.clip(p, eps, 1.0)))


def _brier_score_result(probs: Dict[str, float], actual: str) -> float:
    norm = _normalize_probs(probs)
    return float(np.mean([(norm[k] - (1.0 if k == actual else 0.0)) ** 2 for k in RESULT_KEYS]))


def calibration_ece(
    confidences: List[float], outcomes: List[float], n_bins: int = 10
) -> Dict[str, Any]:
    if not confidences:
        return {"bins": [], "observed_freqs": [], "avg_confidences": [], "counts": [], "ece": None}

    conf_arr = np.asarray(confidences, dtype=float)
    out_arr = np.asarray(outcomes, dtype=float)
    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    bin_centers: List[float] = []
    observed_freqs: List[float] = []
    avg_confidences: List[float] = []
    counts: List[int] = []
    ece = 0.0

    for i in range(n_bins):
        if i == n_bins - 1:
            mask = (conf_arr >= bin_edges[i]) & (conf_arr <= bin_edges[i + 1])
        else:
            mask = (conf_arr >= bin_edges[i]) & (conf_arr < bin_edges[i + 1])

        count = int(mask.sum())
        bin_centers.append(float((bin_edges[i] + bin_edges[i + 1]) / 2.0))
        counts.append(count)
        if count:
            acc = float(out_arr[mask].mean())
            avg_conf = float(conf_arr[mask].mean())
            observed_freqs.append(acc)
            avg_confidences.append(avg_conf)
            ece += (count / len(conf_arr)) * abs(acc - avg_conf)
        else:
            observed_freqs.append(0.0)
            avg_confidences.append(0.0)

    return {
        "bins": bin_centers,
        "observed_freqs": observed_freqs,
        "avg_confidences": avg_confidences,
        "counts": counts,
        "ece": float(ece),
    }


def compute_probability_metrics(
    df: pd.DataFrame, predictor: Callable[[pd.Series], Dict[str, float]], n_bins: int = 10
) -> Dict[str, Any]:
    if df.empty:
        return {"n": 0}

    log_losses: List[float] = []
    brier_scores: List[float] = []
    confidences: List[float] = []
    outcomes: List[float] = []
    correct = 0
    skipped = 0

    for _, row in df.iterrows():
        actual = _actual_result(row)
    for _, r in df.iterrows():
        gl, gv = int(r["goles_local"]), int(r["goles_visitante"])
        actual_mat = _actual_probs(gl, gv, max_goals + 1)

        try:
            probs = _normalize_probs(predictor(row))
        except Exception as exc:
            logger.warning("Error predicting %s vs %s: %s", row["local_name"], row["visit_name"], exc)
            skipped += 1
            continue

        pred = max(probs, key=probs.get)
        is_correct = pred == actual
        correct += int(is_correct)
        log_losses.append(_log_loss_result(probs, actual))
        brier_scores.append(_brier_score_result(probs, actual))
        confidences.append(float(probs[pred]))
        outcomes.append(1.0 if is_correct else 0.0)

    n = len(log_losses)
    if n == 0:
        return {"n": 0, "skipped": skipped}

    return {
        "n": n,
        "skipped": skipped,
        "log_loss": float(np.mean(log_losses)),
        "brier_score": float(np.mean(brier_scores)),
        "accuracy_1x2": float(correct / n),
        "calibration": calibration_ece(confidences, outcomes, n_bins=n_bins),
    }
        # Result accuracy
        if gl > gv:
            actual_res = "home"
        elif gl < gv:
            actual_res = "away"
        else:
            actual_res = "draw"


def _temporal_split(df: pd.DataFrame, test_fraction: float = 0.2, min_train: int = 50) -> Tuple[pd.DataFrame, pd.DataFrame, Optional[str]]:
    if len(df) < min_train + 10:
        return df.iloc[0:0].copy(), df.iloc[0:0].copy(), None

    split_idx = max(min_train, int(len(df) * (1.0 - test_fraction)))
    split_idx = min(split_idx, len(df) - 1)
    train_df = df.iloc[:split_idx].copy()
    test_df = df.iloc[split_idx:].copy()
    cutoff = test_df["fecha_utc"].min().isoformat() if not test_df.empty else None
    return train_df, test_df, cutoff


def _fit_tabular_model(train_df: pd.DataFrame, min_rows: int = 150, min_features: int = 4) -> Optional[Dict[str, Any]]:
    if minimize is None or len(train_df) < min_rows:
        return None

    available = [c for c in TABULAR_CANDIDATE_FEATURES if c in train_df.columns]
    feature_cols = []
    for col in available:
        values = pd.to_numeric(train_df[col], errors="coerce")
        if values.notna().mean() >= 0.7 and values.nunique(dropna=True) > 1:
            feature_cols.append(col)

    if len(feature_cols) < min_features:
        return None

    X_raw = train_df[feature_cols].apply(pd.to_numeric, errors="coerce")
    means = X_raw.mean()
    X_raw = X_raw.fillna(means)
    stds = X_raw.std(ddof=0).replace(0, 1.0).fillna(1.0)
    X = ((X_raw - means) / stds).to_numpy(dtype=float)
    X = np.hstack([np.ones((X.shape[0], 1)), X])
    y = np.array([RESULT_KEYS.index(_actual_result(r)) for _, r in train_df.iterrows()], dtype=int)
    n_features = X.shape[1]
    n_classes = len(RESULT_KEYS)
    l2 = 0.1

    def objective(beta_flat: np.ndarray) -> float:
        beta = beta_flat.reshape(n_features, n_classes)
        scores = X @ beta
        scores -= scores.max(axis=1, keepdims=True)
        exp_scores = np.exp(scores)
        probs = exp_scores / exp_scores.sum(axis=1, keepdims=True)
        nll = -np.log(np.clip(probs[np.arange(len(y)), y], 1e-15, 1.0)).mean()
        penalty = l2 * float(np.sum(beta[1:] ** 2)) / (2.0 * len(y))
        return float(nll + penalty)

    result = minimize(objective, np.zeros(n_features * n_classes), method="L-BFGS-B", options={"maxiter": 500})
    if not result.success:
        logger.warning("Tabular model did not converge: %s", result.message)

    return {
        "type": "multinomial_logistic_regression",
        "feature_cols": feature_cols,
        "means": means.to_dict(),
        "stds": stds.to_dict(),
        "classes": list(RESULT_KEYS),
        "coef": result.x.reshape(n_features, n_classes).tolist(),
        "converged": bool(result.success),
    }


def _predict_tabular(row: pd.Series, model: Dict[str, Any]) -> Dict[str, float]:
    values = []
    for col in model["feature_cols"]:
        value = pd.to_numeric(row.get(col), errors="coerce")
        if pd.isna(value):
            value = model["means"][col]
        values.append((float(value) - float(model["means"][col])) / float(model["stds"][col]))
    x = np.array([1.0] + values, dtype=float)
    coef = np.asarray(model["coef"], dtype=float)
    scores = x @ coef
    scores -= scores.max()
    probs = np.exp(scores)
    probs = probs / probs.sum()
    return {cls: float(probs[i]) for i, cls in enumerate(model["classes"])}


def _dc_predictor(model: Dict[str, Any], max_goals: int) -> Callable[[pd.Series], Dict[str, float]]:
    def predictor(row: pd.Series) -> Dict[str, float]:
        return predict_score_proba(
            row["local_name"],
            row["visit_name"],
            model,
            max_goals=max_goals,
            neutral=bool(row.get("neutral_field", True)),
        )

    return predictor


def _ensemble_predictor(predictors: List[Callable[[pd.Series], Dict[str, float]]]) -> Callable[[pd.Series], Dict[str, float]]:
    def predictor(row: pd.Series) -> Dict[str, float]:
        pred_list = [_normalize_probs(p(row)) for p in predictors]
        return {k: float(np.mean([p[k] for p in pred_list])) for k in RESULT_KEYS}

    return predictor


def _coverage(df: pd.DataFrame) -> Dict[str, Any]:
    both_xg = df["xg_local"].notna() & df["xg_visitante"].notna()
    feature_cols = [c for c in TABULAR_CANDIDATE_FEATURES if c in df.columns]
    rows_with_features = int(df[feature_cols].notna().any(axis=1).sum()) if feature_cols else 0
    return {
        "matches": int(len(df)),
        "xg_matches": int(both_xg.sum()),
        "xg_coverage": float(both_xg.mean()) if len(df) else 0.0,
        "feature_rows": rows_with_features,
        "features_version": settings.FEATURES_VERSION,
    }


def _evaluate_segment(name: str, df: pd.DataFrame, max_goals: int) -> Dict[str, Any]:
    train_df, test_df, cutoff = _temporal_split(df)
    result: Dict[str, Any] = {
        "segment": name,
        "n": int(len(df)),
        "train_matches": int(len(train_df)),
        "test_matches": int(len(test_df)),
        "test_start_date": cutoff,
        "coverage": {"all": _coverage(df), "train": _coverage(train_df), "test": _coverage(test_df)},
        "models": {},
    }
    if train_df.empty or test_df.empty:
        result["status"] = "skipped_insufficient_temporal_data"
        return result

    model_base = fit_dixon_coles(train_df)
    model_xg = fit_dixon_coles_xg(train_df)
    base_predictor = _dc_predictor(model_base, max_goals)
    xg_predictor = _dc_predictor(model_xg, max_goals)

    result["models"]["dixon_coles_base"] = compute_probability_metrics(test_df, base_predictor)
    result["models"]["dixon_coles_xg"] = compute_probability_metrics(test_df, xg_predictor)

    ensemble_parts = [xg_predictor]
    tabular_model = _fit_tabular_model(train_df)
    if tabular_model:
        tabular_predictor = lambda row: _predict_tabular(row, tabular_model)
        result["models"]["tabular_simple"] = compute_probability_metrics(test_df, tabular_predictor)
        result["models"]["tabular_simple"]["features"] = tabular_model["feature_cols"]
        result["models"]["tabular_simple"]["converged"] = tabular_model["converged"]
        ensemble_parts.append(tabular_predictor)
    else:
        result["models"]["tabular_simple"] = {
            "n": 0,
            "status": "skipped_insufficient_features_or_scipy",
        }

    if len(ensemble_parts) > 1:
        result["models"]["ensemble_initial"] = compute_probability_metrics(
            test_df, _ensemble_predictor(ensemble_parts)
        )
        result["models"]["ensemble_initial"]["components"] = ["dixon_coles_xg", "tabular_simple"]
    else:
        result["models"]["ensemble_initial"] = {"n": 0, "status": "skipped_no_tabular_component"}

    best_name = None
    best_log_loss = None
    for model_name, metrics in result["models"].items():
        value = metrics.get("log_loss")
        if value is not None and (best_log_loss is None or value < best_log_loss):
            best_name = model_name
            best_log_loss = value
    result["best_by_log_loss"] = best_name
    return result


def backtest() -> Dict[str, Any]:
    logger.info("Iniciando backtest...")
    engine = get_engine()
    init_db()

    df = _load_backtest_data(engine, max_matches=5000)
    if df.empty:
        logger.warning("No hay datos para backtest")
        return {}

    logger.info("Datos cargados: %d partidos", len(df))
    df_sel = df[df["categoria"] == "seleccion"].copy()
    df_club = df[df["categoria"] == "club"].copy()
    segments = {
        "selecciones": _evaluate_segment("selecciones", df_sel, settings.PREDICT_MAX_GOALS),
        "clubes": _evaluate_segment("clubes", df_club, settings.PREDICT_MAX_GOALS),
    }

    results: Dict[str, Any] = {
        "version": "backtest_v2_temporal_1x2",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "training_date": datetime.now(timezone.utc).date().isoformat(),
        "model_backend_metadata": {
            "version": "backtest_v2_temporal_1x2",
            "features_version": settings.FEATURES_VERSION,
            "max_goals": settings.PREDICT_MAX_GOALS,
            "total_matches": int(len(df)),
            "xg_coverage": _coverage(df)["xg_coverage"],
            "segments": {
                name: {
                    "train_matches": segment.get("train_matches", 0),
                    "test_matches": segment.get("test_matches", 0),
                    "xg_coverage": segment.get("coverage", {}).get("all", {}).get("xg_coverage", 0.0),
                    "training_date": datetime.now(timezone.utc).date().isoformat(),
                    "best_by_log_loss": segment.get("best_by_log_loss"),
                }
                for name, segment in segments.items()
            },
        },
        "segments": segments,
    }

    for segment_name, segment in results["segments"].items():
        if segment.get("status"):
            logger.info("%s: %s", segment_name, segment["status"])
            continue
        logger.info("--- %s train=%d test=%d ---", segment_name, segment["train_matches"], segment["test_matches"])
        for model_name, metrics in segment["models"].items():
            if metrics.get("log_loss") is None:
                logger.info("  %s: %s", model_name, metrics.get("status", "sin resultados"))
                continue
            logger.info(
                "  %s: log_loss=%.4f brier=%.4f acc=%.2f%% ece=%.4f",
                model_name,
                metrics["log_loss"],
                metrics["brier_score"],
                metrics["accuracy_1x2"] * 100,
                metrics["calibration"].get("ece") or 0.0,
            )

    output_path = Path(settings.MODEL_PARAMS_PATH).parent / "backtest_results.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    logger.info("Resultados guardados en %s", output_path)
    return results


def main():
    backtest()
    logger.info("✅ 07_backtest completado")


if __name__ == "__main__":
    main()
