#!/usr/bin/env python3
"""Puebla la tabla Equipo con todos los equipos del CSV histórico.

Lee results.csv, extrae nombres únicos, y para cada uno crea un registro
en la tabla Equipo con nombre_canonico = nombre_csv. Para los equipos
conocidos (~100 selecciones + clubs) incluye aliases para FBref, Understat,
API-Football y códigos ISO/bandera.

Uso:
    python -m entrenador.utils.populate_teams
"""
from __future__ import annotations
import logging
import os
from pathlib import Path
from typing import Dict, Optional

import pandas as pd
from sqlmodel import Session, select, func

# Necesitamos importar desde shared.models para que SQLModel vea todas las tablas
import sys
_SHARED = Path(__file__).resolve().parent.parent.parent / "shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

from entrenador.config import settings
from entrenador.database import get_engine, init_db
from shared.models import Equipo, Torneo

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("populate_teams")

# Mapeo manual para equipos conocidos (selecciones + clubs principales)
# Formato: nombre_csv -> {fbref, understat, api_football, iso, bandera}
TEAM_ALIASES: Dict[str, dict] = {
    # === Selecciones - Mundialistas frecuentes ===
    "Argentina": {"fbref": "Argentina", "understat": "Argentina", "api": "Argentina", "iso": "ARG", "bandera": "ar"},
    "Brazil": {"fbref": "Brazil", "understat": "Brazil", "api": "Brazil", "iso": "BRA", "bandera": "br"},
    "France": {"fbref": "France", "understat": "France", "api": "France", "iso": "FRA", "bandera": "fr"},
    "Germany": {"fbref": "Germany", "understat": "Germany", "api": "Germany", "iso": "DEU", "bandera": "de"},
    "Spain": {"fbref": "Spain", "understat": "Spain", "api": "Spain", "iso": "ESP", "bandera": "es"},
    "England": {"fbref": "England", "understat": "England", "api": "England", "iso": "ENG", "bandera": "gb-eng"},
    "Italy": {"fbref": "Italy", "understat": "Italy", "api": "Italy", "iso": "ITA", "bandera": "it"},
    "Netherlands": {"fbref": "Netherlands", "understat": "Netherlands", "api": "Netherlands", "iso": "NLD", "bandera": "nl"},
    "Portugal": {"fbref": "Portugal", "understat": "Portugal", "api": "Portugal", "iso": "PRT", "bandera": "pt"},
    "Belgium": {"fbref": "Belgium", "understat": "Belgium", "api": "Belgium", "iso": "BEL", "bandera": "be"},
    "Uruguay": {"fbref": "Uruguay", "understat": "Uruguay", "api": "Uruguay", "iso": "URY", "bandera": "uy"},
    "Croatia": {"fbref": "Croatia", "understat": "Croatia", "api": "Croatia", "iso": "HRV", "bandera": "hr"},
    "Denmark": {"fbref": "Denmark", "understat": "Denmark", "api": "Denmark", "iso": "DNK", "bandera": "dk"},
    "Switzerland": {"fbref": "Switzerland", "understat": "Switzerland", "api": "Switzerland", "iso": "CHE", "bandera": "ch"},
    "Mexico": {"fbref": "Mexico", "understat": "Mexico", "api": "Mexico", "iso": "MEX", "bandera": "mx"},
    "Japan": {"fbref": "Japan", "understat": "Japan", "api": "Japan", "iso": "JPN", "bandera": "jp"},
    "South Korea": {"fbref": "South Korea", "understat": "Korea Republic", "api": "South Korea", "iso": "KOR", "bandera": "kr"},
    "USA": {"fbref": "United States", "understat": "USA", "api": "USA", "iso": "USA", "bandera": "us"},
    "Colombia": {"fbref": "Colombia", "understat": "Colombia", "api": "Colombia", "iso": "COL", "bandera": "co"},
    "Chile": {"fbref": "Chile", "understat": "Chile", "api": "Chile", "iso": "CHL", "bandera": "cl"},
    "Paraguay": {"fbref": "Paraguay", "understat": "Paraguay", "api": "Paraguay", "iso": "PRY", "bandera": "py"},
    "Peru": {"fbref": "Peru", "understat": "Peru", "api": "Peru", "iso": "PER", "bandera": "pe"},
    "Ecuador": {"fbref": "Ecuador", "understat": "Ecuador", "api": "Ecuador", "iso": "ECU", "bandera": "ec"},
    "Venezuela": {"fbref": "Venezuela", "understat": "Venezuela", "api": "Venezuela", "iso": "VEN", "bandera": "ve"},
    "Bolivia": {"fbref": "Bolivia", "understat": "Bolivia", "api": "Bolivia", "iso": "BOL", "bandera": "bo"},
    "Sweden": {"fbref": "Sweden", "understat": "Sweden", "api": "Sweden", "iso": "SWE", "bandera": "se"},
    "Norway": {"fbref": "Norway", "understat": "Norway", "api": "Norway", "iso": "NOR", "bandera": "no"},
    "Poland": {"fbref": "Poland", "understat": "Poland", "api": "Poland", "iso": "POL", "bandera": "pl"},
    "Austria": {"fbref": "Austria", "understat": "Austria", "api": "Austria", "iso": "AUT", "bandera": "at"},
    "Czech Republic": {"fbref": "Czech Republic", "understat": "Czech Republic", "api": "Czech Republic", "iso": "CZE", "bandera": "cz"},
    "Russia": {"fbref": "Russia", "understat": "Russia", "api": "Russia", "iso": "RUS", "bandera": "ru"},
    "Turkey": {"fbref": "Turkey", "understat": "Turkey", "api": "Turkey", "iso": "TUR", "bandera": "tr"},
    "Ukraine": {"fbref": "Ukraine", "understat": "Ukraine", "api": "Ukraine", "iso": "UKR", "bandera": "ua"},
    "Scotland": {"fbref": "Scotland", "understat": "Scotland", "api": "Scotland", "iso": "SCO", "bandera": "gb-sct"},
    "Serbia": {"fbref": "Serbia", "understat": "Serbia", "api": "Serbia", "iso": "SRB", "bandera": "rs"},
    "Nigeria": {"fbref": "Nigeria", "understat": "Nigeria", "api": "Nigeria", "iso": "NGA", "bandera": "ng"},
    "Senegal": {"fbref": "Senegal", "understat": "Senegal", "api": "Senegal", "iso": "SEN", "bandera": "sn"},
    "Ghana": {"fbref": "Ghana", "understat": "Ghana", "api": "Ghana", "iso": "GHA", "bandera": "gh"},
    "Cameroon": {"fbref": "Cameroon", "understat": "Cameroon", "api": "Cameroon", "iso": "CMR", "bandera": "cm"},
    "Ivory Coast": {"fbref": "Ivory Coast", "understat": "Ivory Coast", "api": "Ivory Coast", "iso": "CIV", "bandera": "ci"},
    "Morocco": {"fbref": "Morocco", "understat": "Morocco", "api": "Morocco", "iso": "MAR", "bandera": "ma"},
    "Egypt": {"fbref": "Egypt", "understat": "Egypt", "api": "Egypt", "iso": "EGY", "bandera": "eg"},
    "Algeria": {"fbref": "Algeria", "understat": "Algeria", "api": "Algeria", "iso": "DZA", "bandera": "dz"},
    "Tunisia": {"fbref": "Tunisia", "understat": "Tunisia", "api": "Tunisia", "iso": "TUN", "bandera": "tn"},
    "South Africa": {"fbref": "South Africa", "understat": "South Africa", "api": "South Africa", "iso": "ZAF", "bandera": "za"},
    "Saudi Arabia": {"fbref": "Saudi Arabia", "understat": "Saudi Arabia", "api": "Saudi Arabia", "iso": "SAU", "bandera": "sa"},
    "Iran": {"fbref": "Iran", "understat": "Iran", "api": "Iran", "iso": "IRN", "bandera": "ir"},
    "Australia": {"fbref": "Australia", "understat": "Australia", "api": "Australia", "iso": "AUS", "bandera": "au"},
    "China": {"fbref": "China", "understat": "China", "api": "China", "iso": "CHN", "bandera": "cn"},
    "Wales": {"fbref": "Wales", "understat": "Wales", "api": "Wales", "iso": "WAL", "bandera": "gb-wls"},
    "Ireland": {"fbref": "Republic of Ireland", "understat": "Republic of Ireland", "api": "Ireland", "iso": "IRL", "bandera": "ie"},
    "Northern Ireland": {"fbref": "Northern Ireland", "understat": "Northern Ireland", "api": "Northern Ireland", "iso": "NIR", "bandera": "gb-nir"},
    "Iceland": {"fbref": "Iceland", "understat": "Iceland", "api": "Iceland", "iso": "ISL", "bandera": "is"},
    "Greece": {"fbref": "Greece", "understat": "Greece", "api": "Greece", "iso": "GRC", "bandera": "gr"},
    "Romania": {"fbref": "Romania", "understat": "Romania", "api": "Romania", "iso": "ROU", "bandera": "ro"},
    "Hungary": {"fbref": "Hungary", "understat": "Hungary", "api": "Hungary", "iso": "HUN", "bandera": "hu"},
    "Bulgaria": {"fbref": "Bulgaria", "understat": "Bulgaria", "api": "Bulgaria", "iso": "BGR", "bandera": "bg"},
    "Slovakia": {"fbref": "Slovakia", "understat": "Slovakia", "api": "Slovakia", "iso": "SVK", "bandera": "sk"},
    "Slovenia": {"fbref": "Slovenia", "understat": "Slovenia", "api": "Slovenia", "iso": "SVN", "bandera": "si"},
    "Montenegro": {"fbref": "Montenegro", "understat": "Montenegro", "api": "Montenegro", "iso": "MNE", "bandera": "me"},
    "Bosnia and Herzegovina": {"fbref": "Bosnia and Herzegovina", "understat": "Bosnia and Herzegovina", "api": "Bosnia and Herzegovina", "iso": "BIH", "bandera": "ba"},
    "Albania": {"fbref": "Albania", "understat": "Albania", "api": "Albania", "iso": "ALB", "bandera": "al"},
    "Finland": {"fbref": "Finland", "understat": "Finland", "api": "Finland", "iso": "FIN", "bandera": "fi"},
    "North Macedonia": {"fbref": "North Macedonia", "understat": "North Macedonia", "api": "North Macedonia", "iso": "MKD", "bandera": "mk"},
    "Israel": {"fbref": "Israel", "understat": "Israel", "api": "Israel", "iso": "ISR", "bandera": "il"},
    "Costa Rica": {"fbref": "Costa Rica", "understat": "Costa Rica", "api": "Costa Rica", "iso": "CRI", "bandera": "cr"},
    "Honduras": {"fbref": "Honduras", "understat": "Honduras", "api": "Honduras", "iso": "HND", "bandera": "hn"},
    "Panama": {"fbref": "Panama", "understat": "Panama", "api": "Panama", "iso": "PAN", "bandera": "pa"},
    "Jamaica": {"fbref": "Jamaica", "understat": "Jamaica", "api": "Jamaica", "iso": "JAM", "bandera": "jm"},
    "Canada": {"fbref": "Canada", "understat": "Canada", "api": "Canada", "iso": "CAN", "bandera": "ca"},
    "Trinidad and Tobago": {"fbref": "Trinidad and Tobago", "understat": "Trinidad and Tobago", "api": "Trinidad and Tobago", "iso": "TTO", "bandera": "tt"},
    "Haiti": {"fbref": "Haiti", "understat": "Haiti", "api": "Haiti", "iso": "HTI", "bandera": "ht"},
    "Cuba": {"fbref": "Cuba", "understat": "Cuba", "api": "Cuba", "iso": "CUB", "bandera": "cu"},
    # === Clubs (Fase 5) ===
    "Manchester United": {"fbref": "Manchester United", "understat": "Manchester United", "api": "Manchester United", "iso": "ENG", "bandera": "gb-eng"},
    "Manchester City": {"fbref": "Manchester City", "understat": "Manchester City", "api": "Manchester City", "iso": "ENG", "bandera": "gb-eng"},
    "Liverpool": {"fbref": "Liverpool", "understat": "Liverpool", "api": "Liverpool", "iso": "ENG", "bandera": "gb-eng"},
    "Chelsea": {"fbref": "Chelsea", "understat": "Chelsea", "api": "Chelsea", "iso": "ENG", "bandera": "gb-eng"},
    "Arsenal": {"fbref": "Arsenal", "understat": "Arsenal", "api": "Arsenal", "iso": "ENG", "bandera": "gb-eng"},
    "Tottenham": {"fbref": "Tottenham Hotspur", "understat": "Tottenham", "api": "Tottenham Hotspur", "iso": "ENG", "bandera": "gb-eng"},
    "Barcelona": {"fbref": "Barcelona", "understat": "Barcelona", "api": "Barcelona", "iso": "ESP", "bandera": "es"},
    "Real Madrid": {"fbref": "Real Madrid", "understat": "Real Madrid", "api": "Real Madrid", "iso": "ESP", "bandera": "es"},
    "Atletico Madrid": {"fbref": "Atletico Madrid", "understat": "Atletico Madrid", "api": "Atletico Madrid", "iso": "ESP", "bandera": "es"},
    "Bayern Munich": {"fbref": "Bayern Munich", "understat": "Bayern Munich", "api": "Bayern Munich", "iso": "DEU", "bandera": "de"},
    "Borussia Dortmund": {"fbref": "Borussia Dortmund", "understat": "Borussia Dortmund", "api": "Borussia Dortmund", "iso": "DEU", "bandera": "de"},
    "Juventus": {"fbref": "Juventus", "understat": "Juventus", "api": "Juventus", "iso": "ITA", "bandera": "it"},
    "AC Milan": {"fbref": "AC Milan", "understat": "Milan", "api": "AC Milan", "iso": "ITA", "bandera": "it"},
    "Inter Milan": {"fbref": "Inter Milan", "understat": "Inter", "api": "Inter", "iso": "ITA", "bandera": "it"},
    "Paris Saint-Germain": {"fbref": "Paris Saint-Germain", "understat": "PSG", "api": "Paris Saint Germain", "iso": "FRA", "bandera": "fr"},
    "Ajax": {"fbref": "Ajax", "understat": "Ajax", "api": "Ajax", "iso": "NLD", "bandera": "nl"},
    "PSV": {"fbref": "PSV Eindhoven", "understat": "PSV", "api": "PSV", "iso": "NLD", "bandera": "nl"},
    "Benfica": {"fbref": "Benfica", "understat": "Benfica", "api": "Benfica", "iso": "PRT", "bandera": "pt"},
    "Porto": {"fbref": "Porto", "understat": "Porto", "api": "Porto", "iso": "PRT", "bandera": "pt"},
    "Sporting CP": {"fbref": "Sporting CP", "understat": "Sporting CP", "api": "Sporting CP", "iso": "PRT", "bandera": "pt"},
    "Galatasaray": {"fbref": "Galatasaray", "understat": "Galatasaray", "api": "Galatasaray", "iso": "TUR", "bandera": "tr"},
    "Shakhtar Donetsk": {"fbref": "Shakhtar Donetsk", "understat": "Shakhtar Donetsk", "api": "Shakhtar Donetsk", "iso": "UKR", "bandera": "ua"},
    "Dynamo Kyiv": {"fbref": "Dynamo Kyiv", "understat": "Dynamo Kyiv", "api": "Dynamo Kyiv", "iso": "UKR", "bandera": "ua"},
    "Celtic": {"fbref": "Celtic", "understat": "Celtic", "api": "Celtic", "iso": "SCO", "bandera": "gb-sct"},
    "Rangers": {"fbref": "Rangers", "understat": "Rangers", "api": "Rangers", "iso": "SCO", "bandera": "gb-sct"},
}

