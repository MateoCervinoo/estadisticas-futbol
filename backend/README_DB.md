# Base de datos

`shared/models.py` es la fuente conceptual del esquema. Backend y entrenador importan esos modelos compartidos.

Alembic es la fuente operativa para crear o migrar la base. La migración inicial está en `backend/alembic/versions/66275e4affc0_init_schema_v1_all_tables.py` y construye el esquema completo desde cero sobre una DB limpia.

## Tablas principales

- `equipo`: equipos/selecciones normalizados y sus aliases por fuente.
- `torneo`: competiciones y metadata básica.
- `partido`: fixture/resultados, claves externas, deduplicación y campos heredados de visualización.
- `partido_estadisticas`: xG, remates, posesión, tarjetas y métricas por fuente.
- `equipo_elo`: rating histórico por equipo y fuente.
- `model_features`: features materializadas para entrenamiento/análisis.
- `source_coverage`: cobertura por fuente, torneo y temporada.
- `sync_log`: auditoría de sincronizaciones.
- `model_version`: versiones de modelos entrenados y métricas.
- `torneo_tabla_posicion`: tabla de posiciones materializada.
- `torneo_bracket`: llaves/fases eliminatorias.
- `partido_evento`: eventos del partido.
- `usuario_favorito`: favoritos/alertas por usuario.
- `notificacion`: notificaciones generadas por cambios de partido.
- `value_bet`: oportunidades calculadas a partir de probabilidades y cuotas.

## Comandos operativos

Desde `backend/`:

```bash
make migrate_db
make seed_db
make load_results
make sync_data
make reset_db CONFIRM=reset
```

Equivalentes directos:

```bash
python scripts/db_tasks.py migrate_db
python scripts/db_tasks.py seed_db
python scripts/db_tasks.py load_results --since-year 2018
python scripts/db_tasks.py sync_data
```

## Flujo de DB recreable

1. `reset_db`: borra el volumen local y recrea PostgreSQL.
2. `migrate_db`: aplica Alembic hasta `head`.
3. `seed_db`: carga datos mínimos de equipos si la tabla está vacía.
4. `load_results`: ingesta histórica desde `data/results.csv`.
5. `sync_data`: sincroniza fixtures/métricas desde la API externa.

No agregar `ALTER TABLE` manuales ni `SQLModel.metadata.create_all()` como mecanismo de evolución de esquema. Todo cambio estructural debe quedar en modelos compartidos y migración Alembic.
