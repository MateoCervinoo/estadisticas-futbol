import { Dispatch, SetStateAction, useEffect, useState } from 'react'
import { getPartidoFilterMetadata, getPartidos, Partido } from '../../src/services/api'

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
    getPartidoFilterMetadata()
      .then((metadata) => {
        setAniosDisponibles(metadata.years)
        setTemporadasDisponibles(metadata.seasons)
        setAvailableDates(metadata.dates)
        setAvailableCompetitions(metadata.tournaments)
        setAvailableStages(metadata.stages)
        setAvailableGroups(metadata.groups)
        setAvailableMatchdays(metadata.matchdays)
      })
      .catch(() => {})
  }, [])

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
    getPartidoFilterMetadata({
      year: selectedYear,
      season: selectedSeason !== 'Todos' ? selectedSeason : undefined,
      tournament: competitionFilter !== 'Todos' ? competitionFilter : undefined,
      stage: stageFilter !== 'Todos' ? stageFilter : undefined,
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
