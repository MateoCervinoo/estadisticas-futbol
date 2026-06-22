"""Cliente HTTP para API-Football (RapidAPI) con modo mock.

La clase APIFootballClient busca la API key en la variable de entorno
API_FOOTBALL_KEY. Si no está presente, opera en modo mock devolviendo
estructuras de ejemplo para permitir pruebas locales sin llave.

Métodos principales:
- get_world_cup_fixtures(): lista de fixtures (league=1, season=2026)
- get_match_metrics(fixture_id): métricas de remates para un fixture

Este módulo está diseñado para ser robusto a fallos de red y evitar que
errores externos provoquen un 500 en el backend.
"""
from typing import List, Dict, Any, Optional
import os
import logging

import requests

logger = logging.getLogger(__name__)


class APIFootballClient:
    def __init__(self, api_key: Optional[str] = None, timeout: int = 10):
        self.api_key = api_key or os.getenv("API_FOOTBALL_KEY")
        self.timeout = timeout
        self.base_url = "https://api-football-v1.p.rapidapi.com/v3"
        # RapidAPI host header commonly used for this API
        self.host_header = "api-football-v1.p.rapidapi.com"

        if not self.api_key:
            logger.warning("API_FOOTBALL_KEY not set — APIFootballClient running in MOCK mode")
            self.mock = True
        else:
            self.mock = False
            self.headers = {
                "x-rapidapi-key": self.api_key,
                "x-rapidapi-host": self.host_header,
            }

    def _safe_get(self, url: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        try:
            resp = requests.get(url, headers=getattr(self, 'headers', None), params=params, timeout=self.timeout)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            logger.error("Request to %s failed: %s", url, e)
            return None

    def get_world_cup_fixtures(self) -> List[Dict[str, Any]]:
        """Devuelve una lista de fixtures del Mundial 2026.

        Cada dict contiene: fixture_id, date, home_team, away_team, goals_home, goals_away, status
        """
        if self.mock:
            # Datos de ejemplo (2 partidos) – útiles para desarrollo sin clave
            return [
                {
                    "fixture_id": 101,
                    "date": "2026-06-12T18:00:00Z",
                    "home_team": "Argentina",
                    "away_team": "Iceland",
                    "goals_home": None,
                    "goals_away": None,
                    "status": "NS",
                },
                {
                    "fixture_id": 102,
                    "date": "2026-06-13T21:00:00Z",
                    "home_team": "Brazil",
                    "away_team": "France",
                    "goals_home": 2,
                    "goals_away": 1,
                    "status": "FT",
                },
            ]

        url = f"{self.base_url}/fixtures"
        params = {"league": 1, "season": 2026}
        data = self._safe_get(url, params=params)
        if not data or 'response' not in data:
            logger.error("Empty or invalid response from fixtures endpoint")
            return []

        fixtures = []
        for item in data.get('response', []):
            f = item.get('fixture', {})
            teams = item.get('teams', {})
            goals = item.get('goals', {})

            fixture_id = f.get('id')
            date = f.get('date')
            status = f.get('status', {}).get('short') if isinstance(f.get('status'), dict) else f.get('status')

            home_team = teams.get('home', {}).get('name') if teams.get('home') else None
            away_team = teams.get('away', {}).get('name') if teams.get('away') else None

            goals_home = goals.get('home')
            goals_away = goals.get('away')

            fixtures.append(
                {
                    'fixture_id': fixture_id,
                    'date': date,
                    'home_team': home_team,
                    'away_team': away_team,
                    'goals_home': goals_home,
                    'goals_away': goals_away,
                    'status': status,
                }
            )

        return fixtures

    def get_match_metrics(self, fixture_id: int) -> Dict[str, Any]:
        """Devuelve métricas de remates para el fixture indicado.

        Retorna un dict con claves:
        - shots_on_goal: {'home': int, 'away': int}
        - shots_inside_box: {'home': int, 'away': int}
        - shots_outside_box: {'home': int, 'away': int}
        Si no hay datos devuelve valores None.
        """
        if self.mock:
            # Datos simulados: mapeados por fixture_id para reproducibilidad
            mock_stats = {
                101: {
                    'shots_on_goal': {'home': 5, 'away': 2},
                    'shots_inside_box': {'home': 8, 'away': 3},
                    'shots_outside_box': {'home': 4, 'away': 2},
                },
                102: {
                    'shots_on_goal': {'home': 7, 'away': 6},
                    'shots_inside_box': {'home': 12, 'away': 9},
                    'shots_outside_box': {'home': 5, 'away': 4},
                },
            }
            return mock_stats.get(fixture_id, {
                'shots_on_goal': {'home': None, 'away': None},
                'shots_inside_box': {'home': None, 'away': None},
                'shots_outside_box': {'home': None, 'away': None},
            })

        url = f"{self.base_url}/fixtures/statistics"
        params = {"fixture": fixture_id}
        data = self._safe_get(url, params=params)
        if not data or 'response' not in data:
            logger.error("Empty or invalid response from fixtures/statistics endpoint for fixture %s", fixture_id)
            return {
                'shots_on_goal': {'home': None, 'away': None},
                'shots_inside_box': {'home': None, 'away': None},
                'shots_outside_box': {'home': None, 'away': None},
            }

        # The response is generally a list, one item per team with statistics list
        # We'll extract the three metrics by name (case-insensitive substring matching)
        def _find_stat(stats_list, keys):
            for entry in stats_list:
                t = entry.get('type', '')
                v = entry.get('value')
                if not isinstance(t, str):
                    continue
                lower = t.lower()
                for k in keys:
                    if k in lower:
                        return v
            return None

        # initialize
        result = {
            'shots_on_goal': {'home': None, 'away': None},
            'shots_inside_box': {'home': None, 'away': None},
            'shots_outside_box': {'home': None, 'away': None},
        }

        for team_stat in data.get('response', []):
            team = team_stat.get('team', {})
            side = 'home' if team.get('id') and team.get('name') else None
            # API usually doesn't mark home/away here, statistical entries are paired in order —
            # we will use the 'team' object name to determine which side by matching with fixture info
            stats_list = team_stat.get('statistics', [])

            # Extract metrics by checking possible key substrings
            sog = _find_stat(stats_list, ['shots on goal', 'shots on target', 'shots on'])
            inside = _find_stat(stats_list, ['insidebox', 'inside box', 'shots inside', 'shots insidebox'])
            outside = _find_stat(stats_list, ['outsidebox', 'outside box', 'shots outside', 'shots outsidebox'])

            # Determine whether this is home or away by comparing team name to fixture data
            # We need fixture info to disambiguate — fetch it if available
            # As a fallback, assign sequentially: first entry => home, second => away
            # Implement fallback mapping
            if 'fixture_teams_cache' not in locals():
                fixture_teams_cache = None

            # Use ordering fallback: first processed -> home, second -> away
            if result['shots_on_goal']['home'] is None and result['shots_on_goal']['away'] is None:
                # assume first team is home
                dest = 'home'
            elif result['shots_on_goal']['away'] is None:
                dest = 'away'
            else:
                dest = 'away'

            result['shots_on_goal'][dest] = sog
            result['shots_inside_box'][dest] = inside
            result['shots_outside_box'][dest] = outside

        return result
