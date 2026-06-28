from __future__ import annotations
import pandas as pd
import numpy as np

from ..config import settings


TORNEO_IMPORTANCIA = {
    "mundial": 5,
    "continental": 4,
    "copa": 3,
    "liga": 3,
    "clasificatorias": 3,
    "amistoso": 1,
    "friendly": 1,
}


def add_context_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df = df.sort_values(["local_name", "fecha_utc"]).reset_index(drop=True)

    df["dias_descanso_local"] = df.groupby("local_name")["fecha_utc"].diff().dt.days.fillna(7).clip(1, 30)
    df = df.sort_values(["visit_name", "fecha_utc"]).reset_index(drop=True)
    df["dias_descanso_visitante"] = df.groupby("visit_name")["fecha_utc"].diff().dt.days.fillna(7).clip(1, 30)

    df["neutral_field"] = df.get("neutral", pd.Series([False] * len(df)))
    df["neutral_field"] = df["neutral_field"].fillna(False)

    if "tournament" in df.columns:
        df["importancia_torneo"] = df["tournament"].str.lower().map(
            lambda x: max(TORNEO_IMPORTANCIA.get(token, 2) for token in str(x).split())
        )
    else:
        df["importancia_torneo"] = 3

    df["fase_eliminatoria"] = df.get("etapa", pd.Series([""] * len(df))).str.lower().map(
        lambda x: 1 if any(kw in x for kw in ["semi", "final", "quarter", "round of", "elimin"]) else 0
    )

    return df


def compute_completeness_score(df: pd.DataFrame) -> pd.Series:
    candidates = [c for c in df.columns if c.endswith("_diff_5")]
    if not candidates:
        return pd.Series([0.0] * len(df))
    score = df[candidates].notna().sum(axis=1) / len(candidates)
    return score
