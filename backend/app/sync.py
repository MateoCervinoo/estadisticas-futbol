"""Sincronizador de fixtures y cálculo de xG personalizado.

Contiene:
- sync_fixtures_and_metrics(): sincroniza fixtures desde APIFootballClient
- test_sync_flow(): prueba de integración en modo mock (no requiere API key)

Evitar importaciones circulares: no importa main.py.
"""
from __future__ import annotations

import csv
import logging
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

from sqlmodel import Session, select

from .api_client import APIFootballClient
from .models import Partido
from .database import engine, init_db
from .data_mapper import normalize_status, normalize_tournament

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

FINAL_STATUSES = {'FT', 'FINISHED'}
TRAINER_RESULTS_CSV = '/app/data/results.csv'


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


def _append_result_to_trainer_csv(partido: Partido) -> None:
    os.makedirs(os.path.dirname(TRAINER_RESULTS_CSV), exist_ok=True)
    file_exists = os.path.exists(TRAINER_RESULTS_CSV)
    write_header = not file_exists or os.path.getsize(TRAINER_RESULTS_CSV) == 0

    date_value = partido.date.date().isoformat() if partido.date else ''
    with open(TRAINER_RESULTS_CSV, 'a', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(
            csvfile,
            fieldnames=['date', 'home_team', 'away_team', 'home_score', 'away_score', 'tournament'],
        )
        if write_header:
            writer.writeheader()
        writer.writerow({
            'date': date_value,
            'home_team': partido.home_team,
            'away_team': partido.away_team,
            'home_score': partido.home_score,
            'away_score': partido.away_score,
            'tournament': partido.tournament,
        })


def sync_fixtures_and_metrics() -> Dict[str, Any]:
    """Sincroniza fixtures del Mundial y calcula métricas xG.

    Reglas principales:
    - Si el partido no existe, lo crea.
    - Si existe y pasa a 'FT' desde otro estado, actualiza los goles reales
      y calcula/almacena el xG.

    Retorna un resumen con conteos y listas de fixtures procesados.
    """
    client = APIFootballClient()  # si no hay API key, entra en modo mock

    fixtures = client.get_world_cup_fixtures()
    logger.info("Obtenidos %s fixtures desde APIFootballClient", len(fixtures))

    created: List[int] = []
    updated: List[int] = []
    errors: List[str] = []

    with Session(engine) as session:
        for f in fixtures:
            fixture_id = f.get('fixture_id')
            if fixture_id is None:
                msg = f"Fixture sin fixture_id: {f}"
                logger.warning(msg)
                errors.append(msg)
                continue

            date = _parse_datetime(f.get('date'))
            home_team = f.get('home_team')
            away_team = f.get('away_team')
            goals_home = f.get('goals_home')
            goals_away = f.get('goals_away')
            status = f.get('status') or 'NS'
            tournament = 'Mundial'

            # Mapear nombres de la API a IDs de Equipo si existe la tabla
            home_team_id = None
            away_team_id = None
            try:
                from .models import Equipo
                h = session.exec(select(Equipo).where(Equipo.nombre_api == home_team)).first()
                if h:
                    home_team_id = h.id
                a = session.exec(select(Equipo).where(Equipo.nombre_api == away_team)).first()
                if a:
                    away_team_id = a.id
            except Exception:
                home_team_id = None
                away_team_id = None

            stmt = select(Partido).where(Partido.fixture_id == fixture_id)
            existing = session.exec(stmt).first()

            try:
                if not existing:
                    # Crear nuevo registro
                    partido = Partido(
                        fixture_id=fixture_id,
                        date=date or datetime.utcnow(),
                        home_team=home_team or "",
                        away_team=away_team or "",
                        home_team_id=home_team_id,
                        away_team_id=away_team_id,
                        home_score=goals_home,
                        away_score=goals_away,
                        status=status,
                        tournament=tournament,
                    )

                    # Si ya está finalizado, calcular xG
                    if status in FINAL_STATUSES:
                        metrics = client.get_match_metrics(fixture_id)
                        home_xg, away_xg = _compute_xg_from_metrics(metrics)
                        partido.home_xg = home_xg
                        partido.away_xg = away_xg

                    session.add(partido)
                    session.commit()
                    if status in FINAL_STATUSES:
                        _append_result_to_trainer_csv(partido)
                    created.append(fixture_id)
                    logger.info("Creado partido fixture_id=%s status=%s", fixture_id, status)
                else:
                    # UPSERT logic: only update when appropriate
                    # If local is already finalizado, skip updates to avoid overwriting stable data
                    local_final = existing.status in FINAL_STATUSES
                    api_final = status in FINAL_STATUSES or status == 'IN_PLAY'
                    transitioned_to_final = not local_final and status in FINAL_STATUSES

                    # If the local record is final, only update if 2 hours have passed since match date
                    # (approximation for "2 hours since its finalization") or if the API reports a different status
                    allow_update_after_final_hours = False
                    try:
                        now = datetime.utcnow()
                        # If existing.date is naive or tz-aware, handle accordingly (approximate)
                        delta_seconds = (now - existing.date).total_seconds()
                        allow_update_after_final_hours = delta_seconds >= (2 * 3600)
                    except Exception:
                        # If date parsing fails, be conservative and do not allow automatic final updates
                        allow_update_after_final_hours = False

                    if local_final and not allow_update_after_final_hours and status in FINAL_STATUSES:
                        # local final and API also final but within 2 hours -> skip
                        logger.debug("Partido %s final en DB y dentro de ventana de 2h; saltando actualización", fixture_id)
                        continue

                    # Update when local is scheduled/timed and API reports in-play or finished,
                    # or if the status has changed (including after 2 hours for final matches)
                    if (existing.status in ('NS', 'TIMED') and api_final) or (existing.status != status) or (local_final and allow_update_after_final_hours and status in FINAL_STATUSES):
                        existing.home_score = goals_home
                        existing.away_score = goals_away
                        existing.status = status
                        existing.tournament = tournament

                        # Actualizar referencia a Equipo si fue mapeada
                        if home_team_id is not None:
                            existing.home_team_id = home_team_id
                        if away_team_id is not None:
                            existing.away_team_id = away_team_id

                        # If now final, compute xG
                        if status in FINAL_STATUSES:
                            metrics = client.get_match_metrics(fixture_id)
                            home_xg, away_xg = _compute_xg_from_metrics(metrics)
                            existing.home_xg = home_xg
                            existing.away_xg = away_xg

                        session.add(existing)
                        session.commit()
                        if transitioned_to_final:
                            _append_result_to_trainer_csv(existing)
                        updated.append(fixture_id)
                        logger.info("Actualizado/Upserted partido fixture_id=%s status=%s", fixture_id, status)

            except Exception as e:
                msg = f"Error procesando fixture {fixture_id}: {e}"
                logger.exception(msg)
                errors.append(msg)

    summary = {
        'total_fetched': len(fixtures),
        'created': created,
        'updated': updated,
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
            print(f"- fixture_id={p.fixture_id} status={p.status} score={p.home_score}-{p.away_score} home_xg={p.home_xg} away_xg={p.away_xg}")

            # Si el partido está finalizado, esperamos xG calculado coherente
            if p.status == 'FT':
                if p.home_xg is None or p.away_xg is None:
                    print(f"ERROR: partido FT sin xG calculado: fixture_id={p.fixture_id}")
                    ok = False
                else:
                    # Comprobaciones simples de rango
                    if not (0.0 <= p.home_xg <= 20.0):
                        print(f"WARNING: home_xg fuera de rango razonable: {p.home_xg} (fixture {p.fixture_id})")
                    if not (0.0 <= p.away_xg <= 20.0):
                        print(f"WARNING: away_xg fuera de rango razonable: {p.away_xg} (fixture {p.fixture_id})")
            else:
                # Para partidos no jugados, xG idealmente debe ser None
                if p.home_xg is not None or p.away_xg is not None:
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
