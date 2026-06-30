import Link from 'next/link'
import { TablaGrupo, TablaRow } from '../../../../src/services/api'

type TournamentTableProps = {
  tabla: TablaRow[] | null
  tablaGrupos: TablaGrupo[] | null
  sortedTabla: TablaRow[]
  sortCol: string
  sortAsc: boolean
  onToggleSort: (col: string) => void
}

function Tabla({ rows, sortCol, sortAsc, onToggleSort }: { rows: TablaRow[]; sortCol: string; sortAsc: boolean; onToggleSort: (col: string) => void }) {
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
            <th className="text-center" style={{ cursor: 'pointer' }} onClick={() => onToggleSort('xg_diff')}>xG Diff{sortIcon('xg_diff')}</th>
            <th className="text-center fw-bold" style={{ cursor: 'pointer' }} onClick={() => onToggleSort('pts')}>Pts{sortIcon('pts')}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => {
            const xgColor = row.xg_diff > 0 ? 'text-success' : row.xg_diff < 0 ? 'text-danger' : ''
            return (
              <tr key={row.equipo_id}>
                <td className="text-muted">{index + 1}</td>
                <td>
                  <Link href={`/equipos/${row.equipo_id}`} className="text-decoration-none text-dark d-flex align-items-center gap-2">
                    {row.codigo_bandera && <span className={`fi fi-${row.codigo_bandera}`} />}
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
                <td className={`text-center ${xgColor}`}>{row.xg_diff > 0 ? `+${row.xg_diff}` : row.xg_diff}</td>
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
        {tablaGrupos.map((group) => (
          <section key={group.grupo}>
            <h5 className="mb-3">{group.grupo.replace('GROUP_', 'Grupo ')}</h5>
            <Tabla rows={group.tabla} sortCol={sortCol} sortAsc={sortAsc} onToggleSort={onToggleSort} />
          </section>
        ))}
      </div>
    )
  }

  return (
    <>
      {(!tabla || tabla.length === 0) && <div className="text-muted text-center py-5">No hay datos de posiciones.</div>}
      {tabla && tabla.length > 0 && <Tabla rows={sortedTabla} sortCol={sortCol} sortAsc={sortAsc} onToggleSort={onToggleSort} />}
    </>
  )
}
