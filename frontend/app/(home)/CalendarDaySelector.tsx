import { formatDateLabel } from './matchPresentation'

type CalendarDaySelectorProps = {
  uniqueDates: string[]
  selectedDate: string | null
  onSelectDate: (date: string | null) => void
}

export default function CalendarDaySelector({ uniqueDates, selectedDate, onSelectDate }: CalendarDaySelectorProps) {
  return (
    <div className="day-selector d-flex gap-2 overflow-auto pb-2">
      {uniqueDates.length === 0 && <div className="calendar-empty-note">No hay días cargados todavía</div>}
      {uniqueDates.map((iso) => {
        const active = selectedDate === iso
        const label = formatDateLabel(`${iso}T12:00:00Z`)

        return (
          <button
            key={iso}
            className={`btn day-selector-btn text-start ${active ? 'active' : ''}`}
            onClick={() => onSelectDate(active ? null : iso)}
          >
            <div className="small text-uppercase opacity-75">Día</div>
            <div className="fw-semibold text-nowrap">{label}</div>
          </button>
        )
      })}
    </div>
  )
}
