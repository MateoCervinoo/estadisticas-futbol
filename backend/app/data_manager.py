import os
import pandas as pd
from sqlmodel import Session, select
# Importamos el engine de tu base de datos para cuando sumemos los partidos en vivo
from app.database import engine
from app.models import Partido, Equipo
from app.data_mapper import normalize_tournament, normalize_status
import hashlib
import logging
import numpy as np

logger = logging.getLogger(__name__)

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
        # normalize_tournament('') devuelve 'Amistoso'
        df['tournament'] = ''

    cols = ["date", "home_team", "away_team", "home_score", "away_score", "neutral", "tournament"]
    df = df[cols].copy()

    # Normalizar tipos básicos
    df["home_score"] = pd.to_numeric(df["home_score"], errors="coerce").fillna(0).astype(int)
    df["away_score"] = pd.to_numeric(df["away_score"], errors="coerce").fillna(0).astype(int)

    # Generar fixture_id determinístico usando md5 sobre fecha+equipos+torneo
    def make_fixture_id(row):
        tournament = row.get('tournament', '')
        key = f"{row['date'].isoformat()}|{row['home_team']}|{row['away_team']}|{tournament}"
        md = hashlib.md5(key.encode("utf-8")).hexdigest()
        # Reducir a rango de enteros 32-bit para mayor compatibilidad
        return int(md, 16) % (2 ** 31 - 1)

    df["fixture_id"] = df.apply(make_fixture_id, axis=1)

    total = len(df)
    logger.info("Iniciando ingesta de %d partidos históricos (desde %d)", total, since_year)

    # Upsert por batches
    inserted = 0
    with Session(engine) as session:
        for idx, row in df.iterrows():
            fid = int(row["fixture_id"])
            # Intentar mapear home/away a los IDs de Equipo usando nombre_csv
            home_team_id = None
            away_team_id = None
            try:
                home_lookup = session.exec(select(Equipo).where(Equipo.nombre_csv == row["home_team"])).first()
                if home_lookup:
                    home_team_id = home_lookup.id
                away_lookup = session.exec(select(Equipo).where(Equipo.nombre_csv == row["away_team"])).first()
                if away_lookup:
                    away_team_id = away_lookup.id
            except Exception:
                # No bloquear la ingesta si la tabla Equipo no existe aún
                home_team_id = None
                away_team_id = None
            # Buscar partido existente por fixture_id
            existing = session.exec(select(Partido).where(Partido.fixture_id == fid)).first()
            if existing:
                existing.fecha_utc = row["date"]
                existing.home_team = row["home_team"]
                existing.away_team = row["away_team"]
                existing.goles_local = int(row["home_score"]) if pd.notna(row["home_score"]) else None
                existing.goles_visitante = int(row["away_score"]) if pd.notna(row["away_score"]) else None
                existing.estado = normalize_status("FINISHED", source="csv")
                if 'tournament' in row.index:
                    existing.tournament = normalize_tournament(row.get('tournament'))
                if home_team_id is not None:
                    existing.equipo_local_id = home_team_id
                if away_team_id is not None:
                    existing.equipo_visitante_id = away_team_id
                session.add(existing)
            else:
                nuevo = Partido(
                    fixture_id=fid,
                    fecha_utc=row["date"],
                    home_team=row["home_team"],
                    away_team=row["away_team"],
                    equipo_local_id=home_team_id,
                    equipo_visitante_id=away_team_id,
                    goles_local=int(row["home_score"]) if pd.notna(row["home_score"]) else None,
                    goles_visitante=int(row["away_score"]) if pd.notna(row["away_score"]) else None,
                    estado=normalize_status("FINISHED", source="csv"),
                    fuente_origen="csv_historical",
                )
                if 'tournament' in row.index:
                    nuevo.tournament = normalize_tournament(row.get('tournament'))
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
