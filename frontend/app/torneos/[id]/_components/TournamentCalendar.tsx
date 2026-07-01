import { Partido } from '../../../../src/services/api'
import { dateKey, formatDateLabel, groupOf, isPlayed, stageOf } from '../../../(home)/matchPresentation'
import TournamentMatchCard from './TournamentMatchCard'

type TournamentCalendarProps = {
  partidos: Partido[] | null
  filters: CalendarFilters
  onFiltersChange: (filters: CalendarFilters) => void
  onOpenDetail: (partido: Partido) => void
}

export type CalendarFilters = {
  matchday: string
  stage: string
  group: string
  date: string
}

const emptyFilters: CalendarFilters = { matchday: '', stage: '', group: '', date: '' }

const byDate = (a: Partido, b: Partido) => new Date(a.date).getTime() - new Date(b.date).getTime()

const optionLabel = (kind: keyof CalendarFilters, value: string) => {
  if (kind === 'matchday') return `Jornada ${value}`
  if (kind === 'stage') return stageOf({ stage: value } as Partido) || value
  if (kind === 'group') return groupOf({ group: value } as Partido)
  if (kind === 'date') return formatDateLabel(`${value}T12:00:00Z`)
  return value
}

const unique = (values: (string | number | null | undefined)[]) => (
  [...new Set(values.filter((value) => value !== null && value !== undefined && String(value).trim() !== '').map(String))]
)

export default function TournamentCalendar({ partidos, filters, onFiltersChange, onOpenDetail }: TournamentCalendarProps) {
  if (!partidos || partidos.length === 0) {
    return <div className="text-muted text-center py-5">No hay partidos para este torneo.</div>
  }

  const stages = unique(partidos.map((partido) => partido.stage)).sort()
  const groups = unique(partidos.map((partido) => partido.group)).sort()
  const matchdays = unique(partidos.map((partido) => partido.matchday)).sort((a, b) => Number(a) - Number(b))
  const dates = unique(partidos.map((partido) => dateKey(partido.date))).sort()
  const filtered = partidos.filter((partido) => {
    if (filters.matchday && String(partido.matchday ?? '') !== filters.matchday) return false
    if (filters.stage && partido.stage !== filters.stage) return false
    if (filters.group && partido.group !== filters.group) return false
    if (filters.date && dateKey(partido.date) !== filters.date) return false
    return true
  }).sort(byDate)
  const playedCount = partidos.filter(isPlayed).length
  const xgCount = partidos.filter((partido) => partido.home_xg !== null || partido.away_xg !== null).length

  const setFilter = (key: keyof CalendarFilters, value: string) => onFiltersChange({ ...filters, [key]: value })

  return (
    <div className="vstack gap-4">
      <section className="card bg-white shadow-sm border-0 rounded-4 p-3 p-md-4">
        <div className="d-flex flex-column flex-lg-row gap-3 justify-content-between">
          <div>
            <h5 className="mb-1">Calendario</h5>
            <div className="text-muted small">Filtrá por jornada, etapa, grupo o fecha sin recargar el torneo.</div>
          </div>
          <div className="d-flex flex-wrap gap-2">
            <span className="badge text-bg-dark">{partidos.length} partidos</span>
            <span className="badge text-bg-success">{playedCount} jugados</span>
            <span className="badge text-bg-secondary">{partidos.length - playedCount} pendientes</span>
            <span className="badge text-bg-info">{filtered.length} visibles</span>
            {xgCount > 0 && <span className="badge text-bg-warning">{xgCount} con xG</span>}
          </div>
        </div>
        <div className="row g-2 mt-3">
          {([
            ['matchday', 'Jornada', matchdays],
            ['stage', 'Etapa', stages],
            ['group', 'Grupo', groups],
            ['date', 'Fecha', dates],
          ] as [keyof CalendarFilters, string, string[]][]).map(([key, label, values]) => (
            <div key={key} className="col-12 col-sm-6 col-lg-3">
              <label className="form-label small text-muted mb-1">{label}</label>
              <select className="form-select form-select-sm" value={filters[key]} onChange={(event) => setFilter(key, event.target.value)}>
                <option value="">Todos</option>
                {values.map((value) => <option key={value} value={value}>{optionLabel(key, value)}</option>)}
              </select>
            </div>
          ))}
        </div>
        {(filters.matchday || filters.stage || filters.group || filters.date) && (
          <div className="mt-3">
            <button className="btn btn-outline-secondary btn-sm rounded-pill" onClick={() => onFiltersChange(emptyFilters)}>Limpiar filtros</button>
          </div>
        )}
      </section>

      {filtered.length === 0 ? (
        <div className="text-muted text-center py-5">No hay partidos con los filtros seleccionados.</div>
      ) : (
        <div className="row">
          {filtered.map((partido) => <TournamentMatchCard key={partido.id} partido={partido} onOpenDetail={onOpenDetail} />)}
        </div>
      )}
    </div>
  )
}
