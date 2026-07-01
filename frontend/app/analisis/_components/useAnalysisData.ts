import { useCallback, useEffect, useState } from 'react'
import { API_URL } from '../../../src/services/api'
import { AnalysisTab, DistributionPoint, EvolutionPoint, SelectedTeam, TeamSearchResult, TeamType, XgVsRealRow } from './types'

export default function useAnalysisData() {
  const [tab, setTab] = useState<AnalysisTab>('evolution')
  const [teamType, setTeamType] = useState<TeamType>('club')
  const [teamQuery, setTeamQuery] = useState('')
  const [teams, setTeams] = useState<TeamSearchResult[]>([])
  const [selectedTeam, setSelectedTeam] = useState<SelectedTeam | null>(null)
  const [evolution, setEvolution] = useState<EvolutionPoint[]>([])
  const [distribucion, setDistribucion] = useState<DistributionPoint[]>([])
  const [xgData, setXgData] = useState<XgVsRealRow[]>([])
  const [evolLoading, setEvolLoading] = useState(false)
  const [xgLoading, setXgLoading] = useState(false)
  const [distLoading, setDistLoading] = useState(false)
  const [teamSearchError, setTeamSearchError] = useState<string | null>(null)
  const [evolError, setEvolError] = useState<string | null>(null)
  const [xgError, setXgError] = useState<string | null>(null)
  const [distError, setDistError] = useState<string | null>(null)

  useEffect(() => {
    if (teamQuery.trim().length < 2) {
      setTeams([])
      return
    }
    const timer = setTimeout(async () => {
      try {
        setTeamSearchError(null)
        const res = await fetch(`${API_URL}/equipos/search?q=${encodeURIComponent(teamQuery)}&tipo=${teamType}`)
        if (!res.ok) throw new Error('No se pudo buscar equipos')
        setTeams(await res.json())
      } catch {
        setTeams([])
        setTeamSearchError('No se pudo buscar equipos. Probá nuevamente.')
      }
    }, 300)
    return () => clearTimeout(timer)
  }, [teamQuery, teamType])

  useEffect(() => {
    if (!selectedTeam) return
    setEvolLoading(true)
    setEvolError(null)
    fetch(`${API_URL}/equipos/${selectedTeam.id}/evolution`)
      .then((response) => response.ok ? response.json() : Promise.reject(new Error('evolution')))
      .then((data) => {
        if (data) setEvolution(data.evolution || [])
        setEvolLoading(false)
      })
      .catch(() => {
        setEvolution([])
        setEvolError('No se pudo cargar la evolución del equipo.')
        setEvolLoading(false)
      })
  }, [selectedTeam])

  useEffect(() => {
    if (!selectedTeam) return
    setDistLoading(true)
    setDistError(null)
    fetch(`${API_URL}/equipos/${selectedTeam.id}/distribucion`)
      .then((response) => response.ok ? response.json() : Promise.reject(new Error('distribucion')))
      .then((data) => {
        if (data) setDistribucion(data.distribucion || [])
        setDistLoading(false)
      })
      .catch(() => {
        setDistribucion([])
        setDistError('No se pudo cargar la distribución de goles.')
        setDistLoading(false)
      })
  }, [selectedTeam])

  useEffect(() => {
    setXgLoading(true)
    setXgError(null)
    fetch(`${API_URL}/analytics/xg-vs-real?tipo=${teamType}`)
      .then((response) => response.ok ? response.json() : Promise.reject(new Error('xg')))
      .then((data) => {
        if (data) setXgData(data)
        setXgLoading(false)
      })
      .catch(() => {
        setXgData([])
        setXgError('No se pudo cargar el ranking xG.')
        setXgLoading(false)
      })
  }, [teamType])

  const selectTeam = useCallback((team: SelectedTeam) => {
    setSelectedTeam(team)
    setTeamQuery('')
    setTeams([])
  }, [])

  const changeTeamType = useCallback((type: TeamType) => {
    setTeamType(type)
    setSelectedTeam(null)
    setTeamQuery('')
    setTeams([])
    setEvolution([])
    setDistribucion([])
    setXgData([])
    setTeamSearchError(null)
    setEvolError(null)
    setXgError(null)
    setDistError(null)
  }, [])

  const downloadCSV = useCallback(() => {
    if (xgData.length === 0) return
    const headers = ['Equipo', 'PJ', 'Goles', 'xG', 'xGA', 'Dif G-xG', 'Dif xG-xGA', 'Goles p90', 'xG p90', 'xGA p90']
    const rows = xgData.map((row) => [
      row.nombre, row.pj, row.goles, row.xg, row.xga, row.diferencia, row.xg_diff, row.goles_p90, row.xg_p90, row.xga_p90,
    ])
    const csv = [headers.join(','), ...rows.map((row: Array<string | number>) => row.join(','))].join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'xg_vs_real.csv'
    link.click()
    URL.revokeObjectURL(url)
  }, [xgData])

  return {
    tab,
    setTab,
    teamType,
    teamQuery,
    setTeamQuery,
    teams,
    selectedTeam,
    setSelectedTeam,
    evolution,
    distribucion,
    xgData,
    evolLoading,
    xgLoading,
    distLoading,
    teamSearchError,
    evolError,
    xgError,
    distError,
    selectTeam,
    changeTeamType,
    downloadCSV,
  }
}
