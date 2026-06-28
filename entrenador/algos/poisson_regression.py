from __future__ import annotations
from typing import Dict, Any, Optional, Tuple

import numpy as np
import pandas as pd
from scipy.optimize import minimize


def fit_poisson_regression(df: pd.DataFrame) -> Dict[str, Any]:
    teams = sorted(set(df["local_name"].unique()) | set(df["visit_name"].unique()))
    team_to_idx = {t: i for i, t in enumerate(teams)}
    n_teams = len(teams)

    X_rows = []
    y_goals = []
    for _, r in df.iterrows():
        local_idx = team_to_idx[r["local_name"]]
        visit_idx = team_to_idx[r["visit_name"]]
        row_home = np.zeros(n_teams * 2 + 1)
        row_home[local_idx] = 1.0
        row_home[n_teams + visit_idx] = -1.0
        row_home[-1] = 1.0
        X_rows.append(row_home)
        y_goals.append(float(r["goles_local"]))

        row_away = np.zeros(n_teams * 2 + 1)
        row_away[visit_idx] = 1.0
        row_away[n_teams + local_idx] = -1.0
        row_away[-1] = 0.0
        X_rows.append(row_away)
        y_goals.append(float(r["goles_visitante"]))

    X = np.array(X_rows)

    def neg_log_likelihood(beta):
        lin_pred = X @ beta
        mu = np.exp(np.clip(lin_pred, -700, 700))
        ll = np.sum(y_goals * np.log(mu + 1e-12) - mu)
        return -ll

    beta0 = np.zeros(n_teams * 2 + 1)
    result = minimize(neg_log_likelihood, beta0, method="L-BFGS-B", options={"maxiter": 5000})

    params = result.x
    attack = {normalize_name(t): float(params[i]) for t, i in team_to_idx.items()}
    defense = {normalize_name(t): float(params[n_teams + i]) for t, i in team_to_idx.items()}
    home_adv = float(params[-1])
    intercept = float(np.mean(params[:n_teams]))

    model = {
        "attack": attack,
        "defense": defense,
        "home_advantage": home_adv,
        "intercept": intercept,
        "teams": [normalize_name(t) for t in teams],
        "log_likelihood": -result.fun,
        "converged": result.success,
    }
    return model


def normalize_name(name: str) -> str:
    import unicodedata
    s = str(name).lower().strip()
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return s
