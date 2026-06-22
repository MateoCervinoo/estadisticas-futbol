import os
import pandas as pd
from sqlmodel import Session, select
# Importamos el engine de tu base de datos para cuando sumemos los partidos en vivo
from app.database import engine

# Rutas relativas dentro del contenedor Docker
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_PATH = os.path.join(BASE_DIR, "data", "results.csv")
SHOOTOUTS_PATH = os.path.join(BASE_DIR, "data", "shootouts.csv")

def load_historical_data(since_year=2022):
    """
    Carga y limpia el historial de partidos desde el archivo results.csv.
    Combina la información de tandas de penales si el partido fue eliminatorio.
    """
    if not os.path.exists(RESULTS_PATH):
        raise FileNotFoundError(f"No se encontró el archivo histórico en: {RESULTS_PATH}")

    # 1. Leer partidos históricos
    df = pd.read_csv(RESULTS_PATH)
    df["date"] = pd.to_datetime(df["date"])

    # Filtramos para usar el ciclo moderno (Volumen óptimo para Dixon-Coles)
    df = df[df["date"] >= f"{since_year}-01-01"].copy()

    # 2. Leer y acoplar tandas de penales (shootouts) si existen
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

if __name__ == "__main__":
    # Test rápido de ejecución local
    try:
        data = get_combined_dataset()
        print(f"📊 Dataset cargado con éxito. Total de partidos para el modelo: {len(data)}")
        print(data.head())
    except Exception as e:
        print(f"❌ Error al cargar los datos: {e}")