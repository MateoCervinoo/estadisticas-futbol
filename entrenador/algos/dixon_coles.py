from __future__ import annotations
import json
import math
import unicodedata
from typing import Dict, Any, Optional, Tuple

import numpy as np
import pandas as pd

from ..config import settings


def normalize_team_name(name: str) -> str:
    s = str(name).lower().strip()
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return s


def fit_dixon_coles(df: pd.DataFrame) -> Dict[str, Any]:
    teams = sorted(set(df["local_name"].unique()) | set(df["visit_name"].unique()))
    team_to_idx = {t: i for i, t in enumerate(teams)}

    overall_home = df["goles_local"].mean()
    overall_away = df["goles_visitante"].mean()
    overall = np.mean([overall_home, overall_away])
    overall = max(overall, 0.01)

    goals_for: Dict[str, list] = {t: [] for t in teams}
    goals_against: Dict[str, list] = {t: [] for t in teams}

    for _, r in df.iterrows():
        ht = r["local_name"]
        at = r["visit_name"]
        goals_for[ht].append(float(r["goles_local"]))
        goals_against[ht].append(float(r["goles_visitante"]))
        goals_for[at].append(float(r["goles_visitante"]))
        goals_against[at].append(float(r["goles_local"]))

    attack = []
    defense = []
    for t in teams:
        gf = np.mean(goals_for[t]) if goals_for[t] else overall
        ga = np.mean(goals_against[t]) if goals_against[t] else overall
        attack.append(float(gf / overall))
        defense.append(float(ga / overall))

    gamma = float(overall_home - overall_away)
    rho = settings.DIXON_COLES_RHO

    norm_teams = [normalize_team_name(t) for t in teams]
    model = {
        "attack": dict(zip(norm_teams, attack)),
        "defense": dict(zip(norm_teams, defense)),
        "gamma": gamma,
        "rho": rho,
        "teams": norm_teams,
        "team_to_idx": {normalize_team_name(t): i for t, i in team_to_idx.items()},
        "saved_at": pd.Timestamp.utcnow().isoformat(),
    }
    return model


def predict_match(home_team: str, away_team: str, model: Dict[str, Any],
                  max_goals: int = None, neutral: bool = True) -> list:
    if max_goals is None:
        max_goals = settings.PREDICT_MAX_GOALS

    atk = model.get("attack", {})
    df_params = model.get("defense", {})
    gamma = float(model.get("gamma", 0.0))
    rho = float(model.get("rho", 0.0))

    if isinstance(atk, dict):
        atk = {normalize_team_name(k): float(v) for k, v in atk.items()}
    if isinstance(df_params, dict):
        df_params = {normalize_team_name(k): float(v) for k, v in df_params.items()}

    hkey = normalize_team_name(home_team)
    akey = normalize_team_name(away_team)

    atk_h = float(atk.get(hkey, 1.0))
    def_a = float(df_params.get(akey, 1.0))
    atk_a = float(atk.get(akey, 1.0))
    def_h = float(df_params.get(hkey, 1.0))

    gamma_h = 0.0 if neutral else gamma

    eta_h = float(np.clip(atk_h - def_a + gamma_h, -700, 700))
    eta_a = float(np.clip(atk_a - def_h, -700, 700))

    lambda_h = math.exp(eta_h)
    lambda_a = math.exp(eta_a)

    size = max_goals + 1
    P = np.zeros((size, size), dtype=float)

    for i in range(size):
        for j in range(size):
            P[i, j] = (
                (lambda_h ** i) * math.exp(-lambda_h) / math.factorial(i) *
                (lambda_a ** j) * math.exp(-lambda_a) / math.factorial(j)
            )

    if abs(rho) > 1e-12:
        p0h = math.exp(-lambda_h)
        p1h = p0h * lambda_h
        p0a = math.exp(-lambda_a)
        p1a = p0a * lambda_a

        if size > 0 and size > 0:
            P[0, 0] *= 1.0 + rho * p0h * p0a
        if size > 0 and size > 1:
            P[0, 1] *= 1.0 - rho * p0h * p1a
        if size > 1 and size > 0:
            P[1, 0] *= 1.0 - rho * p1h * p0a
        if size > 1 and size > 1:
            P[1, 1] *= 1.0 + rho * p1h * p1a

    total = float(np.nansum(P))
    if total <= 0:
        return [[1.0 / (size * size)] * size for _ in range(size)]

    P = P / total
    return P.tolist()


def predict_score_proba(home_team: str, away_team: str, model: Dict[str, Any],
                         max_goals: int = None, neutral: bool = True) -> Dict[str, float]:
    P = predict_match(home_team, away_team, model, max_goals, neutral)
    n = len(P)
    home_win = sum(P[i][j] for i in range(n) for j in range(n) if i > j)
    draw = sum(P[i][i] for i in range(n))
    away_win = sum(P[i][j] for i in range(n) for j in range(n) if i < j)
    return {"home": home_win, "draw": draw, "away": away_win}


def save_model(model: Dict[str, Any], path: str = None):
    if path is None:
        path = str(settings.MODEL_PARAMS_PATH)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(model, f, ensure_ascii=False)


def load_model(path: str = None) -> Dict[str, Any]:
    if path is None:
        path = str(settings.MODEL_PARAMS_PATH)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
