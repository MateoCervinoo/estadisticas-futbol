"use client"

import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import {
  getTablaPosiciones, getBracket, getPartidos, getPartidoEstadisticas, getTorneoTemporadas,
  getPartidoFilterMetadata, getTorneoCobertura,
  TablaRow, TablaGrupo, BracketRound, Partido, PartidoEstadisticas, PartidoFilterMetadata, TorneoCobertura,
} from '../../../src/services/api'
import TournamentBracket from './_components/TournamentBracket'
import TournamentMatchCard from './_components/TournamentMatchCard'
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
    setFilterMetadata(null)
    setCobertura(null)
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

      {temporadas.length > 0 && (
        <div className="card bg-white shadow-sm border-0 rounded-3 p-3 mb-4">
          <div className="d-flex flex-wrap align-items-end gap-3">
            {stageOptions.length > 1 && (
              <label className="form-label small mb-0">
                Etapa
                <select className="form-select form-select-sm mt-1" value={stageFilter} onChange={(e) => setStageFilter(e.target.value)}>
                  {stageOptions.map((stage) => <option key={stage} value={stage}>{stage}</option>)}
                </select>
              </label>
            )}
            {showGroupFilter && (
              <label className="form-label small mb-0">
                Grupo
                <select className="form-select form-select-sm mt-1" value={groupFilter} onChange={(e) => setGroupFilter(e.target.value)}>
                  {groupOptions.map((group) => <option key={group} value={group}>{group}</option>)}
                </select>
              </label>
            )}
            {matchdayOptions.length > 0 && (
              <label className="form-label small mb-0">
                Jornada
                <select className="form-select form-select-sm mt-1" value={matchdayFilter} onChange={(e) => setMatchdayFilter(e.target.value)}>
                  <option value="">Todas</option>
                  {matchdayOptions.map((matchday) => <option key={matchday} value={matchday}>Jornada {matchday}</option>)}
                </select>
              </label>
            )}
            {dateOptions.length > 0 && (
              <label className="form-label small mb-0">
                Fecha
                <select className="form-select form-select-sm mt-1" value={dateFilter} onChange={(e) => setDateFilter(e.target.value)}>
                  <option value="">Todas</option>
                  {dateOptions.map((date) => <option key={date} value={date}>{date}</option>)}
                </select>
              </label>
            )}
            <button className="btn btn-outline-secondary btn-sm ms-auto" onClick={clearTournamentFilters}>Limpiar filtros</button>
          </div>
        </div>
      )}

      {cobertura && (
        <div className="card bg-white shadow-sm border-0 rounded-3 p-3 mb-4">
          <div className="d-flex flex-wrap align-items-center justify-content-between gap-3 mb-3">
            <div>
              <div className="fw-semibold">Cobertura de datos</div>
              <div className="small text-muted">Totales según la temporada y filtros seleccionados</div>
            </div>
            {cobertura.partidos_esperados !== null && (
              <span className={`badge ${cobertura.temporada_completa ? 'bg-success' : 'bg-warning text-dark'}`}>
                {cobertura.temporada_completa ? 'Temporada completa' : `Incompleta: faltan ${cobertura.partidos_faltantes}`}
              </span>
            )}
          </div>
          <div className="row g-2 small">
            <div className="col-6 col-md-2"><strong>{cobertura.total_partidos}</strong><div className="text-muted">partidos</div></div>
            <div className="col-6 col-md-2"><strong>{cobertura.partidos_finalizados}</strong><div className="text-muted">finalizados</div></div>
            <div className="col-6 col-md-2"><strong>{cobertura.partidos_proximos}</strong><div className="text-muted">próximos</div></div>
            <div className="col-6 col-md-2"><strong>{cobertura.partidos_con_escudo}</strong><div className="text-muted">con escudo</div></div>
            <div className="col-6 col-md-2"><strong>{cobertura.partidos_con_xg}</strong><div className="text-muted">con xG</div></div>
            <div className="col-6 col-md-2"><strong>{cobertura.partidos_esperados ?? '-'}</strong><div className="text-muted">esperados</div></div>
          </div>
          <div className="small text-muted mt-3">
            Etapas disponibles: {cobertura.etapas_disponibles.length > 0 ? cobertura.etapas_disponibles.join(', ') : 'sin datos'}.
            {torTipo === 'mundial' && !cobertura.etapas_disponibles.some((stage) => stage !== 'GROUP_STAGE') && ' La fuente todavía no trae eliminatorias para esta selección.'}
          </div>
          {cobertura.jornadas_disponibles.length > 0 && (
            <div className="small text-muted mt-1">Jornadas disponibles: {cobertura.jornadas_disponibles.join(', ')}</div>
          )}
        </div>
      )}

      <TournamentTabs activeTab={activeTab} onChange={setActiveTab} />

      {error && <div className="alert alert-danger">{error}</div>}
      {loading && <div className="text-muted">Cargando...</div>}
      {!loading && !error && temporadas.length === 0 && <div className="text-muted text-center py-5">No hay temporadas cargadas para este torneo.</div>}

      {/* ──────── TAB: CALENDARIO ──────── */}
      {!loading && !error && activeTab === 'calendario' && (
        <div>
          {(!partidos || partidos.length === 0) && (
            <div className="text-muted text-center py-5">No hay partidos para este torneo.</div>
          )}
          <div className="row">
            {partidos?.map((partido) => (
              <TournamentMatchCard key={partido.id} partido={partido} onOpenDetail={openDetail} />
            ))}
          </div>
        </div>
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
        <TournamentStats tabla={tabla} />
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
