"""Pequeño script para verificar importaciones y la inicialización básica.

Ejecutar desde la raíz del proyecto con el intérprete de Python del contenedor
o localmente (asegúrate de que las dependencias estén instaladas).
"""
import sys

try:
    # Importar módulos principales para detectar import cycles
    from app.database import engine, init_db
    from app.models import Team, Partido, EstadisticasPartido
    from app.dixoncoles import fit_dixon_coles, predict_exact_score_matrix
except Exception as e:
    print("ERROR importing backend modules:", e)
    sys.exit(1)

print("Backend imports OK. Initializing DB (metadata create_all)...")
try:
    init_db()
    print("DB initialization OK.")
except Exception as e:
    print("ERROR initializing DB:", e)
    sys.exit(2)

print("All checks passed.")
