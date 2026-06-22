"""
Módulo de scraping / actualización de partidos.

Por ahora contiene funciones que generan datos simulados y el esqueleto
para usar BeautifulSoup si se conecta a una fuente real.

La función `actualizar_partidos_post_partido` está pensada para ejecutarse
varias veces al día (scheduler) y procesar partidos cuya fecha ya pasó y
que aún no están finalizados.
"""
from typing import List
from datetime import datetime
import random
from bs4 import BeautifulSoup
import requests
from sqlmodel import Session, select

from .models import Partido, EstadisticasPartido
from .database import engine


def _scrape_match_stats_external(match_url: str) -> dict:
    """Esqueleto: conecta a `match_url`, parsea con BeautifulSoup y retorna
    estadísticas clave. Por ahora devuelve datos simulados.
    """
    # Ejemplo de uso real (comentado):
    # resp = requests.get(match_url, timeout=10)
    # soup = BeautifulSoup(resp.text, "html.parser")
    # extraer xG, remates, posesion, etc.

    # Simulamos datos para demostrar la estructura
    return {
        "goles_local": random.randint(0, 4),
        "goles_visitante": random.randint(0, 4),
        "xg_local": round(random.uniform(0, 3), 2),
        "xg_visitante": round(random.uniform(0, 3), 2),
        "remates_local": random.randint(2, 20),
        "remates_visitante": random.randint(2, 20),
        "posesion_local": round(random.uniform(30, 70), 1),
        "posesion_visitante": round(random.uniform(30, 70), 1),
        "corners_local": random.randint(0, 10),
        "corners_visitante": random.randint(0, 10),
    }


def actualizar_partidos_post_partido():
    """Busca partidos cuya fecha ya pasó (<= ahora) y que estén en estado
    'programado', los procesa como si hubieran finalizado: obtiene datos
    (scraping o simulados), actualiza goles y guarda estadísticas.

    Diseñado para ejecutarse periódicamente (p. ej. 4 veces/día).
    """
    ahora = datetime.utcnow()
    with Session(engine) as session:
        stmt = select(Partido).where(Partido.fecha <= ahora, Partido.estado == "programado")
        resultados = session.exec(stmt).all()
        for partido in resultados:
            # En una implementación real usaríamos un match_url almacenado o
            # construido con IDs; aquí usamos el ID sólo para generar datos
            datos = _scrape_match_stats_external(f"https://example.com/match/{partido.id}")

            partido.goles_local = datos["goles_local"]
            partido.goles_visitante = datos["goles_visitante"]
            partido.estado = "finalizado"

            # Guardar estadísticas
            stats = EstadisticasPartido(
                partido_id=partido.id,
                xg_local=datos["xg_local"],
                xg_visitante=datos["xg_visitante"],
                remates_local=datos["remates_local"],
                remates_visitante=datos["remates_visitante"],
                posesion_local=datos["posesion_local"],
                posesion_visitante=datos["posesion_visitante"],
                corners_local=datos["corners_local"],
                corners_visitante=datos["corners_visitante"],
            )
            session.add(stats)
            session.add(partido)
        session.commit()


if __name__ == "__main__":
    # Para pruebas rápidas
    actualizar_partidos_post_partido()
