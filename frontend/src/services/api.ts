// Servicio de API para consumir el backend de FastAPI
// Define la interfaz Partido exactamente con los campos expuestos por el backend
export interface Partido {
  id: number
  fixture_id: number
  date: string
  home_team: string
  away_team: string
  home_score: number | null
  away_score: number | null
  ht_home_score: number | null
  ht_away_score: number | null
  status: string // e.g. 'NS', 'FT'
  tournament?: string | null
  stage?: string | null
  group?: string | null
  home_crest_url?: string | null
  away_crest_url?: string | null
  home_codigo_bandera?: string | null
  away_codigo_bandera?: string | null
  home_xg: number | null
  away_xg: number | null
}

export const API_BASE_URL = (process.env.NEXT_PUBLIC_API_URL || '').replace(/\/$/, '')
export const API_URL = `${API_BASE_URL}/api`
export const WS_URL = process.env.NEXT_PUBLIC_WS_URL || API_BASE_URL.replace(/^http/, 'ws') + '/ws/matches'

const BASE_URL = API_URL

export interface PredictionResponse {
  status: 'ok' | 'insufficient_data' | 'model_not_loaded' | 'team_not_supported'
  message?: string
  model_type?: 'seleccion' | 'club'
  model_version?: string | null
  neutral?: boolean
  home_win?: number
  draw?: number
  away_win?: number
  score_matrix?: number[][]
  score_matrix_flat?: { home: number; away: number; prob: number }[]
  most_likely?: { home: number; away: number }
}

async function safeJson(response: Response) {
  const text = await response.text()
  try {
    return JSON.parse(text)
  } catch (err) {
    // If backend returned non-JSON, include raw text for debugging
    throw new Error(`Invalid JSON response: ${text}`)
  }
}

async function assertOk(response: Response, label: string) {
  if (response.ok) return
  const body = await response.text()
  throw new Error(`${label}: ${response.status} ${response.statusText}${body ? ` - ${body}` : ''}`)
}

export interface PartidoFilters {
  year?: number
  season?: string
  torneo_id?: number
  tournament?: string
  stage?: string
  group?: string
  matchday?: number
  date?: string
}

export interface PartidoFilterMetadata {
  years: number[]
  tournaments: string[]
  stages: string[]
  groups: string[]
  matchdays: number[]
  dates: string[]
}

export async function getPartidos(filters?: number | PartidoFilters): Promise<Partido[]> {
  try {
    let url = `${BASE_URL}/partidos`
    const params = new URLSearchParams()
    if (typeof filters === 'number') {
      params.set('year', String(filters))
    } else if (filters) {
      if (filters.year !== undefined) params.set('year', String(filters.year))
      if (filters.season) params.set('season', filters.season)
      if (filters.torneo_id !== undefined) params.set('torneo_id', String(filters.torneo_id))
      if (filters.tournament) params.set('tournament', filters.tournament)
      if (filters.stage) params.set('stage', filters.stage)
      if (filters.group) params.set('group', filters.group)
      if (filters.matchday !== undefined) params.set('matchday', String(filters.matchday))
      if (filters.date) params.set('date', filters.date)
    }
    const query = params.toString()
    if (query) url += `?${query}`

    const res = await fetch(url)
    if (!res.ok) {
      const body = await res.text()
      throw new Error(`Failed to fetch partidos: ${res.status} ${res.statusText} - ${body}`)
    }
    const data = await safeJson(res)
    return data as Partido[]
  } catch (err) {
    // eslint-disable-next-line no-console
    console.error('getPartidos error:', err)
    throw err
  }
}

export async function getAniosDisponibles(): Promise<number[]> {
  try {
    const res = await fetch(`${BASE_URL}/partidos/anyos`)
    if (!res.ok) return []
    const data = await safeJson(res)
    return data as number[]
  } catch {
    return []
  }
}

