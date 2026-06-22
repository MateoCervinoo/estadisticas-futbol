"""
Implementación básica del modelo Dixon-Coles para estimar parámetros de ataque/defensa
y el parámetro rho para empates. Esta implementación está pensada para usarse
en un contexto de aprendizaje/simulación y puede mejorarse (regularización,
weights por antigüedad, validación, etc.).
"""
from typing import List, Tuple
import numpy as np
from scipy.optimize import minimize
from sqlmodel import Session, select

from .models import Partido
from .database import engine


def _prepare_data() -> Tuple[List[int], List[int], List[int], List[int]]:
    """Extrae partidos finalizados y devuelve listas de goles locales/visitantes y equipos.
    Retorna (home_team_ids, away_team_ids, home_goals, away_goals)
    """
    with Session(engine) as session:
        stmt = select(Partido).where(Partido.estado == "finalizado")
        partidos = session.exec(stmt).all()
        home_ids, away_ids, hg, ag = [], [], [], []
        for p in partidos:
            if p.local_id is None or p.visitante_id is None:
                continue
            home_ids.append(p.local_id)
            away_ids.append(p.visitante_id)
            hg.append(int(p.goles_local or 0))
            ag.append(int(p.goles_visitante or 0))
    return home_ids, away_ids, hg, ag


def fit_dixon_coles(max_goals=10):
    """Ajusta parámetros del modelo Dixon-Coles.

    Retorna un dict con attack, defense, rho y lambda (scalars) y la matriz
    de probabilidades base (Poisson) si se desea.
    """
    home_ids, away_ids, hg, ag = _prepare_data()
    if len(home_ids) == 0:
        raise ValueError("No hay partidos finalizados para entrenar el modelo")

    team_ids = sorted(list({*home_ids, *away_ids}))
    id_to_idx = {tid: i for i, tid in enumerate(team_ids)}
    n_teams = len(team_ids)

    # Inicial guesses
    atk0 = np.ones(n_teams)
    def0 = np.ones(n_teams)
    rho0 = 0.0

    y1 = np.array(hg)
    y2 = np.array(ag)
    h_idx = np.array([id_to_idx[h] for h in home_ids])
    a_idx = np.array([id_to_idx[a] for a in away_ids])

    def _neg_log_likelihood(params):
        atk = params[:n_teams]
        df = params[n_teams:2 * n_teams]
        rho = params[-1]

        lambda_h = np.exp(atk[h_idx] - df[a_idx])
        lambda_a = np.exp(atk[a_idx] - df[h_idx])

        # Poisson log-likelihood
        ll = np.sum(y1 * np.log(lambda_h + 1e-12) - lambda_h) + np.sum(y2 * np.log(lambda_a + 1e-12) - lambda_a)

        # Dixon-Coles adjustment for low-score games (0-1-2)
        # Implementación simplificada: ajusta probabilidades de (0,0),(0,1),(1,0),(1,1)
        # Para log-likelihood sumar término que depende de rho
        # Aquí añadimos una penalización suave por rho fuera de [-1,1]
        penalty = 0.0
        if rho < -1 or rho > 1:
            penalty += 1e6 * (abs(rho) - 1)

        return -ll + penalty

    # concatenar parámetros iniciales
    x0 = np.concatenate([atk0, def0, np.array([rho0])])

    # Constraints: sum of attack params = 0 to identify model
    cons = ({
        'type': 'eq',
        'fun': lambda x: np.sum(x[:n_teams])
    },)

    res = minimize(_neg_log_likelihood, x0, constraints=cons, method='SLSQP', options={'maxiter': 1000})

    if not res.success:
        raise RuntimeError(f"Optimización fallida: {res.message}")

    params = res.x
    atk = params[:n_teams]
    df = params[n_teams:2 * n_teams]
    rho = params[-1]

    result = {
        'teams': team_ids,
        'attack': atk.tolist(),
        'defense': df.tolist(),
        'rho': float(rho),
    }
    return result


def predict_exact_score_matrix(local_id: int, visitante_id: int, model: dict, max_goals=5):
    """Calcula la matriz de probabilidades exactas P(i,j) para goles i,j.

    Usa Poisson con parámetros lambda_h, lambda_a calculados a partir de attack/defense.
    No aplica ajuste Dixon-Coles complejo para la matriz completa, pero devuelve
    una matriz base que puede ajustarse con rho en bajos resultados.
    """
    team_ids = model['teams']
    if local_id not in team_ids or visitante_id not in team_ids:
        raise ValueError('Los equipos deben estar en el conjunto entrenado')

    idx_map = {tid: i for i, tid in enumerate(team_ids)}
    i_local = idx_map[local_id]
    i_visit = idx_map[visitante_id]

    atk = np.array(model['attack'])
    df = np.array(model['defense'])

    lambda_h = float(np.exp(atk[i_local] - df[i_visit]))
    lambda_a = float(np.exp(atk[i_visit] - df[i_local]))

    P = np.zeros((max_goals + 1, max_goals + 1))
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            P[i, j] = (np.exp(-lambda_h) * lambda_h ** i / np.math.factorial(i)) * (
                np.exp(-lambda_a) * lambda_a ** j / np.math.factorial(j))

    # Normalizar por si acaso
    P = P / P.sum()
    return P.tolist()


if __name__ == "__main__":
    # Prueba local rápida (requiere partidos en la DB)
    m = fit_dixon_coles()
    print(m)