# Mapeo ISO alpha-3 -> alpha-2 para derivar códigos de bandera
ISO3_TO_ISO2: Dict[str, str] = {
    "ARG": "ar", "BRA": "br", "FRA": "fr", "DEU": "de", "ESP": "es", "ENG": "gb-eng",
    "ITA": "it", "NLD": "nl", "PRT": "pt", "BEL": "be", "URY": "uy", "HRV": "hr",
    "DNK": "dk", "CHE": "ch", "MEX": "mx", "JPN": "jp", "KOR": "kr", "USA": "us",
    "COL": "co", "CHL": "cl", "PRY": "py", "PER": "pe", "ECU": "ec", "SWE": "se",
    "NOR": "no", "POL": "pl", "AUT": "at", "RUS": "ru", "TUR": "tr", "UKR": "ua",
    "SCO": "gb-sct", "SRB": "rs", "NGA": "ng", "SEN": "sn", "GHA": "gh", "CMR": "cm",
    "CIV": "ci", "MAR": "ma", "EGY": "eg", "DZA": "dz", "TUN": "tn", "ZAF": "za",
    "SAU": "sa", "IRN": "ir", "AUS": "au", "CHN": "cn", "WAL": "gb-wls", "IRL": "ie",
    "ISL": "is", "GRC": "gr", "ROU": "ro", "HUN": "hu", "BGR": "bg", "SVK": "sk",
    "SVN": "si", "MNE": "me", "BIH": "ba", "ALB": "al", "FIN": "fi", "ISR": "il",
    "CRI": "cr", "HND": "hn", "PAN": "pa", "JAM": "jm", "CAN": "ca", "BOL": "bo",
    "VEN": "ve", "NIR": "gb-nir", "CZE": "cz",
}