export async function getPartidoFilterMetadata(filters?: PartidoFilters): Promise<PartidoFilterMetadata> {
  try {
    const params = new URLSearchParams()
    if (filters?.year !== undefined) params.set('year', String(filters.year))
    if (filters?.season) params.set('season', filters.season)
    if (filters?.torneo_id !== undefined) params.set('torneo_id', String(filters.torneo_id))
    if (filters?.tournament) params.set('tournament', filters.tournament)
    if (filters?.stage) params.set('stage', filters.stage)
    if (filters?.group) params.set('group', filters.group)
    if (filters?.matchday !== undefined) params.set('matchday', String(filters.matchday))
    if (filters?.date) params.set('date', filters.date)
    const query = params.toString()
    const res = await fetch(`${BASE_URL}/partidos/filtros${query ? `?${query}` : ''}`)
    if (!res.ok) {
      return { years: [], tournaments: [], stages: [], groups: [], matchdays: [], dates: [] }
    }
    const data = await safeJson(res)
    return {
      years: Array.isArray(data.years) ? data.years : [],
      tournaments: Array.isArray(data.tournaments) ? data.tournaments : [],
      stages: Array.isArray(data.stages) ? data.stages : [],
      groups: Array.isArray(data.groups) ? data.groups : [],
      matchdays: Array.isArray(data.matchdays) ? data.matchdays : [],
      dates: Array.isArray(data.dates) ? data.dates : [],
    }
  } catch {
    return { years: [], tournaments: [], stages: [], groups: [], matchdays: [], dates: [] }
  }
}

export interface PartidoEstadisticas {
  partido_id: number
  fuente: string
  xg_local: number | null
  xg_visitante: number | null
  remates_local: number | null
  remates_visitante: number | null
  remates_puerta_local: number | null
  remates_puerta_visitante: number | null
  remates_fuera_local: number | null
  remates_fuera_visitante: number | null
  remates_bloqueados_local: number | null
  remates_bloqueados_visitante: number | null
  posesion_local: number | null
  posesion_visitante: number | null
  corners_local: number | null
  corners_visitante: number | null
  faltas_local: number | null
  faltas_visitante: number | null
  tarjetas_amarillas_local: number | null
  tarjetas_amarillas_visitante: number | null
  tarjetas_rojas_local: number | null
  tarjetas_rojas_visitante: number | null
  fueras_juego_local: number | null
  fueras_juego_visitante: number | null
  paradas_local: number | null
  paradas_visitante: number | null
}

export async function getPartidosFinalizados(): Promise<Partido[]> {
  const partidos = await getPartidos()
  return partidos.filter((p) => p.status === 'FT')
}

export async function getPartidoEstadisticas(partidoId: number): Promise<PartidoEstadisticas | null> {
  try {
    const res = await fetch(`${BASE_URL}/partidos/${partidoId}/estadisticas`)
    if (!res.ok) return null
    const data = await safeJson(res)
    const stats = data?.estadisticas?.[0] ?? null
    return stats as PartidoEstadisticas | null
  } catch {
    return null
  }
}

export async function getPartidoPrediccion(fixtureId: number): Promise<PredictionResponse | null> {
  try {
    const res = await fetch(`${BASE_URL}/partidos/${fixtureId}/prediccion`)
    if (!res.ok) return null
    return safeJson(res)
  } catch {
    return null
  }
}

// ──────────── FASE 5 ────────────

export interface Torneo {
  id: number
  nombre_canonico: string
  tipo: string
  categoria: string
  nivel: number | null
  total_partidos: number
}

export interface TablaRow {
  equipo_id: number
  equipo: string
  codigo_bandera: string | null
  pj: number
  pg: number
  pe: number
  pp: number
  gf: number
  gc: number
  gd: number
  pts: number
  xg_favor: number
  xg_contra: number
  xg_diff: number
}

export interface TablaGrupo {
  grupo: string
  tabla: TablaRow[]
}

export interface BracketMatch {
  partido_id: number
  home_team: string
  away_team: string
  home_score: number | null
  away_score: number | null
  estado: string
  fecha: string | null
  grupo: string | null
}

export interface BracketRound {
  stage: string
  label: string
  order: number
  matches: BracketMatch[]
}

export interface FormaEntry {
  partido_id: number
  resultado: string
  goles_favor: number
  goles_contra: number
  rival: string
  fecha: string | null
}

export interface EquipoPerfil {
  equipo_id: number
  nombre: string
  codigo_bandera: string | null
  forma: FormaEntry[]
  proximos: {
    partido_id: number
    fixture_id: number | null
    local: boolean
    rival: string
    fecha: string | null
    torneo_id: number | null
    home_team: string | null
    away_team: string | null
  }[]
  stats: {
    pj: number; pg: number; pe: number; pp: number
    gf: number; gc: number; gd: number; pts: number
  }
}

export interface ComparacionStats {
  pj: number; pg: number; pe: number; pp: number
  gf: number; gc: number; gd: number; pts: number
  xg_favor: number; xg_contra: number
}

