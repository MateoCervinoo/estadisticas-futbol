import csv
import os
from collections import defaultdict
from typing import Any

from sqlmodel import Session, select

from ..database import engine
from ..models import Partido
from .data_normalization_service import build_hash_dedupe, canonical_key, classify_tipo_dato

DEFAULT_BAD_RECORDS_PATH = os.path.join("/", "app", "data", "bad_records.csv")


def validate_partido_record(partido: Partido) -> list[str]:
    errors = []
    if not partido.fecha_utc:
        errors.append("fecha_utc_missing")
    if not canonical_key(partido.home_team) or not canonical_key(partido.away_team):
        errors.append("team_name_missing")
    if partido.equipo_local_id is None or partido.equipo_visitante_id is None:
        errors.append("team_id_missing")
    if partido.equipo_local_id is not None and partido.equipo_local_id == partido.equipo_visitante_id:
        errors.append("same_team")
    if partido.torneo_id is None:
        errors.append("torneo_id_missing")
    if partido.fixture_id is None and not partido.hash_dedupe:
        errors.append("dedupe_key_missing")
    if partido.hash_dedupe:
        expected_hash = build_hash_dedupe(partido.fecha_utc, partido.home_team, partido.away_team, partido.tournament)
        if expected_hash != partido.hash_dedupe:
            errors.append("hash_dedupe_mismatch")
    return errors


def build_data_quality_report(export_path: str | None = DEFAULT_BAD_RECORDS_PATH) -> dict[str, Any]:
    with Session(engine) as session:
        partidos = session.exec(select(Partido)).all()

    invalid_records = []
    hash_groups: dict[str, list[Partido]] = defaultdict(list)
    fixture_groups: dict[int, list[Partido]] = defaultdict(list)
    source_counts: dict[str, int] = defaultdict(int)
    type_counts: dict[str, int] = defaultdict(int)

    for partido in partidos:
        source_counts[partido.fuente_origen] += 1
        type_counts[getattr(partido, "tipo_dato", None) or "sin_tipo"] += 1
        if partido.hash_dedupe:
            hash_groups[partido.hash_dedupe].append(partido)
        if partido.fixture_id is not None:
            fixture_groups[partido.fixture_id].append(partido)

        errors = validate_partido_record(partido)
        if errors:
            invalid_records.append(_record_to_report_row(partido, errors))

    duplicate_hashes = [rows for rows in hash_groups.values() if len(rows) > 1]
    duplicate_fixtures = [rows for rows in fixture_groups.values() if len(rows) > 1]
    for rows in duplicate_hashes:
        for partido in rows:
            invalid_records.append(_record_to_report_row(partido, ["duplicate_hash_dedupe"]))
    for rows in duplicate_fixtures:
        for partido in rows:
            invalid_records.append(_record_to_report_row(partido, ["duplicate_fixture_id"]))

    if export_path:
        export_bad_records(invalid_records, export_path)

    return {
        "total_partidos": len(partidos),
        "invalid_count": len(invalid_records),
        "duplicate_hash_groups": len(duplicate_hashes),
        "duplicate_fixture_groups": len(duplicate_fixtures),
        "source_counts": dict(sorted(source_counts.items())),
        "type_counts": dict(sorted(type_counts.items())),
        "export_path": export_path,
        "records": invalid_records,
    }


def export_bad_records(records: list[dict[str, Any]], path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fields = [
        "id",
        "fixture_id",
        "fixture_id_externo",
        "hash_dedupe",
        "fuente_origen",
        "tipo_dato",
        "fecha_utc",
        "home_team",
        "away_team",
        "torneo_id",
        "tournament",
        "errors",
    ]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)


def repair_partido_identity(dry_run: bool = True) -> dict[str, Any]:
    repaired = []
    skipped = []
    with Session(engine) as session:
        partidos = session.exec(select(Partido)).all()
        for partido in partidos:
            expected_hash = build_hash_dedupe(partido.fecha_utc, partido.home_team, partido.away_team, partido.tournament)
            changes = {}

            if partido.hash_dedupe != expected_hash:
                conflict = session.exec(
                    select(Partido).where(Partido.hash_dedupe == expected_hash, Partido.id != partido.id)
                ).first()
                if conflict:
                    skipped.append({"id": partido.id, "reason": "target_hash_exists", "target_hash": expected_hash})
                    continue
                changes["hash_dedupe"] = expected_hash

            if partido.fuente_origen in {"csv_historical", "csv_historico"}:
                if partido.fixture_id is not None:
                    changes["fixture_id"] = None
                if not partido.fixture_id_externo:
                    changes["fixture_id_externo"] = f"csv_{expected_hash[:12]}"
                if partido.fuente_origen == "csv_historico":
                    changes["fuente_origen"] = "csv_historical"

            expected_tipo = classify_tipo_dato(partido.fuente_origen, partido.estado, partido.fecha_utc)
            if getattr(partido, "tipo_dato", None) != expected_tipo:
                changes["tipo_dato"] = expected_tipo

            if not changes:
                continue

            repaired.append({"id": partido.id, "changes": sorted(changes.keys())})
            if not dry_run:
                for field, value in changes.items():
                    setattr(partido, field, value)
                session.add(partido)

        if not dry_run:
            session.commit()

    return {"dry_run": dry_run, "repaired_count": len(repaired), "skipped_count": len(skipped), "repaired": repaired, "skipped": skipped}


def purge_invalid_placeholder_fixtures(dry_run: bool = True) -> dict[str, Any]:
    deleted = []
    with Session(engine) as session:
        partidos = session.exec(select(Partido)).all()
        for partido in partidos:
            errors = validate_partido_record(partido)
            if partido.tipo_dato != "fixture" or "team_name_missing" not in errors:
                continue
            deleted.append({"id": partido.id, "fixture_id": partido.fixture_id, "fecha_utc": partido.fecha_utc.isoformat() if partido.fecha_utc else None})
            if not dry_run:
                session.delete(partido)
        if not dry_run:
            session.commit()
    return {"dry_run": dry_run, "deleted_count": len(deleted), "deleted": deleted}


def _record_to_report_row(partido: Partido, errors: list[str]) -> dict[str, Any]:
    return {
        "id": partido.id,
        "fixture_id": partido.fixture_id,
        "fixture_id_externo": partido.fixture_id_externo,
        "hash_dedupe": partido.hash_dedupe,
        "fuente_origen": partido.fuente_origen,
        "tipo_dato": getattr(partido, "tipo_dato", None),
        "fecha_utc": partido.fecha_utc.isoformat() if partido.fecha_utc else None,
        "home_team": partido.home_team,
        "away_team": partido.away_team,
        "torneo_id": partido.torneo_id,
        "tournament": partido.tournament,
        "errors": ",".join(errors),
    }
