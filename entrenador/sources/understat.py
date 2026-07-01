from __future__ import annotations
import logging
import math
from typing import Dict, List, Optional, Set
from datetime import datetime, timezone

from ..config import settings

logger = logging.getLogger(__name__)


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

    def _normalize_league(self, name: Optional[str]) -> Optional[str]:
        if not name:
            return None
        mapping = {
            "ENG-Premier League": "ENG-Premier League",
            "ESP-La Liga": "ESP-La Liga",
            "ITA-Serie A": "ITA-Serie A",
            "GER-Bundesliga": "GER-Bundesliga",
            "FRA-Ligue 1": "FRA-Ligue 1",
            "EPL": "ENG-Premier League",
            "La_liga": "ESP-La Liga",
            "Serie_A": "ITA-Serie A",
            "Bundesliga": "GER-Bundesliga",
            "Ligue_1": "FRA-Ligue 1",
        }
        return mapping.get(name, name)

    def get_match_stats(self, league: str, season: str) -> List[Dict]:
        if not self._available:
            return []
        try:
            from soccerdata.understat import Understat
            from ..utils.dedupe import generate_match_hash

            league_name = self._normalize_league(league)
            if not league_name:
                return []

            understat = Understat(leagues=league_name, seasons=season)

            matches = understat.read_schedule()
            if matches is None or matches.empty:
                return []

            team_stats = understat.read_team_match_stats()
            if team_stats is None or team_stats.empty:
                return []

            stats_by_game = {}
            for _, row in team_stats.iterrows():
                gid = row.get("game_id")
                if gid is not None:
                    stats_by_game[gid] = row

            results = []
            for _, row in matches.iterrows():
                home = row.get("home_team") or ""
                away = row.get("away_team") or ""
                date_val = row.get("date")
                gid = row.get("game_id")
                if not home or not away or date_val is None:
                    continue
                date_str = str(date_val.date()) if hasattr(date_val, "date") else str(date_val)[:10]
                comp = row.get("league") or league
                hash_dedupe = generate_match_hash(date_str, home, away, comp)

                sr = stats_by_game.get(gid)
                if sr is None:
                    continue

                results.append({
                    "hash_dedupe": hash_dedupe,
                    "fuente": "understat",
                    "date": date_str,
                    "home_team": home,
                    "away_team": away,
                    "league": comp,
                    "xg_local": _safe_float(sr.get("home_xg")),
                    "xg_visitante": _safe_float(sr.get("away_xg")),
                    "goles_local": _safe_int(sr.get("home_goals")),
                    "goles_visitante": _safe_int(sr.get("away_goals")),
                    "remates_local": None,
                    "remates_visitante": None,
                    "remates_puerta_local": None,
                    "remates_puerta_visitante": None,
                    "posesion_local": None,
                    "posesion_visitante": None,
                    "corners_local": None,
                    "corners_visitante": None,
                    "faltas_local": None,
                    "faltas_visitante": None,
                    "tarjetas_amarillas_local": None,
                    "tarjetas_amarillas_visitante": None,
                    "tarjetas_rojas_local": None,
                    "tarjetas_rojas_visitante": None,
                })
            return results

        except Exception as e:
            logger.error("Error obteniendo stats Understat: %s", e)
            return []


def _safe_float(val) -> Optional[float]:
    if val is None:
        return None
    try:
        value = float(val)
        return None if math.isnan(value) else value
    except (ValueError, TypeError):
        return None


def _safe_int(val) -> Optional[int]:
    if val is None:
        return None
    try:
        if math.isnan(float(val)):
            return None
        return int(val)
    except (ValueError, TypeError):
        return None
