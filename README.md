<p align="center">
  <img src="./source/Pizarron%20Estadistico.png" alt="Pizarrón Estadístico" width="320" />
</p>

# estadisticas-futbol

Plataforma web para visualizar el calendario del Mundial y predecir resultados de partidos con un modelo probabilístico Dixon-Coles.

## Qué incluye

- **Frontend** en Next.js + React
- **Backend** en FastAPI + SQLModel
- **PostgreSQL** para guardar fixtures y resultados
- **Entrenador** independiente para generar `model_params.json`
- **Sincronizador** para actualizar partidos y alimentar el histórico
- **Docker Compose** para levantar todo junto

## Cómo funciona

El backend no hace el cálculo pesado. Lee los parámetros ya entrenados desde `./data/model_params.json` y responde rápido al frontend.

El script `entrenador.py` procesa `results.csv`, recalcula las métricas ofensivas/defensivas y vuelve a generar los parámetros del modelo.

El script `actualizar_partidos.py` sincroniza partidos, estados y goles desde la API externa, y agrega los partidos finalizados al histórico.

## Stack

- **Frontend:** Next.js, React, Bootstrap
- **Backend:** FastAPI, SQLModel, Python
- **Base de datos:** PostgreSQL
- **Modelo:** Dixon-Coles
- **Infraestructura:** Docker Compose

## Roadmap

### Prioridad alta

1. **Agregar más estadísticas**
   - Integrar una API más completa o de pago.
   - Incorporar métricas avanzadas como xG, remates, posesión, tiros al arco, corners y tarjetas.

2. **Mostrar más información del partido**
   - Estadio
   - Ciudad/país
   - Árbitro
   - Asistencia
   - Fase, grupo y contexto del torneo

3. **Agregar más ligas y torneos**
   - Premier League
   - Liga Argentina
   - Otras ligas y copas internacionales

### Prioridad media

4. **Mejoras en la predicción**
   - Ajustes por competencia
   - Factor localía más fino
   - Peso por recencia de partidos
   - Calibración de probabilidades

5. **Historial y tendencia por equipo**
   - Forma reciente
   - Racha de goles a favor/en contra
   - Rendimiento local y visitante

6. **Comparador de equipos**
   - Vista lado a lado con estadísticas clave
   - Probabilidades históricas y proyección del enfrentamiento

7. **UX y visualización**
   - Filtros más potentes
   - Búsqueda por equipo
   - Más detalle en el modal
   - Gráficos de evolución del modelo

### Prioridad baja

8. **Favoritos y alertas**
   - Marcar partidos favoritos
   - Recordatorios antes del inicio

9. **Exportación y compartido**
   - Exportar predicciones a CSV o PDF
   - Compartir cards de partido

## Estructura general

- `frontend/`: interfaz web
- `backend/`: API, DB y lógica de sincronización
- `entrenador/`: entrenamiento del modelo
- `data/`: archivos compartidos por volumen Docker
- `source/`: assets, incluyendo el logo principal

## Archivos fuente y derivados

Se consideran fuente del proyecto:

- Código de `backend/`, `frontend/`, `entrenador/` y `shared/`
- Migraciones de `backend/alembic/`
- Datos base versionables de `data/`, como CSV y parámetros de modelo necesarios para desarrollo
- Assets de `source/` y `frontend/public/`
- Configuración reproducible: `docker-compose.yml`, `Dockerfile`, `Makefile`, `package.json`, `requirements.txt`

Se consideran derivados/locales y no deben versionarse:

- Entornos y dependencias: `venv/`, `node_modules/`
- Builds y cache: `frontend/.next/`, `frontend/.next*/`, `frontend/tsconfig.tsbuildinfo`
- Cache Python: `__pycache__/`, `*.pyc`
- Logs: `*.log`
- Secretos/local config: `.env`, `.env.*`, `entrenador/.env`
- Archivos privados o temporales: `archivos-privados/`, `downloaded_files/`, `session-*.md`

## Configuracion local

Crear archivos `.env` locales a partir de los ejemplos cuando haga falta. No versionar secretos.

- Backend/compose: `.env` en la raiz puede definir `API_FOOTBALL_KEY`.
- Frontend: `frontend/.env.example` documenta `NEXT_PUBLIC_API_URL` y `NEXT_PUBLIC_WS_URL`.
- Docker Compose ya define `NEXT_PUBLIC_API_URL=http://localhost:8000` para el frontend del stack local.

## Levantar el proyecto

```bash
docker compose up --build
```

Equivalente:

```bash
make up
```

Frontend: `http://localhost:3000`  
Backend: `http://localhost:8000`

## Base de datos

El esquema conceptual vive en `shared/models.py`. El esquema operativo se gestiona con Alembic desde `backend/alembic`.

La documentación específica está en `backend/README_DB.md`.

Aplicar migraciones directamente desde `backend/`:

```bash
alembic upgrade head
```

O desde la raiz con Docker:

```bash
make migrate
```

Reset controlado de la DB local:

```bash
make reset-db
```

El reset borra el volumen local de PostgreSQL y recrea el esquema desde las migraciones. Usarlo solo cuando los datos puedan regenerarse desde scripts, CSV o sincronización externa.

## Flujo Operativo De DB

Orden recomendado para recrear datos locales:

```bash
make reset-db
make seed
make load-results
make sync
```

Comandos equivalentes desde `backend/`:

```bash
make reset-db CONFIRM=reset
make seed_db
make load_results
make sync_data
```

## Fuentes De Datos

- `shared/models.py`: modelo conceptual de tablas SQLModel.
- `backend/alembic/`: fuente operativa del esquema de DB.
- `data/results.csv`: histórico base para ingesta local.
- `data/shootouts.csv`: definición de penales para partidos históricos cuando existe.
- API externa configurada por `API_FOOTBALL_KEY`: fixtures, estados, escudos y métricas sincronizadas.
- `data/model_params.json`: parámetros entrenados que consume el backend para predicciones.

Los archivos derivados/cache no son fuente: `.env`, `__pycache__/`, `.next*/`, logs, `.pytest_cache/`, `node_modules/`.

## Entrenar El Modelo

Con dependencias de `entrenador/requirements.txt` instaladas:

```bash
make train
```

Equivalente directo:

```bash
python -m entrenador.05_train_model
```

El entrenamiento lee datos desde la DB configurada y guarda parámetros en la ruta configurada por el entrenador, normalmente `data/model_params.json`.

## Verificacion

Backend:

```bash
make test-backend
```

Frontend:

```bash
make build-frontend
```

Si el entorno Python local no tiene dependencias, crear un virtualenv e instalar `backend/requirements.txt` antes de correr tests.
