from __future__ import annotations
from typing import Optional, List
from datetime import datetime, timezone
from decimal import Decimal

from sqlmodel import SQLModel, Field, Column, JSON, BigInteger, SmallInteger, UniqueConstraint, Index


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Equipo(SQLModel, table=True):
    __tablename__ = "equipo"

    id: Optional[int] = Field(default=None, primary_key=True)
    nombre_canonico: str = Field(unique=True, max_length=100)
    nombre_es: Optional[str] = None
    nombre_api: Optional[str] = None
    nombre_csv: Optional[str] = None
    nombre_fbref: Optional[str] = None
    nombre_understat: Optional[str] = None
    codigo_iso: Optional[str] = Field(default=None, max_length=3)
    codigo_bandera: Optional[str] = Field(default=None, max_length=10)
    tipo: str = Field(default="seleccion", max_length=20)
    activo: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Torneo(SQLModel, table=True):
    __tablename__ = "torneo"

    id: Optional[int] = Field(default=None, primary_key=True)
    nombre_canonico: str = Field(unique=True, max_length=100)
    nombre_api: Optional[str] = None
    nombre_fbref: Optional[str] = None
    tipo: str = Field(max_length=30)
    categoria: str = Field(max_length=20)
    pais: Optional[str] = Field(default=None, max_length=3)
    nivel: Optional[int] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Sede(SQLModel, table=True):
    __tablename__ = "sede"

    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str = Field(max_length=150)
    ciudad: Optional[str] = None
    pais: Optional[str] = Field(default=None, max_length=3)
    neutral: bool = False
    capacidad: Optional[int] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Arbitro(SQLModel, table=True):
    __tablename__ = "arbitro"

    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str = Field(max_length=150)
    pais: Optional[str] = Field(default=None, max_length=3)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Partido(SQLModel, table=True):
    __tablename__ = "partido"

    id: Optional[int] = Field(default=None, primary_key=True)

    # --- From backend API ---
    fixture_id: Optional[int] = Field(default=None, unique=True, index=True)

    # --- From entrenador CSV ---
    fixture_id_externo: Optional[str] = Field(default=None, max_length=50)
    fuente_origen: str = Field(max_length=30)
    hash_dedupe: Optional[str] = Field(default=None, unique=True, index=True, max_length=32)

    fecha_utc: datetime
    torneo_id: Optional[int] = Field(default=None, foreign_key="torneo.id")
    etapa: Optional[str] = None
    grupo: Optional[str] = None
    sede_id: Optional[int] = Field(default=None, foreign_key="sede.id")
    arbitro_id: Optional[int] = Field(default=None, foreign_key="arbitro.id")
    asistencia: Optional[int] = None
    neutral: bool = False

    equipo_local_id: Optional[int] = Field(default=None, foreign_key="equipo.id")
    equipo_visitante_id: Optional[int] = Field(default=None, foreign_key="equipo.id")

    # --- Legacy team name strings (from backend, for display) ---
    home_team: Optional[str] = None
    away_team: Optional[str] = None

    # --- Denormalized tournament name (from backend, for quick display) ---
    tournament: Optional[str] = None

    # --- Crests (from backend API) ---
    home_crest_url: Optional[str] = None
    away_crest_url: Optional[str] = None

    goles_local: Optional[int] = Field(default=None, sa_type=SmallInteger)
    goles_visitante: Optional[int] = Field(default=None, sa_type=SmallInteger)
    goles_local_ht: Optional[int] = Field(default=None, sa_type=SmallInteger)
    goles_visitante_ht: Optional[int] = Field(default=None, sa_type=SmallInteger)
    ganador_penales_id: Optional[int] = Field(default=None, foreign_key="equipo.id")

    estado: str = Field(default="NS", max_length=20)

    xg_local: Optional[float] = None
    xg_visitante: Optional[float] = None

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("fixture_id_externo", "fuente_origen"),
        Index("idx_partido_fecha", "fecha_utc"),
        Index("idx_partido_equipos", "equipo_local_id", "equipo_visitante_id"),
        Index("idx_partido_torneo_fecha", "torneo_id", "fecha_utc"),
    )


