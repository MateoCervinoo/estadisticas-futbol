"use client"

import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import FootballLoader from '../../../components/FootballLoader'
import {
  getTablaPosiciones, getBracket, getPartidos, getPartidoEstadisticas, getTorneoTemporadas,
  getPartidoFilterMetadata, getTorneoCobertura,
  TablaRow, TablaGrupo, BracketRound, Partido, PartidoEstadisticas, PartidoFilterMetadata, TorneoCobertura,
} from '../../../src/services/api'
import TournamentBracket from './_components/TournamentBracket'
import TournamentCalendar, { CalendarFilters } from './_components/TournamentCalendar'
import TournamentMatchDetailModal from './_components/TournamentMatchDetailModal'
import TournamentStats from './_components/TournamentStats'
import TournamentTable from './_components/TournamentTable'
import TournamentTabs, { TournamentTab } from './_components/TournamentTabs'

export default function TorneoDetailPage() {
  const params = useParams()
  const torneoId = Number(params.id)
  const [activeTab, setActiveTab] = useState<TournamentTab>('calendario')
  const [tabla, setTabla] = useState<TablaRow[] | null>(null)
  const [tablaGrupos, setTablaGrupos] = useState<TablaGrupo[] | null>(null)
  const [bracket, setBracketData] = useState<BracketRound[] | null>(null)
  const [partidos, setPartidos] = useState<Partido[] | null>(null)
  const [torName, setTorName] = useState('')
  const [torTipo, setTorTipo] = useState('')
  const [temporadas, setTemporadas] = useState<string[]>([])
  const [selectedSeason, setSelectedSeason] = useState<string>('')
  const [stageFilter, setStageFilter] = useState('Todos')
  const [groupFilter, setGroupFilter] = useState('Todos')
  const [matchdayFilter, setMatchdayFilter] = useState('')
  const [dateFilter, setDateFilter] = useState('')
  const [filterMetadata, setFilterMetadata] = useState<PartidoFilterMetadata | null>(null)
  const [cobertura, setCobertura] = useState<TorneoCobertura | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [sortCol, setSortCol] = useState<string>('pts')
  const [sortAsc, setSortAsc] = useState(false)
  const [calendarFilters, setCalendarFilters] = useState<CalendarFilters>({ matchday: '', stage: '', group: '', date: '' })
  // detail modal
  const [selectedMatch, setSelectedMatch] = useState<Partido | null>(null)
  const [currentStats, setCurrentStats] = useState<PartidoEstadisticas | null>(null)
  const [statsLoading, setStatsLoading] = useState(false)

  useEffect(() => {
    let mounted = true
    setLoading(true)
    setError(null)
    setTemporadas([])
    setSelectedSeason('')
    getTorneoTemporadas(torneoId)
      .then((values) => {
        if (!mounted) return
        setTemporadas(values)
        setSelectedSeason(values[0] || '')
        if (values.length === 0) setLoading(false)
      })
      .catch((err) => {
        if (!mounted) return
        setError(err instanceof Error ? err.message : 'No se pudieron cargar las temporadas')
        setLoading(false)
      })
    return () => { mounted = false }
  }, [torneoId])

  const clearTournamentFilters = () => {
    setStageFilter('Todos')
    setGroupFilter('Todos')
    setMatchdayFilter('')
    setDateFilter('')
  }

  const selectedSeasonBaseFilters = useMemo(() => {
    if (!selectedSeason) return null
    return /^\d{4}$/.test(selectedSeason)
      ? { torneo_id: torneoId, year: Number(selectedSeason) }
      : { torneo_id: torneoId, season: selectedSeason }
  }, [torneoId, selectedSeason])

  const selectedMatchFilters = useMemo(() => {
    if (!selectedSeasonBaseFilters) return null
    return {
      ...selectedSeasonBaseFilters,
      ...(stageFilter !== 'Todos' ? { stage: stageFilter } : {}),
      ...(groupFilter !== 'Todos' ? { group: groupFilter } : {}),
      ...(matchdayFilter ? { matchday: Number(matchdayFilter) } : {}),
      ...(dateFilter ? { date: dateFilter } : {}),
    }
  }, [selectedSeasonBaseFilters, stageFilter, groupFilter, matchdayFilter, dateFilter])

  useEffect(() => {
    if (!selectedSeason) return
    let mounted = true
    setLoading(true)
    setError(null)
    setTabla(null)
    setTablaGrupos(null)
    setBracketData(null)
    setPartidos(null)
    setCalendarFilters({ matchday: '', stage: '', group: '', date: '' })
    const seasonFilters = /^\d{4}$/.test(selectedSeason)
      ? { year: Number(selectedSeason), grouped: true }
      : { season: selectedSeason, grouped: true }
    if (!selectedMatchFilters || !selectedSeasonBaseFilters) return
    Promise.all([
      getTablaPosiciones(torneoId, { ...seasonFilters, ...(groupFilter !== 'Todos' ? { group: groupFilter } : {}) }),
      getBracket(torneoId, {
        ...seasonFilters,
        ...(stageFilter !== 'Todos' && stageFilter !== 'GROUP_STAGE' ? { stage: stageFilter } : {}),
        ...(dateFilter ? { date: dateFilter } : {}),
      }),
      getPartidos(selectedMatchFilters),
      getPartidoFilterMetadata(selectedSeasonBaseFilters),
      getTorneoCobertura(torneoId, selectedMatchFilters),
    ]).then(([t, b, ps, metadata, coverage]) => {
      if (!mounted) return
      setTabla(t.tabla)
      setTablaGrupos(t.grupos ?? null)
      setTorName(t.torneo)
      setTorTipo(t.tipo)
      setBracketData(b.bracket)
      setPartidos(ps)
      setFilterMetadata(metadata)
      setCobertura(coverage)
    }).catch((err) => {
      if (!mounted) return
      setError(err instanceof Error ? err.message : 'No se pudieron cargar los datos del torneo')
    }).finally(() => {
      if (mounted) setLoading(false)
    })
    return () => { mounted = false }
  }, [torneoId, selectedSeason, selectedSeasonBaseFilters, selectedMatchFilters, stageFilter, groupFilter, matchdayFilter, dateFilter])

  const stageOptions = useMemo(() => ['Todos', ...Array.from(new Set(filterMetadata?.stages ?? []))], [filterMetadata])
  const groupOptions = useMemo(() => ['Todos', ...Array.from(new Set(filterMetadata?.groups ?? []))], [filterMetadata])
  const matchdayOptions = useMemo(() => filterMetadata?.matchdays ?? [], [filterMetadata])
  const dateOptions = useMemo(() => filterMetadata?.dates ?? [], [filterMetadata])
  const showGroupFilter = groupOptions.length > 1 && (stageFilter === 'Todos' || stageFilter === 'GROUP_STAGE')

  useEffect(() => {
    if (stageFilter !== 'Todos' && stageFilter !== 'GROUP_STAGE') setGroupFilter('Todos')
  }, [stageFilter])

  const sortedTabla = useMemo(() => {
    if (!tabla) return []
    const col = sortCol as keyof TablaRow
    return [...tabla].sort((a, b) => {
      const av = Number(a[col] ?? 0)
      const bv = Number(b[col] ?? 0)
      return sortAsc ? av - bv : bv - av
    })
  }, [tabla, sortCol, sortAsc])

  const toggleSort = (col: string) => {
    if (sortCol === col) setSortAsc(!sortAsc)
    else { setSortCol(col); setSortAsc(false) }
  }

  const openDetail = (p: Partido) => {
    setSelectedMatch(p)
    setCurrentStats(null)
    setStatsLoading(true)
    getPartidoEstadisticas(p.id)
      .then(stats => setCurrentStats(stats))
      .finally(() => setStatsLoading(false))
  }

  const closeModal = () => { setSelectedMatch(null); setCurrentStats(null) }

  return (
    <main className="container py-4">
      <div className="d-flex align-items-center gap-3 mb-4">
        <Link href="/torneos" className="btn btn-outline-secondary btn-sm">&larr; Torneos</Link>
        <h3 className="mb-0">{torName || 'Torneo'}</h3>
        <span className="badge bg-secondary">{torTipo}</span>
        {temporadas.length > 0 && (
          <select
            className="form-select form-select-sm ms-auto"
            style={{ maxWidth: 160 }}
            value={selectedSeason}
            onChange={(e) => { setSelectedSeason(e.target.value); clearTournamentFilters() }}
            aria-label="Temporada"
          >
            {temporadas.map((season) => (
              <option key={season} value={season}>{season}</option>
            ))}
          </select>
        )}
      </div>

      {!loading && !error && temporadas.length > 0 && (
        <section className="card border-0 shadow-sm rounded-4 p-3 p-md-4 mb-4 bg-white">
          <div className="row g-3 align-items-center">
            <div className="col-12 col-lg">
              <div className="text-uppercase text-muted small fw-semibold">Temporada {selectedSeason}</div>
              <h4 className="mb-1">{torName || 'Torneo'}</h4>
              <div className="text-muted small">Calendario, posiciones, eliminatorias y leaders en una vista unificada.</div>
            </div>
            <div className="col-6 col-md-3 col-lg-2">
              <div className="border rounded-3 p-3 text-center">
                <div className="fs-4 fw-bold">{partidos?.length ?? 0}</div>
                <div className="small text-muted">Partidos</div>
              </div>
            </div>
            <div className="col-6 col-md-3 col-lg-2">
              <div className="border rounded-3 p-3 text-center">
                <div className="fs-4 fw-bold">{tabla?.length ?? 0}</div>
                <div className="small text-muted">Equipos</div>
              </div>
            </div>
            <div className="col-6 col-md-3 col-lg-2">
              <div className="border rounded-3 p-3 text-center">
                <div className="fs-4 fw-bold">{tablaGrupos?.length || '-'}</div>
                <div className="small text-muted">Grupos</div>
              </div>
            </div>
            <div className="col-6 col-md-3 col-lg-2">
              <div className="border rounded-3 p-3 text-center">
                <div className="fs-4 fw-bold">{bracket?.reduce((sum, round) => sum + round.matches.length, 0) ?? 0}</div>
                <div className="small text-muted">Eliminatorias</div>
              </div>
            </div>
          </div>
        </section>
      )}

      {!loading && !error && cobertura && (
        <section className="card border-0 shadow-sm rounded-4 p-3 p-md-4 mb-4 bg-white">
          <div className="d-flex flex-column flex-lg-row justify-content-between gap-3 mb-3">
            <div>
              <div className="text-uppercase text-muted small fw-semibold">Cobertura de datos</div>
              <h5 className="mb-1">Estado de la temporada {selectedSeason}</h5>
              <div className="text-muted small">
                {cobertura.partidos_esperados
                  ? `${cobertura.total_partidos}/${cobertura.partidos_esperados} partidos cargados`
                  : `${cobertura.total_partidos} partidos cargados`}
              </div>
            </div>
            {cobertura.temporada_completa !== null && (
              <span className={`badge align-self-start ${cobertura.temporada_completa ? 'text-bg-success' : 'text-bg-warning'}`}>
                {cobertura.temporada_completa ? 'Temporada completa' : `${cobertura.partidos_faltantes} faltantes`}
              </span>
            )}
          </div>
          <div className="row g-2">
            <div className="col-6 col-lg-2"><div className="border rounded-3 p-2 text-center"><strong>{cobertura.partidos_finalizados}</strong><div className="small text-muted">Finalizados</div></div></div>
            <div className="col-6 col-lg-2"><div className="border rounded-3 p-2 text-center"><strong>{cobertura.partidos_proximos}</strong><div className="small text-muted">Próximos</div></div></div>
            <div className="col-6 col-lg-2"><div className="border rounded-3 p-2 text-center"><strong>{cobertura.partidos_con_escudo}</strong><div className="small text-muted">Con escudo</div></div></div>
            <div className="col-6 col-lg-2"><div className="border rounded-3 p-2 text-center"><strong>{cobertura.partidos_con_xg}</strong><div className="small text-muted">Con xG</div></div></div>
            <div className="col-6 col-lg-2"><div className="border rounded-3 p-2 text-center"><strong>{cobertura.etapas_disponibles.length || '-'}</strong><div className="small text-muted">Etapas</div></div></div>
            <div className="col-6 col-lg-2"><div className="border rounded-3 p-2 text-center"><strong>{cobertura.jornadas_disponibles.length || '-'}</strong><div className="small text-muted">Jornadas</div></div></div>
          </div>
          {cobertura.tipo === 'mundial' && cobertura.etapas_disponibles.length > 0 && (
            <div className="small text-muted mt-3">Fases disponibles: {cobertura.etapas_disponibles.join(', ')}</div>
          )}
        </section>
      )}

      <TournamentTabs activeTab={activeTab} onChange={setActiveTab} />

      {error && <div className="alert alert-danger">{error}</div>}
      {loading && <FootballLoader />}
      {!loading && !error && temporadas.length === 0 && <div className="text-muted text-center py-5">No hay temporadas cargadas para este torneo.</div>}

      {/* ──────── TAB: CALENDARIO ──────── */}
      {!loading && !error && activeTab === 'calendario' && (
        <TournamentCalendar partidos={partidos} filters={calendarFilters} onFiltersChange={setCalendarFilters} onOpenDetail={openDetail} />
      )}

      {/* ──────── TAB: POSICIONES ──────── */}
      {!loading && !error && activeTab === 'posiciones' && (
        <TournamentTable
          tabla={tabla}
          tablaGrupos={tablaGrupos}
          sortedTabla={sortedTabla}
          sortCol={sortCol}
          sortAsc={sortAsc}
          onToggleSort={toggleSort}
        />
      )}

      {/* ──────── TAB: ELIMINATORIAS ──────── */}
      {!loading && !error && activeTab === 'eliminatorias' && (
        <TournamentBracket bracket={bracket} />
      )}

      {/* ──────── TAB: ESTADÍSTICAS ──────── */}
      {!loading && !error && activeTab === 'estadisticas' && (
        <TournamentStats tabla={tabla} partidos={partidos} />
      )}

      {/* ──── Detail Modal ──── */}
      {selectedMatch && (
        <TournamentMatchDetailModal
          selectedMatch={selectedMatch}
          currentStats={currentStats}
          statsLoading={statsLoading}
          onClose={closeModal}
        />
      )}
    </main>
  )
}
