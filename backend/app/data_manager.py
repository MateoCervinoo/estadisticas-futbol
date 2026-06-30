import os
import pandas as pd
from sqlmodel import select
from app.db.session import Session, engine
from app.models import Partido, Equipo
from app.data_mapper import normalize_status
import logging
import numpy as np
from app.services.data_normalization_service import (
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
MUNDIAL_2026_START = "2026-06-11"

# Rutas relativas dentro del contenedor Docker.
# Allow overriding the historical CSV path via CSV_DATA_PATH environment variable
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_RESULTS = os.path.join(BASE_DIR, "data", "results.csv")
DEFAULT_SHOOTOUTS = os.path.join(BASE_DIR, "data", "shootouts.csv")

# CSV_DATA_PATH may point to a single combined historical dataset (recommended)
RESULTS_PATH = os.getenv("CSV_DATA_PATH", DEFAULT_RESULTS)
SHOOTOUTS_PATH = os.getenv("CSV_SHOOTOUTS_PATH", DEFAULT_SHOOTOUTS)

def load_historical_data(since_year=2022):
    """
    Carga y limpia el historial de partidos desde el archivo results.csv.
    Combina la información de tandas de penales si el partido fue eliminatorio.
    """
    # Diagnóstico: listar contenido de /app/data/ y de las rutas relevantes para ayudar a detectar montajes Docker
    try:
        app_data_dir = "/app/data"
        logger.info(f"BASE_DIR={BASE_DIR} cwd={os.getcwd()} RESULTS_PATH={RESULTS_PATH}")
        logger.info(f"Contenido de /app/data/: {os.listdir(app_data_dir) if os.path.exists(app_data_dir) else 'Carpeta no existe'}")
        base_data_dir = os.path.join(BASE_DIR, "data")
        logger.info(f"Contenido de {base_data_dir}: {os.listdir(base_data_dir) if os.path.exists(base_data_dir) else 'Carpeta no existe'}")
    except Exception:
        logger.exception("No se pudo listar directorios para diagnóstico de data/")

    # Construir una lista de rutas candidatas para results.csv para mayor flexibilidad en entornos Docker
    candidates = []
    # Preferir variable de entorno explícita
    env_path = os.getenv("CSV_DATA_PATH")
    if env_path:
        candidates.append(env_path)

    # Ruta por defecto construida a partir del paquete
    candidates.append(RESULTS_PATH)

    # Posibles rutas de montaje en contenedores
    candidates.append("/app/data/results.csv")
    candidates.append(os.path.join(os.getcwd(), "backend", "app", "data", "results.csv"))
    candidates.append(os.path.join(os.getcwd(), "app", "data", "results.csv"))
    candidates.append(os.path.join(os.getcwd(), "data", "results.csv"))

    # Buscar archivos .csv en los directorios típicos y añadir coincidencias
    probe_dirs = [app_data_dir, base_data_dir, os.path.join(os.getcwd(), "data"), os.path.join(os.getcwd(), "backend", "app", "data")]
    for d in probe_dirs:
        try:
            if os.path.exists(d) and os.path.isdir(d):
                for f in os.listdir(d):
                    if f.lower().endswith("results.csv") or f.lower().endswith(".csv"):
                        candidates.append(os.path.join(d, f))
        except Exception:
            # no bloquear por errores de listing
            logger.debug("No se pudo inspeccionar directorio %s", d)

    # Deduplicar manteniendo orden
    seen = set()
    candidates2 = []
    for c in candidates:
        if c and c not in seen:
            candidates2.append(c)
            seen.add(c)
    candidates = candidates2

    # Seleccionar la primera ruta válida
    chosen = None
    for c in candidates:
        try:
            if c and os.path.exists(c) and os.path.isfile(c):
                chosen = c
                break
        except Exception:
            continue

    if not chosen:
        # Información de diagnóstico para debugging en logs/errores
        diag = {
            "candidates_tried": candidates,
            "cwd": os.getcwd(),
            "base_dir": BASE_DIR,
            "app_data_exists": os.path.exists(app_data_dir),
            "base_data_exists": os.path.exists(base_data_dir),
        }
        raise FileNotFoundError(f"No se encontró el archivo histórico. Intentadas rutas: {candidates}. Diagnóstico: {diag}")

    logger.info("Usando archivo histórico: %s", chosen)

    # 1. Leer partidos históricos
    # Permitimos que el CSV venga con nombres de columnas distintos; se espera
    # al menos: date, home_team, away_team, home_score, away_score. El campo
    # 'neutral' es opcional y se añadirá con False si falta.
    df = pd.read_csv(chosen)
    df["date"] = pd.to_datetime(df["date"])

    # Filtramos para usar el ciclo moderno (Volumen óptimo para Dixon-Coles)
    df = df[df["date"] >= f"{since_year}-01-01"].copy()

    # Asegurarnos de que existan las columnas mínimas esperadas por el modelo
    # Si falta 'neutral', la asumimos como False (no neutral)
    if 'neutral' not in df.columns:
        df['neutral'] = False

    required = {'date', 'home_team', 'away_team', 'home_score', 'away_score', 'neutral'}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"El CSV histórico debe contener las columnas: {', '.join(sorted(required))}. Faltan: {', '.join(sorted(missing))}")

    # 2. Auditoría de datos: separar registros sanos y corruptos
    # Reglas estrictas:
    #  - home_team y away_team no deben ser nulos ni cadenas vacías
    #  - home_score y away_score deben ser numéricos enteros y no negativos
    #  - date no debe ser nulo
    try:
        # Normalizar temporalmente los scores para validar
        home_scores_num = pd.to_numeric(df['home_score'], errors='coerce')
        away_scores_num = pd.to_numeric(df['away_score'], errors='coerce')

        names_ok = df['home_team'].notna() & df['away_team'].notna() & \
                   df['home_team'].astype(str).str.strip().ne('') & df['away_team'].astype(str).str.strip().ne('')

        scores_ok = home_scores_num.notna() & away_scores_num.notna() & \
                    np.isfinite(home_scores_num) & np.isfinite(away_scores_num) & \
                    (home_scores_num >= 0) & (away_scores_num >= 0) & \
                    ((home_scores_num % 1) == 0) & ((away_scores_num % 1) == 0)

        date_ok = df['date'].notna()

        mask_sano = names_ok & scores_ok & date_ok
        df_sanos = df[mask_sano].copy()
        df_corruptos = df[~mask_sano].copy()

        # Si hay corruptos, exportarlos para auditoría y advertir en logs
        if not df_corruptos.empty:
            bad_path = os.path.join('/', 'app', 'data', 'bad_records.csv')
            os.makedirs(os.path.dirname(bad_path), exist_ok=True)
            try:
                df_corruptos.to_csv(bad_path, index=False)
                logger.warning(f"Se detectaron %d registros inválidos. Ver en %s", len(df_corruptos), bad_path)
            except Exception:
                logger.exception("No se pudo exportar bad_records.csv para auditoría")

        # Reemplazamos df por df_sanos para que el resto del pipeline solo trabaje con datos válidos
        df = df_sanos
    except Exception:
        # Si la auditoría falla de forma inesperada, no bloqueamos la carga; dejamos el df original
        logger.exception("Error durante la auditoría de datos. Se continuará con el dataset original sin separar corruptos.")

    if "tournament" in df.columns:
        world_cup_mask = df["tournament"].astype(str).str.lower().str.contains("world cup|mundial", na=False)
        before_filter = len(df)
        df = df[~(world_cup_mask & (df["date"] >= MUNDIAL_2026_START))].copy()
        filtered = before_filter - len(df)
        if filtered:
            logger.info("Partidos del Mundial 2026 omitidos del histórico: %d", filtered)

    # 3. Leer y acoplar tandas de penales (shootouts) si existen
    if os.path.exists(SHOOTOUTS_PATH):
        df_shootouts = pd.read_csv(SHOOTOUTS_PATH)
        df_shootouts["date"] = pd.to_datetime(df_shootouts["date"])

        # Combinamos por fecha y equipos para saber quién ganó en penales si hubo empate
        df = pd.merge(
            df,
            df_shootouts[["date", "home_team", "away_team", "winner"]],
            on=["date", "home_team", "away_team"],
            how="left"
        )
        df["penalty_winner"] = df["winner"]
        df.drop(columns=["winner"], inplace=True)
    else:
        df["penalty_winner"] = None

    return df

