import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { EvolutionPoint, SelectedTeam } from './types'

type EvolutionPanelProps = {
  selectedTeam: SelectedTeam | null
  evolution: EvolutionPoint[]
  loading: boolean
}

export default function EvolutionPanel({ selectedTeam, evolution, loading }: EvolutionPanelProps) {
  return (
    <div>
      {!selectedTeam && <div className="text-muted text-center py-5">Seleccioná un equipo para ver su evolución</div>}
      {loading && <div className="text-muted text-center py-5">Cargando evolución...</div>}
      {!loading && selectedTeam && evolution.length === 0 && (
        <div className="text-muted text-center py-5">No hay datos de evolución para este equipo</div>
      )}
      {!loading && evolution.length > 0 && (
        <div className="card shadow-sm border-0 rounded-3 p-3">
          <p className="small text-muted mb-3">
            Media móvil de goles a favor y en contra (ventana de 5 partidos)
          </p>
          <ResponsiveContainer width="100%" height={350}>
            <LineChart data={evolution}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="match_index" label={{ value: 'Partido #', position: 'insideBottomRight', offset: -5 }} />
              <YAxis label={{ value: 'Goles', angle: -90, position: 'insideLeft' }} />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="rolling_gf_avg" stroke="#28a745" strokeWidth={2} dot={false} name="Goles a favor (media 5)" />
              <Line type="monotone" dataKey="rolling_gc_avg" stroke="#dc3545" strokeWidth={2} dot={false} name="Goles en contra (media 5)" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}
