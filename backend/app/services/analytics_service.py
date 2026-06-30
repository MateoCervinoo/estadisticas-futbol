def team_display_name(equipo, fallback: str) -> str:
    if not equipo:
        return fallback
    return equipo.nombre_canonico or equipo.nombre_es or equipo.nombre_csv or fallback
