"""Dixon-Coles prediction utilities.

This module provides a pure numerical prediction function `predict_match`
and a helper `load_params` that reads model parameters from JSON. Training
logic was moved to the separate entrenador/entrenador.py script.
"""
from typing import Dict, Any, Optional
import math
import numpy as np
import unicodedata


def predict_match(home_team: str, away_team: str, model: Dict[str, Any], max_goals: int = 4, neutral: Optional[bool] = True):
    """Compute exact score probability matrix for home vs away using provided params.

    New model format expects 'attack' and 'defense' to be dicts keyed by
    normalized team name (strip + casefold). If old list-based format is
    supplied, this function will attempt to adapt safely.
    """
    if not isinstance(model, dict):
        raise ValueError('model must be a dict')

    def _norm(s: str) -> str:
        try:
            ss = s.lower().strip()
        except Exception:
            ss = str(s).lower().strip()
        # remove diacritic marks after NFD normalization
        return ''.join(c for c in unicodedata.normalize('NFD', ss) if unicodedata.category(c) != 'Mn')

    # prefer dict keyed access; support legacy list format if present
    # Clean input names (remove leading/trailing whitespace) and expose params variable
    home_name = home_team.strip() if isinstance(home_team, str) else str(home_team).strip()
    away_name = away_team.strip() if isinstance(away_team, str) else str(away_team).strip()
    params = model

    atk = params.get('attack', {})
    df = params.get('defense', {})

    # If legacy format with team_to_idx + list values, convert to dict keyed by normalized names
    team_to_idx = model.get('team_to_idx')
    if team_to_idx and isinstance(team_to_idx, dict):
        # only convert if attack/defense are lists/tuples
        if isinstance(atk, (list, tuple)) or isinstance(df, (list, tuple)):
            atk_tmp = {}
            def_tmp = {}
            for name, idx in team_to_idx.items():
                try:
                    key = name.strip().casefold()
                except Exception:
                    key = str(name).strip().casefold()
                try:
                    atk_tmp[key] = float(atk[int(idx)])
                except Exception:
                    atk_tmp[key] = 1.0
                try:
                    def_tmp[key] = float(df[int(idx)])
                except Exception:
                    def_tmp[key] = 1.0
            atk = atk_tmp
            df = def_tmp
    else:
        # If pure list format without team_to_idx, fallback to empty dicts so lookups return default 1.0
        if isinstance(atk, (list, tuple)):
            atk = {}
        if isinstance(df, (list, tuple)):
            df = {}

    gamma = float(model.get('gamma', 0.0))
    rho = float(model.get('rho', 0.0))

    # normalized keys (apply strip before normalizing)
    hkey = _norm(home_name)
    akey = _norm(away_name)

    # For robust matching, normalize both supplied names and the dict keys
    try:
        atk_map = { _norm(str(k)): float(v) for k, v in atk.items() } if isinstance(atk, dict) else {}
    except Exception:
        atk_map = {}
    try:
        def_map = { _norm(str(k)): float(v) for k, v in df.items() } if isinstance(df, dict) else {}
    except Exception:
        def_map = {}

    lh = _norm(home_name)
    la = _norm(away_name)

    atk_h = float(atk_map.get(lh, 1.0))
    df_a = float(def_map.get(la, 1.0))
    atk_a = float(atk_map.get(la, 1.0))
    df_h = float(def_map.get(lh, 1.0))

    # Diagnostic print requested for immediate troubleshooting
    try:
        print(f"🚨 PREDICCIÓN: {home_name} (Atk: {atk_h}) vs {away_name} (Def de away: {df_a})")
    except Exception:
        # Don't let logging break prediction
        pass

    # No debug printing; lookups use normalized keys and default to 1.0 if missing

    # apply home advantage only if not neutral
    gamma_home = 0.0 if neutral else float(gamma)

    # compute linear predictors and lambdas
    try:
        eta_h = float(atk_h - df_a + gamma_home)
    except Exception:
        eta_h = 0.0
    try:
        eta_a = float(atk_a - df_h)
    except Exception:
        eta_a = 0.0

    # Clip to safe ranges and exponentiate safely
    eta_h = float(np.clip(eta_h, -1000.0, 1000.0))
    eta_a = float(np.clip(eta_a, -1000.0, 1000.0))
    # Prevent overflow/underflow in exp
    lambda_h = float(np.exp(np.maximum(eta_h, -700.0)))
    lambda_a = float(np.exp(np.maximum(eta_a, -700.0)))

    # Build joint Poisson matrix
    P = np.zeros((max_goals + 1, max_goals + 1), dtype=float)
    lam_h_safe = float(np.clip(lambda_h, 1e-12, 1e12))
    lam_a_safe = float(np.clip(lambda_a, 1e-12, 1e12))

    # Precompute Poisson pmfs for efficiency
    pmf_h = [float(np.exp(-lam_h_safe) * (lam_h_safe ** k) / math.factorial(k)) for k in range(max_goals + 1)]
    pmf_a = [float(np.exp(-lam_a_safe) * (lam_a_safe ** k) / math.factorial(k)) for k in range(max_goals + 1)]

    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            P[i, j] = pmf_h[i] * pmf_a[j]

    # Dixon-Coles small score adjustment (multiplicative)
    if abs(rho) > 1e-12:
        p0h = float(np.exp(-np.maximum(lambda_h, 1e-12)))
        p1h = float(p0h * np.maximum(lambda_h, 1e-12))
        p0a = float(np.exp(-np.maximum(lambda_a, 1e-12)))
        p1a = float(p0a * np.maximum(lambda_a, 1e-12))

        # adjust specific cells safely if they exist
        if P.shape[0] > 0 and P.shape[1] > 0:
            P[0, 0] = P[0, 0] * (1.0 + rho * p0h * p0a)
        if P.shape[0] > 0 and P.shape[1] > 1:
            P[0, 1] = P[0, 1] * (1.0 - rho * p0h * p1a)
        if P.shape[0] > 1 and P.shape[1] > 0:
            P[1, 0] = P[1, 0] * (1.0 - rho * p1h * p0a)
        if P.shape[0] > 1 and P.shape[1] > 1:
            P[1, 1] = P[1, 1] * (1.0 + rho * p1h * p1a)

    total = float(np.nansum(P))
    if not np.isfinite(total) or total <= 0.0:
        # safe fallback: uniform matrix
        size = max_goals + 1
        uniform = np.full((size, size), 1.0 / (size * size), dtype=float)
        return uniform.tolist()

    P = P / total
    return P.tolist()


# keep compatibility name
def predict_exact_score_matrix(home_team: str, away_team: str, model: Dict[str, Any], max_goals: int = 4, neutral: Optional[bool] = True):
    return predict_match(home_team, away_team, model, max_goals=max_goals, neutral=neutral)