# ISO alpha-3 codes for identifiable countries
COUNTRY_ISO: Dict[str, str] = {
    "Argentina": "ARG", "Brazil": "BRA", "France": "FRA", "Germany": "DEU",
    "Spain": "ESP", "England": "ENG", "Italy": "ITA", "Netherlands": "NLD",
    "Portugal": "PRT", "Belgium": "BEL", "Uruguay": "URY", "Croatia": "HRV",
    "Denmark": "DNK", "Switzerland": "CHE", "Mexico": "MEX", "Japan": "JPN",
    "South Korea": "KOR", "USA": "USA", "Colombia": "COL", "Chile": "CHL",
    "Paraguay": "PRY", "Peru": "PER", "Ecuador": "ECU", "Sweden": "SWE",
    "Norway": "NOR", "Poland": "POL", "Austria": "AUT", "Russia": "RUS",
    "Turkey": "TUR", "Ukraine": "UKR", "Scotland": "SCO", "Serbia": "SRB",
    "Nigeria": "NGA", "Senegal": "SEN", "Ghana": "GHA", "Cameroon": "CMR",
    "Ivory Coast": "CIV", "Morocco": "MAR", "Egypt": "EGY", "Algeria": "DZA",
    "Tunisia": "TUN", "South Africa": "ZAF", "Saudi Arabia": "SAU",
    "Iran": "IRN", "Australia": "AUS", "China": "CHN", "Wales": "WAL",
    "Ireland": "IRL", "Iceland": "ISL", "Greece": "GRC", "Romania": "ROU",
    "Hungary": "HUN", "Bulgaria": "BGR", "Slovakia": "SVK", "Slovenia": "SVN",
    "Montenegro": "MNE", "Bosnia and Herzegovina": "BIH", "Albania": "ALB",
    "Finland": "FIN", "Israel": "ISR", "Costa Rica": "CRI", "Honduras": "HND",
    "Panama": "PAN", "Jamaica": "JAM", "Canada": "CAN", "Bolivia": "BOL",
    "Venezuela": "VEN", "Czech Republic": "CZE", "Northern Ireland": "NIR",
    "United Arab Emirates": "ARE", "Oman": "OMN", "Bahrain": "BHR",
    "Estonia": "EST", "Indonesia": "IDN", "Moldova": "MDA",
    "Azerbaijan": "AZE", "Latvia": "LVA", "Sierra Leone": "SLE",
    "Andorra": "AND", "Liechtenstein": "LIE", "Antigua and Barbuda": "ATG",
    "Bermuda": "BMU", "Belarus": "BLR", "Lithuania": "LTU", "Georgia": "GEO",
    "Armenia": "ARM", "Kazakhstan": "KAZ", "Luxembourg": "LUX",
    "Faroe Islands": "FRO", "Malta": "MLT", "Cyprus": "CYP",
    "San Marino": "SMR", "Gibraltar": "GIB", "Kosovo": "XKX",
    "New Zealand": "NZL", "Thailand": "THA", "Vietnam": "VNM",
    "Iraq": "IRQ", "Syria": "SYR", "Jordan": "JOR", "Lebanon": "LBN",
    "Kuwait": "KWT", "Qatar": "QAT", "Yemen": "YEM",
    "India": "IND", "Pakistan": "PAK", "Bangladesh": "BGD",
    "Sri Lanka": "LKA", "Myanmar": "MMR", "Malaysia": "MYS",
    "Philippines": "PHL", "Singapore": "SGP", "Hong Kong": "HKG",
    "North Korea": "PRK", "Mongolia": "MNG", "Taiwan": "TWN",
    "Palestine": "PSE", "Uzbekistan": "UZB", "Turkmenistan": "TKM",
    "Tajikistan": "TJK", "Kyrgyzstan": "KGZ", "Afghanistan": "AFG",
    "Nepal": "NPL", "Maldives": "MDV", "Bhutan": "BTN",
    "Korea Republic": "KOR", "Congo": "COG", "Congo DR": "COD",
    "Kenya": "KEN", "Tanzania": "TZA", "Uganda": "UGA", "Rwanda": "RWA",
    "Ethiopia": "ETH", "Somalia": "SOM", "Sudan": "SDN", "Libya": "LBY",
    "Angola": "AGO", "Mozambique": "MOZ", "Zambia": "ZMB", "Zimbabwe": "ZWE",
    "Malawi": "MWI", "Botswana": "BWA", "Namibia": "NAM", "Lesotho": "LSO",
    "Madagascar": "MDG", "Mauritius": "MUS", "Cape Verde": "CPV",
    "Guinea": "GIN", "Guinea-Bissau": "GNB", "Mali": "MLI",
    "Burkina Faso": "BFA", "Niger": "NER", "Chad": "TCD",
    "Benin": "BEN", "Togo": "TGO", "Liberia": "LBR", "Gambia": "GMB",
    "Mauritania": "MRT", "Central African Republic": "CAF",
    "São Tomé and Príncipe": "STP", "Equatorial Guinea": "GNQ",
    "Gabon": "GAB", "Seychelles": "SYC", "Comoros": "COM",
    "Eswatini": "SWZ", "Djibouti": "DJI", "Burundi": "BDI",
    "Fiji": "FJI", "Papua New Guinea": "PNG", "Solomon Islands": "SLB",
    "Vanuatu": "VUT", "Samoa": "WSM", "Tonga": "TON",
    "New Caledonia": "NCL", "Tahiti": "PYF", "Cook Islands": "COK",
    "El Salvador": "SLV", "Guatemala": "GTM", "Nicaragua": "NIC",
    "Dominican Republic": "DOM", "Puerto Rico": "PRI",
    "Guyana": "GUY", "Suriname": "SUR", "French Guiana": "GUF",
    "Martinique": "MTQ", "Guadeloupe": "GLP", "Curaçao": "CUW",
    "Aruba": "ABW", "Barbados": "BRB", "Saint Lucia": "LCA",
    "Grenada": "GRD", "Saint Vincent and the Grenadines": "VCT",
    "Saint Kitts and Nevis": "KNA", "Dominica": "DMA",
    "Trinidad and Tobago": "TTO", "Bahamas": "BHS",
    "Belize": "BLZ", "Cayman Islands": "CYM",
    "Turks and Caicos Islands": "TCA", "Montserrat": "MSR",
    "British Virgin Islands": "VGB", "US Virgin Islands": "VIR",
    "Anguilla": "AIA", "Bonaire": "BES",
}

