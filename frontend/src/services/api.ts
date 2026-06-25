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

export async function getPartidos(): Promise<Partido[]> {
  try {
    const res = await fetch(`${BASE_URL}/partidos`)
    if (!res.ok) {
      // Try to include response body to ease debugging
      const body = await res.text()
      throw new Error(`Failed to fetch partidos: ${res.status} ${res.statusText} - ${body}`)
    }
    const data = await safeJson(res)
    return data as Partido[]
  } catch (err) {
    // Log and rethrow so the caller can decide how to handle it
    // eslint-disable-next-line no-console
    console.error('getPartidos error:', err)
    throw err
  }
}

export async function getPartidosFinalizados(): Promise<Partido[]> {
  const partidos = await getPartidos()
  return partidos.filter((p) => p.status === 'FT')
}
