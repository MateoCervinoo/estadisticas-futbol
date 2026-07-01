import { useEffect, useState } from 'react'
import { TOURNAMENT_LABELS } from './matchPresentation'

export default function useMatchFilters() {
  const [selectedYear, setSelectedYear] = useState<number | undefined>(undefined)
  const [selectedSeason, setSelectedSeason] = useState<string>('')
  const [selectedDate, setSelectedDate] = useState<string | null>(null)
  const [competitionFilter, setCompetitionFilter] = useState<string>('Todos')
  const [stageFilter, setStageFilter] = useState<string>('Todos')
  const [groupFilter, setGroupFilter] = useState<string>('Todos')
  const [matchdayFilter, setMatchdayFilter] = useState<number | undefined>(undefined)
  const [showFilters, setShowFilters] = useState<boolean>(false)
  const hasActiveServerFilters = Boolean(
    competitionFilter !== 'Todos'
    || selectedDate
    || selectedYear !== undefined
    || selectedSeason
    || stageFilter !== 'Todos'
    || groupFilter !== 'Todos'
    || matchdayFilter !== undefined
  )

  useEffect(() => {
    setSelectedYear(undefined)
    setSelectedSeason('')
    setSelectedDate(null)
    setStageFilter('Todos')
    setGroupFilter('Todos')
    setMatchdayFilter(undefined)
  }, [competitionFilter])

  useEffect(() => {
    if (stageFilter !== 'Todos' && stageFilter !== 'GROUP_STAGE') {
      setGroupFilter('Todos')
    }
  }, [stageFilter])

  useEffect(() => {
    setSelectedDate(null)
    setStageFilter('Todos')
    setGroupFilter('Todos')
    setMatchdayFilter(undefined)
  }, [selectedYear, selectedSeason])

  const selectedCompetitionLabel = competitionFilter === 'Todos'
    ? ''
    : (TOURNAMENT_LABELS[competitionFilter] ?? competitionFilter)
  const isWorldCupFilter = selectedCompetitionLabel === 'Mundial' || /world cup/i.test(competitionFilter)
  const isQualifierFilter = /clasific|qualification|qualifier/i.test(selectedCompetitionLabel) || /qualification|qualifier/i.test(competitionFilter)
  const isLeagueFilter = competitionFilter !== 'Todos' && !isWorldCupFilter && !isQualifierFilter

  return {
    selectedYear,
    setSelectedYear,
    selectedSeason,
    setSelectedSeason,
    selectedDate,
    setSelectedDate,
    competitionFilter,
    setCompetitionFilter,
    stageFilter,
    setStageFilter,
    groupFilter,
    setGroupFilter,
    matchdayFilter,
    setMatchdayFilter,
    showFilters,
    setShowFilters,
    hasActiveServerFilters,
    showStageFilter: isWorldCupFilter,
    showGroupFilter: isWorldCupFilter && (stageFilter === 'Todos' || stageFilter === 'GROUP_STAGE'),
    isLeagueFilter,
  }
}