def get_combined_dataset():
    """
    Une el dataset histórico del .csv con los partidos en vivo
    del Mundial 2026 guardados en la base de datos PostgreSQL.
    """
    # Cargamos la base histórica de los últimos años
    df_historical = load_historical_data()

    # Seleccionamos solo las columnas esenciales para el modelo matemático
    columns_needed = ["date", "home_team", "away_team", "home_score", "away_score", "neutral"]
    df_historical = df_historical[columns_needed].dropna()

    # TODO: En el próximo módulo, acá haremos un SELECT de los partidos finalizados
    # de PostgreSQL y los sumaremos con pd.concat() para tener el "en vivo".

    return df_historical


def ingest_historical_to_db(since_year: int = 2018, batch_size: int = 1000):
    """
    Ingresa los partidos del CSV histórico en la tabla Partido de PostgreSQL.

    - Lee RESULTS_PATH (puede ser sobreescrito por CSV_DATA_PATH)
    - Filtra desde since_year-01-01
    - Calcula un fixture_id determinístico por fila
    - Realiza upsert (buscar por fixture_id => actualizar o crear)

    Esta función está pensada para ejecutarse en el evento de startup del servidor.
    """
    # Cargamos el dataset filtrado
    df = load_historical_data(since_year=since_year)

    # Minimizar columnas tratadas; asegurarnos de que exista 'tournament'
    if 'tournament' not in df.columns:
        # Fallback: el CSV debería tener columna tournament, pero si falta,
        # canonical_tournament_name('') devuelve 'Otro'.
        df['tournament'] = ''

    world_cup_mask = df["tournament"].astype(str).str.lower().str.contains("world cup|mundial", na=False)
    before_filter = len(df)
    df = df[~(world_cup_mask & (df["date"] >= MUNDIAL_2026_START))].copy()
    filtered = before_filter - len(df)
    if filtered:
        logger.info("Partidos del Mundial 2026 omitidos de la ingesta histórica: %d", filtered)

    cols = ["date", "home_team", "away_team", "home_score", "away_score", "neutral", "tournament"]
    df = df[cols].copy()

    # Normalizar tipos básicos
    df["home_score"] = pd.to_numeric(df["home_score"], errors="coerce").fillna(0).astype(int)
    df["away_score"] = pd.to_numeric(df["away_score"], errors="coerce").fillna(0).astype(int)

    def make_hash_dedupe(row):
        return build_hash_dedupe(
            row["date"],
            row.get("home_team"),
            row.get("away_team"),
            row.get("tournament"),
        )

    df["hash_dedupe"] = df.apply(make_hash_dedupe, axis=1)
    df["fixture_id_externo"] = df["hash_dedupe"]

    total = len(df)
    logger.info("Iniciando ingesta de %d partidos históricos (desde %d)", total, since_year)

    # Upsert por batches
    inserted = 0
    with Session(engine) as session:
        for idx, row in df.iterrows():
            hash_dedupe = row["hash_dedupe"]
            tournament = row.get("tournament")
            tournament_name = canonical_tournament_name(tournament)
            home_team = canonical_team_name(row["home_team"])
            away_team = canonical_team_name(row["away_team"])
            home_team_id = resolve_equipo_id(session, home_team, "nombre_csv", "seleccion")
            away_team_id = resolve_equipo_id(session, away_team, "nombre_csv", "seleccion")
            torneo_id = resolve_torneo_id(session, tournament, "seleccion")
            validation_errors = validate_partido_values(row["date"], home_team, away_team, home_team_id, away_team_id, torneo_id, None, hash_dedupe)
            if validation_errors:
                logger.warning("Fila histórica inválida idx=%s hash=%s: %s", idx, hash_dedupe, ",".join(validation_errors))
                continue

            existing, conflict = find_partido_for_upsert(session, None, hash_dedupe)
            if conflict:
                logger.warning("Conflicto histórico fixture/hash idx=%s hash=%s", idx, hash_dedupe)
                continue

            tipo_dato = classify_tipo_dato("csv_historical", normalize_status("FINISHED", source="csv"), row["date"])
            if existing:
                existing.fecha_utc = row["date"]
                existing.home_team = home_team
                existing.away_team = away_team
                existing.goles_local = int(row["home_score"]) if pd.notna(row["home_score"]) else None
                existing.goles_visitante = int(row["away_score"]) if pd.notna(row["away_score"]) else None
                existing.estado = normalize_status("FINISHED", source="csv")
                existing.hash_dedupe = hash_dedupe
                existing.fixture_id_externo = row["fixture_id_externo"]
                existing.tipo_dato = tipo_dato
                if home_team_id is not None:
                    existing.equipo_local_id = home_team_id
                if away_team_id is not None:
                    existing.equipo_visitante_id = away_team_id
                if torneo_id is not None:
                    existing.torneo_id = torneo_id
                existing.tournament = tournament_name
                session.add(existing)
            else:
                nuevo = Partido(
                    fixture_id=None,
                    fixture_id_externo=row["fixture_id_externo"],
                    fecha_utc=row["date"],
                    home_team=home_team,
                    away_team=away_team,
                    equipo_local_id=home_team_id,
                    equipo_visitante_id=away_team_id,
                    goles_local=int(row["home_score"]) if pd.notna(row["home_score"]) else None,
                    goles_visitante=int(row["away_score"]) if pd.notna(row["away_score"]) else None,
                    estado=normalize_status("FINISHED", source="csv"),
                    fuente_origen="csv_historical",
                    tipo_dato=tipo_dato,
                    hash_dedupe=hash_dedupe,
                    torneo_id=torneo_id,
                    tournament=tournament_name,
                )
                session.add(nuevo)

            inserted += 1

            # Commit por batch para no consumir demasiada memoria/locks
            if inserted % batch_size == 0:
                session.commit()

        # Commit final
        session.commit()

    logger.info("Ingesta histórica finalizada. Total procesados: %d", total)


