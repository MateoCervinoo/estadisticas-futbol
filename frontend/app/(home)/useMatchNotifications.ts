import { Dispatch, SetStateAction, useEffect, useRef } from 'react'
import { getPartidos, Partido, WS_URL } from '../../src/services/api'
import { getFavorites } from '../../src/services/favorites'
import { ToastMessage } from './useFavorites'

type NotificationFilters = {
  hasActiveServerFilters: boolean
  selectedYear: number | undefined
  selectedSeason: string
  selectedDate: string | null
  competitionFilter: string
  stageFilter: string
  groupFilter: string
  matchdayFilter: number | undefined
}

type UseMatchNotificationsParams = NotificationFilters & {
  setPartidos: Dispatch<SetStateAction<Partido[] | null>>
  setToasts: Dispatch<SetStateAction<ToastMessage[]>>
}

export default function useMatchNotifications({
  hasActiveServerFilters,
  selectedYear,
  selectedSeason,
  selectedDate,
  competitionFilter,
  stageFilter,
  groupFilter,
  matchdayFilter,
  setPartidos,
  setToasts,
}: UseMatchNotificationsParams) {
  const matchFiltersRef = useRef<NotificationFilters>({
    hasActiveServerFilters,
    selectedYear,
    selectedSeason,
    selectedDate,
    competitionFilter,
    stageFilter,
    groupFilter,
    matchdayFilter,
  })

  useEffect(() => {
    matchFiltersRef.current = {
      hasActiveServerFilters,
      selectedYear,
      selectedSeason,
      selectedDate,
      competitionFilter,
      stageFilter,
      groupFilter,
      matchdayFilter,
    }
  }, [hasActiveServerFilters, selectedYear, selectedSeason, selectedDate, competitionFilter, stageFilter, groupFilter, matchdayFilter])

  useEffect(() => {
    let ws: WebSocket | null = null
    let reconnectTimer: ReturnType<typeof setTimeout>
    let cancelled = false

    const connect = () => {
      if (cancelled) return
      ws = new WebSocket(WS_URL)
      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data)
          if (msg.type === 'notification') {
            const filters = matchFiltersRef.current
            if (!filters.hasActiveServerFilters) return
            getPartidos({
              year: filters.selectedYear,
              season: filters.selectedSeason !== 'Todos' ? filters.selectedSeason : undefined,
              date: filters.selectedDate ?? undefined,
              tournament: filters.competitionFilter !== 'Todos' ? filters.competitionFilter : undefined,
              stage: filters.stageFilter !== 'Todos' ? filters.stageFilter : undefined,
              group: filters.groupFilter !== 'Todos' ? filters.groupFilter : undefined,
              matchday: filters.matchdayFilter,
            }).then((data) => {
              if (data) setPartidos(data)
            }).catch(() => {})
            const pid = Number(msg.data?.partido_id)
            if (pid && getFavorites().includes(pid)) {
              setToasts((prev) => [...prev, { id: Date.now(), msg: `⭐ ${msg.data.mensaje}` }])
            } else if (pid) {
              setToasts((prev) => [...prev, { id: Date.now(), msg: msg.data.mensaje }])
            }
          }
        } catch {}
      }
      ws.onclose = () => {
        if (!cancelled) reconnectTimer = setTimeout(connect, 5000)
      }
      ws.onerror = () => {
        ws?.close()
      }
    }

    connect()
    return () => {
      cancelled = true
      if (ws?.readyState === WebSocket.CONNECTING) {
        ws.onopen = () => ws?.close()
      } else {
        ws?.close()
      }
      clearTimeout(reconnectTimer)
    }
  }, [setPartidos, setToasts])
}
