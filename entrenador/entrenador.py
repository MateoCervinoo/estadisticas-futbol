"""
Entrenador independiente para generar parámetros del modelo Dixon-Coles.

Lee el CSV histórico (preferentemente en /data/results.csv) y escribe
los parámetros resultantes en /data/model_params.json.

Este script está pensado para ser invocado por el backend cuando falten
o estén desactualizados los parámetros.
"""
from __future__ import annotations
import os
import json
import datetime
from typing import Dict, Any
import unicodedata
import pandas as pd
import numpy as np

def _find_results_csv():
    # Obtiene la ruta de la carpeta donde está este script (entrenador/)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # La carpeta raíz es un nivel arriba de entrenador/
    root_dir = os.path.dirname(script_dir)

    # Busca en la carpeta 'data' que está en la raíz
    possible_path = os.path.join(root_dir, 'data', 'results.csv')

    if os.path.exists(possible_path):
        print(f"✅ Archivo encontrado en: {possible_path}")
        return possible_path
    else:
        raise FileNotFoundError(f"❌ No se encontró results.csv en la ruta esperada: {possible_path}")


def load_historical_data(since_year: int = 2018) -> pd.DataFrame:
    """
    Copia funcional de la versión usada por el backend pero adaptada
    para ejecutarse de forma independiente en el entrenador.
    """
    path = _find_results_csv()
    df = pd.read_csv(path)
    df['date'] = pd.to_datetime(df['date'])
    df = df[df['date'] >= f"{since_year}-01-01"].copy()
    if 'neutral' not in df.columns:
        df['neutral'] = False

    required = {'date', 'home_team', 'away_team', 'home_score', 'away_score', 'neutral'}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"El CSV histórico debe contener las columnas: {', '.join(sorted(required))}. Faltan: {', '.join(sorted(missing))}")

    # Validación simple similar a la versión en data_manager
    df['home_score'] = pd.to_numeric(df['home_score'], errors='coerce')
    df['away_score'] = pd.to_numeric(df['away_score'], errors='coerce')

    mask = df['home_team'].notna() & df['away_team'].notna() & df['date'].notna() & df['home_score'].notna() & df['away_score'].notna()
    df = df[mask].copy()

    return df


def fit_dixon_coles(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Entrenamiento liviano que estima fuerzas de ataque/defensa por equipo.

    - attack: media de goles a favor relativa a la media global
    - defense: media de goles en contra relativa a la media global
    - gamma: diferencia media (home - away)
    - rho: ajuste pequeño por Dixon-Coles (dejamos 0.0 por simplicidad)
    """
    # Asegurar columnas minimas
    cols = ['home_team', 'away_team', 'home_score', 'away_score']
    for c in cols:
        if c not in df.columns:
            raise ValueError(f"Columna requerida no encontrada: {c}")

    teams = sorted(set(df['home_team'].unique()).union(df['away_team'].unique()))
    team_to_idx = {t: i for i, t in enumerate(teams)}

    # Calcular medias
    overall_home_goals = df['home_score'].mean()
    overall_away_goals = df['away_score'].mean()
    overall = np.mean([overall_home_goals, overall_away_goals]) if np.isfinite(overall_home_goals) and np.isfinite(overall_away_goals) else 1.0

    # Inicializar counts
    goals_for = {t: [] for t in teams}
    goals_against = {t: [] for t in teams}

    for _, r in df.iterrows():
        ht = r['home_team']
        at = r['away_team']
        hf = float(r['home_score'])
        af = float(r['away_score'])
        goals_for[ht].append(hf)
        goals_against[ht].append(af)
        goals_for[at].append(af)
        goals_against[at].append(hf)

    attack = []
    defense = []
    for t in teams:
        gf = np.mean(goals_for[t]) if len(goals_for[t]) > 0 else overall
        ga = np.mean(goals_against[t]) if len(goals_against[t]) > 0 else overall
        # Relative strengths
        atk = float(gf / overall) if overall > 0 else 1.0
        df_st = float(ga / overall) if overall > 0 else 1.0
        attack.append(atk)
        defense.append(df_st)

    gamma = float(overall_home_goals - overall_away_goals) if np.isfinite(overall_home_goals) and np.isfinite(overall_away_goals) else 0.0
    rho = 0.0

    model = {
        'teams': teams,
        'team_to_idx': team_to_idx,
        'attack': attack,
        'defense': defense,
        'gamma': gamma,
        'rho': rho,
        'saved_at': datetime.datetime.utcnow().isoformat() + 'Z',
    }

    return model


def write_model(model):
    # Obtiene la ruta del script para calcular la ruta relativa a 'data'
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(script_dir)

    # Define la ruta absoluta al archivo dentro de la carpeta 'data' de la raíz
    path = os.path.join(root_dir, 'data', 'model_params.json')

    os.makedirs(os.path.dirname(path), exist_ok=True)
    # Normalización: quitar acentos/diacríticos y forzar minúsculas
    def norm(name: str) -> str:
        try:
            s = name.lower().strip()
        except Exception:
            s = str(name).lower().strip()
        return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

    # Si el modelo tiene listas de equipos/attack/defense, convertirlas a dict
    teams = model.get('teams')
    attack = model.get('attack')
    defense = model.get('defense')

    if isinstance(teams, (list, tuple)) and isinstance(attack, (list, tuple)) and isinstance(defense, (list, tuple)):
        # Emparejar por posición y normalizar nombres
        new_atk = {norm(name): val for name, val in zip(teams, attack)}
        new_def = {norm(name): val for name, val in zip(teams, defense)}
        to_save = {'attack': new_atk, 'defense': new_def}
    else:
        # Si no están en el formato esperado, guardar el modelo tal cual
        to_save = model

    with open(path, "w", encoding='utf-8') as f:
        json.dump(to_save, f, ensure_ascii=False)


def main():
    try:
        df = load_historical_data()
    except Exception as e:
        print(f"ERROR cargando histórico: {e}")
        raise

    model = fit_dixon_coles(df)
    write_model(model)
    print("Model params written to /data/model_params.json")


if __name__ == '__main__':
    main()
