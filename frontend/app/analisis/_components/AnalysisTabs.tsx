import { AnalysisTab } from './types'

type AnalysisTabsProps = {
  tab: AnalysisTab
  onChange: (tab: AnalysisTab) => void
}

const tabs: { key: AnalysisTab; label: string; kicker: string }[] = [
  { key: 'evolution', label: 'Evolución', kicker: 'forma y xG' },
  { key: 'xg-vs-real', label: 'Ranking xG', kicker: 'calidad vs eficacia' },
  { key: 'distribucion', label: 'Distribución', kicker: 'goles esperados' },
]

export default function AnalysisTabs({ tab, onChange }: AnalysisTabsProps) {
  return (
    <div className="analysis-tabs mb-4" role="tablist" aria-label="Vistas de análisis">
      {tabs.map((item) => (
        <button key={item.key} className={`analysis-tab ${tab === item.key ? 'active' : ''}`} onClick={() => onChange(item.key)}>
          <span>{item.label}</span>
          <small>{item.kicker}</small>
        </button>
      ))}
    </div>
  )
}
