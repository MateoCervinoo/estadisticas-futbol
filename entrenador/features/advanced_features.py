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

    df["xg_local"] = stats_df["xg_local"].reindex(df.index) if "xg_local" in stats_df.columns else np.nan
    df["xg_visitante"] = stats_df["xg_visitante"].reindex(df.index) if "xg_visitante" in stats_df.columns else np.nan
    df["posesion_local"] = stats_df["posesion_local"].reindex(df.index) if "posesion_local" in stats_df.columns else np.nan
    df["posesion_visitante"] = stats_df["posesion_visitante"].reindex(df.index) if "posesion_visitante" in stats_df.columns else np.nan
    df["remates_local"] = stats_df["remates_local"].reindex(df.index) if "remates_local" in stats_df.columns else np.nan
    df["remates_visitante"] = stats_df["remates_visitante"].reindex(df.index) if "remates_visitante" in stats_df.columns else np.nan
    df["corners_local"] = stats_df["corners_local"].reindex(df.index) if "corners_local" in stats_df.columns else np.nan
    df["corners_visitante"] = stats_df["corners_visitante"].reindex(df.index) if "corners_visitante" in stats_df.columns else np.nan

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
