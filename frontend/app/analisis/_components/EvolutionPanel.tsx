import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { EvolutionPoint, SelectedTeam } from './types'

type EvolutionPanelProps = {
  selectedTeam: SelectedTeam | null
  evolution: EvolutionPoint[]
  loading: boolean
  error?: string | null
}

export default function EvolutionPanel({ selectedTeam, evolution, loading, error }: EvolutionPanelProps) {
  const latest = evolution[evolution.length - 1]
  const hasXg = evolution.some((point) => point.xg_favor !== null && point.xg_favor !== undefined)

  return (
    <div className="analysis-panel-grid">
      {!selectedTeam && <EmptyState title="Selecciona un equipo" text="La evolución combina goles, goles concedidos y xG por partido cuando el backend tiene esos datos." />}
      {loading && <LoadingState text="Cargando evolución del equipo..." />}
      {error && !loading && <EmptyState title="Error de carga" text={error} tone="danger" />}
      {!error && !loading && selectedTeam && evolution.length === 0 && (
        <EmptyState title="Sin muestra suficiente" text="No encontramos partidos finalizados para construir la curva de rendimiento." />
      )}
      {!error && !loading && evolution.length > 0 && (
        <>
          <div className="analysis-card analysis-main-chart">
            <div className="analysis-card-header">
              <div>
                <span className="analysis-eyebrow dark">Forma reciente</span>
                <h2>Curva ataque/defensa</h2>
              </div>
              <span className="analysis-chip">Ventana 5 partidos</span>
            </div>
            <ResponsiveContainer width="100%" height={380}>
              <LineChart data={evolution} margin={{ top: 12, right: 12, left: -16, bottom: 8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(15, 23, 42, 0.1)" />
                <XAxis dataKey="match_index" tick={{ fontSize: 12 }} tickLine={false} axisLine={false} />
                <YAxis tick={{ fontSize: 12 }} tickLine={false} axisLine={false} />
                <Tooltip formatter={(value) => Number(value).toFixed(2)} labelFormatter={(label) => `Partido #${label}`} />
              <Legend />
                <Line type="monotone" dataKey="rolling_gf_avg" stroke="#16a34a" strokeWidth={3} dot={false} name="GF media 5" />
                <Line type="monotone" dataKey="rolling_gc_avg" stroke="#ef4444" strokeWidth={3} dot={false} name="GC media 5" />
                {hasXg && <Line type="monotone" dataKey="xg_favor" stroke="#f59e0b" strokeWidth={2} dot={false} name="xG" />}
                {hasXg && <Line type="monotone" dataKey="xg_contra" stroke="#64748b" strokeWidth={2} dot={false} name="xGA" />}
            </LineChart>
          </ResponsiveContainer>
          </div>
          <aside className="analysis-card analysis-side-card">
            <span className="analysis-eyebrow dark">Lectura rápida</span>
            <h3>{selectedTeam?.nombre}</h3>
            <div className="analysis-metric-list">
              <Metric label="Partidos analizados" value={evolution.length} />
              <Metric label="GF media movil" value={latest?.rolling_gf_avg.toFixed(2) ?? '-'} positive />
              <Metric label="GC media movil" value={latest?.rolling_gc_avg.toFixed(2) ?? '-'} />
              <Metric label="Último xG" value={latest?.xg_favor?.toFixed(2) ?? 'Sin dato'} positive />
              <Metric label="Último xGA" value={latest?.xg_contra?.toFixed(2) ?? 'Sin dato'} />
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
