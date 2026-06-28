from __future__ import annotations
import pandas as pd
import numpy as np


def validate_partido_row(row: dict) -> bool:
    required = {"date", "home_team", "away_team", "home_score", "away_score"}
    for col in required:
        if col not in row or pd.isna(row[col]):
            return False
    try:
        hs = int(row["home_score"])
        vs = int(row["away_score"])
        if hs < 0 or vs < 0:
            return False
    except (ValueError, TypeError):
        return False
    return True


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in ("home_score", "away_score"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["date", "home_team", "away_team", "home_score", "away_score"])
    df = df[(df["home_score"] >= 0) & (df["away_score"] >= 0)]
    df["home_score"] = df["home_score"].astype(int)
    df["away_score"] = df["away_score"].astype(int)
    return df
