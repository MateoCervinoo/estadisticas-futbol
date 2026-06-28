from __future__ import annotations
import os
from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path

try:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent / ".env"
    load_dotenv(env_path)
except Exception:
    pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_RESULTS_CSV = DEFAULT_DATA_DIR / "results.csv"
DEFAULT_SHOOTOUTS_CSV = DEFAULT_DATA_DIR / "shootouts.csv"
DEFAULT_MODEL_PARAMS = DEFAULT_DATA_DIR / "model_params.json"


def _bool_env(key: str, default: bool = False) -> bool:
    return os.getenv(key, str(default)).strip().lower() in ("1", "true", "yes")


def _env(key: str, default: str = "") -> str:
    return os.getenv(key, default)


class Settings:
    DB_ENGINE: str = _env("ENTRENADOR_DB_ENGINE", "postgresql")
    SQLITE_PATH: str = _env("ENTRENADOR_SQLITE_PATH", str(DEFAULT_DATA_DIR / "entrenador.db"))
    POSTGRES_URL: str = _env("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/estadisticas")

    RESULTS_CSV: str = _env("CSV_DATA_PATH", str(DEFAULT_RESULTS_CSV))
    SHOOTOUTS_CSV: str = _env("CSV_SHOOTOUTS_PATH", str(DEFAULT_SHOOTOUTS_CSV))
    MODEL_PARAMS_PATH: str = _env("MODEL_PARAMS_PATH", str(DEFAULT_MODEL_PARAMS))

    FOOTBALL_DATA_KEY: str = _env("API_FOOTBALL_KEY", "")
    FOOTBALL_DATA_BASE: str = _env("FOOTBALL_DATA_BASE", "https://api.football-data.org/v4")
    FOOTBALL_DATA_START_SEASON: int = int(_env("FOOTBALL_DATA_START_SEASON", "2020"))
    FOOTBALL_DATA_END_SEASON: int = int(_env("FOOTBALL_DATA_END_SEASON", "2025"))

    SINCE_YEAR: int = int(_env("SINCE_YEAR", "2018"))
    TRAIN_HISTORICAL_SINCE: int = int(_env("TRAIN_HISTORICAL_SINCE", "2018"))
    ROLLING_WINDOWS: List[int] = [5, 10, 20]
    FEATURES_VERSION: str = _env("FEATURES_VERSION", "v1")

    SOCCERDATA_FBREF: bool = _bool_env("SOCCERDATA_FBREF", True)
    SOCCERDATA_UNDERSTAT: bool = _bool_env("SOCCERDATA_UNDERSTAT", False)
    SOCCERDATA_CLUBELO: bool = _bool_env("SOCCERDATA_CLUBELO", True)

    LOG_LEVEL: str = _env("LOG_LEVEL", "INFO")
    PREDICT_MAX_GOALS: int = int(_env("PREDICT_MAX_GOALS", "6"))
    DIXON_COLES_RHO: float = float(_env("DIXON_COLES_RHO", "0.0"))
    ENABLE_ML_MODELS: bool = _bool_env("ENABLE_ML_MODELS", False)

    @property
    def database_url(self) -> str:
        if self.DB_ENGINE == "sqlite":
            return f"sqlite:///{self.SQLITE_PATH}"
        return self.POSTGRES_URL

    @property
    def database_schema(self) -> Optional[str]:
        if self.DB_ENGINE == "postgresql":
            return "public"
        return None


settings = Settings()


@dataclass
class LeagueConfig:
    nombre_canonico: str
    nombre_fbref: str
    nombre_football_data: Optional[str] = None
    nombre_understat: Optional[str] = None
    tipo: str = "liga"
    categoria: str = "club"
    pais: Optional[str] = None
    nivel: int = 3
    fbref_seasons: List[str] = field(default_factory=list)
    understat_seasons: List[str] = field(default_factory=list)
    football_data_league_code: Optional[str] = None
    sync_enabled: bool = True


LEAGUES_REGISTRY: List[LeagueConfig] = [
    LeagueConfig("Mundial", "World Cup", "WC", tipo="mundial", categoria="seleccion", nivel=1, sync_enabled=True),
    #LeagueConfig("Copa América", "Copa América", "CA", tipo="continental", categoria="seleccion", pais="SA", nivel=2),
    LeagueConfig("Eurocopa", "European Championship", "EC", tipo="continental", categoria="seleccion", nivel=2),
    #LeagueConfig("Clasificatorias Mundial", "World Cup Qualification", "WQC", tipo="clasificatorias", categoria="seleccion", nivel=3),
    LeagueConfig("Premier League", "ENG-Premier League", "PL", "EPL", tipo="liga", categoria="club", pais="GB", nivel=1,
                 fbref_seasons=["2020-2021", "2021-2022", "2022-2023", "2023-2024", "2024-2025"],
                 understat_seasons=["2020", "2021", "2022", "2023", "2024"],
                 football_data_league_code="PL"),
    LeagueConfig("La Liga", "ESP-La Liga", "PD", "La_liga", tipo="liga", categoria="club", pais="ES", nivel=1,
                 fbref_seasons=["2020-2021", "2021-2022", "2022-2023", "2023-2024", "2024-2025"],
                 understat_seasons=["2020", "2021", "2022", "2023", "2024"],
                 football_data_league_code="PD"),
    LeagueConfig("Serie A", "ITA-Serie A", "SA", "Serie_A", tipo="liga", categoria="club", pais="IT", nivel=1,
                 fbref_seasons=["2020-2021", "2021-2022", "2022-2023", "2023-2024", "2024-2025"],
                 understat_seasons=["2020", "2021", "2022", "2023", "2024"],
                 football_data_league_code="SA"),
    LeagueConfig("Bundesliga", "GER-Bundesliga", "BL1", "Bundesliga", tipo="liga", categoria="club", pais="DE", nivel=1,
                 fbref_seasons=["2020-2021", "2021-2022", "2022-2023", "2023-2024", "2024-2025"],
                 football_data_league_code="BL1"),
    LeagueConfig("Ligue 1", "FRA-Ligue 1", "FL1", "Ligue_1", tipo="liga", categoria="club", pais="FR", nivel=1,
                 fbref_seasons=["2020-2021", "2021-2022", "2022-2023", "2023-2024", "2024-2025"],
                 football_data_league_code="FL1"),
    LeagueConfig("Champions League", None, "CL", "UCL", tipo="copa", categoria="club", nivel=1,
                 fbref_seasons=[], understat_seasons=[],  # FBref no tiene Champions League como liga standalone
                 football_data_league_code="CL"),
    #LeagueConfig("Copa Libertadores", "Copa Libertadores", "CLI", None, tipo="copa", categoria="club", pais="SA", nivel=1,
                 #fbref_seasons=["2020-2021", "2021-2022", "2022-2023", "2023-2024", "2024-2025"],
                 #football_data_league_code="CLI"),
]
