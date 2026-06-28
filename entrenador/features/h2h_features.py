from __future__ import annotations
import pandas as pd
import numpy as np


def add_h2h_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values("fecha_utc").reset_index(drop=True)
    df["h2h_partidos"] = 0
    df["h2h_victorias_local"] = 0
    df["h2h_victorias_visitante"] = 0
    df["h2h_goles_local"] = 0
    df["h2h_goles_visitante"] = 0

    h2h_cache: dict = {}
    for idx, row in df.iterrows():
        local = row["local_name"]
        visit = row["visit_name"]
        key = tuple(sorted([local, visit]))
        past = h2h_cache.get(key, [])
        if past:
            total = len(past)
            wins_local = sum(1 for p in past if p["local"] == local and p["gf"] > p["ga"])
            wins_visit = sum(1 for p in past if p["local"] == visit and p["ga"] > p["gf"])
            draws = sum(1 for p in past if p["gf"] == p["ga"])
            gf_local = sum(p["gf"] for p in past if p["local"] == local) + sum(p["ga"] for p in past if p["local"] == visit)
            ga_local = sum(p["ga"] for p in past if p["local"] == local) + sum(p["gf"] for p in past if p["local"] == visit)
            gf_visit = sum(p["gf"] for p in past if p["local"] == visit) + sum(p["ga"] for p in past if p["local"] == local)
            ga_visit = sum(p["ga"] for p in past if p["local"] == visit) + sum(p["gf"] for p in past if p["local"] == local)

            df.at[idx, "h2h_partidos"] = total
            df.at[idx, "h2h_victorias_local"] = wins_local
            df.at[idx, "h2h_victorias_visitante"] = wins_visit
            df.at[idx, "h2h_goles_local"] = gf_local
            df.at[idx, "h2h_goles_visitante"] = gf_visit

        gl = row["goles_local"]
        gv = row["goles_visitante"]
        if key not in h2h_cache:
            h2h_cache[key] = []
        h2h_cache[key].append({
            "local": local,
            "gf": gl,
            "ga": gv,
        })

    return df
