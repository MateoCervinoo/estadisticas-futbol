"""
Dixon-Coles model implementation adapted to use a real historical dataset
provided by app.data_manager.get_combined_dataset().

This module exposes:
- fit_dixon_coles(): fit attack/defense parameters, home advantage and rho
- predict_exact_score_matrix(home_team, away_team, model, max_goals=5)

Design notes:
- The dataset must be a pandas DataFrame with columns:
  date, home_team, away_team, home_score, away_score, neutral (bool/0-1)
- For non-neutral matches a scalar home advantage gamma is applied; for
  neutral matches (e.g. most World Cup matches) gamma is not applied.
- The likelihood uses independent Poissons for goals with a Dixon-Coles
  adjustment (rho) applied to low-score outcomes (0-0,0-1,1-0,1-1).
"""

from typing import Dict, Any, Optional, Tuple
import numpy as np
from scipy.optimize import minimize
from scipy.special import gammaln

from app.data_manager import get_combined_dataset


def _prepare_data_from_df(df):
    """Transforma el DataFrame esperado en arrays numéricos para el modelo.

    df: pandas.DataFrame con columnas ['date','home_team','away_team','home_score','away_score','neutral']
    Retorna: teams (list), map_team_to_idx (dict), arrays home_idx, away_idx, y_home, y_away, neutral_flag
    """
    teams = sorted(list(set(df['home_team']).union(set(df['away_team']))))
    team_to_idx = {t: i for i, t in enumerate(teams)}

    home_idx = df['home_team'].map(team_to_idx).to_numpy(dtype=int)
    away_idx = df['away_team'].map(team_to_idx).to_numpy(dtype=int)
    y_home = df['home_score'].to_numpy(dtype=int)
    y_away = df['away_score'].to_numpy(dtype=int)
    neutral = df['neutral'].astype(int).to_numpy(dtype=int)

    return teams, team_to_idx, home_idx, away_idx, y_home, y_away, neutral


def fit_dixon_coles(df=None, max_iter: int = 1000, verbose: bool = False) -> Dict[str, Any]:
    """Entrena el modelo usando el DataFrame provisto por app.data_manager.get_combined_dataset().

    Parámetros:
    - df: opcional pandas.DataFrame; si no se provee se llama a get_combined_dataset()
    - max_iter: iteraciones máximas para el optimizador

    Retorna un dict con keys: teams, attack, defense, gamma (home adv), rho
    """
    import pandas as pd

    if df is None:
        df = get_combined_dataset()

    # Validaciones básicas
    required_cols = {'date', 'home_team', 'away_team', 'home_score', 'away_score', 'neutral'}
    if not required_cols.issubset(df.columns):
        raise ValueError(f"DataFrame must contain columns: {required_cols}")

    teams, team_to_idx, h_idx, a_idx, y_home, y_away, neutral = _prepare_data_from_df(df)
    n_teams = len(teams)

    # Initial parameters: small random noise around zero
    rng = np.random.default_rng(42)
    atk0 = rng.normal(0.0, 0.1, size=n_teams)
    def0 = rng.normal(0.0, 0.1, size=n_teams)
    gamma0 = 0.1  # home advantage
    rho0 = 0.0

    # Pack parameters: [atk(0..n-1), def(0..n-1), gamma, rho]
    x0 = np.concatenate([atk0, def0, np.array([gamma0, rho0])])

    # Precompute factorial logs for Poisson via gammaln for numerical stability
    max_goal = max(int(y_home.max()), int(y_away.max()), 5)

    def _log_poisson_pmf(k, lam):
        # log P(K=k) = k*log(lam) - lam - log(k!)
        return k * np.log(lam + 1e-12) - lam - gammaln(k + 1)

    def _neg_log_likelihood(x):
        atk = x[:n_teams]
        df = x[n_teams:2 * n_teams]
        gamma = x[-2]
        rho = x[-1]

        lambda_h = np.exp(atk[h_idx] - df[a_idx] + gamma * (1 - neutral))
        lambda_a = np.exp(atk[a_idx] - df[h_idx] + gamma * 0)  # away side doesn't get gamma

        # Poisson log-likelihoods
        ll = np.sum(_log_poisson_pmf(y_home, lambda_h) + _log_poisson_pmf(y_away, lambda_a))

        # Dixon-Coles adjustment for low-score games (0-0, 0-1, 1-0, 1-1)
        # Following Dixon & Coles, we add log adjustment term for these combinations
        # phi = 1 - rho * (1 - p0h - p1h) * (1 - p0a - p1a) ... simplified here
        # Implement exact adjustment per the original paper for scores (0,0),(0,1),(1,0),(1,1)
        # Compute small-score probabilities
        adj = 0.0
        for i in range(len(h_idx)):
            lam_h = lambda_h[i]
            lam_a = lambda_a[i]
            p0h = np.exp(-lam_h)
            p1h = p0h * lam_h
            p0a = np.exp(-lam_a)
            p1a = p0a * lam_a

            if y_home[i] == 0 and y_away[i] == 0:
                adj += np.log(1 + rho * (1 - p0h) * (1 - p0a) + 1e-12)
            elif y_home[i] == 0 and y_away[i] == 1:
                adj += np.log(1 - rho * p0h * (1 - p0a) + 1e-12)
            elif y_home[i] == 1 and y_away[i] == 0:
                adj += np.log(1 - rho * (1 - p0h) * p0a + 1e-12)
            elif y_home[i] == 1 and y_away[i] == 1:
                adj += np.log(1 + rho * p0h * p0a + 1e-12)

        total_ll = ll + adj

        # Regularization: small L2 to stabilize with many teams
        reg = 1e-4 * (np.sum(atk ** 2) + np.sum(df ** 2) + gamma ** 2 + rho ** 2)

        neg_ll = -total_ll + reg
        if verbose:
            print(f"neg_ll={neg_ll:.3f}")
        return neg_ll

    # Constraint: sum of attacks = 0 for identifiability
    cons = ({'type': 'eq', 'fun': lambda x: np.sum(x[:n_teams])},)

    res = minimize(_neg_log_likelihood, x0, method='SLSQP', constraints=cons, options={'maxiter': max_iter})

    if not res.success:
        raise RuntimeError(f"Optimización fallida: {res.message}")

    x_opt = res.x
    attack = x_opt[:n_teams]
    defense = x_opt[n_teams:2 * n_teams]
    gamma = float(x_opt[-2])
    rho = float(x_opt[-1])

    return {
        'teams': teams,
        'team_to_idx': team_to_idx,
        'attack': attack.tolist(),
        'defense': defense.tolist(),
        'gamma': gamma,
        'rho': rho,
    }


