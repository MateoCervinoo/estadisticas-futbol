"use client"

import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import {
  getTablaPosiciones, getBracket, getPartidos, getPartidoEstadisticas, getTorneoTemporadas,
  TablaRow, TablaGrupo, BracketRound, Partido, PartidoEstadisticas,
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

  useEffect(() => {
    if (!selectedSeason) return
    let mounted = true
    setLoading(true)
    setError(null)
    setTabla(null)
    setTablaGrupos(null)
    setBracketData(null)
    setPartidos(null)
    const seasonFilters = /^\d{4}$/.test(selectedSeason)
      ? { year: Number(selectedSeason), grouped: true }
      : { season: selectedSeason, grouped: true }
    const matchFilters = /^\d{4}$/.test(selectedSeason)
      ? { torneo_id: torneoId, year: Number(selectedSeason) }
      : { torneo_id: torneoId, season: selectedSeason }
    Promise.all([
      getTablaPosiciones(torneoId, seasonFilters),
      getBracket(torneoId, seasonFilters),
      getPartidos(matchFilters),
    ]).then(([t, b, ps]) => {
      if (!mounted) return
      setTabla(t.tabla)
      setTablaGrupos(t.grupos ?? null)
      setTorName(t.torneo)
      setTorTipo(t.tipo)
      setBracketData(b.bracket)
      setPartidos(ps)
    }).catch((err) => {
      if (!mounted) return
      setError(err instanceof Error ? err.message : 'No se pudieron cargar los datos del torneo')
    }).finally(() => {
      if (mounted) setLoading(false)
    })
    return () => { mounted = false }
  }, [torneoId, selectedSeason])

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
            onChange={(e) => setSelectedSeason(e.target.value)}
            aria-label="Temporada"
          >
            {temporadas.map((season) => (
              <option key={season} value={season}>{season}</option>
            ))}
          </select>
        )}
      </div>

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
