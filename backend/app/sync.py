"""Sincronizador de fixtures y cálculo de xG personalizado.

Contiene:
- sync_fixtures_and_metrics(): sincroniza fixtures desde APIFootballClient
- test_sync_flow(): prueba de integración en modo mock (no requiere API key)

Evitar importaciones circulares: no importa main.py.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from sqlmodel import select

from .api_client import APIFootballClient
from .models import Partido, PartidoEstadisticas, Notificacion
from .database import init_db
from .db.session import Session, engine
from .data_mapper import normalize_status
from .services.data_normalization_service import (
    build_hash_dedupe,
    canonical_team_name,
    canonical_tournament_name,
    classify_tipo_dato,
    find_partido_for_upsert,
    resolve_equipo_id,
    resolve_torneo_id,
    validate_partido_values,
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

FINAL_STATUSES = {'FT', 'FINISHED'}

# Competencias de clubes a sincronizar con football-data.org
# código -> nombre_canonico del Torneo
CLUB_COMPETITIONS = {
    "PL": "Premier League",
    "PD": "La Liga",
    "SA": "Serie A",
    "BL1": "Bundesliga",
    "FL1": "Ligue 1",
    "CL": "Champions League",
}

# Temporadas disponibles a sincronizar desde football-data.org.
# season=2026 corresponde a la temporada 2026/2027 en ligas de clubes.
CLUB_SEASONS = [2023, 2024, 2025, 2026]


def _parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    """Parsea una ISO string que puede terminar en 'Z' a datetime con tzinfo.

    Devuelve None si dt_str es falsy o no parseable.
    """
    if not dt_str:
        return None
    try:
        # fromisoformat doesn't accept trailing 'Z', convertir a +00:00
        if dt_str.endswith('Z'):
            dt_str = dt_str.replace('Z', '+00:00')
        return datetime.fromisoformat(dt_str)
    except Exception:
        logger.exception("No se pudo parsear la fecha: %s", dt_str)
        return None


def _compute_xg_from_metrics(metrics: Dict[str, Any]) -> (Optional[float], Optional[float]):
    """Calcula el xG propio a partir de métricas de remates.

    Fórmula simple y explicable:
    xG = (shots_inside_box * 0.13) + (shots_outside_box * 0.04)

    Si faltan métricas para un equipo, se asume 0 para esa métrica.
    """
    try:
        inside = metrics.get('shots_inside_box', {})
        outside = metrics.get('shots_outside_box', {})

        home_inside = inside.get('home') or 0
        away_inside = inside.get('away') or 0

        home_out = outside.get('home') or 0
        away_out = outside.get('away') or 0

        home_xg = float(home_inside) * 0.13 + float(home_out) * 0.04
        away_xg = float(away_inside) * 0.13 + float(away_out) * 0.04

        return home_xg, away_xg
    except Exception:
        logger.exception("Error calculando xG a partir de metrics: %s", metrics)
        return None, None


def _fetch_competition(client: APIFootballClient, code: str, season: Optional[int] = None,
                       torneo_name: str = "FIFA World Cup") -> List[Dict[str, Any]]:
    """Obtiene fixtures de una competición y los etiqueta con el nombre del torneo."""
    fixtures = client.get_competition_fixtures(code, season=season)
    for f in fixtures:
        if 'torneo_name' not in f:
            f['torneo_name'] = torneo_name
    return fixtures


def _process_fixture(session: Session, f: Dict[str, Any], client: APIFootballClient,
                     created: List[int], updated: List[int], errors: List[str]) -> None:
    """Procesa un fixture individual: crea o actualiza el Partido."""
    fixture_id = f.get('fixture_id')
    if fixture_id is None:
        msg = f"Fixture sin fixture_id: {f}"
        logger.warning(msg)
        errors.append(msg)
        return

    torneo_name = f.get('torneo_name', 'FIFA World Cup')
    date = _parse_datetime(f.get('date'))
    home_team = canonical_team_name(f.get('home_team'))
    away_team = canonical_team_name(f.get('away_team'))
    goals_home = f.get('goals_home')
    goals_away = f.get('goals_away')
    ht_goals_home = f.get('ht_goals_home')
    ht_goals_away = f.get('ht_goals_away')
    stage = f.get('stage')
    group = f.get('group')
    matchday = f.get('matchday')
    home_crest_url = f.get('home_crest_url')
    away_crest_url = f.get('away_crest_url')
    raw_status = f.get('status')
    status = normalize_status(raw_status, source="api")
    tournament = canonical_tournament_name(f.get('tournament') or torneo_name)
    category = "club" if torneo_name in CLUB_COMPETITIONS.values() else "seleccion"

    try:
        torneo_id = resolve_torneo_id(session, tournament or torneo_name, category)
    except Exception:
        logger.exception("No se pudo resolver torneo para fixture_id=%s", fixture_id)
        torneo_id = None

    hash_dedupe = build_hash_dedupe(date, home_team, away_team, tournament)

    home_team_id = resolve_equipo_id(session, home_team, "nombre_api", category)
    away_team_id = resolve_equipo_id(session, away_team, "nombre_api", category)
    validation_errors = validate_partido_values(date, home_team, away_team, home_team_id, away_team_id, torneo_id, fixture_id, hash_dedupe)
    if validation_errors:
        msg = f"Fixture inválido fixture_id={fixture_id}: {','.join(validation_errors)}"
        logger.warning(msg)
        errors.append(msg)
        return

    existing, conflict = find_partido_for_upsert(session, fixture_id, hash_dedupe)
    if conflict:
        msg = f"Conflicto fixture_id/hash_dedupe fixture_id={fixture_id} hash={hash_dedupe}"
        logger.warning(msg)
        errors.append(msg)
        return

    tipo_dato = classify_tipo_dato("api_football_data", status, date)

    try:
        if not existing:
            partido = Partido(
                fixture_id=fixture_id,
                hash_dedupe=hash_dedupe,
                fuente_origen="api_football_data",
                tipo_dato=tipo_dato,
                torneo_id=torneo_id,
                fecha_utc=date,
                home_team=home_team or "",
                away_team=away_team or "",
                equipo_local_id=home_team_id,
                equipo_visitante_id=away_team_id,
                goles_local=goals_home,
                goles_visitante=goals_away,
                goles_local_ht=ht_goals_home,
                goles_visitante_ht=ht_goals_away,
                estado=status,
                tournament=tournament,
                etapa=stage,
                grupo=group,
                jornada=matchday,
                home_crest_url=home_crest_url,
                away_crest_url=away_crest_url,
            )

            if status in FINAL_STATUSES:
                metrics = client.get_match_metrics(fixture_id)
                home_xg, away_xg = _compute_xg_from_metrics(metrics)
                partido.xg_local = home_xg
                partido.xg_visitante = away_xg

            session.add(partido)
            session.commit()
            created.append(fixture_id)
            logger.info("Creado partido fixture_id=%s status=%s (%s)", fixture_id, status, torneo_name)
        else:
            local_final = existing.estado in FINAL_STATUSES
            api_final = status in FINAL_STATUSES or status == 'IN_PLAY'
            metadata_changed = (
                existing.etapa != stage
                or existing.grupo != group
                or existing.jornada != matchday
                or existing.home_crest_url != home_crest_url
                or existing.away_crest_url != away_crest_url
                or existing.goles_local_ht != ht_goals_home
                or existing.goles_visitante_ht != ht_goals_away
                or existing.equipo_local_id != home_team_id
                or existing.equipo_visitante_id != away_team_id
                or existing.torneo_id != torneo_id
            )
            score_changed = (
                existing.goles_local != goals_home
                or existing.goles_visitante != goals_away
            )

            allow_update_after_final_hours = False
            try:
                now = datetime.now(timezone.utc)
                if existing.fecha_utc.tzinfo is None:
                    match_dt = existing.fecha_utc.replace(tzinfo=timezone.utc)
                else:
                    match_dt = existing.fecha_utc
                delta_seconds = (now - match_dt).total_seconds()
                allow_update_after_final_hours = delta_seconds >= (2 * 3600)
            except Exception:
                allow_update_after_final_hours = False

            if local_final and not allow_update_after_final_hours and status in FINAL_STATUSES and not (metadata_changed or score_changed):
                logger.debug("Partido %s final en DB y dentro de ventana de 2h; saltando actualización", fixture_id)
                return

            old_status = existing.estado
            if (
                (old_status in ('NS', 'TIMED') and api_final)
                or (old_status != status)
                or score_changed
                or metadata_changed
                or (local_final and allow_update_after_final_hours and status in FINAL_STATUSES)
            ):
                existing.goles_local = goals_home
                existing.goles_visitante = goals_away
                existing.fixture_id = fixture_id
                existing.hash_dedupe = hash_dedupe
                existing.fuente_origen = "api_football_data"
                existing.tipo_dato = tipo_dato
                existing.goles_local_ht = ht_goals_home
                existing.goles_visitante_ht = ht_goals_away
                existing.estado = status
                existing.tournament = tournament
                existing.torneo_id = torneo_id
                existing.etapa = stage
                existing.grupo = group
                existing.jornada = matchday
                existing.home_crest_url = home_crest_url
                existing.away_crest_url = away_crest_url

                if home_team_id is not None:
                    existing.equipo_local_id = home_team_id
                if away_team_id is not None:
                    existing.equipo_visitante_id = away_team_id

                needs_metrics = (
                    status in FINAL_STATUSES
                    and (
                        existing.xg_local is None
                        or existing.xg_visitante is None
                        or score_changed
                        or old_status not in FINAL_STATUSES
                    )
                )
                if needs_metrics:
                    metrics = client.get_match_metrics(fixture_id)
                    home_xg, away_xg = _compute_xg_from_metrics(metrics)
                    existing.xg_local = home_xg
                    existing.xg_visitante = away_xg

                # Create notification on status transition
                transition_type = None
                if old_status in ('NS', 'TIMED') and status == 'IN_PLAY':
                    transition_type = 'inicio'
                    msg = f"{home_team or '?'} vs {away_team or '?'} empezó"
                elif old_status == 'IN_PLAY' and status in ('FT', 'AET', 'PEN'):
                    transition_type = 'fin'
                    score = f"{goals_home or 0}-{goals_away or 0}"
                    msg = f"{home_team or '?'} {score} {away_team or '?'} terminó"
                if transition_type and existing.id:
                    notif = Notificacion(
                        partido_id=existing.id,
                        tipo=transition_type,
                        mensaje=msg,
                    )
                    session.add(notif)

                session.add(existing)
                session.commit()
                updated.append(fixture_id)
                logger.info("Actualizado partido fixture_id=%s status=%s (%s)", fixture_id, status, torneo_name)

    except Exception as e:
        msg = f"Error procesando fixture {fixture_id}: {e}"
        logger.exception(msg)
        errors.append(msg)


def _populate_stats(session: Session) -> int:
    """Puebla PartidoEstadisticas con xG de Partido para partidos FT."""
    stats_fetched = 0
    try:
        finished = session.exec(
            select(Partido).where(Partido.estado.in_(FINAL_STATUSES))
        ).all()
        for p in finished:
            existing = session.get(PartidoEstadisticas, (p.id, 'api_football_data'))
            if existing:
                continue
            if p.xg_local is None and p.xg_visitante is None:
                continue
            pe = PartidoEstadisticas(
                partido_id=p.id,
                fuente='api_football_data',
                xg_local=p.xg_local,
                xg_visitante=p.xg_visitante,
            )
            session.add(pe)
            session.commit()
            stats_fetched += 1
    except Exception:
        logger.exception("Error poblando PartidoEstadisticas desde xG de Partido")
    return stats_fetched


def sync_fixtures_and_metrics() -> Dict[str, Any]:
    """Sincroniza fixtures del Mundial y ligas de clubes desde football-data.org.

    Reglas principales:
    - Si el partido no existe, lo crea.
    - Si existe y pasa a 'FT' desde otro estado, actualiza los goles reales
      y calcula/almacena el xG.

    Retorna un resumen con conteos y listas de fixtures procesados.
    """
    client = APIFootballClient()

    created: List[int] = []
    updated: List[int] = []
    errors: List[str] = []
    total_fetched = 0

    # --- Mundial ---
    fixtures = client.get_world_cup_fixtures()
    logger.info("Obtenidos %s fixtures del Mundial", len(fixtures))
    total_fetched += len(fixtures)

    with Session(engine) as session:
        for f in fixtures:
            f['torneo_name'] = 'FIFA World Cup'
            _process_fixture(session, f, client, created, updated, errors)

    # --- Ligas de clubes ---
    for code, torneo_name in CLUB_COMPETITIONS.items():
        for season in CLUB_SEASONS:
            try:
                fixtures = client.get_competition_fixtures(code, season=season)
                logger.info("Obtenidos %s fixtures de %s (season=%s)", len(fixtures), code, season)
                total_fetched += len(fixtures)

                with Session(engine) as session:
                    for f in fixtures:
                        f['torneo_name'] = torneo_name
                        _process_fixture(session, f, client, created, updated, errors)
            except Exception as e:
                msg = f"Error obteniendo fixtures de {code} season={season}: {e}"
                logger.exception(msg)
                errors.append(msg)

    # --- Poblar PartidoEstadisticas ---
    with Session(engine) as session:
        stats_fetched = _populate_stats(session)

    summary = {
        'total_fetched': total_fetched,
        'created': created,
        'updated': updated,
        'stats_fetched': stats_fetched,
        'errors': errors,
    }
    return summary


def test_sync_flow() -> bool:
    """Prueba de integración en modo mock.

    - Inicializa la DB (crea tablas si no existen).
    - Ejecuta el sincronizador (el cliente se inicializa en modo mock si no hay API key).
    - Revisa los registros en la tabla Partido y emite un reporte en consola.

    Retorna True si los checks básicos pasan, False en caso contrario.
    """
    print("=== test_sync_flow: Inicializando DB de prueba (si es necesario) ===")
    init_db()

    print("=== Ejecutando sincronizador (modo mock si no hay API key) ===")
    summary = sync_fixtures_and_metrics()
    print("Resumen sync:", summary)

    # Verificar contenido en la base de datos
    ok = True
    with Session(engine) as session:
        partidos = session.exec(select(Partido)).all()

        print(f"Se encontraron {len(partidos)} partidos en la base de datos:")
        for p in partidos:
            print(f"- fixture_id={p.fixture_id} estado={p.estado} score={p.goles_local}-{p.goles_visitante} xg_local={p.xg_local} xg_visitante={p.xg_visitante}")

            if p.estado == 'FT':
                if p.xg_local is None or p.xg_visitante is None:
                    print(f"ERROR: partido FT sin xG calculado: fixture_id={p.fixture_id}")
                    ok = False
                else:
                    if not (0.0 <= p.xg_local <= 20.0):
                        print(f"WARNING: xg_local fuera de rango razonable: {p.xg_local} (fixture {p.fixture_id})")
                    if not (0.0 <= p.xg_visitante <= 20.0):
                        print(f"WARNING: xg_visitante fuera de rango razonable: {p.xg_visitante} (fixture {p.fixture_id})")
            else:
                if p.xg_local is not None or p.xg_visitante is not None:
                    print(f"WARNING: partido no jugado tiene xG no nulo: fixture_id={p.fixture_id}")

    print("=== test_sync_flow: Resultado final ===")
    if ok:
        print("TEST OK: sincronizador procesó fixtures y calculó xG coherente en modo mock.")
    else:
        print("TEST FAILED: se detectaron incoherencias. Revisa los mensajes anteriores.")

    return ok


if __name__ == '__main__':
    # Ejecutar prueba de autoverificación cuando se ejecute el módulo directamente.
    test_sync_flow()
