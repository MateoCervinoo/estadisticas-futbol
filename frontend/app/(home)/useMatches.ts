import { Dispatch, SetStateAction, useEffect, useState } from 'react'
import { getPartidoFilterMetadata, getPartidos, Partido } from '../../src/services/api'

type UseMatchesParams = {
  selectedYear: number | undefined
  selectedDate: string | null
  competitionFilter: string
  stageFilter: string
  groupFilter: string
  matchdayFilter: number | undefined
  hasActiveServerFilters: boolean
}

export default function useMatches({
  selectedYear,
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
  const [availableDates, setAvailableDates] = useState<string[]>([])
  const [availableCompetitions, setAvailableCompetitions] = useState<string[]>([])
  const [availableStages, setAvailableStages] = useState<string[]>([])
  const [availableGroups, setAvailableGroups] = useState<string[]>([])
  const [availableMatchdays, setAvailableMatchdays] = useState<number[]>([])

  useEffect(() => {
    getPartidoFilterMetadata()
      .then((metadata) => {
        setAniosDisponibles(metadata.years)
        setAvailableDates(metadata.dates)
        setAvailableCompetitions(metadata.tournaments)
        setAvailableStages(metadata.stages)
        setAvailableGroups(metadata.groups)
        setAvailableMatchdays(metadata.matchdays)
      })
      .catch(() => {})
  }, [])

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
  }, [selectedYear, selectedDate, competitionFilter, stageFilter, groupFilter, matchdayFilter, hasActiveServerFilters])

  useEffect(() => {
    getPartidoFilterMetadata({
      year: selectedYear,
      tournament: competitionFilter !== 'Todos' ? competitionFilter : undefined,
      stage: stageFilter !== 'Todos' ? stageFilter : undefined,
    })
      .then((metadata) => {
        setAvailableStages(metadata.stages)
        setAvailableGroups(metadata.groups)
        setAvailableMatchdays(metadata.matchdays)
      })
      .catch(() => {})
  }, [selectedYear, competitionFilter, stageFilter])

  return {
    partidos,
    setPartidos: setPartidos as Dispatch<SetStateAction<Partido[] | null>>,
    error,
    loading,
    slowLoading,
    initialLoad,
    aniosDisponibles,
    availableDates,
    availableCompetitions,
    availableStages,
    availableGroups,
    availableMatchdays,
  }
}
