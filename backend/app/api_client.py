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
import time

import requests

logger = logging.getLogger(__name__)

# URL base de football-data.org (v4)
URL_BASE = "https://api.football-data.org/v4"


class APIFootballClient:
    def __init__(self, api_key: Optional[str] = None, timeout: int = 10):
        # Prefer explicit argument, otherwise read from environment
        self.api_key = api_key or os.getenv("API_FOOTBALL_KEY")
        self.timeout = timeout
        # Use the official API-Sports base URL
        self.base_url = URL_BASE

        # Allow overriding which league ids to fetch via env var (comma-separated ids)
        leagues_env = os.getenv("API_FOOTBALL_LEAGUES")
        if leagues_env:
            try:
                self.league_ids = [int(x.strip()) for x in leagues_env.split(",") if x.strip()]
            except Exception:
                logger.warning("API_FOOTBALL_LEAGUES contains non-integer values; ignoring")
                self.league_ids = [1]
        else:
            # Default to league id 1 (commonly World Cup in many sample datasets).
            # The user may override this via the API_FOOTBALL_LEAGUES env var.
            self.league_ids = [1]

        if not self.api_key:
            logger.warning("API_FOOTBALL_KEY not set — APIFootballClient running in MOCK mode")
            self.mock = True
        else:
            self.mock = False

    def _safe_get(self, url: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        # Implementar reintentos defensivos y manejo específico para 429
        api_key = self.api_key or os.getenv("API_FOOTBALL_KEY")
        headers = {"X-Auth-Token": api_key} if api_key else {}

        max_retries = 2
        attempt = 0
        while attempt < max_retries:
            attempt += 1
            try:
                if not api_key:
                    logger.warning("_safe_get called without API_FOOTBALL_KEY set; request will likely fail")

                resp = requests.get(url, headers=headers, params=params, timeout=self.timeout)

                # Debug logs: URL consultada
                try:
                    logger.info("URL consultada: %s", resp.url)
                except Exception:
                    logger.info("URL consultada no disponible en la respuesta")

                # Manejo específico para 429 Too Many Requests
                if resp.status_code == 429:
                    logger.warning("Recibido 429 Too Many Requests para %s (attempt %s/%s). Esperando y reintentando...", url, attempt, max_retries)
                    time.sleep(6)
                    continue

                # Intentamos parsear JSON para extraer keys útiles
                data = None
                try:
                    data = resp.json()
                except ValueError:
                    logger.warning("Respuesta no es JSON válido (response.text es mostrado en DEBUG)")
                    logger.debug("Response text: %s", resp.text)

                if isinstance(data, dict):
                    logger.warning("Errores de la API: %s", data.get('errors'))
                    logger.info("Resultados según la API: %s", data.get('results'))

                # Silenciar 4xx (no hay datos disponibles, no es error del sistema)
                # No reintentar 4xx porque no hay datos que recuperar
                if 400 <= resp.status_code < 500 and resp.status_code != 429:
                    logger.debug("API responded with %s for %s - no retry for 4xx", resp.status_code, url)
                    return None

                resp.raise_for_status()

                return data
            except requests.exceptions.RequestException as e:
                # Loguear con nivel info (no error) para 4xx
                resp_status = getattr(e.response, 'status_code', 0) if hasattr(e, 'response') else 0
                if 400 <= resp_status < 500 and resp_status != 429:
                    logger.debug("Skipping %s (status %s)", url, resp_status)
                else:
                    logger.error("Request to %s failed on attempt %s/%s: %s", url, attempt, max_retries, e)
                if attempt < max_retries:
                    logger.info("Esperando 6s antes de reintentar... (backoff)")
                    time.sleep(6)
                    continue
                return None

    def get_world_cup_fixtures(self) -> List[Dict[str, Any]]:
        """Devuelve una lista de fixtures para los leagues configurados.

        Cada dict contiene: fixture_id, date, home_team, away_team, goals_home, goals_away, status, league
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
                    'league': 1,
                },
                {
                    "fixture_id": 102,
                    "date": "2026-06-13T21:00:00Z",
                    "home_team": "Brazil",
                    "away_team": "France",
                    "goals_home": 2,
                    "goals_away": 1,
                    "status": "FT",
                    'league': 1,
                },
            ]

        # Endpoint fijo para obtener todos los matches del Mundial
        url = f"{self.base_url}/competitions/WC/matches"
        # No enviamos parámetros de fecha para evitar errores 400 y simplificar el flujo
        data = self._safe_get(url, params={})

        fixtures = []
        if not data or 'matches' not in data:
            logger.warning("Empty/invalid response from football-data matches endpoint")
            return fixtures

        all_matches = data.get('matches', [])
        self._last_matches = all_matches

        for match in all_matches:
            # football-data match structure
            fixture_id = match.get('id')
            date = match.get('utcDate')
            status_api = match.get('status')  # e.g. 'FINISHED', 'SCHEDULED', 'IN_PLAY', 'TIMED'

            home_team = None
            away_team = None
            try:
                home_team = match.get('homeTeam', {}).get('name')
                away_team = match.get('awayTeam', {}).get('name')
            except Exception:
                logger.exception("Error parsing teams from match: %s", match)

            # Goals usually under score.fullTime
            full_time = match.get('score', {}).get('fullTime', {}) or {}
            goals_home = full_time.get('home')
            goals_away = full_time.get('away')

            half_time = match.get('score', {}).get('halfTime', {}) or {}

            # Extraer nombre del torneo desde la respuesta (FIFA World Cup, UEFA Euro, etc.)
            competition_name = None
            try:
                competition_name = match.get('competition', {}).get('name')
            except Exception:
                pass

            fixtures.append({
                'fixture_id': fixture_id,
                'date': date,
                'home_team': home_team,
                'away_team': away_team,
                'goals_home': goals_home,
                'goals_away': goals_away,
                'ht_goals_home': half_time.get('home'),
                'ht_goals_away': half_time.get('away'),
                'stage': match.get('stage'),
                'group': match.get('group'),
                'matchday': match.get('matchday'),
                'home_crest_url': match.get('homeTeam', {}).get('crest'),
                'away_crest_url': match.get('awayTeam', {}).get('crest'),
                'tournament': competition_name,
                'status': status_api,
            })

        return fixtures

    def get_competition_fixtures(self, code: str, season: Optional[int] = None) -> List[Dict[str, Any]]:
        """Obtiene fixtures para una competición específica de football-data.org.

        code: código de competición (PL, PD, SA, BL1, FL1, CL, WC, etc.)
        season: año de temporada (ej. 2025 para 2025/2026). Opcional.
        """
        if self.mock:
            return []

        url = f"{self.base_url}/competitions/{code}/matches"
        params = {}
        if season is not None:
            params["season"] = str(season)
        data = self._safe_get(url, params=params)

        fixtures = []
        if not data or 'matches' not in data:
            logger.warning("Empty/invalid response from football-data for %s season=%s", code, season)
            return fixtures

        for match in data.get('matches', []):
            fixture_id = match.get('id')
            date = match.get('utcDate')
            status_api = match.get('status')
            home_team = None
            away_team = None
            try:
                home_team = match.get('homeTeam', {}).get('name')
                away_team = match.get('awayTeam', {}).get('name')
            except Exception:
                pass

            full_time = match.get('score', {}).get('fullTime', {}) or {}
            goals_home = full_time.get('home')
            goals_away = full_time.get('away')
            half_time = match.get('score', {}).get('halfTime', {}) or {}

            competition_name = None
            try:
                competition_name = match.get('competition', {}).get('name')
            except Exception:
                pass

            fixtures.append({
                'fixture_id': fixture_id,
                'date': date,
                'home_team': home_team,
                'away_team': away_team,
                'goals_home': goals_home,
                'goals_away': goals_away,
                'ht_goals_home': half_time.get('home'),
                'ht_goals_away': half_time.get('away'),
                'stage': match.get('stage'),
                'group': match.get('group'),
                'matchday': match.get('matchday'),
                'home_crest_url': match.get('homeTeam', {}).get('crest'),
                'away_crest_url': match.get('awayTeam', {}).get('crest'),
                'tournament': competition_name,
                'status': status_api,
                'competition_code': code,
            })

        return fixtures

    def get_match_metrics(self, fixture_id: int) -> Dict[str, Any]:
        """Devuelve métricas de remates para el fixture indicado.

        Retorna un dict con claves:
        - shots_on_goal: {'home': int, 'away': int}
        - shots_inside_box: {'home': int, 'away': int}
        - shots_outside_box: {'home': int, 'away': int}
        Si no hay datos devuelve valores None.
        """
        # Prefer buscar en el último payload completo (evitar consultas individuales por ID)
        if hasattr(self, '_last_matches') and self._last_matches:
            for m in self._last_matches:
                if m.get('id') == fixture_id:
                    # Intentar extraer estadísticas si están presentes
                    stats = m.get('statistics') or m.get('stats') or {}
                    # Normalizar forma esperada: dict con 'shots_inside_box'/'shots_outside_box'
                    # En la mayoría de respuestas públicas no están disponibles, así que retornamos vacíos
                    if stats:
                        # Intentar mapear a la estructura que _compute_xg_from_metrics espera
                        # Este bloque es defensivo; la estructura exacta de la API puede variar.
                        shots_inside = {'home': None, 'away': None}
                        shots_outside = {'home': None, 'away': None}
                        # No hay forma estándar garantizada, así que devolvemos empty_metrics si no hay datos claros
                        # Caerá más abajo a empty_metrics
                        pass
                    break

        # If no cached detailed stats available, do NOT make an individual HTTP request per fixture
        # to avoid hitting rate limits. Return empty metrics instead.
        empty_metrics = {
            'shots_on_goal': {'home': None, 'away': None},
            'shots_inside_box': {'home': None, 'away': None},
            'shots_outside_box': {'home': None, 'away': None},
        }

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

        logger.debug("Sin métricas cacheadas para fixture %s; se omite request individual para evitar rate limits", fixture_id)
        return empty_metrics

    def fetch_match_statistics(self, fixture_id: int) -> Optional[Dict[str, Any]]:
        """Obtiene estadísticas detalladas de un partido desde football-data.org.

        endpoint: GET /v4/matches/{fixture_id}
        Retorna un dict con la estructura de PartidoEstadisticas, o None si no disponible.
        Solo hace la llamada si hay API key configurada (no mock).
        """
        if self.mock or not self.api_key:
            return None

        url = f"{self.base_url}/matches/{fixture_id}"
        try:
            data = self._safe_get(url)
        except Exception:
            return None
        if not data:
            return None

        match = data.get('match', data)
        stats_raw = match.get('statistics') or []
        if not stats_raw:
            return None

        def _safe_int(val) -> Optional[int]:
            try:
                return int(val)
            except (TypeError, ValueError):
                return None

        def _safe_float(val) -> Optional[float]:
            try:
                return float(val)
            except (TypeError, ValueError):
                return None

        stat_map: Dict[str, Dict[str, Any]] = {}
        for item in stats_raw:
            stype = (item.get('type') or '').strip().lower()
            stat_map[stype] = {
                'home': _safe_int(item.get('home')),
                'away': _safe_int(item.get('away')),
            }

        result: Dict[str, Any] = {}

        type_map = {
            'shots on goal': ('remates_puerta_local', 'remates_puerta_visitante'),
            'shots off goal': ('remates_fuera_local', 'remates_fuera_visitante'),
            'total shots': ('remates_local', 'remates_visitante'),
            'blocked shots': ('remates_bloqueados_local', 'remates_bloqueados_visitante'),
            'possession': ('posesion_local', 'posesion_visitante'),
            'corner kicks': ('corners_local', 'corners_visitante'),
            'fouls': ('faltas_local', 'faltas_visitante'),
            'yellow cards': ('tarjetas_amarillas_local', 'tarjetas_amarillas_visitante'),
            'red cards': ('tarjetas_rojas_local', 'tarjetas_rojas_visitante'),
            'offsides': ('fueras_juego_local', 'fueras_juego_visitante'),
            'saves': ('paradas_local', 'paradas_visitante'),
        }

        for api_type, (home_field, away_field) in type_map.items():
            entry = stat_map.get(api_type)
            if entry:
                result[home_field] = entry.get('home')
                result[away_field] = entry.get('away')

        if 'total shots' in stat_map:
            remates = stat_map['total shots']
            result['remates_local'] = remates.get('home')
            result['remates_visitante'] = remates.get('away')

        if 'shots on goal' in stat_map:
            sog = stat_map['shots on goal']
            result['remates_puerta_local'] = sog.get('home')
            result['remates_puerta_visitante'] = sog.get('away')

        if 'possession' in stat_map:
            pos = stat_map['possession']
            result['posesion_local'] = _safe_float(pos.get('home'))
            result['posesion_visitante'] = _safe_float(pos.get('away'))

        logger.info("Estadísticas obtenidas para fixture %s: %s", fixture_id, {k: v for k, v in result.items() if v is not None})
        return result if result else None
