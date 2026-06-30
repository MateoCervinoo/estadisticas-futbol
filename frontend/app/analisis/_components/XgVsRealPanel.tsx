import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { XgVsRealRow } from './types'

type XgVsRealPanelProps = {
  xgData: XgVsRealRow[]
  loading: boolean
  onDownloadCSV: () => void
}

export default function XgVsRealPanel({ xgData, loading, onDownloadCSV }: XgVsRealPanelProps) {
  return (
    <div>
      {loading && <div className="text-muted text-center py-5">Cargando datos xG...</div>}
      {!loading && xgData.length === 0 && (
        <div className="text-muted text-center py-5">No hay datos xG disponibles</div>
      )}
      {!loading && xgData.length > 0 && (
        <div>
          <div className="d-flex justify-content-end mb-2">
            <button className="btn btn-sm btn-outline-secondary" onClick={onDownloadCSV}>
              Exportar CSV
            </button>
          </div>
          <div className="card shadow-sm border-0 rounded-3 p-3">
            <p className="small text-muted mb-3">Goles reales, xG y xGA por equipo (todos los torneos)</p>
            <ResponsiveContainer width="100%" height={500}>
              <BarChart data={xgData.slice(0, 30)} layout="vertical" margin={{ left: 120 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" />
                <YAxis type="category" dataKey="nombre" width={110} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Legend />
                <Bar dataKey="goles_p90" fill="#28a745" name="Goles p90" />
                <Bar dataKey="xg_p90" fill="#ffc107" name="xG p90" />
                <Bar dataKey="xga_p90" fill="#dc3545" name="xGA p90" />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-3">
            <div className="table-responsive">
              <table className="table table-sm table-striped">
                <thead>
                  <tr>
                    <th>Equipo</th>
                    <th className="text-end">PJ</th>
                    <th className="text-end">Goles</th>
                    <th className="text-end">xG</th>
                    <th className="text-end">xGA</th>
                    <th className="text-end">G-xG</th>
                    <th className="text-end">xG-xGA</th>
                    <th className="text-end">G/p90</th>
                    <th className="text-end">xG/p90</th>
                    <th className="text-end">xGA/p90</th>
                  </tr>
                </thead>
                <tbody>
                  {xgData.map((row) => (
                    <tr key={row.equipo_id}>
                      <td>{row.codigo_bandera && <span className={`fi fi-${row.codigo_bandera} me-1`} />}{row.nombre}</td>
                      <td className="text-end">{row.pj}</td>
                      <td className="text-end">{row.goles}</td>
                      <td className="text-end">{row.xg}</td>
                      <td className="text-end">{row.xga}</td>
                      <td className={`text-end fw-semibold ${row.diferencia > 0 ? 'text-success' : row.diferencia < 0 ? 'text-danger' : ''}`}>
                        {row.diferencia > 0 ? '+' : ''}{row.diferencia}
                      </td>
                      <td className={`text-end fw-semibold ${row.xg_diff > 0 ? 'text-success' : row.xg_diff < 0 ? 'text-danger' : ''}`}>
                        {row.xg_diff > 0 ? '+' : ''}{row.xg_diff}
                      </td>
                      <td className="text-end">{row.goles_p90}</td>
                      <td className="text-end">{row.xg_p90}</td>
                      <td className="text-end">{row.xga_p90}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
