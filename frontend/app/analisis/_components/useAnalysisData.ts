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

  useEffect(() => {
    if (teamQuery.trim().length < 2) {
      setTeams([])
      return
    }
    const timer = setTimeout(async () => {
      try {
        const res = await fetch(`${API_URL}/equipos/search?q=${encodeURIComponent(teamQuery)}&tipo=${teamType}`)
        if (res.ok) setTeams(await res.json())
      } catch {}
    }, 300)
    return () => clearTimeout(timer)
  }, [teamQuery, teamType])

  useEffect(() => {
    if (!selectedTeam) return
    setEvolLoading(true)
    fetch(`${API_URL}/equipos/${selectedTeam.id}/evolution`)
      .then((response) => response.ok ? response.json() : null)
      .then((data) => {
        if (data) setEvolution(data.evolution || [])
        setEvolLoading(false)
      })
      .catch(() => setEvolLoading(false))
  }, [selectedTeam])

  useEffect(() => {
    if (!selectedTeam) return
    setDistLoading(true)
    fetch(`${API_URL}/equipos/${selectedTeam.id}/distribucion`)
      .then((response) => response.ok ? response.json() : null)
      .then((data) => {
        if (data) setDistribucion(data.distribucion || [])
        setDistLoading(false)
      })
      .catch(() => setDistLoading(false))
  }, [selectedTeam])

  useEffect(() => {
    if (tab !== 'xg-vs-real') return
    setXgLoading(true)
    fetch(`${API_URL}/analytics/xg-vs-real?tipo=${teamType}`)
      .then((response) => response.ok ? response.json() : null)
      .then((data) => {
        if (data) setXgData(data)
        setXgLoading(false)
      })
      .catch(() => setXgLoading(false))
  }, [tab, teamType])

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
    selectTeam,
    changeTeamType,
    downloadCSV,
  }
}
