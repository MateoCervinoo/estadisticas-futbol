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

## Levantar el proyecto

```bash
docker compose up --build -d
```

Frontend: `http://localhost:3000`  
Backend: `http://localhost:8000`
