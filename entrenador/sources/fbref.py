from __future__ import annotations
import logging
import math
import signal
from typing import Dict, List, Optional, Set

from ..config import settings

logger = logging.getLogger(__name__)


class TimeoutError(Exception):
    pass


def _timeout_handler(signum, frame):
    raise TimeoutError("FBref operation timed out")


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

    def _with_timeout(self, func, timeout=45):
        if not hasattr(signal, "SIGALRM"):
            return func()
        old = signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(timeout)
        try:
            result = func()
            signal.alarm(0)
            return result
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old)

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

        def _fetch():
            from soccerdata.fbref import FBref
            from ..utils.dedupe import generate_match_hash

            league_name = self._normalize_league(league)
            fbref = FBref(leagues=league_name, seasons=season)

            matches = fbref.read_schedule()
            if matches is None or matches.empty:
                return []

            teams_df = fbref.read_team_season_stats()
            if teams_df is None or teams_df.empty:
                return []

            team_names = list(teams_df.index.get_level_values("team").unique())

            team_lookup = {}
            for team in team_names:
                for st in ("shooting", "misc"):
                    try:
                        df = fbref.read_team_match_stats(stat_type=st, team=team)
                        if df is not None and not df.empty:
                            team_lookup.setdefault(team, {})[st] = df
                    except Exception as e:
                        logger.debug("FBref %s %s %s: %s", league, st, team, e)

            if not team_lookup:
                return []

            def _get_value(row, *keys):
                for key in keys:
                    try:
                        value = row.get(key)
                    except Exception:
                        value = None
                    if value is not None:
                        return value
                return None

            def _find_row(df, opponent, venue, date_str):
                if df is None:
                    return None
                for _, r in df.iterrows():
                    row_date = _get_value(r, ("date", ""), "date")
                    row_date_str = str(row_date.date()) if hasattr(row_date, "date") else str(row_date)[:10]
                    if row_date_str != date_str:
                        continue
                    row_opponent = _get_value(r, ("opponent", ""), "opponent")
                    row_venue = _get_value(r, ("venue", ""), "venue")
                    if row_opponent == opponent and row_venue == venue:
                        return r
                return None

            results = []
            for _, row in matches.iterrows():
                home = row.get("home_team") or ""
                away = row.get("away_team") or ""
                date_val = row.get("date")
                if not home or not away or date_val is None:
                    continue
                date_str = str(date_val.date()) if hasattr(date_val, "date") else str(date_val)[:10]
                comp = row.get("league") or league
                hash_dedupe = generate_match_hash(date_str, home, away, comp)

                home_stats = {}
                away_stats = {}

                hd = team_lookup.get(home, {})
                ad = team_lookup.get(away, {})

                h_row = _find_row(hd.get("shooting"), away, "Home", date_str)
                a_row = _find_row(ad.get("shooting"), home, "Away", date_str)
                if h_row is not None:
                    home_stats["xg"] = _safe_float(_get_value(h_row, ("Standard", "xG"), ("Expected", "xG"), "xG"))
                    home_stats["shots"] = _safe_int(_get_value(h_row, ("Standard", "Sh"), "Sh"))
                    home_stats["shots_on_target"] = _safe_int(_get_value(h_row, ("Standard", "SoT"), "SoT"))
                if a_row is not None:
                    away_stats["xg"] = _safe_float(_get_value(a_row, ("Standard", "xG"), ("Expected", "xG"), "xG"))
                    away_stats["shots"] = _safe_int(_get_value(a_row, ("Standard", "Sh"), "Sh"))
                    away_stats["shots_on_target"] = _safe_int(_get_value(a_row, ("Standard", "SoT"), "SoT"))

                h_misc = _find_row(hd.get("misc"), away, "Home", date_str)
                a_misc = _find_row(ad.get("misc"), home, "Away", date_str)
                if h_misc is not None:
                    home_stats["corners"] = _safe_int(_get_value(h_misc, ("Misc", "Crs"), "Crs"))
                    home_stats["fouls"] = _safe_int(_get_value(h_misc, ("Misc", "Fls"), "Fls"))
                    home_stats["yellow"] = _safe_int(_get_value(h_misc, ("Misc", "CrdY"), "CrdY"))
                    home_stats["red"] = _safe_int(_get_value(h_misc, ("Misc", "CrdR"), "CrdR"))
                if a_misc is not None:
                    away_stats["corners"] = _safe_int(_get_value(a_misc, ("Misc", "Crs"), "Crs"))
                    away_stats["fouls"] = _safe_int(_get_value(a_misc, ("Misc", "Fls"), "Fls"))
                    away_stats["yellow"] = _safe_int(_get_value(a_misc, ("Misc", "CrdY"), "CrdY"))
                    away_stats["red"] = _safe_int(_get_value(a_misc, ("Misc", "CrdR"), "CrdR"))

                results.append({
                    "hash_dedupe": hash_dedupe,
                    "fuente": "fbref",
                    "date": date_str,
                    "home_team": home,
                    "away_team": away,
                    "league": comp,
                    "xg_local": home_stats.get("xg"),
                    "xg_visitante": away_stats.get("xg"),
                    "remates_local": home_stats.get("shots"),
                    "remates_visitante": away_stats.get("shots"),
                    "remates_puerta_local": home_stats.get("shots_on_target"),
                    "remates_puerta_visitante": away_stats.get("shots_on_target"),
                    "posesion_local": None,
                    "posesion_visitante": None,
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

        try:
            return self._with_timeout(_fetch, timeout=180)
        except TimeoutError:
            logger.warning("FBref timeout para %s %s", league, season)
            return []
        except Exception as e:
            logger.error("Error obteniendo stats FBref: %s", e)
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
