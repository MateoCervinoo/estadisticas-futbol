import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { DistributionPoint, SelectedTeam } from './types'

type DistributionPanelProps = {
  selectedTeam: SelectedTeam | null
  distribucion: DistributionPoint[]
  loading: boolean
}

export default function DistributionPanel({ selectedTeam, distribucion, loading }: DistributionPanelProps) {
  return (
    <div>
      {!selectedTeam && <div className="text-muted text-center py-5">Seleccioná un equipo para ver su distribución Poisson</div>}
      {loading && <div className="text-muted text-center py-5">Cargando distribución...</div>}
      {!loading && selectedTeam && distribucion.length === 0 && (
        <div className="text-muted text-center py-5">No hay datos de distribución para este equipo</div>
      )}
      {!loading && distribucion.length > 0 && (
        <div className="card shadow-sm border-0 rounded-3 p-3">
          <p className="small text-muted mb-3">
            Frecuencia real de goles anotados vs. distribución Poisson esperada
          </p>
          <ResponsiveContainer width="100%" height={350}>
            <BarChart data={distribucion}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="goles" label={{ value: 'Goles anotados', position: 'insideBottomRight', offset: -5 }} />
              <YAxis label={{ value: '%', angle: -90, position: 'insideLeft' }} />
              <Tooltip />
              <Legend />
              <Bar dataKey="actual_pct" fill="#28a745" name="Real %" />
              <Bar dataKey="poisson_pct" fill="#ffc107" name="Poisson %" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}