class PartidoEstadisticas(SQLModel, table=True):
    __tablename__ = "partido_estadisticas"

    partido_id: int = Field(primary_key=True, foreign_key="partido.id", ondelete="CASCADE")
    fuente: str = Field(max_length=30, primary_key=True)

    xg_local: Optional[Decimal] = Field(default=None, max_digits=4, decimal_places=2)
    xg_visitante: Optional[Decimal] = Field(default=None, max_digits=4, decimal_places=2)
    xg_local_ht: Optional[Decimal] = Field(default=None, max_digits=4, decimal_places=2)
    xg_visitante_ht: Optional[Decimal] = Field(default=None, max_digits=4, decimal_places=2)

    remates_local: Optional[int] = None
    remates_visitante: Optional[int] = None
    remates_puerta_local: Optional[int] = None
    remates_puerta_visitante: Optional[int] = None
    remates_fuera_local: Optional[int] = None
    remates_fuera_visitante: Optional[int] = None
    remates_bloqueados_local: Optional[int] = None
    remates_bloqueados_visitante: Optional[int] = None

    posesion_local: Optional[float] = None
    posesion_visitante: Optional[float] = None

    corners_local: Optional[int] = None
    corners_visitante: Optional[int] = None
    faltas_local: Optional[int] = None
    faltas_visitante: Optional[int] = None
    tarjetas_amarillas_local: Optional[int] = None
    tarjetas_amarillas_visitante: Optional[int] = None
    tarjetas_rojas_local: Optional[int] = None
    tarjetas_rojas_visitante: Optional[int] = None
    fueras_juego_local: Optional[int] = None
    fueras_juego_visitante: Optional[int] = None
    paradas_local: Optional[int] = None
    paradas_visitante: Optional[int] = None

    elo_local_pre: Optional[int] = None
    elo_visitante_pre: Optional[int] = None
    elo_local_post: Optional[int] = None
    elo_visitante_post: Optional[int] = None

    alineacion_local: Optional[dict] = Field(default=None, sa_type=JSON)
    alineacion_visitante: Optional[dict] = Field(default=None, sa_type=JSON)
    formacion_local: Optional[str] = None
    formacion_visitante: Optional[str] = None

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EquipoElo(SQLModel, table=True):
    __tablename__ = "equipo_elo"

    id: Optional[int] = Field(default=None, primary_key=True)
    equipo_id: int = Field(foreign_key="equipo.id")
    fecha: str = Field(max_length=10)
    elo: int
    ranking_fifa: Optional[int] = None
    fuente: str = Field(max_length=20)

    __table_args__ = (
        UniqueConstraint("equipo_id", "fecha", "fuente"),
    )


class ModelFeatures(SQLModel, table=True):
    __tablename__ = "model_features"

    id: Optional[int] = Field(default=None, primary_key=True)
    partido_id: int = Field(foreign_key="partido.id", ondelete="CASCADE")
    version_features: str = Field(default="v1", max_length=20)

    resultado: Optional[str] = Field(default=None, max_length=1)
    goles_local: Optional[int] = None
    goles_visitante: Optional[int] = None
    total_goles: Optional[int] = None
    ambos_marcan: Optional[bool] = None

    attack_local: Optional[float] = None
    defense_local: Optional[float] = None
    attack_visitante: Optional[float] = None
    defense_visitante: Optional[float] = None
    home_advantage: Optional[float] = None

    forma_local_5: Optional[float] = None
    forma_visitante_5: Optional[float] = None
    forma_local_10: Optional[float] = None
    forma_visitante_10: Optional[float] = None
    goles_favor_local_5: Optional[float] = None
    goles_contra_local_5: Optional[float] = None
    goles_favor_visitante_5: Optional[float] = None
    goles_contra_visitante_5: Optional[float] = None

    xg_diff_5: Optional[float] = None
    xg_diff_10: Optional[float] = None
    posesion_diff_5: Optional[float] = None
    shots_diff_5: Optional[float] = None
    corners_diff_5: Optional[float] = None
    elo_diff: Optional[int] = None
    ranking_fifa_diff: Optional[int] = None

    dias_descanso_local: Optional[int] = None
    dias_descanso_visitante: Optional[int] = None
    neutral_field: Optional[bool] = None
    importancia_torneo: Optional[int] = None
    fase_eliminatoria: Optional[bool] = None

    h2h_partidos: Optional[int] = None
    h2h_victorias_local: Optional[int] = None
    h2h_victorias_visitante: Optional[int] = None
    h2h_goles_local: Optional[int] = None
    h2h_goles_visitante: Optional[int] = None

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("partido_id", "version_features"),
    )


