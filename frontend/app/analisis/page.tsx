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
    selectTeam,
    changeTeamType,
    downloadCSV,
  } = useAnalysisData()

  return (
    <main className="min-vh-100 bg-light p-4 text-dark">
      <div className="container mt-3">
        <h4 className="mb-3">
          Análisis Avanzado
          <small className="text-muted ms-2" style={{ fontSize: '0.7rem' }}>Evolución, xG vs real y distribución Poisson</small>
        </h4>

        <TeamSelector
          teamType={teamType}
          teamQuery={teamQuery}
          teams={teams}
          selectedTeam={selectedTeam}
          onChangeTeamType={changeTeamType}
          onChangeQuery={setTeamQuery}
          onSelectTeam={selectTeam}
          onClearTeam={() => setSelectedTeam(null)}
        />

        <AnalysisTabs tab={tab} onChange={setTab} />

        {tab === 'evolution' && (
          <EvolutionPanel selectedTeam={selectedTeam} evolution={evolution} loading={evolLoading} />
        )}

        {tab === 'xg-vs-real' && (
          <XgVsRealPanel xgData={xgData} loading={xgLoading} onDownloadCSV={downloadCSV} />
        )}

        {tab === 'distribucion' && (
          <DistributionPanel selectedTeam={selectedTeam} distribucion={distribucion} loading={distLoading} />
        )}
      </div>
    </main>
  )
}
