"use client"

import AnalysisTabs from './_components/AnalysisTabs'
import DistributionPanel from './_components/DistributionPanel'
import EvolutionPanel from './_components/EvolutionPanel'
import TeamSelector from './_components/TeamSelector'
import useAnalysisData from './_components/useAnalysisData'
import XgVsRealPanel from './_components/XgVsRealPanel'

export default function AnalisisPage() {
  const {
    tab,
    setTab,
    teamType,
    teamQuery,
    setTeamQuery,
    teams,
    selectedTeam,
    setSelectedTeam,
    evolution,
    distribucion,
    xgData,
    evolLoading,
    xgLoading,
    distLoading,
    teamSearchError,
    evolError,
    xgError,
    distError,
    selectTeam,
    changeTeamType,
    downloadCSV,
  } = useAnalysisData()

  const topXgTeam = [...xgData].sort((a, b) => b.xg_diff - a.xg_diff)[0]
  const overperformer = [...xgData].sort((a, b) => b.diferencia - a.diferencia)[0]
  const underperformer = [...xgData].sort((a, b) => a.diferencia - b.diferencia)[0]
  const selectedEvolution = evolution.length > 0 ? evolution[evolution.length - 1] : null
  const xgCoverage = xgData.length

  return (
    <main className="analysis-shell min-vh-100 text-dark">
      <div className="container py-4 py-lg-5">
        <section className="analysis-hero mb-4">
          <div className="row g-4 align-items-end">
            <div className="col-lg-7">
              <span className="analysis-eyebrow">Centro de inteligencia</span>
              <h1 className="display-6 fw-bold mb-3">Análisis avanzado de rendimiento</h1>
              <p className="analysis-hero-copy mb-0">
                Lectura de forma, calidad de ocasiones y eficiencia ofensiva para detectar tendencias antes de que aparezcan en la tabla.
              </p>
            </div>
            <div className="col-lg-5">
              <TeamSelector
                teamType={teamType}
                teamQuery={teamQuery}
                teams={teams}
                selectedTeam={selectedTeam}
                error={teamSearchError}
                onChangeTeamType={changeTeamType}
                onChangeQuery={setTeamQuery}
                onSelectTeam={selectTeam}
                onClearTeam={() => setSelectedTeam(null)}
              />
            </div>
          </div>
        </section>

        <section className="row g-3 mb-4">
          <div className="col-6 col-xl-3">
            <div className="analysis-kpi-card">
              <span>Equipos medidos</span>
              <strong>{xgLoading ? '...' : xgCoverage}</strong>
              <small>{teamType === 'club' ? 'Clubes' : 'Selecciones'} con partidos finalizados</small>
            </div>
          </div>
          <div className="col-6 col-xl-3">
            <div className="analysis-kpi-card accent-green">
              <span>Mejor balance xG</span>
              <strong>{topXgTeam ? `${topXgTeam.xg_diff > 0 ? '+' : ''}${topXgTeam.xg_diff}` : '-'}</strong>
              <small>{topXgTeam?.nombre || 'Sin datos xG'}</small>
            </div>
          </div>
          <div className="col-6 col-xl-3">
            <div className="analysis-kpi-card accent-gold">
              <span>Overperformance</span>
              <strong>{overperformer ? `${overperformer.diferencia > 0 ? '+' : ''}${overperformer.diferencia}` : '-'}</strong>
              <small>{overperformer?.nombre || 'Goles - xG'}</small>
            </div>
          </div>
          <div className="col-6 col-xl-3">
            <div className="analysis-kpi-card accent-red">
              <span>Equipo seleccionado</span>
              <strong>{selectedEvolution ? selectedEvolution.rolling_gf_avg.toFixed(2) : '-'}</strong>
              <small>{selectedTeam ? 'GF media movil 5P' : underperformer ? `Under: ${underperformer.nombre}` : 'Selecciona un equipo'}</small>
            </div>
          </div>
        </section>

        <AnalysisTabs tab={tab} onChange={setTab} />

        {tab === 'evolution' && (
          <EvolutionPanel selectedTeam={selectedTeam} evolution={evolution} loading={evolLoading} error={evolError} />
        )}

        {tab === 'xg-vs-real' && (
          <XgVsRealPanel xgData={xgData} loading={xgLoading} error={xgError} onDownloadCSV={downloadCSV} />
        )}

        {tab === 'distribucion' && (
          <DistributionPanel selectedTeam={selectedTeam} distribucion={distribucion} loading={distLoading} error={distError} />
        )}
      </div>
    </main>
  )
}
