"""Script único para asignar torneo_id a los partidos que quedaron huérfanos.

Los 8151 partidos de selecciones (csv_historical) tienen tournament en español
pero NULL en torneo_id porque la tabla Torneo se pobló con nombres en inglés
desde la API sync. Este script:
  1. Crea entradas Torneo con nombres en español (los que faltan)
  2. Asigna torneo_id a todos los partidos según su tournament

Uso: python -m entrenador.scripts.relink_torneos
"""
from __future__ import annotations
import logging

from sqlmodel import Session, select, text as sqltext

from ..config import settings
from ..database import get_engine, init_db
from ..models import Torneo, Partido

logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL))
logger = logging.getLogger("relink_torneos")

# Mapa: nombre español en partido.tournament -> tipo canónico
TOURNAMENT_TYPE = {
    "Mundial": "mundial",
    "Clasificatorias": "clasificatorias",
    "Amistoso": "amistoso",
    "Nations League": "nations_league",
    "Eurocopa": "continental",
    "Copa América": "continental",
    "Copa Africana": "continental",
    "Copa Asiática": "continental",
    "Copa Oro": "continental",
    "Copa AFF": "continental",
    "Copa EAFF": "continental",
    "Copa Oceanía": "continental",
    "Juegos del Pacífico": "juegos",
}

# Para torneos que ya existen con nombre inglés, reusamos el Torneo existente
# en lugar de crear uno nuevo con nombre español.
REUSE_EXISTING = {
    "Mundial": "FIFA World Cup",
    "Eurocopa": "UEFA Euro",
    "Copa América": "Copa América",
    "Copa Africana": "African Cup of Nations",
    "Copa Asiática": "AFC Asian Cup",
    "Copa Oro": "Gold Cup",
    "Copa AFF": "AFF Championship",
    "Copa EAFF": "EAFF Championship",
    "Copa Oceanía": "Oceania Nations Cup",
    "Juegos del Pacífico": "Pacific Games",
    "Nations League": "UEFA Nations League",
}


def main():
    engine = get_engine()
    init_db()

    with Session(engine) as session:
        # 1. Obtener torneos existentes
        existing = session.exec(select(Torneo)).all()
        existing_map = {t.nombre_canonico: t for t in existing}

        # 2. Obtener tournaments únicos sin torneo_id
        rows = session.execute(sqltext(
            "SELECT DISTINCT tournament FROM partido WHERE torneo_id IS NULL AND tournament IS NOT NULL"
        )).fetchall()
        tournaments = [r[0] for r in rows]
        logger.info("Tournaments huérfanos: %s", tournaments)

        # 3. Resolver torneo destino para cada tournament huérfano
        #    - Si está en REUSE_EXISTING, apuntar al Torneo inglés existente
        #    - Si ya existe en la DB con ese nombre, usarlo
        #    - Si no, crear Torneo nuevo
        target = {}  # tournament_name -> torneo_id
        created = 0

        for name in sorted(tournaments):
            # Reuse existing English torneo?
            eng_name = REUSE_EXISTING.get(name)
            if eng_name and eng_name in existing_map:
                target[name] = existing_map[eng_name].id
                logger.info("  %s → reusa torneo existente '%s' (id=%d)", name, eng_name, existing_map[eng_name].id)
                continue

            # Already exists with same name?
            if name in existing_map:
                target[name] = existing_map[name].id
                logger.info("  %s → ya existe (id=%d)", name, existing_map[name].id)
                continue

            # Create new
            tipo = TOURNAMENT_TYPE.get(name, "otro")
            torneo = Torneo(nombre_canonico=name, tipo=tipo, categoria="seleccion")
            session.add(torneo)
            session.flush()
            existing_map[name] = torneo
            target[name] = torneo.id
            created += 1
            logger.info("  Torneo creado: %s (tipo=%s, id=%d)", name, tipo, torneo.id)

        session.commit()
        logger.info("Torneos creados: %d", created)

        # 4. Actualizar torneo_id en partidos
        updated = 0
        for name, tid in target.items():
            r = session.execute(
                sqltext("UPDATE partido SET torneo_id = :tid WHERE torneo_id IS NULL AND tournament = :t"),
                {"tid": tid, "t": name}
            )
            updated += r.rowcount
            logger.info("  %s → torneo_id=%d (%d partidos)", name, tid, r.rowcount)

        session.commit()
        logger.info("Total partidos actualizados: %d", updated)

        # 5. Verificar
        remaining = session.execute(sqltext(
            "SELECT COUNT(*) FROM partido WHERE torneo_id IS NULL"
        )).scalar_one()
        logger.info("Partidos aún sin torneo_id: %d", remaining)


if __name__ == "__main__":
    main()
