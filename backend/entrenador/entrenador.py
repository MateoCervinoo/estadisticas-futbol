"""
Entrenador independiente: genera /data/model_params.json con estructuras dict

Guarda attack/defense como diccionarios con claves = nombres de equipos
tal como aparecen en el CSV (llaves humanas, p. ej. 'Argentina').
"""
from __future__ import annotations
import os
import json
import datetime
from typing import Dict, Any
import pandas as pd
import numpy as np


def _find_results_csv() -> str:
    candidates = [
        '/data/results.csv',
        os.path.join('/', 'app', 'data', 'results.csv'),
        os.path.join(os.getcwd(), 'backend', 'app', 'data', 'results.csv'),
        os.path.join(os.getcwd(), 'data', 'results.csv'),
    ]
    for c in candidates:
        if c and os.path.exists(c) and os.path.isfile(c):
            return c

    # last-resort: scan backend/app/data
    alt = os.path.join(os.getcwd(), 'backend', 'app', 'data')
    if os.path.isdir(alt):
        for f in os.listdir(alt):
            if f.lower().endswith('.csv'):
                return os.path.join(alt, f)

    raise FileNotFoundError('No se encontró results.csv en /data ni en rutas conocidas')


def load_historical_data(since_year: int = 2018) -> pd.DataFrame:
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

    # Simple audit: drop rows with missing critical data
    df['home_score'] = pd.to_numeric(df['home_score'], errors='coerce')
    df['away_score'] = pd.to_numeric(df['away_score'], errors='coerce')
    mask = df['home_team'].notna() & df['away_team'].notna() & df['date'].notna() & df['home_score'].notna() & df['away_score'].notna()
    df = df[mask].copy()
    return df


def fit_dixon_coles(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Estima fuerzas attack/defense y devuelve un dict donde attack/defense
    son a su vez diccionarios: {"Argentina": 1.12, "Brazil": 0.91}
    """
    def _norm_name(s: str) -> str:
        try:
            return s.strip().casefold()
        except Exception:
            return str(s).strip().casefold()

    # Build mapping normalized_name -> canonical raw name (first seen)
    raw_teams = list(df['home_team'].unique()) + list(df['away_team'].unique())
    norm_to_raw = {}
    for t in raw_teams:
        if pd.isna(t):
            continue
        tn = _norm_name(t)
        if tn not in norm_to_raw:
            norm_to_raw[tn] = str(t).strip()

    # Initialize stats using normalized keys
    goals_for = {tn: [] for tn in norm_to_raw.keys()}
    goals_against = {tn: [] for tn in norm_to_raw.keys()}

    for _, r in df.iterrows():
        ht_raw = r['home_team']
        at_raw = r['away_team']
        ht = _norm_name(ht_raw)
        at = _norm_name(at_raw)
        hf = float(r['home_score'])
        af = float(r['away_score'])

        if ht not in goals_for:
            goals_for[ht] = []
            goals_against[ht] = []
            norm_to_raw[ht] = str(ht_raw).strip()
        if at not in goals_for:
            goals_for[at] = []
            goals_against[at] = []
            norm_to_raw[at] = str(at_raw).strip()

        goals_for[ht].append(hf)
        goals_against[ht].append(af)
        goals_for[at].append(af)
        goals_against[at].append(hf)

    overall_home_goals = df['home_score'].mean()
    overall_away_goals = df['away_score'].mean()
    overall = np.mean([overall_home_goals, overall_away_goals]) if np.isfinite(overall_home_goals) and np.isfinite(overall_away_goals) else 1.0

    attack = {}
    defense = {}
    # Store attack/defense keyed by normalized names for robust lookup
    for tn in sorted(goals_for.keys()):
        gf = np.mean(goals_for[tn]) if len(goals_for[tn]) > 0 else overall
        ga = np.mean(goals_against[tn]) if len(goals_against[tn]) > 0 else overall
        attack[tn] = float(gf / overall) if overall > 0 else 1.0
        defense[tn] = float(ga / overall) if overall > 0 else 1.0

    gamma = float(overall_home_goals - overall_away_goals) if np.isfinite(overall_home_goals) and np.isfinite(overall_away_goals) else 0.0
    rho = 0.0

    model = {
        # Provide original display names mapping for reference
        'teams': [norm_to_raw.get(k, k) for k in sorted(goals_for.keys())],
        # attack/defense keyed by normalized name (strip+casefold)
        'attack': attack,
        'defense': defense,
        'gamma': gamma,
        'rho': rho,
        'saved_at': datetime.datetime.now(timezone.utc).isoformat() + 'Z',
    }

    return model


def write_model(model: Dict[str, Any], path: str = '/data/model_params.json') -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(model, fh, indent=2, ensure_ascii=False)


def main():
    df = load_historical_data()
    model = fit_dixon_coles(df)
    write_model(model)
    print("Model params written to /data/model_params.json")


if __name__ == '__main__':
    main()
