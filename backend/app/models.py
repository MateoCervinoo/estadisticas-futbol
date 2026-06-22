from sqlmodel import SQLModel, Field, Relationship
from typing import Optional
from datetime import datetime


class Team(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    group: Optional[str] = None


class Partido(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    local_id: Optional[int] = Field(foreign_key="team.id")
    visitante_id: Optional[int] = Field(foreign_key="team.id")
    goles_local: Optional[int] = None
    goles_visitante: Optional[int] = None
    fecha: Optional[datetime] = None
    estado: str = Field(default="programado")  # 'programado' o 'finalizado'

    # Relaciones ligeras; para queries complejas usar joins explícitos
    local: Optional[Team] = Relationship(sa_relationship_kwargs={"lazy": "joined"})
    visitante: Optional[Team] = Relationship(sa_relationship_kwargs={"lazy": "joined"})


class EstadisticasPartido(SQLModel, table=True):
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
