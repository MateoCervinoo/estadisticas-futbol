import { EquipoPerfil } from '../../../../src/services/api'
import { formaBadge } from './teamPresentation'

type TeamSummaryCardsProps = {
  perfil: EquipoPerfil
}

export default function TeamSummaryCards({ perfil }: TeamSummaryCardsProps) {
  return (
    <div className="row g-3 mb-4">
      <div className="col-12 col-md-8">
        <div className="card bg-white shadow-sm border-0 rounded-3 p-4">
          <h6 className="fw-semibold mb-3">Estadísticas totales</h6>
          <div className="row text-center g-3">
            {[
              { label: 'PJ', value: perfil.stats.pj },
              { label: 'PG', value: perfil.stats.pg },
              { label: 'PE', value: perfil.stats.pe },
              { label: 'PP', value: perfil.stats.pp },
              { label: 'GF', value: perfil.stats.gf },
              { label: 'GC', value: perfil.stats.gc },
              { label: 'GD', value: perfil.stats.gd > 0 ? `+${perfil.stats.gd}` : perfil.stats.gd },
              { label: 'Pts', value: perfil.stats.pts },
            ].map((stat) => (
              <div key={stat.label} className="col-3 col-md-3">
                <div className="fw-bold fs-5">{stat.value}</div>
                <div className="small text-muted">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="col-12 col-md-4">
        <div className="card bg-white shadow-sm border-0 rounded-3 p-4 h-100">
          <h6 className="fw-semibold mb-3">Últimos 5</h6>
          {perfil.forma.length === 0 && <div className="text-muted small">Sin partidos</div>}
          <div className="vstack gap-2">
            {perfil.forma.map((form) => (
              <div key={form.partido_id} className="d-flex justify-content-between align-items-center small">
                <div>{formaBadge(form.resultado)}</div>
                <div>{form.goles_favor}-{form.goles_contra}</div>
                <div className="text-muted text-truncate ms-2" style={{ maxWidth: 120 }}>{form.rival}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
