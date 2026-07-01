export type AnalysisTab = 'evolution' | 'xg-vs-real' | 'distribucion'
export type TeamType = 'club' | 'seleccion'
export type TeamSearchResult = { id: number; nombre: string; codigo_bandera: string | null }
export type SelectedTeam = { id: number; nombre: string }

export type EvolutionPoint = {
  match_index: number
  fecha?: string | null
  resultado?: 'H' | 'A' | 'D'
  gf?: number
  gc?: number
  rolling_gf_avg: number
  rolling_gc_avg: number
  xg_favor?: number | null
  xg_contra?: number | null
}

export type DistributionPoint = {
  goles: number
  actual_pct: number
  poisson_pct: number
  actual_partidos?: number
}

export type XgVsRealRow = {
  equipo_id: number
  nombre: string
  codigo_bandera?: string | null
  pj: number
  goles: number
  xg: number
  xga: number
  diferencia: number
  xg_diff: number
  goles_p90: number
  xg_p90: number
  xga_p90: number
}
