from __future__ import annotations
import logging
import time
from datetime import datetime, date
from typing import Dict, List, Optional, Any

import requests

from ..config import settings

logger = logging.getLogger(__name__)

START_SEASON = settings.FOOTBALL_DATA_START_SEASON
END_SEASON = settings.FOOTBALL_DATA_END_SEASON


class FootballDataClient:
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or settings.FOOTBALL_DATA_KEY
        self.base_url = base_url or settings.FOOTBALL_DATA_BASE
        self.mock = not bool(self.api_key)

        if self.mock:
            logger.warning("FOOTBALL_DATA_KEY no configurada — modo MOCK")

    def _safe_get(self, url: str, params: Optional[Dict] = None) -> Optional[Dict]:
        if self.mock:
            return None
        headers = {"X-Auth-Token": self.api_key}
        for attempt in range(2):
            try:
                resp = requests.get(url, headers=headers, params=params, timeout=15)
                if resp.status_code == 429:
                    logger.warning("429 Too Many Requests — esperando 6s")
                    time.sleep(6)
                    continue
                if resp.status_code == 400:
                    logger.warning("400 Bad Request — url: %s params: %s body: %s",
                                   resp.url, params, resp.text[:200])
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                if attempt == 1:
                    logger.error("Error consultando %s: %s", url, e)
                    return None
                logger.warning("Reintentando %s (error: %s)", url, e)
                time.sleep(1)
        return None

    def get_competition_matches(self, competition_code: str, season: int = None) -> List[Dict]:
        url = f"{self.base_url}/competitions/{competition_code}/matches"
        params = {}
        if season is not None:
            params["season"] = season
        data = self._safe_get(url, params)

        if not data or "matches" not in data:
            return self._mock_matches(competition_code, season)

        results = []
        for m in data["matches"]:
            full_time = (m.get("score") or {}).get("fullTime") or {}
            half_time = (m.get("score") or {}).get("halfTime") or {}
            results.append({
                "fixture_id": m.get("id"),
                "date": m.get("utcDate"),
                "home_team": (m.get("homeTeam") or {}).get("name"),
                "away_team": (m.get("awayTeam") or {}).get("name"),
                "goals_home": full_time.get("home"),
                "goals_away": full_time.get("away"),
                "ht_goals_home": half_time.get("home"),
                "ht_goals_away": half_time.get("away"),
                "stage": m.get("stage"),
                "group": m.get("group"),
                "status": m.get("status"),
                "home_crest": (m.get("homeTeam") or {}).get("crest"),
                "away_crest": (m.get("awayTeam") or {}).get("crest"),
                "venue": (m.get("venue") or {}).get("name") if isinstance(m.get("venue"), dict) else m.get("venue"),
                "competition": competition_code,
            })
        return results

    def get_competition_matches_multi_season(self, competition_code: str,
                                               start_season: int = None,
                                               end_season: int = None) -> List[Dict]:
        if start_season is None:
            start_season = START_SEASON
        if end_season is None:
            end_season = END_SEASON

        all_matches = []
        for s in range(start_season, end_season + 1):
            logger.info("  → Temporada %d/%d", s, s + 1)
            matches = self.get_competition_matches(competition_code, s)
            all_matches.extend(matches)
            time.sleep(0.35)
        return all_matches

    def _mock_matches(self, competition_code: str, season: int = None) -> List[Dict]:
        suffix = f"{competition_code}_{season or 'current'}"
        return [
            {"fixture_id": f"{suffix}_1", "date": "2026-06-12T18:00:00Z", "home_team": "Argentina",
             "away_team": "Iceland", "goals_home": None, "goals_away": None,
             "status": "SCHEDULED", "competition": competition_code},
            {"fixture_id": f"{suffix}_2", "date": "2026-06-13T21:00:00Z", "home_team": "Brazil",
             "away_team": "France", "goals_home": 2, "goals_away": 1,
             "status": "FINISHED", "competition": competition_code},
        ]
