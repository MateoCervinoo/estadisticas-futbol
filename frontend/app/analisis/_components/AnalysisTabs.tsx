import { AnalysisTab } from './types'

type AnalysisTabsProps = {
  tab: AnalysisTab
  onChange: (tab: AnalysisTab) => void
}

const tabs: { key: AnalysisTab; label: string }[] = [
  { key: 'evolution', label: 'Evolución Ataque/Defensa' },
  { key: 'xg-vs-real', label: 'xG vs Goles Reales' },
  { key: 'distribucion', label: 'Distribución Poisson' },
]

export default function AnalysisTabs({ tab, onChange }: AnalysisTabsProps) {
  return (
    <ul className="nav nav-tabs mb-3">
      {tabs.map((item) => (
        <li key={item.key} className="nav-item">
          <button className={`nav-link ${tab === item.key ? 'active fw-semibold' : ''}`} onClick={() => onChange(item.key)}>
            {item.label}
          </button>
        </li>
      ))}
    </ul>
  )
}
