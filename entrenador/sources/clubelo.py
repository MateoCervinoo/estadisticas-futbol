from __future__ import annotations
import logging
from typing import Dict, List, Optional
from datetime import datetime, date

import pandas as pd
import requests

from ..utils.team_mapper import TeamMapper
from ..utils.dedupe import normalize_team

logger = logging.getLogger(__name__)

CLUBELO_URL = "http://api.clubelo.com/"


class ClubEloClient:
    def __init__(self):
        pass

    def get_elo_for_date(self, target_date: date = None) -> List[Dict]:
        if target_date is None:
            target_date = date.today()
        date_str = target_date.strftime("%Y-%m-%d")
        url = f"{CLUBELO_URL}{date_str}"
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.text
        except Exception as e:
            logger.error("Error obteniendo Elo de ClubElo: %s", e)
            return []

        results = []
        for line in data.strip().split("\n")[1:]:
            parts = line.split(",")
            if len(parts) < 5:
                continue
            try:
                results.append({
                    "team": parts[0].strip().strip('"'),
                    "elo": int(float(parts[1])),
                    "rank": int(parts[2]) if parts[2] else None,
                    "country": parts[3].strip().strip('"') if len(parts) > 3 else None,
                    "level": parts[4].strip().strip('"') if len(parts) > 4 else None,
                    "date": date_str,
                })
            except (ValueError, IndexError):
                continue
        return results

    def get_elo_for_team(self, team_name: str, since_date: str = "2018-01-01") -> List[Dict]:
        url = f"{CLUBELO_URL}{team_name}"
        params = {"from": since_date}
        try:
            resp = requests.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.text
        except Exception as e:
            logger.error("Error obteniendo Elo histórico para %s: %s", team_name, e)
            return []

        results = []
        for line in data.strip().split("\n")[1:]:
            parts = line.split(",")
            if len(parts) < 3:
                continue
            try:
                results.append({
                    "team": team_name,
                    "date": parts[0].strip(),
                    "elo": int(float(parts[1])),
                    "rank": int(parts[2]) if len(parts) > 2 and parts[2] else None,
                })
            except (ValueError, IndexError):
                continue
        return results

    def get_elo_at_date(self, team_name: str, target_date: str) -> Optional[int]:
        elo_history = self.get_elo_for_team(team_name, since_date=target_date)
        for entry in sorted(elo_history, key=lambda x: x["date"], reverse=True):
            if entry["date"] <= target_date:
                return entry["elo"]
        return None
