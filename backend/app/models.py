from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime


class Team(SQLModel, table=True):
    """Representa una selección o equipo."""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    group: Optional[str] = None


class Partido(SQLModel, table=True):
    """Modelo principal para almacenar fixtures provenientes de la API.

    Campos requeridos por la especificación:
    - fixture_id: mapea al ID único de la API (indexado y único)
    - date: fecha y hora del partido
    - home_team / away_team: nombres de las selecciones
    - home_score / away_score: goles (None si no se jugó)
    - status: estado del partido (ej. 'NS', 'FT')
    - home_xg / away_xg: xG calculado por el backend
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    fixture_id: int = Field(index=True, unique=True)
    date: datetime
    home_team: str
    away_team: str
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    status: str = Field(default="NS")
    home_xg: Optional[float] = None
    away_xg: Optional[float] = None


class EstadisticasPartido(SQLModel, table=True):
    """Tabla opcional para estadísticas adicionales enlazadas por partido."""
    id: Optional[int] = Field(default=None, primary_key=True)
    partido_id: Optional[int] = Field(foreign_key="partido.id")
    xg_local: Optional[float] = None
    xg_visitante: Optional[float] = None
    remates_local: Optional[int] = None
    remates_visitante: Optional[int] = None
    posesion_local: Optional[float] = None  # porcentaje 0-100
    posesion_visitante: Optional[float] = None
    corners_local: Optional[int] = None
    corners_visitante: Optional[int] = None