# Flag codes (lowercase ISO 3166-1 alpha-2 + special UK codes)
FLAG_CODES: Dict[str, str] = {
    "Argentina": "ar", "Brazil": "br", "France": "fr", "Germany": "de",
    "Spain": "es", "England": "gb-eng", "Italy": "it", "Netherlands": "nl",
    "Portugal": "pt", "Belgium": "be", "Uruguay": "uy", "Croatia": "hr",
    "Denmark": "dk", "Switzerland": "ch", "Mexico": "mx", "Japan": "jp",
    "South Korea": "kr", "USA": "us", "Colombia": "co", "Chile": "cl",
    "Paraguay": "py", "Peru": "pe", "Ecuador": "ec", "Sweden": "se",
    "Norway": "no", "Poland": "pl", "Austria": "at", "Russia": "ru",
    "Turkey": "tr", "Ukraine": "ua", "Scotland": "gb-sct", "Serbia": "rs",
    "Nigeria": "ng", "Senegal": "sn", "Ghana": "gh", "Cameroon": "cm",
    "Ivory Coast": "ci", "Morocco": "ma", "Egypt": "eg", "Algeria": "dz",
    "Tunisia": "tn", "South Africa": "za", "Saudi Arabia": "sa", "Iran": "ir",
    "Australia": "au", "China": "cn", "Wales": "gb-wls", "Ireland": "ie",
    "Iceland": "is", "Greece": "gr", "Romania": "ro", "Hungary": "hu",
    "Bulgaria": "bg", "Slovakia": "sk", "Slovenia": "si", "Montenegro": "me",
    "Bosnia and Herzegovina": "ba", "Albania": "al", "Finland": "fi",
    "Israel": "il", "Costa Rica": "cr", "Honduras": "hn", "Panama": "pa",
    "Jamaica": "jm", "Canada": "ca", "Bolivia": "bo", "Venezuela": "ve",
    "Northern Ireland": "gb-nir", "Czech Republic": "cz",
}

