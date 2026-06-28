from __future__ import annotations
import logging
from typing import Dict, List, Optional, Set
from datetime import datetime

from ..config import settings

logger = logging.getLogger(__name__)


class FBrefClient:
    def __init__(self):
        self._available = False
        self._check_availability()

    def _check_availability(self):
        try:
            import soccerdata
            self._available = True
        except ImportError:
            logger.warning("soccerdata no instalado — FBref no disponible")

    def _normalize_league(self, league: str) -> str:
        intl_leagues = {
            "World Cup": "FIFA World Cup",
            "Copa América": "Copa América",
            "European Championship": "UEFA Euro",
            "Africa Cup of Nations": "Africa Cup of Nations",
            "Asian Cup": "AFC Asian Cup",
            "Gold Cup": "CONCACAF Gold Cup",
        }
        return intl_leagues.get(league, league)

    def get_available_hashes(self, league: str, season: str) -> Set[str]:
        if not self._available:
            return set()
        try:
            from soccerdata.fbref import FBref
            from ..utils.dedupe import generate_match_hash

            league_name = self._normalize_league(league)
            fbref = FBref(leagues=league_name, seasons=season)
            matches = fbref.read_schedule()

            if matches is None or matches.empty:
                return set()

            hashes = set()
            for _, row in matches.iterrows():
                home = row.get("home_team") or ""
                away = row.get("away_team") or ""
                date_val = row.get("date")
                if date_val is not None and home and away:
                    date_str = str(date_val.date()) if hasattr(date_val, "date") else str(date_val)[:10]
                    comp = row.get("league") or league
                    hashes.add(generate_match_hash(date_str, home, away, comp))
            return hashes
        except Exception as e:
            logger.error("Error obteniendo hashes FBref: %s", e)
            return set()

    def get_match_stats(self, league: str, season: str) -> List[Dict]:
        if not self._available:
            return []

        try:
            from soccerdata.fbref import FBref
            from ..utils.dedupe import generate_match_hash

            league_name = self._normalize_league(league)
            fbref = FBref(leagues=league_name, seasons=season)

            matches = fbref.read_schedule()
            if matches is None or matches.empty:
                return []

            shooting = fbref.read_shooting()
            passing = fbref.read_passing()
            possession = fbref.read_possession()
            misc = fbref.read_misc()

            results = []
            for idx, row in matches.iterrows():
                home = row.get("home_team") or ""
                away = row.get("away_team") or ""
                date_val = row.get("date")
                if date_val is None or not home or not away:
                    continue
                date_str = str(date_val.date()) if hasattr(date_val, "date") else str(date_val)[:10]
                comp = row.get("league") or league
                hash_dedupe = generate_match_hash(date_str, home, away, comp)

                home_stats = {}
                away_stats = {}
                if shooting is not None and idx in shooting.index:
                    try:
                        s = shooting.loc[idx]
                        home_stats["xg"] = _safe_float(s.get(("xg", home), None))
                        away_stats["xg"] = _safe_float(s.get(("xg", away), None))
                        home_stats["shots"] = _safe_int(s.get(("shots_total", home), None))
                        away_stats["shots"] = _safe_int(s.get(("shots_total", away), None))
                        home_stats["shots_on_target"] = _safe_int(s.get(("shots_on_target", home), None))
                        away_stats["shots_on_target"] = _safe_int(s.get(("shots_on_target", away), None))
                    except Exception:
                        pass

                if possession is not None and idx in possession.index:
                    try:
                        p = possession.loc[idx]
                        home_stats["possession"] = _safe_float(p.get(("possession", home), None))
                        away_stats["possession"] = _safe_float(p.get(("possession", away), None))
                    except Exception:
                        pass

                if misc is not None and idx in misc.index:
                    try:
                        m = misc.loc[idx]
                        home_stats["corners"] = _safe_int(m.get(("corner_kicks", home), None))
                        away_stats["corners"] = _safe_int(m.get(("corner_kicks", away), None))
                        home_stats["fouls"] = _safe_int(m.get(("fouls", home), None))
                        away_stats["fouls"] = _safe_int(m.get(("fouls", away), None))
                        home_stats["yellow"] = _safe_int(m.get(("yellow_cards", home), None))
                        away_stats["yellow"] = _safe_int(m.get(("yellow_cards", away), None))
                        home_stats["red"] = _safe_int(m.get(("red_cards", home), None))
                        away_stats["red"] = _safe_int(m.get(("red_cards", away), None))
                    except Exception:
                        pass

                results.append({
                    "hash_dedupe": hash_dedupe,
                    "fuente": "fbref",
                    "xg_local": home_stats.get("xg"),
                    "xg_visitante": away_stats.get("xg"),
                    "remates_local": home_stats.get("shots"),
                    "remates_visitante": away_stats.get("shots"),
                    "remates_puerta_local": home_stats.get("shots_on_target"),
                    "remates_puerta_visitante": away_stats.get("shots_on_target"),
                    "posesion_local": home_stats.get("possession"),
                    "posesion_visitante": away_stats.get("possession"),
                    "corners_local": home_stats.get("corners"),
                    "corners_visitante": away_stats.get("corners"),
                    "faltas_local": home_stats.get("fouls"),
                    "faltas_visitante": away_stats.get("fouls"),
                    "tarjetas_amarillas_local": home_stats.get("yellow"),
                    "tarjetas_amarillas_visitante": away_stats.get("yellow"),
                    "tarjetas_rojas_local": home_stats.get("red"),
                    "tarjetas_rojas_visitante": away_stats.get("red"),
                })
            return results

        except Exception as e:
            logger.error("Error obteniendo stats FBref: %s", e)
            return []


def _safe_float(val) -> Optional[float]:
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _safe_int(val) -> Optional[int]:
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None