export interface Comparacion {
  equipo1: { id: number; nombre: string; codigo_bandera: string | null; stats: ComparacionStats }
  equipo2: { id: number; nombre: string; codigo_bandera: string | null; stats: ComparacionStats }
  h2h: {
    eq1_wins: number; eq2_wins: number; draws: number
    matches: { eq1_goals: number; eq2_goals: number; fecha: string | null }[]
  }
}

export async function getTorneos(): Promise<Torneo[]> {
  const res = await fetch(`${BASE_URL}/torneos`)
  await assertOk(res, 'Failed to fetch torneos')
  return safeJson(res)
}

export async function getTablaPosiciones(
  torneoId: number,
  filters?: { year?: number; season?: string; grouped?: boolean }
): Promise<{ torneo: string; tipo: string; tabla: TablaRow[]; grupos?: TablaGrupo[] }> {
  const params = new URLSearchParams()
  if (filters?.year !== undefined) params.set('year', String(filters.year))
  if (filters?.season) params.set('season', filters.season)
  if (filters?.grouped) params.set('grouped', 'true')
  const query = params.toString()
  const res = await fetch(`${BASE_URL}/torneos/${torneoId}/tabla-posiciones${query ? `?${query}` : ''}`)
  await assertOk(res, 'Failed to fetch tabla de posiciones')
  return safeJson(res)
}

export async function getBracket(
  torneoId: number,
  filters?: { year?: number; season?: string }
): Promise<{ torneo: string; bracket: BracketRound[] }> {
  const params = new URLSearchParams()
  if (filters?.year !== undefined) params.set('year', String(filters.year))
  if (filters?.season) params.set('season', filters.season)
  const query = params.toString()
  const res = await fetch(`${BASE_URL}/torneos/${torneoId}/bracket${query ? `?${query}` : ''}`)
  await assertOk(res, 'Failed to fetch bracket')
  return safeJson(res)
}

export async function getTorneoTemporadas(torneoId: number): Promise<string[]> {
  const res = await fetch(`${BASE_URL}/torneos/${torneoId}/temporadas`)
  await assertOk(res, 'Failed to fetch temporadas')
  const data = await safeJson(res)
  return Array.isArray(data.temporadas) ? data.temporadas : []
}

export async function getEquipoPerfil(equipoId: number): Promise<EquipoPerfil | null> {
  try {
    const res = await fetch(`${BASE_URL}/equipos/${equipoId}/perfil`)
    if (!res.ok) return null
    return safeJson(res)
  } catch { return null }
}

export async function getComparacion(eq1: number, eq2: number): Promise<Comparacion | null> {
  try {
    const res = await fetch(`${BASE_URL}/equipos/comparar?eq1=${eq1}&eq2=${eq2}`)
    if (!res.ok) return null
    return safeJson(res)
  } catch { return null }
}

// ──────────── FASE 6 — Live + Notifications ────────────

export interface NotificacionItem {
  id: number
  partido_id: number
  tipo: string
  mensaje: string
  leida: boolean
  created_at: string | null
}

export async function getNotificaciones(noLeidas?: boolean): Promise<NotificacionItem[]> {
  try {
    const params = noLeidas ? '?no_leidas=true' : ''
    const res = await fetch(`${BASE_URL}/notificaciones${params}`)
    if (!res.ok) return []
    return safeJson(res)
  } catch { return [] }
}

export async function getNotificacionesNoLeidasCount(): Promise<number> {
  try {
    const res = await fetch(`${BASE_URL}/notificaciones/no-leidas`)
    if (!res.ok) return 0
    const data = await safeJson(res)
    return data.count ?? 0
  } catch { return 0 }
}

export async function marcarNotificacionLeida(id: number): Promise<boolean> {
  try {
    const res = await fetch(`${BASE_URL}/notificaciones/${id}/leer`, { method: 'POST' })
    return res.ok
  } catch { return false }
}

export async function marcarTodasLeidas(): Promise<number> {
  try {
    const res = await fetch(`${BASE_URL}/notificaciones/leer-todas`, { method: 'POST' })
    if (!res.ok) return 0
    const data = await safeJson(res)
    return data.marcadas ?? 0
  } catch { return 0 }
}

export async function getPartidosEnVivo(): Promise<Partido[]> {
  try {
    const res = await fetch(`${BASE_URL}/partidos/live`)
    if (!res.ok) return []
    return safeJson(res)
  } catch { return [] }
}
