import Link from 'next/link'
import { TablaGrupo, TablaRow } from '../../../../src/services/api'
import { flagClass } from '../../../(home)/matchPresentation'

type TournamentTableProps = {
  tabla: TablaRow[] | null
  tablaGrupos: TablaGrupo[] | null
  sortedTabla: TablaRow[]
  sortCol: string
  sortAsc: boolean
  onToggleSort: (col: string) => void
}

const hasXgCoverage = (rows: TablaRow[]) => rows.some((row) => row.xg_favor > 0 || row.xg_contra > 0 || row.xg_diff !== 0)

function Tabla({ rows, sortCol, sortAsc, onToggleSort }: { rows: TablaRow[]; sortCol: string; sortAsc: boolean; onToggleSort: (col: string) => void }) {
  const showXg = hasXgCoverage(rows)
  const displayRows = [...rows].sort((a, b) => {
    const col = sortCol as keyof TablaRow
    const primary = Number(a[col] ?? 0) - Number(b[col] ?? 0)
    if (primary !== 0) return sortAsc ? primary : -primary
    return b.pts - a.pts || b.gd - a.gd || b.gf - a.gf || a.equipo.localeCompare(b.equipo)
  })
  const sortIcon = (col: string) => {
    if (sortCol !== col) return ''
    return sortAsc ? ' ▲' : ' ▼'
  }

  return (
    <div className="table-responsive">
      <table className="table table-hover table-sm align-middle">
        <thead className="table-light">
          <tr>
            <th>#</th>
            <th>Equipo</th>
            <th className="text-center" style={{ cursor: 'pointer' }} onClick={() => onToggleSort('pj')}>PJ{sortIcon('pj')}</th>
            <th className="text-center" style={{ cursor: 'pointer' }} onClick={() => onToggleSort('pg')}>PG{sortIcon('pg')}</th>
            <th className="text-center" style={{ cursor: 'pointer' }} onClick={() => onToggleSort('pe')}>PE{sortIcon('pe')}</th>
            <th className="text-center" style={{ cursor: 'pointer' }} onClick={() => onToggleSort('pp')}>PP{sortIcon('pp')}</th>
            <th className="text-center" style={{ cursor: 'pointer' }} onClick={() => onToggleSort('gf')}>GF{sortIcon('gf')}</th>
            <th className="text-center" style={{ cursor: 'pointer' }} onClick={() => onToggleSort('gc')}>GC{sortIcon('gc')}</th>
            <th className="text-center" style={{ cursor: 'pointer' }} onClick={() => onToggleSort('gd')}>GD{sortIcon('gd')}</th>
            {showXg && <th className="text-center" style={{ cursor: 'pointer' }} onClick={() => onToggleSort('xg_favor')}>xG{sortIcon('xg_favor')}</th>}
            {showXg && <th className="text-center" style={{ cursor: 'pointer' }} onClick={() => onToggleSort('xg_contra')}>xGA{sortIcon('xg_contra')}</th>}
            {showXg && <th className="text-center" style={{ cursor: 'pointer' }} onClick={() => onToggleSort('xg_diff')}>xG Diff{sortIcon('xg_diff')}</th>}
            <th className="text-center fw-bold" style={{ cursor: 'pointer' }} onClick={() => onToggleSort('pts')}>Pts{sortIcon('pts')}</th>
          </tr>
        </thead>
        <tbody>
          {displayRows.map((row, index) => {
            const xgColor = row.xg_diff > 0 ? 'text-success' : row.xg_diff < 0 ? 'text-danger' : ''
            return (
              <tr key={row.equipo_id}>
                <td className="text-muted">{index + 1}</td>
                <td>
                  <Link href={`/equipos/${row.equipo_id}`} className="text-decoration-none text-dark d-flex align-items-center gap-2">
                    <span className={flagClass(row.equipo, row.codigo_bandera)} />
                    {row.equipo}
                  </Link>
                </td>
                <td className="text-center">{row.pj}</td>
                <td className="text-center">{row.pg}</td>
                <td className="text-center">{row.pe}</td>
                <td className="text-center">{row.pp}</td>
                <td className="text-center">{row.gf}</td>
                <td className="text-center">{row.gc}</td>
                <td className="text-center">{row.gd > 0 ? `+${row.gd}` : row.gd}</td>
                {showXg && <td className="text-center">{row.xg_favor.toFixed(2)}</td>}
                {showXg && <td className="text-center">{row.xg_contra.toFixed(2)}</td>}
                {showXg && <td className={`text-center ${xgColor}`}>{row.xg_diff > 0 ? `+${row.xg_diff.toFixed(2)}` : row.xg_diff.toFixed(2)}</td>}
                <td className="text-center fw-bold">{row.pts}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

export default function TournamentTable({ tabla, tablaGrupos, sortedTabla, sortCol, sortAsc, onToggleSort }: TournamentTableProps) {
  if (tablaGrupos && tablaGrupos.length > 0) {
    return (
      <div className="vstack gap-4">
        <div className="alert alert-light border mb-0 small text-muted">
          Las tablas por grupo se ordenan por puntos, diferencia de gol y goles a favor. Las columnas xG/xGA aparecen solo cuando hay cobertura cargada.
        </div>
        {tablaGrupos.map((group) => (
          <section key={group.grupo} className="card bg-white border-0 shadow-sm rounded-4 p-3">
            <div className="d-flex align-items-center justify-content-between mb-3">
              <h5 className="mb-0">{group.grupo.replace('GROUP_', 'Grupo ')}</h5>
              <span className="badge text-bg-secondary">{group.tabla.length} equipos</span>
            </div>
            <Tabla rows={group.tabla} sortCol={sortCol} sortAsc={sortAsc} onToggleSort={onToggleSort} />
          </section>
        ))}
      </div>
    )
  }

  return (
    <>
      {(!tabla || tabla.length === 0) && <div className="text-muted text-center py-5">No hay datos de posiciones.</div>}
      {tabla && tabla.length > 0 && (
        <div className="card bg-white border-0 shadow-sm rounded-4 p-3">
          <div className="d-flex align-items-center justify-content-between mb-3">
            <h5 className="mb-0">Tabla general</h5>
            <span className="badge text-bg-secondary">{tabla.length} equipos</span>
          </div>
          <Tabla rows={sortedTabla} sortCol={sortCol} sortAsc={sortAsc} onToggleSort={onToggleSort} />
          {!hasXgCoverage(tabla) && <div className="text-muted small mt-2">No hay datos xG/xGA cargados para esta tabla.</div>}
        </div>
      )}
    </>
  )
}
