import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { DistributionPoint, SelectedTeam } from './types'

type DistributionPanelProps = {
  selectedTeam: SelectedTeam | null
  distribucion: DistributionPoint[]
  loading: boolean
  error?: string | null
}

export default function DistributionPanel({ selectedTeam, distribucion, loading, error }: DistributionPanelProps) {
  const peak = [...distribucion].sort((a, b) => b.actual_pct - a.actual_pct)[0]
  const avgBucket = distribucion.reduce((acc, item) => acc + item.goles * (item.actual_pct / 100), 0)

  return (
    <div className="analysis-panel-grid">
      {!selectedTeam && <EmptyState title="Selecciona un equipo" text="La distribución compara frecuencia real de goles anotados contra una curva Poisson esperada." />}
      {loading && <LoadingState text="Cargando distribución de goles..." />}
      {error && !loading && <EmptyState title="Error de carga" text={error} tone="danger" />}
      {!error && !loading && selectedTeam && distribucion.length === 0 && (
        <EmptyState title="Sin distribución disponible" text="Hace falta al menos una muestra de partidos finalizados para estimar los porcentajes." />
      )}
      {!error && !loading && distribucion.length > 0 && (
        <>
          <div className="analysis-card analysis-main-chart">
            <div className="analysis-card-header">
              <div>
                <span className="analysis-eyebrow dark">Perfil de gol</span>
                <h2>Distribución real vs Poisson</h2>
              </div>
              <span className="analysis-chip">{selectedTeam?.nombre}</span>
            </div>
            <ResponsiveContainer width="100%" height={380}>
              <BarChart data={distribucion} margin={{ top: 12, right: 12, left: -16, bottom: 8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(15, 23, 42, 0.1)" />
                <XAxis dataKey="goles" tickLine={false} axisLine={false} />
                <YAxis tickLine={false} axisLine={false} tickFormatter={(value) => `${value}%`} />
                <Tooltip formatter={(value) => `${Number(value).toFixed(1)}%`} labelFormatter={(label) => `${label} goles`} />
              <Legend />
                <Bar dataKey="actual_pct" fill="#16a34a" name="Real %" radius={[8, 8, 0, 0]} />
                <Bar dataKey="poisson_pct" fill="#f59e0b" name="Poisson %" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
          </div>
          <aside className="analysis-card analysis-side-card">
            <span className="analysis-eyebrow dark">Lectura rápida</span>
            <h3>Patrón anotador</h3>
            <div className="analysis-metric-list">
              <Metric label="Goles más frecuentes" value={peak ? `${peak.goles}` : '-'} positive />
              <Metric label="Frecuencia pico" value={peak ? `${peak.actual_pct}%` : '-'} positive />
              <Metric label="Media estimada" value={avgBucket.toFixed(2)} positive />
              <Metric label="Buckets medidos" value={distribucion.length} />
            </div>
          </aside>
        </>
      )}
    </div>
  )
}

function Metric({ label, value, positive }: { label: string; value: string | number; positive?: boolean }) {
  return (
    <div className="analysis-metric-row">
      <span>{label}</span>
      <strong className={positive ? 'text-success' : ''}>{value}</strong>
    </div>
  )
}

function LoadingState({ text }: { text: string }) {
  return <div className="analysis-empty-state"><div className="analysis-loader" /><strong>{text}</strong></div>
}

function EmptyState({ title, text, tone }: { title: string; text: string; tone?: 'danger' }) {
  return <div className={`analysis-empty-state ${tone === 'danger' ? 'danger' : ''}`}><strong>{title}</strong><span>{text}</span></div>
}
