from __future__ import annotations
from typing import List, Optional, Dict

import pandas as pd
import numpy as np

from ..config import settings


def add_advanced_features(df: pd.DataFrame,
                           stats_df: pd.DataFrame,
                           windows: List[int] = None) -> pd.DataFrame:
    if windows is None:
        windows = settings.ROLLING_WINDOWS

    df = df.copy()
    df = df.sort_values("fecha_utc").reset_index(drop=True)

    stat_cols = [
        "xg_local", "xg_visitante", "posesion_local", "posesion_visitante",
        "remates_local", "remates_visitante", "corners_local", "corners_visitante",
    ]
    if not stats_df.empty and "partido_id" in stats_df.columns:
        merge_cols = ["partido_id"] + [c for c in stat_cols if c in stats_df.columns]
        stats_by_match = stats_df[merge_cols].drop_duplicates("partido_id")
        df = df.merge(stats_by_match, on="partido_id", how="left")
    for col in stat_cols:
        if col not in df.columns:
            df[col] = np.nan

    advanced_cols = ["xg", "posesion", "remates", "corners"]
    for window in windows:
        for col_base in advanced_cols:
            local_col = f"{col_base}_local"
            visit_col = f"{col_base}_visitante"
            diff_col = f"{col_base}_diff_{window}"

            if local_col not in df.columns or visit_col not in df.columns:
                continue

            local_rolling = df.groupby("local_name")[local_col].transform(
                lambda x: x.rolling(window, min_periods=1).mean().shift(1)
            )
            visit_rolling = df.groupby("visit_name")[visit_col].transform(
                lambda x: x.rolling(window, min_periods=1).mean().shift(1)
            )
            team_avg_local = df.groupby("local_name")[local_col].transform("mean")
            team_avg_visit = df.groupby("visit_name")[visit_col].transform("mean")
            global_avg_local = df[local_col].mean()
            global_avg_visit = df[visit_col].mean()

            local_rolling = local_rolling.fillna(team_avg_local).fillna(global_avg_local).fillna(0)
            visit_rolling = visit_rolling.fillna(team_avg_visit).fillna(global_avg_visit).fillna(0)

            df[diff_col] = local_rolling - visit_rolling
            df[diff_col] = df[diff_col].fillna(0)

    return df


def add_elo_features(df: pd.DataFrame, elo_df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if elo_df.empty:
        df["elo_diff"] = 0
        df["ranking_fifa_diff"] = 0
        return df

    elo_map = {}
    for _, row in elo_df.iterrows():
        key = (row["equipo_id"], row["fecha"])
        elo_map[key] = row["elo"]

    def get_elo(team_id, date_str):
        return elo_map.get((team_id, str(date_str)[:10]))

    df["elo_local"] = df.apply(lambda r: get_elo(r["equipo_local_id"], r["fecha_utc"]), axis=1)
    df["elo_visitante"] = df.apply(lambda r: get_elo(r["equipo_visitante_id"], r["fecha_utc"]), axis=1)

    team_avg_elo = df.groupby("equipo_local_id")["elo_local"].transform("mean")
    df["elo_local"] = df["elo_local"].fillna(team_avg_elo)
    df["elo_visitante"] = df["elo_visitante"].fillna(df.groupby("equipo_visitante_id")["elo_visitante"].transform("mean"))
    df["elo_local"] = df["elo_local"].fillna(1500)
    df["elo_visitante"] = df["elo_visitante"].fillna(1500)

    df["elo_diff"] = (df["elo_local"] - df["elo_visitante"]).fillna(0).astype(int)
    df["ranking_fifa_diff"] = 0

    return df