def seed_equipos_if_empty():
    """Puebla la tabla Equipo con selecciones principales si está vacía.

    Usa nombres en español, posibles nombres en la API y en el CSV, y códigos de bandera
    que coincidan con el frontend (p. ej. 'ar', 'br', 'fr').
    """
    ejemplos = [
        {"nombre_es": "Argentina", "nombre_api": "Argentina", "nombre_csv": "Argentina", "codigo_bandera": "ar"},
        {"nombre_es": "Brasil", "nombre_api": "Brazil", "nombre_csv": "Brazil", "codigo_bandera": "br"},
        {"nombre_es": "Francia", "nombre_api": "France", "nombre_csv": "France", "codigo_bandera": "fr"},
        {"nombre_es": "Alemania", "nombre_api": "Germany", "nombre_csv": "Germany", "codigo_bandera": "de"},
        {"nombre_es": "España", "nombre_api": "Spain", "nombre_csv": "Spain", "codigo_bandera": "es"},
        {"nombre_es": "Uruguay", "nombre_api": "Uruguay", "nombre_csv": "Uruguay", "codigo_bandera": "uy"},
        {"nombre_es": "Islandia", "nombre_api": "Iceland", "nombre_csv": "Iceland", "codigo_bandera": "is"},
        {"nombre_es": "Corea del Sur", "nombre_api": "South Korea", "nombre_csv": "South Korea", "codigo_bandera": "kr"},
        # Añadir más según sea necesario
    ]

    with Session(engine) as session:
        existing = session.exec(select(Equipo)).first()
        if existing:
            logger.info("Tabla Equipo ya poblada; seed omitido.")
            return

        logger.info("Poblando tabla Equipo con selecciones de ejemplo...")
        for e in ejemplos:
            equipo = Equipo(
                nombre_canonico=e["nombre_api"],
                nombre_es=e["nombre_es"],
                nombre_api=e.get("nombre_api"),
                nombre_csv=e.get("nombre_csv"),
                codigo_bandera=e.get("codigo_bandera"),
            )
            session.add(equipo)
        session.commit()
        logger.info("Seed de Equipo completado.")


if __name__ == "__main__":
    # Test rápido de ejecución local
    try:
        data = get_combined_dataset()
        print(f"📊 Dataset cargado con éxito. Total de partidos para el modelo: {len(data)}")
        print(data.head())
    except Exception as e:
        print(f"❌ Error al cargar los datos: {e}")
