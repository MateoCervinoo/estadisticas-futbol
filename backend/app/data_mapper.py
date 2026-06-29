from typing import Optional

# Mapa de torneos conocidos (nombre_csv exacto -> categoría canónica)
EXACT_TOURNAMENT_MAP: dict[str, str] = {
    # Mundial
    "fifa world cup": "Mundial",
    "world cup": "Mundial",
    "confederations cup": "Confederaciones",
    "fifa confederations cup": "Confederaciones",
    # Eurocopa
    "uefa euro": "Eurocopa",
    "european championship": "Eurocopa",
    # Copa América
    "copa america": "Copa América",
    "copa américa": "Copa América",
    # Nations League
    "uefa nations league": "Nations League",
    "concacaf nations league": "Nations League",
    # Copas continentales
    "african cup of nations": "Copa Africana",
    "africa cup of nations": "Copa Africana",
    "afc asian cup": "Copa Asiática",
    "asian cup": "Copa Asiática",
    "gold cup": "Copa Oro",
    "concacaf gold cup": "Copa Oro",
    "concacaf championship": "Copa Concacaf",
    "afc challenge cup": "Copa Desafío",
    "afc solidarity cup": "Copa Solidaridad",
    "oceania nations cup": "Copa Oceanía",
    "cfu caribbean cup": "Copa del Caribe",
    "aff championship": "Copa AFF",
    "asean championship": "Copa AFF",
    "eaff championship": "Copa EAFF",
    "saff championship": "Copa SAFF",
    "waiff championship": "Copa WAFF",
    "uniffac cup": "Copa UNIFFAC",
    "unca federation cup": "Copa UNCAF",
    # Juegos
    "olympic games": "Juegos Olímpicos",
    "asian games": "Juegos Asiáticos",
    "southeast asian games": "Juegos del Sudeste Asiático",
    "south asian games": "Juegos del Sur de Asia",
    "south pacific games": "Juegos del Pacífico",
    "pacific games": "Juegos del Pacífico",
    "all-african games": "Juegos Panafricanos",
    "african games": "Juegos Panafricanos",
    "east asian games": "Juegos del Este Asiático",
    "central american and caribbean games": "Juegos Centroamericanos",
    "pan american games": "Juegos Panamericanos",
    "bolivarian games": "Juegos Bolivarianos",
    # Amistosos / Invitacionales
    "friendly": "Amistoso",
    "friendlies": "Amistoso",
    "fifa series": "Amistoso",
    "merdeka tournament": "Amistoso",
    "british home championship": "Amistoso",
    "nordic championship": "Amistoso",
    "island games": "Amistoso",
    "king's cup": "Amistoso",
    "kirin cup": "Amistoso",
    "nehru cup": "Amistoso",
    "baltic cup": "Amistoso",
    "muratti vase": "Amistoso",
    "gulf cup": "Amistoso",
    "cosafa cup": "Amistoso",
    "cecafa cup": "Amistoso",
    "caribbean cup": "Amistoso",
    "caribbean championship": "Amistoso",
    "windward islands tournament": "Amistoso",
    "indian ocean island games": "Amistoso",
    "melanesia cup": "Amistoso",
    "copaeou": "Amistoso",
    "superclásico de las américas": "Amistoso",
    "superclásico de las americas": "Amistoso",
    "intercontinental cup": "Amistoso",
    "dynasty cup": "Amistoso",
    "soccer ashes": "Amistoso",
    "inter games": "Amistoso",
    "mukuru 4 nations": "Amistoso",
    "morocco, capital of african football": "Amistoso",
    "waff championship": "Amistoso",
    "asean championship qualification": "Clasificatorias",
    # Clasificatorias específicas
    "abierto": "Clasificatorias",
    "copa america qualification": "Clasificatorias",
    "copa américa qualification": "Clasificatorias",
}


def normalize_status(raw: Optional[str], source: str = "api") -> str:
    if not raw:
        return "NS"
    r = str(raw).strip().upper()
    if r in ("FINISHED", "FT"):
        return "FT"
    if r in ("TIMED", "SCHEDULED"):
        return "NS"
    if r in ("IN_PLAY", "PAUSED"):
        return "IN_PLAY"
    return "NS"


def normalize_tournament(raw: Optional[str]) -> str:
    if not raw:
        return "Otro"
    r = str(raw).strip().lower()

    # 1. Exact match
    if r in EXACT_TOURNAMENT_MAP:
        return EXACT_TOURNAMENT_MAP[r]

    # 2. Qualification
    if "qualification" in r or "qualifying" in r or "clasific" in r or r == "abierto":
        return "Clasificatorias"

    # 3. World Cup
    if "fifa world cup" in r or r == "world cup":
        return "Mundial"

    # 4. Copa América
    if "copa america" in r or "copa américa" in r:
        return "Copa América"

    # 5. UEFA Euro
    if "uefa euro" in r or "european championship" in r:
        return "Eurocopa"

    # 6. Nations League
    if "nations league" in r:
        return "Nations League"

    # 7. Confederaciones
    if "confed" in r:
        return "Confederaciones"

    # 8. Copa Africana
    if "african cup" in r or "africa cup" in r:
        return "Copa Africana"

    # 9. Copa Asiática
    if "asian cup" in r:
        return "Copa Asiática"

    # 10. Copa Oro
    if "gold cup" in r:
        return "Copa Oro"

    # 11. Olympics
    if "olympic" in r:
        return "Juegos Olímpicos"

    # 12. Torneos con Cup/Copa/Tournament → Amistoso (si no clasificatorio ni mayor)
    if any(kw in r for kw in ["cup", "copa", "trophy", "tournament", "shield", "series"]):
        return "Amistoso"

    # 13. Fallback: preserve original name
    return raw
