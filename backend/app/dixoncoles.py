"""Dixon-Coles prediction utilities.

This module provides a pure numerical prediction function `predict_match`
and a helper `load_params` that reads model parameters from JSON. Training
logic was moved to the separate entrenador/entrenador.py script.
"""
from typing import Dict, Any, Optional, List
import math
import os
import json
import numpy as np
import unicodedata


def _norm(s: str) -> str:
    try:
        ss = s.lower().strip()
    except Exception:
        ss = str(s).lower().strip()
    return ''.join(c for c in unicodedata.normalize('NFD', ss) if unicodedata.category(c) != 'Mn')


def _norm_dict_keys(d: Any) -> Dict[str, float]:
    """Normalize all keys of a dict and convert values to float."""
    if not isinstance(d, dict):
        return {}
    result = {}
    for k, v in d.items():
        try:
            result[_norm(str(k))] = float(v)
        except Exception:
            pass
    return result


def predict_match(home_team: str, away_team: str, model: Dict[str, Any],
                  max_goals: int = 4, neutral: Optional[bool] = True):
    """Compute exact score probability matrix for home vs away using provided params.

    Supports both old (attack/defense) and new (xg_attack/xg_defense/feature_weights)
    model formats. When xG features are present, blends goal-based and xG-based lambdas.
    """
    if not isinstance(model, dict):
        raise ValueError('model must be a dict')

    home_name = home_team.strip() if isinstance(home_team, str) else str(home_team).strip()
    away_name = away_team.strip() if isinstance(away_team, str) else str(away_team).strip()

    # Parse attack/defense (support legacy list format)
    atk_raw = model.get('attack', {})
    df_raw = model.get('defense', {})

    # Legacy format conversion
    team_to_idx = model.get('team_to_idx')
    if team_to_idx and isinstance(team_to_idx, dict):
        if isinstance(atk_raw, (list, tuple)) or isinstance(df_raw, (list, tuple)):
            atk_tmp = {}
            def_tmp = {}
            for name, idx in team_to_idx.items():
                key = _norm(str(name))
                try:
                    atk_tmp[key] = float(atk_raw[int(idx)])
                except Exception:
                    atk_tmp[key] = 1.0
                try:
                    def_tmp[key] = float(df_raw[int(idx)])
                except Exception:
                    def_tmp[key] = 1.0
            atk_raw, df_raw = atk_tmp, def_tmp
    else:
        if isinstance(atk_raw, (list, tuple)):
            atk_raw = {}
        if isinstance(df_raw, (list, tuple)):
            df_raw = {}

    atk_map = _norm_dict_keys(atk_raw)
    def_map = _norm_dict_keys(df_raw)

    gamma = float(model.get('gamma', 0.0))
    rho = float(model.get('rho', 0.0))

    hkey = _norm(home_name)
    akey = _norm(away_name)

    atk_h = float(atk_map.get(hkey, 1.0))
    df_a = float(def_map.get(akey, 1.0))
    atk_a = float(atk_map.get(akey, 1.0))
    df_h = float(def_map.get(hkey, 1.0))

    # apply home advantage only if not neutral
    gamma_home = 0.0 if neutral else float(gamma)

    # compute goal-based lambdas
    eta_h = float(np.clip(float(atk_h - df_a + gamma_home), -700, 700))
    eta_a = float(np.clip(float(atk_a - df_h), -700, 700))
    lambda_h = float(np.exp(np.maximum(eta_h, -700.0)))
    lambda_a = float(np.exp(np.maximum(eta_a, -700.0)))

    # --- xG blend if available ---
    xg_atk_raw = model.get('xg_attack')
    xg_df_raw = model.get('xg_defense')
    rho_xg = float(model.get('rho_xg', 0.0))
    fw = model.get('feature_weights', {})
    xg_blend = float(fw.get('xg_blend', 0.0))

    if xg_atk_raw and xg_df_raw and abs(xg_blend) > 1e-12:
        xg_atk_map = _norm_dict_keys(xg_atk_raw)
        xg_def_map = _norm_dict_keys(xg_df_raw)

        xg_atk_h = float(xg_atk_map.get(hkey, atk_h))
        xg_def_a = float(xg_def_map.get(akey, df_a))
        xg_atk_a = float(xg_atk_map.get(akey, atk_a))
        xg_def_h = float(xg_def_map.get(hkey, df_h))

        xg_eta_h = float(np.clip(float(xg_atk_h - xg_def_a + gamma_home), -700, 700))
        xg_eta_a = float(np.clip(float(xg_atk_a - xg_def_h), -700, 700))
        xg_lambda_h = float(np.exp(np.maximum(xg_eta_h, -700.0)))
        xg_lambda_a = float(np.exp(np.maximum(xg_eta_a, -700.0)))

        lambda_h = (1.0 - xg_blend) * lambda_h + xg_blend * xg_lambda_h
        lambda_a = (1.0 - xg_blend) * lambda_a + xg_blend * xg_lambda_a
        rho = rho_xg if abs(rho_xg) > 1e-12 else rho

    # Build joint Poisson matrix
    lam_h_safe = float(np.clip(lambda_h, 1e-12, 1e12))
    lam_a_safe = float(np.clip(lambda_a, 1e-12, 1e12))

    pmf_h = [float(np.exp(-lam_h_safe) * (lam_h_safe ** k) / math.factorial(k)) for k in range(max_goals + 1)]
    pmf_a = [float(np.exp(-lam_a_safe) * (lam_a_safe ** k) / math.factorial(k)) for k in range(max_goals + 1)]

    P = np.zeros((max_goals + 1, max_goals + 1), dtype=float)
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            P[i, j] = pmf_h[i] * pmf_a[j]

    # Dixon-Coles small score adjustment (multiplicative)
    if abs(rho) > 1e-12:
        p0h = float(np.exp(-np.maximum(lambda_h, 1e-12)))
        p1h = float(p0h * np.maximum(lambda_h, 1e-12))
        p0a = float(np.exp(-np.maximum(lambda_a, 1e-12)))
        p1a = float(p0a * np.maximum(lambda_a, 1e-12))

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
        size = max_goals + 1
        uniform = np.full((size, size), 1.0 / (size * size), dtype=float)
        return uniform.tolist()

    P = P / total
    return P.tolist()


# keep compatibility name
def predict_exact_score_matrix(home_team: str, away_team: str, model: Dict[str, Any], max_goals: int = 4, neutral: Optional[bool] = True):
    return predict_match(home_team, away_team, model, max_goals=max_goals, neutral=neutral)


def load_model_json(path: str) -> Optional[Dict[str, Any]]:
    """Load model from JSON path, returning None if not found."""
    try:
        if os.path.exists(path):
            with open(path, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    return None


def select_model_for_match(partido_id: int, engine, sel_model: Optional[Dict],
                           club_model: Optional[Dict]) -> Optional[Dict[str, Any]]:
    """Select the correct model (selecciones or clubes) based on match's tournament category."""
    from sqlmodel import Session, select
    from .models import Partido, Torneo

    try:
        with Session(engine) as session:
            p = session.get(Partido, partido_id)
            if not p:
                return sel_model or club_model
            if p.torneo_id:
                t = session.get(Torneo, p.torneo_id)
                if t:
                    if t.categoria == "club":
                        return club_model or sel_model
                    return sel_model or club_model
            return sel_model or club_model
    except Exception:
        return sel_model or club_model