# Intentar usar pycountry para convertir ISO3 -> ISO2
try:
    import pycountry
    # Poblar ISO3_TO_ISO2 usando pycountry si faltan entradas
    for country in pycountry.countries:
        a3 = country.alpha_3
        a2 = country.alpha_2
        if a3 not in ISO3_TO_ISO2:
            ISO3_TO_ISO2[a3] = a2.lower()
except ImportError:
    pass


def read_csv_teams() -> set:
    """Lee results.csv y devuelve conjunto de nombres únicos."""
    csv_path = settings.RESULTS_CSV
    if not os.path.exists(csv_path):
        logger.warning("No se encontró %s, usando DATA_DIR", csv_path)
        csv_path = str(Path(settings.MODEL_PARAMS_PATH).parent / "results.csv")
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"No se encontró results.csv en {csv_path}")

    df = pd.read_csv(csv_path)
    teams = set(df["home_team"].dropna().unique()) | set(df["away_team"].dropna().unique())
    return teams


def infer_tipo(name: str) -> str:
    """Infiere si es seleccion o club según si está en TEAM_ALIASES o es país conocido."""
    if name in TEAM_ALIASES:
        return "seleccion"
    iso = COUNTRY_ISO.get(name)
    name_lower = name.lower()
    # Equipos que claramente son selecciones
    country_suffixes = (" fc", "sc", " united", " city", " utd", " afc", " fk")
    if iso:
        return "seleccion"
    if any(name_lower.endswith(s) for s in country_suffixes):
        return "club"
    if name_lower.startswith(("real ", "fk ", "fk ", "ac ", "fc ")):
        return "club"
    # Por defecto, club (hay muchos clubes históricos obsoletos en el CSV)
    return "club"


