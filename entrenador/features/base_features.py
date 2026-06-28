from __future__ import annotations
from typing import List, Optional, Dict
from datetime import datetime, timedelta

import pandas as pd
import numpy as np

from ..config import settings


def compute_dixon_coles_strengths(df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
    overall_home = df["goles_local"].mean()
    overall_away = df["goles_visitante"].mean()
    overall = np.mean([overall_home, overall_away]) if np.isfinite(overall_home) and np.isfinite(overall_away) else 1.0
    overall = max(overall, 0.01)

    goals_for: Dict[str, List[float]] = {}
    goals_against: Dict[str, List[float]] = {}
    for _, r in df.iterrows():
        local = r["local_name"]
        visit = r["visit_name"]
        gf_l = float(r["goles_local"])
        ga_l = float(r["goles_visitante"])
        goals_for.setdefault(local, []).append(gf_l)
        goals_against.setdefault(local, []).append(ga_l)
        goals_for.setdefault(visit, []).append(ga_l)
        goals_against.setdefault(visit, []).append(gf_l)

    strengths = {}
    for team in set(list(goals_for.keys()) + list(goals_against.keys())):
        gf = np.mean(goals_for.get(team, [overall])) if goals_for.get(team) else overall
        ga = np.mean(goals_against.get(team, [overall])) if goals_against.get(team) else overall
        strengths[team] = {
            "attack": float(gf / overall),
            "defense": float(ga / overall),
        }
    return strengths


def add_dixon_coles_features(df_partidos: pd.DataFrame, strengths: Dict[str, Dict[str, float]],
                              home_team_col: str = "equipo_local",
                              away_team_col: str = "equipo_visitante") -> pd.DataFrame:
    df = df_partidos.copy()
    df["attack_local"] = df[home_team_col].map(lambda x: strengths.get(x, {}).get("attack", 1.0))
    df["defense_local"] = df[home_team_col].map(lambda x: strengths.get(x, {}).get("defense", 1.0))
    df["attack_visitante"] = df[away_team_col].map(lambda x: strengths.get(x, {}).get("attack", 1.0))
    df["defense_visitante"] = df[away_team_col].map(lambda x: strengths.get(x, {}).get("defense", 1.0))
    df["home_advantage"] = 1.0
    return df


def add_form_features(df: pd.DataFrame, windows: List[int] = None) -> pd.DataFrame:
    if windows is None:
        windows = settings.ROLLING_WINDOWS
    df = df.sort_values("fecha_utc").reset_index(drop=True)

    for window in windows:
        col_form_local = f"forma_local_{window}"
        col_form_visit = f"forma_visitante_{window}"
        col_gf_local = f"goles_favor_local_{window}"
        col_gc_local = f"goles_contra_local_{window}"
        col_gf_visit = f"goles_favor_visitante_{window}"
        col_gc_visit = f"goles_contra_visitante_{window}"

        df[col_form_local] = np.nan
        df[col_form_visit] = np.nan
        df[col_gf_local] = np.nan
        df[col_gc_local] = np.nan
        df[col_gf_visit] = np.nan
        df[col_gc_visit] = np.nan

        team_games: Dict[str, List[Dict]] = {}
        for idx, row in df.iterrows():
            local = row["local_name"]
            visit = row["visit_name"]
            gl = row["goles_local"]
            gv = row["goles_visitante"]

            for team, goals_for_team, goals_against_team in [
                (local, gl, gv), (visit, gv, gl)
            ]:
                if team not in team_games:
                    team_games[team] = []
                team_games[team].append({
                    "idx": idx,
                    "gf": goals_for_team,
                    "ga": goals_against_team,
                    "w": goals_for_team > goals_against_team,
                    "d": goals_for_team == goals_against_team,
                })

        for team, games in team_games.items():
            for i, g in enumerate(games):
                past = games[max(0, i - window):i]
                if not past:
                    continue
                puntos = sum((3 if p["w"] else 1 if p["d"] else 0) for p in past)
                gf = sum(p["gf"] for p in past)
                ga = sum(p["ga"] for p in past)
                n = len(past)

                idx = g["idx"]
                if team == df.at[idx, "local_name"]:
                    df.at[idx, col_form_local] = puntos / n
                    df.at[idx, col_gf_local] = gf / n
                    df.at[idx, col_gc_local] = ga / n
                else:
                    df.at[idx, col_form_visit] = puntos / n
                    df.at[idx, col_gf_visit] = gf / n
                    df.at[idx, col_gc_visit] = ga / n

    for col in [c for c in df.columns if c.startswith(("forma_", "goles_favor_", "goles_contra_"))]:
        df[col] = df[col].fillna(0.0)

    return df
