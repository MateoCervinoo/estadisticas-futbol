export type TournamentTab = 'calendario' | 'posiciones' | 'eliminatorias' | 'estadisticas'

type TournamentTabsProps = {
  activeTab: TournamentTab
  onChange: (tab: TournamentTab) => void
}

const tabs: { key: TournamentTab; label: string }[] = [
  { key: 'calendario', label: 'Calendario' },
  { key: 'posiciones', label: 'Posiciones' },
  { key: 'eliminatorias', label: 'Eliminatorias' },
  { key: 'estadisticas', label: 'Estadísticas' },
]

export default function TournamentTabs({ activeTab, onChange }: TournamentTabsProps) {
  return (
    <ul className="nav nav-tabs mb-4">
      {tabs.map((tab) => (
        <li key={tab.key} className="nav-item">
          <button
            className={`nav-link ${activeTab === tab.key ? 'active fw-semibold' : ''}`}
            onClick={() => onChange(tab.key)}
          >
            {tab.label}
          </button>
        </li>
      ))}
    </ul>
  )
}
