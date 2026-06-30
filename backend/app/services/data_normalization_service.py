import hashlib
import re
from datetime import datetime, timezone
from typing import Any, Optional

from sqlmodel import Session, select

from ..data_mapper import normalize_tournament
from ..models import Equipo, Partido, Torneo

CANONICAL_TEAM_ALIASES = {
    "brazil": "Brazil",
    "brasil": "Brazil",
    "germany": "Germany",
    "alemania": "Germany",
    "spain": "Spain",
    "espana": "Spain",
    "españa": "Spain",
    "france": "France",
    "francia": "France",
    "argentina": "Argentina",
    "united states": "United States",
    "usa": "United States",
    "u.s.a.": "United States",
    "south korea": "South Korea",
    "korea republic": "South Korea",
    "korea republic of": "South Korea",
}

CANONICAL_TOURNAMENT_ALIASES = {
    "fifa world cup": "Mundial",
    "world cup": "Mundial",
    "mundial": "Mundial",
    "premier league": "Premier League",
    "la liga": "La Liga",
    "serie a": "Serie A",
    "bundesliga": "Bundesliga",
    "ligue 1": "Ligue 1",
    "champions league": "Champions League",
}


def canonical_key(value: Any) -> str:
    text = str(value or "").strip().casefold()
    text = re.sub(r"\s+", " ", text)
    return text


def canonical_team_name(raw: Optional[str]) -> str:
    key = canonical_key(raw)
    if not key:
        return ""
    return CANONICAL_TEAM_ALIASES.get(key, str(raw).strip())


def canonical_tournament_name(raw: Optional[str]) -> str:
    key = canonical_key(raw)
    if not key:
        return "Otro"
    return CANONICAL_TOURNAMENT_ALIASES.get(key, normalize_tournament(raw))


def partido_date_key(fecha_utc: datetime | None) -> str:
    return fecha_utc.strftime("%Y-%m-%d") if fecha_utc else ""


def build_hash_dedupe(
    fecha_utc: datetime | None,
    home_team: Optional[str],
    away_team: Optional[str],
    tournament: Optional[str],
) -> str:
    key = "|".join([
        partido_date_key(fecha_utc),
        canonical_key(canonical_team_name(home_team)),
        canonical_key(canonical_team_name(away_team)),
        canonical_key(canonical_tournament_name(tournament)),
    ])
    return hashlib.md5(key.encode("utf-8")).hexdigest()


def classify_tipo_dato(fuente_origen: str, estado: Optional[str], fecha_utc: datetime | None) -> str:
    if fuente_origen in {"csv_historical", "csv_historico"}:
        return "historico"
    status = str(estado or "").upper()
    if status in {"NS", "TIMED", "SCHEDULED"}:
        return "fixture"
    if fecha_utc:
        dt = fecha_utc if fecha_utc.tzinfo else fecha_utc.replace(tzinfo=timezone.utc)
        if dt > datetime.now(timezone.utc) and status not in {"FT", "FINISHED", "AET", "PEN"}:
            return "fixture"
    return "api_sync"


def resolve_equipo_id(session: Session, raw_name: Optional[str], source_field: str, tipo: str) -> int | None:
    canonical = canonical_team_name(raw_name)
    if not canonical:
        return None

    comparisons = [
        Equipo.nombre_canonico == canonical,
        Equipo.nombre_api == str(raw_name).strip(),
        Equipo.nombre_csv == str(raw_name).strip(),
    ]
    equipo = None
    for comparison in comparisons:
        equipo = session.exec(select(Equipo).where(comparison)).first()
        if equipo:
            break

    if not equipo:
        values = {"nombre_canonico": canonical, "tipo": tipo}
        if source_field == "nombre_api":
            values["nombre_api"] = str(raw_name).strip()
        elif source_field == "nombre_csv":
            values["nombre_csv"] = str(raw_name).strip()
        equipo = Equipo(**values)
        session.add(equipo)
        session.flush()
    else:
        raw_clean = str(raw_name).strip()
        if source_field == "nombre_api" and not equipo.nombre_api:
            equipo.nombre_api = raw_clean
        if source_field == "nombre_csv" and not equipo.nombre_csv:
            equipo.nombre_csv = raw_clean
        session.add(equipo)
        session.flush()

    return equipo.id


def resolve_torneo_id(session: Session, raw_name: Optional[str], category: str) -> int | None:
    canonical = canonical_tournament_name(raw_name)
    if not canonical:
        return None

    torneo = session.exec(select(Torneo).where(Torneo.nombre_canonico == canonical)).first()
    if torneo:
        return torneo.id

    tipo = "mundial" if canonical == "Mundial" else ("liga" if category == "club" else "otro")
    torneo = Torneo(
        nombre_canonico=canonical,
        nombre_api=str(raw_name).strip() if raw_name else canonical,
        tipo=tipo,
        categoria=category,
    )
    session.add(torneo)
    session.flush()
    return torneo.id


def find_partido_for_upsert(session: Session, fixture_id: int | None, hash_dedupe: str | None) -> tuple[Partido | None, str | None]:
    by_fixture = session.exec(select(Partido).where(Partido.fixture_id == fixture_id)).first() if fixture_id is not None else None
    by_hash = session.exec(select(Partido).where(Partido.hash_dedupe == hash_dedupe)).first() if hash_dedupe else None

    if by_fixture and by_hash and by_fixture.id != by_hash.id:
        return by_fixture, "fixture_hash_conflict"
    if by_fixture:
        return by_fixture, None
    if by_hash:
        return by_hash, None
    return None, None


def validate_partido_values(
    fecha_utc: datetime | None,
    home_team: Optional[str],
    away_team: Optional[str],
    equipo_local_id: int | None,
    equipo_visitante_id: int | None,
    torneo_id: int | None,
    fixture_id: int | None,
    hash_dedupe: str | None,
) -> list[str]:
    errors = []
    if not fecha_utc:
        errors.append("fecha_utc_missing")
    if not canonical_key(home_team) or not canonical_key(away_team):
        errors.append("team_name_missing")
    if equipo_local_id is None or equipo_visitante_id is None:
        errors.append("team_id_missing")
    if equipo_local_id is not None and equipo_local_id == equipo_visitante_id:
        errors.append("same_team")
    if torneo_id is None:
        errors.append("torneo_id_missing")
    if fixture_id is None and not hash_dedupe:
        errors.append("dedupe_key_missing")
    return errors
