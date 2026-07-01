import { Dispatch, SetStateAction, useEffect, useState } from 'react'
import { getPartidoFilterMetadata, getPartidos, getTorneoTemporadas, getTorneos, Partido, Torneo } from '../../src/services/api'

type UseMatchesParams = {
  selectedYear: number | undefined
  selectedSeason: string
  selectedDate: string | null
  competitionFilter: string
  stageFilter: string
  groupFilter: string
  matchdayFilter: number | undefined
  hasActiveServerFilters: boolean
}

export default function useMatches({
  selectedYear,
  selectedSeason,
  selectedDate,
  competitionFilter,
  stageFilter,
  groupFilter,
  matchdayFilter,
  hasActiveServerFilters,
}: UseMatchesParams) {
  const [partidos, setPartidos] = useState<Partido[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState<boolean>(true)
  const [slowLoading, setSlowLoading] = useState<boolean>(false)
  const [initialLoad, setInitialLoad] = useState<boolean>(true)
  const [aniosDisponibles, setAniosDisponibles] = useState<number[]>([])
  const [temporadasDisponibles, setTemporadasDisponibles] = useState<string[]>([])
  const [availableDates, setAvailableDates] = useState<string[]>([])
  const [availableCompetitions, setAvailableCompetitions] = useState<string[]>([])
  const [availableStages, setAvailableStages] = useState<string[]>([])
  const [availableGroups, setAvailableGroups] = useState<string[]>([])
  const [availableMatchdays, setAvailableMatchdays] = useState<number[]>([])

  useEffect(() => {
    Promise.all([getPartidoFilterMetadata(), getTorneos()])
      .then(([metadata, torneos]) => {
        setAniosDisponibles(metadata.years)
        setTemporadasDisponibles(metadata.seasons)
        setAvailableDates(metadata.dates)
        setAvailableCompetitions(metadata.tournaments)
        setAvailableTournaments(torneos)
        setAvailableStages(metadata.stages)
        setAvailableGroups(metadata.groups)
        setAvailableMatchdays(metadata.matchdays)
      })
      .catch(() => {})
  }, [])

  const selectedTournament = availableTournaments.find((torneo) => torneo.nombre_canonico === competitionFilter)

  useEffect(() => {
    if (!selectedTournament?.id) {
      setTemporadasDisponibles([])
      return
    }

    let mounted = true
    getTorneoTemporadas(selectedTournament.id)
      .then((temporadas) => {
        if (mounted) setTemporadasDisponibles(temporadas)
      })
      .catch(() => {
        if (mounted) setTemporadasDisponibles([])
      })
    return () => { mounted = false }
  }, [selectedTournament?.id])

  useEffect(() => {
    getPartidoFilterMetadata({
      tournament: competitionFilter !== 'Todos' ? competitionFilter : undefined,
    })
      .then((metadata) => {
        setAniosDisponibles(metadata.years)
        setTemporadasDisponibles(metadata.seasons)
        setAvailableDates(metadata.dates)
      })
      .catch(() => {})
  }, [competitionFilter])

  useEffect(() => {
    if (!hasActiveServerFilters) {
      setPartidos(null)
      setLoading(false)
      setSlowLoading(false)
      setError(null)
      setInitialLoad(false)
      return
    }

    let mounted = true
    let slowTimer: ReturnType<typeof setTimeout> | undefined
    setLoading(true)
    setSlowLoading(false)
    setError(null)
    slowTimer = setTimeout(() => {
      if (mounted) setSlowLoading(true)
    }, 6000)

    getPartidos({
      year: selectedYear,
      season: selectedSeason !== 'Todos' ? selectedSeason : undefined,
      date: selectedDate ?? undefined,
      tournament: competitionFilter !== 'Todos' ? competitionFilter : undefined,
      stage: stageFilter !== 'Todos' ? stageFilter : undefined,
      group: groupFilter !== 'Todos' ? groupFilter : undefined,
      matchday: matchdayFilter,
    })
      .then((data) => {
        if (mounted) {
          setPartidos(data)
          setInitialLoad(false)
        }
      })
      .catch((err) => {
        if (mounted) {
          setError(String(err))
          setInitialLoad(false)
        }
      })
      .finally(() => {
        if (mounted) {
          setLoading(false)
          setSlowLoading(false)
        }
        if (slowTimer) clearTimeout(slowTimer)
      })

    return () => {
      mounted = false
      if (slowTimer) clearTimeout(slowTimer)
    }
  }, [selectedYear, selectedSeason, selectedDate, competitionFilter, stageFilter, groupFilter, matchdayFilter, hasActiveServerFilters])

  useEffect(() => {
    const periodFilters = {
      year: selectedSeason && /^\d{4}$/.test(selectedSeason) ? Number(selectedSeason) : selectedYear,
      season: selectedSeason && !/^\d{4}$/.test(selectedSeason) ? selectedSeason : undefined,
    }
    getPartidoFilterMetadata({
      year: selectedYear,
      season: selectedSeason !== 'Todos' ? selectedSeason : undefined,
      tournament: competitionFilter !== 'Todos' ? competitionFilter : undefined,
      stage: stageFilter !== 'Todos' ? stageFilter : undefined,
      group: groupFilter !== 'Todos' ? groupFilter : undefined,
      matchday: matchdayFilter,
    })
      .then((metadata) => {
        setAvailableStages(metadata.stages)
        setAvailableGroups(metadata.groups)
        setAvailableMatchdays(metadata.matchdays)
        setAvailableDates(metadata.dates)
      })
      .catch(() => {})
  }, [selectedYear, selectedSeason, competitionFilter, stageFilter])

  return {
    partidos,
    setPartidos: setPartidos as Dispatch<SetStateAction<Partido[] | null>>,
    error,
    loading,
    slowLoading,
    initialLoad,
    aniosDisponibles,
    temporadasDisponibles,
    availableDates,
    availableCompetitions,
    availableStages,
    availableGroups,
    availableMatchdays,
  }
}
