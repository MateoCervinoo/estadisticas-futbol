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

const BASE_URL = 'http://localhost:8000/api'

async function safeJson(response: Response) {
  const text = await response.text()
  try {
    return JSON.parse(text)
  } catch (err) {
    // If backend returned non-JSON, include raw text for debugging
    throw new Error(`Invalid JSON response: ${text}`)
  }
}

export async function getPartidos(year?: number): Promise<Partido[]> {
  try {
    let url = `${BASE_URL}/partidos`
    const params: string[] = []
    if (year !== undefined) params.push(`year=${year}`)
    if (params.length) url += '?' + params.join('&')

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
