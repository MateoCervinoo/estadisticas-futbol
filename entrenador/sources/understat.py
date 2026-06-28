from __future__ import annotations
import logging
from typing import Dict, List, Optional, Set
from datetime import datetime

import pandas as pd

from ..config import settings
from ..utils.dedupe import generate_match_hash

logger = logging.getLogger(__name__)

LEAGUE_MAP = {
    "EPL": "Premier League",
    "La_liga": "La Liga",
    "Serie_A": "Serie A",
    "Bundesliga": "Bundesliga",
    "Ligue_1": "Ligue 1",
    "UCL": "Champions League",
    "EURO": "European Championship",
}


class UnderstatClient:
    def __init__(self):
        self._available = False
        self._check_availability()

    def _check_availability(self):
        try:
            import soccerdata
            self._available = True
        except ImportError:
            logger.warning("soccerdata no instalado — Understat no disponible")

    def get_available_hashes(self, league: str, season: str) -> Set[str]:
        if not self._available:
            return set()
        try:
            from soccerdata.understat import Understat

            league_key = self._resolve_league(league)
            if league_key is None:
                return set()

            us = Understat(leagues=league_key, seasons=season)
            matches = us.read_schedule()
            if matches is None or matches.empty:
                return set()

            hashes = set()
            for _, row in matches.iterrows():
                home = row.get("home_team") or ""
                away = row.get("away_team") or ""
                date_val = row.get("date")
                if date_val is not None and home and away:
                    date_str = str(date_val.date()) if hasattr(date_val, "date") else str(date_val)[:10]
                    hashes.add(generate_match_hash(date_str, home, away, league))
            return hashes
        except Exception as e:
            logger.error("Error obteniendo hashes Understat: %s", e)
            return set()

    def _resolve_league(self, league_name: str) -> Optional[str]:
        for k, v in LEAGUE_MAP.items():
            if v.lower() == league_name.lower() or k.lower() == league_name.lower():
                return k
        return None

    def get_match_xg(self, league: str, season: str) -> List[Dict]:
        if not self._available:
            return []

        try:
            from soccerdata.understat import Understat

            league_key = self._resolve_league(league)
            if league_key is None:
                return []

            us = Understat(leagues=league_key, seasons=season)
            matches = us.read_schedule()
            if matches is None or matches.empty:
                return []

            shooting = us.read_shooting()
            results = []
            for idx, row in matches.iterrows():
                home = row.get("home_team") or ""
                away = row.get("away_team") or ""
                date_val = row.get("date")
                if date_val is None or not home or not away:
                    continue
                date_str = str(date_val.date()) if hasattr(date_val, "date") else str(date_val)[:10]
                hash_dedupe = generate_match_hash(date_str, home, away, league)

                home_xg = None
                away_xg = None
                if shooting is not None and idx in shooting.index:
                    try:
                        s = shooting.loc[idx]
                        home_xg = float(s.get(("xg", home)) or 0) if pd.notna(s.get(("xg", home))) else None
                        away_xg = float(s.get(("xg", away)) or 0) if pd.notna(s.get(("xg", away))) else None
                    except Exception:
                        pass

                results.append({
                    "hash_dedupe": hash_dedupe,
                    "fuente": "understat",
                    "xg_local": home_xg,
                    "xg_visitante": away_xg,
                })
            return results
        except Exception as e:
            logger.error("Error obteniendo xG Understat: %s", e)
            return []