class SourceCoverage(SQLModel, table=True):
    __tablename__ = "source_coverage"

    id: Optional[int] = Field(default=None, primary_key=True)
    fuente: str = Field(max_length=30)
    torneo_id: Optional[int] = Field(default=None, foreign_key="torneo.id")
    temporada: str = Field(max_length=20)
    total_partidos: int = 0
    partidos_con_stats: int = 0
    ultima_sync: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint("fuente", "torneo_id", "temporada"),
    )


class SyncLog(SQLModel, table=True):
    __tablename__ = "sync_log"

    id: Optional[int] = Field(default=None, primary_key=True)
    fuente: str = Field(max_length=30)
    tipo: str = Field(max_length=20)
    fecha_inicio: datetime = Field(default_factory=utc_now)
    fecha_fin: Optional[datetime] = None
    partidos_procesados: int = 0
    partidos_nuevos: int = 0
    partidos_actualizados: int = 0
    errores: int = 0
    estado: str = Field(default="running", max_length=20)


class ModelVersion(SQLModel, table=True):
    __tablename__ = "model_version"

    id: Optional[int] = Field(default=None, primary_key=True)
    version: str = Field(max_length=20, unique=True, index=True)
    model_type: str = Field(max_length=30)
    features_version: str = Field(max_length=10)
    data_cutoff: datetime
    train_size: int
    metrics: dict = Field(default={}, sa_type=JSON)
    params_json: dict = Field(default={}, sa_type=JSON)
    created_at: datetime = Field(default_factory=utc_now)


class TorneoTablaPosicion(SQLModel, table=True):
    __tablename__ = "torneo_tabla_posicion"

    torneo_id: int = Field(foreign_key="torneo.id", primary_key=True)
    equipo_id: int = Field(foreign_key="equipo.id", primary_key=True)
    pj: int = 0
    pg: int = 0
    pe: int = 0
    pp: int = 0
    gf: int = 0
    gc: int = 0
    pts: int = 0
    xg_favor: float = 0
    xg_contra: float = 0
    forma_5: str = Field(default="", max_length=10)
    updated_at: datetime = Field(default_factory=utc_now)


class TorneoBracket(SQLModel, table=True):
    __tablename__ = "torneo_bracket"

    id: Optional[int] = Field(default=None, primary_key=True)
    torneo_id: int = Field(foreign_key="torneo.id", index=True)
    ronda: str = Field(max_length=30, index=True)
    orden: int = Field(index=True)
    partido_id: Optional[int] = Field(default=None, foreign_key="partido.id")
    equipo1_id: Optional[int] = Field(default=None, foreign_key="equipo.id")
    equipo2_id: Optional[int] = Field(default=None, foreign_key="equipo.id")
    ganador_id: Optional[int] = Field(default=None, foreign_key="equipo.id")


class PartidoEvento(SQLModel, table=True):
    __tablename__ = "partido_evento"

    id: Optional[int] = Field(default=None, primary_key=True)
    partido_id: int = Field(foreign_key="partido.id", index=True)
    minuto: int = Field(index=True)
    tipo: str = Field(max_length=20, index=True)
    equipo_id: int = Field(foreign_key="equipo.id")
    jugador: Optional[str] = Field(default=None, max_length=100)
    detalle: Optional[str] = Field(default=None, max_length=100)


class UsuarioFavorito(SQLModel, table=True):
    __tablename__ = "usuario_favorito"

    usuario_id: str = Field(max_length=64, primary_key=True)
    partido_id: int = Field(foreign_key="partido.id", primary_key=True)
    alerta_gol: bool = True
    alerta_inicio: bool = True
    alerta_fin: bool = True
    created_at: datetime = Field(default_factory=utc_now)


class ValueBet(SQLModel, table=True):
    __tablename__ = "value_bet"

    id: Optional[int] = Field(default=None, primary_key=True)
    partido_id: int = Field(foreign_key="partido.id", index=True)
    mercado: str = Field(max_length=20, index=True)
    prob_modelo: float
    cuota_mercado: float
    value: float
    detectado_at: datetime = Field(default_factory=utc_now, index=True)
