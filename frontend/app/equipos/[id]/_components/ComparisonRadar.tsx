import { Comparacion } from '../../../../src/services/api'

type RadarPoint = {
  label: string
  v1: number
  v2: number
}

type ComparisonRadarProps = {
  comparacion: Comparacion
  radarData: RadarPoint[]
  maxRadar: number
}

export default function ComparisonRadar({ comparacion, radarData, maxRadar }: ComparisonRadarProps) {
  const cx = 150
  const cy = 150
  const radius = 120
  const angles = radarData.map((_, index) => (2 * Math.PI * index) / radarData.length - Math.PI / 2)
  const levels = [0.25, 0.5, 0.75, 1.0]

  const polygonPoints = (values: number[]) => values.map((value, index) => {
    const ratio = value / maxRadar
    const x = cx + radius * ratio * Math.cos(angles[index])
    const y = cy + radius * ratio * Math.sin(angles[index])
    return `${x},${y}`
  }).join(' ')

  return (
    <>
      <h6 className="fw-semibold mt-4 mb-2">Radar Chart (valores normalizados)</h6>
      <div className="d-flex justify-content-center">
        <svg viewBox="0 0 300 300" style={{ width: 300, height: 300 }}>
          {levels.map((level) => {
            const points = radarData.map((_, index) => {
              const x = cx + radius * level * Math.cos(angles[index])
              const y = cy + radius * level * Math.sin(angles[index])
              return `${x},${y}`
            }).join(' ')
            return <polygon key={level} points={points} fill="none" stroke="#ddd" strokeWidth={1} />
          })}
          {radarData.map((_, index) => {
            const x = cx + radius * Math.cos(angles[index])
            const y = cy + radius * Math.sin(angles[index])
            return <line key={index} x1={cx} y1={cy} x2={x} y2={y} stroke="#ddd" strokeWidth={1} />
          })}
          {radarData.map((value, index) => {
            const lx = cx + (radius + 20) * Math.cos(angles[index])
            const ly = cy + (radius + 20) * Math.sin(angles[index])
            return (
              <text key={index} x={lx} y={ly} textAnchor="middle" dominantBaseline="middle" fontSize={10} fill="#666">
                {value.label}
              </text>
            )
          })}
          <polygon points={polygonPoints(radarData.map((value) => value.v1))} fill="rgba(25,135,84,0.2)" stroke="#198754" strokeWidth={2} />
          <polygon points={polygonPoints(radarData.map((value) => value.v2))} fill="rgba(220,53,69,0.2)" stroke="#dc3545" strokeWidth={2} />
          <circle cx={10} cy={10} r={4} fill="#198754" />
          <text x={20} y={14} fontSize={10} fill="#198754">{comparacion.equipo1.nombre}</text>
          <circle cx={10} cy={26} r={4} fill="#dc3545" />
          <text x={20} y={30} fontSize={10} fill="#dc3545">{comparacion.equipo2.nombre}</text>
        </svg>
      </div>
    </>
  )
}
