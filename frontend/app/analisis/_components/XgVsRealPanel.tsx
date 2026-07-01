import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { XgVsRealRow } from './types'

type XgVsRealPanelProps = {
  xgData: XgVsRealRow[]
  loading: boolean
  error?: string | null
  onDownloadCSV: () => void
}

export default function XgVsRealPanel({ xgData, loading, error, onDownloadCSV }: XgVsRealPanelProps) {
  const xgRanking = [...xgData].sort((a, b) => b.xg_diff - a.xg_diff).slice(0, 8)
  const over = [...xgData].sort((a, b) => b.diferencia - a.diferencia).slice(0, 6)
  const under = [...xgData].sort((a, b) => a.diferencia - b.diferencia).slice(0, 6)
  const defensive = [...xgData].sort((a, b) => a.xga_p90 - b.xga_p90).slice(0, 6)

  return (
    <div>
      {loading && <LoadingState text="Cargando ranking xG..." />}
      {error && !loading && <EmptyState title="Error de carga" text={error} tone="danger" />}
      {!error && !loading && xgData.length === 0 && (
        <EmptyState title="No hay datos xG disponibles" text="Cuando existan partidos finalizados con xG, se mostrarán rankings de volumen, balance y eficiencia." />
      )}
      {!error && !loading && xgData.length > 0 && (
        <div>
          <div className="d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3 mb-3">
            <div>
              <span className="analysis-eyebrow dark">Modelo ofensivo</span>
              <h2 className="h4 fw-bold mb-0">xG, xGA y eficiencia real</h2>
            </div>
            <button className="btn btn-dark btn-sm rounded-pill px-3" onClick={onDownloadCSV}>Exportar CSV</button>
          </div>
          <div className="analysis-ranking-grid mb-4">
            <RankingCard title="Balance xG" subtitle="xG - xGA" rows={xgRanking} value={(row) => row.xg_diff} positive />
            <RankingCard title="Overperformance" subtitle="Goles - xG" rows={over} value={(row) => row.diferencia} positive />
            <RankingCard title="Underperformance" subtitle="Goles - xG" rows={under} value={(row) => row.diferencia} />
            <RankingCard title="Defensa elite" subtitle="xGA p90 menor" rows={defensive} value={(row) => row.xga_p90} />
          </div>
          <div className="analysis-card mb-4">
            <div className="analysis-card-header">
              <div>
                <span className="analysis-eyebrow dark">Comparativa visual</span>
                <h2>Producción por 90 minutos</h2>
              </div>
              <span className="analysis-chip">Top 24 por goles</span>
            </div>
            <ResponsiveContainer width="100%" height={560}>
              <BarChart data={xgData.slice(0, 24)} layout="vertical" margin={{ left: 108, right: 12 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(15, 23, 42, 0.1)" />
                <XAxis type="number" />
                <YAxis type="category" dataKey="nombre" width={110} tick={{ fontSize: 11 }} />
                <Tooltip formatter={(value) => Number(value).toFixed(2)} />
                <Legend />
                <Bar dataKey="goles_p90" fill="#16a34a" name="Goles p90" radius={[0, 6, 6, 0]} />
                <Bar dataKey="xg_p90" fill="#f59e0b" name="xG p90" radius={[0, 6, 6, 0]} />
                <Bar dataKey="xga_p90" fill="#ef4444" name="xGA p90" radius={[0, 6, 6, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="analysis-card analysis-table-card">
            <div className="analysis-card-header">
              <h2>Tabla analítica completa</h2>
              <span className="analysis-chip">{xgData.length} equipos</span>
            </div>
            <div className="table-responsive">
              <table className="table table-sm align-middle analysis-table">
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
                      <td className="fw-semibold">{row.codigo_bandera && <span className={`fi fi-${row.codigo_bandera} me-1`} />}{row.nombre}</td>
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

function RankingCard({ title, subtitle, rows, value, positive }: { title: string; subtitle: string; rows: XgVsRealRow[]; value: (row: XgVsRealRow) => number; positive?: boolean }) {
  return (
    <div className="analysis-card analysis-ranking-card">
      <span className="analysis-eyebrow dark">{subtitle}</span>
      <h3>{title}</h3>
      <div className="analysis-ranking-list">
        {rows.map((row, index) => {
          const val = value(row)
          return (
            <div className="analysis-ranking-row" key={`${title}-${row.equipo_id}`}>
              <span className="analysis-rank">{index + 1}</span>
              <span className="text-truncate">{row.nombre}</span>
              <strong className={positive && val > 0 ? 'text-success' : val < 0 ? 'text-danger' : ''}>{val > 0 ? '+' : ''}{val}</strong>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function LoadingState({ text }: { text: string }) {
  return <div className="analysis-empty-state"><div className="analysis-loader" /><strong>{text}</strong></div>
}

function EmptyState({ title, text, tone }: { title: string; text: string; tone?: 'danger' }) {
  return <div className={`analysis-empty-state ${tone === 'danger' ? 'danger' : ''}`}><strong>{title}</strong><span>{text}</span></div>
}