def fetch_api_teams() -> dict:
    """Opcional: enriquece con football-data.org si hay API key."""
    api_key = settings.FOOTBALL_DATA_KEY
    if not api_key:
        return {}

    import requests
    result = {}
    competitions = ["WC", "EC", "PL", "PD", "SA", "BL1", "FL1", "CL"]
    for comp in competitions:
        try:
            resp = requests.get(
                f"{settings.FOOTBALL_DATA_BASE}/competitions/{comp}/teams",
                headers={"X-Auth-Token": api_key},
                timeout=10,
            )
            if resp.ok:
                for t in resp.json().get("teams", []):
                    name = t.get("name", "")
                    tla = t.get("tla", "")
                    crest = t.get("crest", "")
                    if name:
                        existing = result.setdefault(name, {})
                        existing["api"] = name
                        if tla:
                            existing["iso"] = tla
                        if crest:
                            existing["crest"] = crest
        except Exception as e:
            logger.debug("Error fetching %s: %s", comp, e)
    logger.info("Enriquecidos %d equipos desde API-Football", len(result))
    return result


def main():
    init_db()
    engine = get_engine()

    csv_teams = read_csv_teams()
    logger.info("Equipos únicos en CSV: %d", len(csv_teams))

    # Enriquecer desde API si hay key
    api_data = fetch_api_teams()

    created = 0
    updated = 0

    with Session(engine) as session:
        for csv_name in sorted(csv_teams):
            if not csv_name or not csv_name.strip():
                continue

            aliases = TEAM_ALIASES.get(csv_name, {})
            api_info = api_data.get(csv_name, {})

            existing = session.exec(
                select(Equipo).where(Equipo.nombre_csv == csv_name)
            ).first()

            nombre_fbref = aliases.get("fbref")
            nombre_understat = aliases.get("understat")
            nombre_api = aliases.get("api") or api_info.get("api")
            codigo_iso = aliases.get("iso") or api_info.get("iso") or COUNTRY_ISO.get(csv_name)
            # Inferir flag: primero de aliases, luego de FLAG_CODES, luego derivar de ISO3
            if aliases.get("bandera"):
                codigo_bandera = aliases["bandera"]
            elif FLAG_CODES.get(csv_name):
                codigo_bandera = FLAG_CODES[csv_name]
            elif codigo_iso and codigo_iso in ISO3_TO_ISO2:
                codigo_bandera = ISO3_TO_ISO2[codigo_iso]
            else:
                codigo_bandera = None
            tipo = aliases.get("tipo") or infer_tipo(csv_name)

            if existing:
                changed = False
                if nombre_fbref and not existing.nombre_fbref:
                    existing.nombre_fbref = nombre_fbref; changed = True
                if nombre_understat and not existing.nombre_understat:
                    existing.nombre_understat = nombre_understat; changed = True
                if nombre_api and not existing.nombre_api:
                    existing.nombre_api = nombre_api; changed = True
                if codigo_iso and not existing.codigo_iso:
                    existing.codigo_iso = codigo_iso; changed = True
                if codigo_bandera and not existing.codigo_bandera:
                    existing.codigo_bandera = codigo_bandera; changed = True
                if existing.nombre_canonico != csv_name:
                    existing.nombre_canonico = csv_name; changed = True
                if changed:
                    session.add(existing)
                    updated += 1
            else:
                equipo = Equipo(
                    nombre_canonico=csv_name,
                    nombre_csv=csv_name,
                    nombre_fbref=nombre_fbref,
                    nombre_understat=nombre_understat,
                    nombre_api=nombre_api,
                    codigo_iso=codigo_iso,
                    codigo_bandera=codigo_bandera,
                    tipo=tipo,
                )
                session.add(equipo)
                created += 1

            # Commit cada 200
            total_proc = created + updated
            if total_proc > 0 and total_proc % 200 == 0:
                session.commit()
                logger.info("Procesados %d equipos...", total_proc)

        session.commit()

    total = session.exec(select(func.count(Equipo.id))).one()
    logger.info("Seed completado: %d creados, %d actualizados. Total en BD: %d",
                created, updated, total)


if __name__ == "__main__":
    main()
