from __future__ import annotations
import hashlib
import unicodedata
from datetime import datetime

ALIASES = {
    "usa": "united states",
    "korea republic": "south korea",
    "czech republic": "czechia",
    "côte d'ivoire": "ivory coast",
    "swaziland": "eswatini",
    "macedonia": "north macedonia",
    "east timor": "timor-leste",
    "cape verde islands": "cape verde",
    "bosnia-herzegovina": "bosnia and herzegovina",
    "st kitts and nevis": "saint kitts and nevis",
    "st lucia": "saint lucia",
    "st vincent and the grenadines": "saint vincent and the grenadines",
    "guinea bissau": "guinea-bissau",
    "congo dr": "congo dr",
    "china pr": "china",
    "south korea": "south korea",
    "northern ireland": "northern ireland",
}


def normalize_team(name: str) -> str:
    s = str(name).lower().strip()
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    s = s.replace("-", " ").replace("_", " ").replace(".", "").replace("'", " ")
    s = " ".join(s.split())
    return ALIASES.get(s, s)


def normalize_tournament(name: str) -> str:
    s = str(name).lower().strip()
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    s = " ".join(s.split())
    replacements = {
        "fifa world cup": "world cup",
        "world cup qualification": "world cup qualifiers",
        "fifa world cup qualification": "world cup qualifiers",
        "fifa friendly": "friendly",
    }
    return replacements.get(s, s)


def generate_match_hash(date: str, home: str, away: str, tournament: str = "") -> str:
    key = f"{date}|{normalize_team(home)}|{normalize_team(away)}|{normalize_tournament(tournament)}"
    return hashlib.md5(key.encode("utf-8")).hexdigest()


def generate_fixture_id(date: str, home: str, away: str) -> int:
    key = f"{date}|{normalize_team(home)}|{normalize_team(away)}"
    md = hashlib.md5(key.encode("utf-8")).hexdigest()
    return int(md, 16) % (2 ** 31 - 1)
