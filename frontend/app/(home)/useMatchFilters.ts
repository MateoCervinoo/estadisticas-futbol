import { useEffect, useState } from 'react'
import { TOURNAMENT_LABELS } from './matchPresentation'

export default function useMatchFilters() {
  const [selectedYear, setSelectedYear] = useState<number | undefined>(undefined)
  const [selectedDate, setSelectedDate] = useState<string | null>(null)
  const [competitionFilter, setCompetitionFilter] = useState<string>('Todos')
  const [stageFilter, setStageFilter] = useState<string>('Todos')
  const [groupFilter, setGroupFilter] = useState<string>('Todos')
  const [matchdayFilter, setMatchdayFilter] = useState<number | undefined>(undefined)
  const [showFilters, setShowFilters] = useState<boolean>(false)
  const hasActiveServerFilters = Boolean(
    selectedYear !== undefined
    || selectedDate
    || competitionFilter !== 'Todos'
    || stageFilter !== 'Todos'
    || groupFilter !== 'Todos'
    || matchdayFilter !== undefined
  )

  useEffect(() => {
    setStageFilter('Todos')
    setGroupFilter('Todos')
    setMatchdayFilter(undefined)
  }, [competitionFilter])

  useEffect(() => {
    if (stageFilter !== 'Todos' && stageFilter !== 'GROUP_STAGE') {
      setGroupFilter('Todos')
    }
  }, [stageFilter])

  const selectedCompetitionLabel = competitionFilter === 'Todos'
    ? ''
    : (TOURNAMENT_LABELS[competitionFilter] ?? competitionFilter)
  const isWorldCupFilter = selectedCompetitionLabel === 'Mundial' || /world cup/i.test(competitionFilter)
  const isQualifierFilter = /clasific|qualification|qualifier/i.test(selectedCompetitionLabel) || /qualification|qualifier/i.test(competitionFilter)
  const isLeagueFilter = competitionFilter !== 'Todos' && !isWorldCupFilter && !isQualifierFilter

  return {
    selectedYear,
    setSelectedYear,
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
