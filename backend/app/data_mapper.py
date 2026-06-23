"""Funciones utilitarias para normalizar estados y nombres de competiciones.

Estas funciones ayudan a estandarizar la información procedente tanto del CSV
como de las APIs externas antes de hacer el UPSERT en la base de datos.
"""
from typing import Optional


def normalize_status(raw: Optional[str], source: str = "api") -> str:
    """Normaliza el estado del partido a los valores usados por el frontend.

    Reglas principales:
    - 'FINISHED' o valores que indiquen que se jugó -> 'FT'
    - 'TIMED' o 'SCHEDULED' -> 'NS'
    - 'IN_PLAY'/'PAUSED' -> 'IN_PLAY'
    - En caso de duda, devolver 'NS' por defecto.
    """
    if not raw:
        return "NS"
    r = str(raw).strip().upper()
    if r in ("FINISHED", "FT"):
        return "FT"
    if r in ("TIMED", "SCHEDULED"):
        return "NS"
    if r in ("IN_PLAY", "PAUSED"):
        return "IN_PLAY"
    # Si viene de CSV y detectamos goles numéricos en las columnas, el llamador
    # puede forzar 'FT' sin usar esta función.
    # Por defecto, devolver 'NS' para evitar marcar partidos como finalizados erróneamente.
    return "NS"


def normalize_tournament(raw: Optional[str]) -> str:
    """Mapea nombres de torneos a las categorías exactas del frontend.

    Ejemplos:
    - 'FIFA World Cup' o 'World Cup' -> 'Mundial'
    - 'Copa América' -> 'Copa América'
    - 'FIFA World Cup qualification' o 'Abierto' -> 'Clasificatorias'
    - Si no se reconoce, devuelve el original o 'Otro' si está vacío.
    """
    if not raw:
        return "Otro"
    r = str(raw).strip().lower()
    if "world cup" in r or "fifa world cup" in r or r == "mundial":
        return "Mundial"
    if "copa america" in r:
        return "Copa América"
    if "qualification" in r or "clasific" in r or r == "abierto":
        return "Clasificatorias"
    # Passthrough conocido
    return raw
