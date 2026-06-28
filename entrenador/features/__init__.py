from typing import List, Dict

FEATURE_GROUPS: Dict[str, List[str]] = {
    "dixon_coles_base": [
        "attack_local", "defense_local", "attack_visitante", "defense_visitante",
        "home_advantage",
    ],
    "recent_form": [
        "forma_local_5", "forma_visitante_5", "forma_local_10", "forma_visitante_10",
        "goles_favor_local_5", "goles_contra_local_5",
        "goles_favor_visitante_5", "goles_contra_visitante_5",
    ],
    "advanced_stats": [
        "xg_diff_5", "xg_diff_10", "posesion_diff_5", "shots_diff_5", "corners_diff_5",
    ],
    "elo_ratings": [
        "elo_diff", "ranking_fifa_diff",
    ],
    "context": [
        "dias_descanso_local", "dias_descanso_visitante",
        "neutral_field", "importancia_torneo", "fase_eliminatoria",
    ],
    "h2h": [
        "h2h_partidos", "h2h_victorias_local", "h2h_victorias_visitante",
        "h2h_goles_local", "h2h_goles_visitante",
    ],
}

MODEL_FEATURE_CONFIG: Dict[str, str] = {
    "dixon_coles": "dixon_coles_base,recent_form,context,h2h,elo_ratings",
    "poisson_regression": "dixon_coles_base,recent_form,context,elo_ratings",
    "xgboost": "dixon_coles_base,recent_form,advanced_stats,elo_ratings,context,h2h",
}