def predict_exact_score_matrix(home_team: str, away_team: str, model: Dict[str, Any], max_goals: int = 5, neutral: Optional[bool] = True):
    """Genera la matriz P(i,j) de probabilidades exactas hasta max_goals.

    home_team and away_team are strings matching the team names in the trained model.
    neutral: if True, no home advantage is applied; if False, gamma is applied.
    """
    teams = model['teams']
    team_to_idx = model['team_to_idx']
    if home_team not in team_to_idx or away_team not in team_to_idx:
        raise ValueError('Both teams must be present in the trained model')

    i_home = team_to_idx[home_team]
    i_away = team_to_idx[away_team]

    atk = np.array(model['attack'])
    df = np.array(model['defense'])
    gamma = float(model.get('gamma', 0.0))

    # Apply home advantage only if not neutral
    gamma_home = gamma if not neutral else 0.0

    lambda_h = float(np.exp(atk[i_home] - df[i_away] + gamma_home))
    lambda_a = float(np.exp(atk[i_away] - df[i_home] + 0.0))

    P = np.zeros((max_goals + 1, max_goals + 1), dtype=float)
    for i in range(max_goals + 1):
        # compute Poisson pmf for home i
        p_i = np.exp(-lambda_h) * lambda_h ** i / np.math.factorial(i)
        for j in range(max_goals + 1):
            p_j = np.exp(-lambda_a) * lambda_a ** j / np.math.factorial(j)
            P[i, j] = p_i * p_j

    # Optionally apply Dixon-Coles rho adjustment for low-scoring results
    rho = float(model.get('rho', 0.0))
    if abs(rho) > 1e-8:
        # Adjust cells (0,0),(0,1),(1,0),(1,1)
        p0h = np.exp(-lambda_h)
        p1h = p0h * lambda_h
        p0a = np.exp(-lambda_a)
        p1a = p0a * lambda_a

        # original probabilities
        # apply multiplicative adjustments similar to Dixon-Coles
        P00 = P[0, 0]
        P01 = P[0, 1]
        P10 = P[1, 0]
        P11 = P[1, 1]

        P[0, 0] = P00 * (1 + rho * p0h * p0a)
        P[0, 1] = P01 * (1 - rho * p0h * p1a)
        P[1, 0] = P10 * (1 - rho * p1h * p0a)
        P[1, 1] = P11 * (1 + rho * p1h * p1a)

    # Normalize to ensure sum to 1
    P = P / P.sum()
    return P.tolist()


if __name__ == "__main__":
    # Prueba local rápida (requiere partidos en la DB)
    m = fit_dixon_coles()
    print(m)
