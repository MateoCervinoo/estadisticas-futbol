import { PredictionResponse } from '../../src/services/api'

export type ExactScore = {
  home: number
  away: number
  prob: number
}

export type ProbabilityKey = 'home_win' | 'draw' | 'away_win'

export const topExactScores = (predictionData: PredictionResponse | null): ExactScore[] => {
  if (Array.isArray(predictionData?.score_matrix_flat)) {
    return predictionData.score_matrix_flat
      .filter((item) => Number.isFinite(Number(item?.prob)))
      .map((item) => ({
        home: Number(item.home),
        away: Number(item.away),
        prob: Number(item.prob),
      }))
      .sort((a: ExactScore, b: ExactScore) => b.prob - a.prob)
      .slice(0, 3)
  }

  if (!Array.isArray(predictionData?.score_matrix)) return []

  return predictionData.score_matrix
    .flatMap((row: number[], home: number) =>
      Array.isArray(row)
        ? row.map((prob: number, away: number) => ({
            home,
            away,
            prob: Number(prob),
          }))
        : []
    )
    .filter((item: ExactScore) => Number.isFinite(item.prob))
    .sort((a: ExactScore, b: ExactScore) => b.prob - a.prob)
    .slice(0, 3)
}

export const exactScoreMatrix = (predictionData: PredictionResponse | null): number[][] => {
  if (!Array.isArray(predictionData?.score_matrix)) return []

  return predictionData.score_matrix.slice(0, 5).map((row) =>
    Array.isArray(row)
      ? row.slice(0, 5).map((cell) => {
          const value = Number(cell)
          return Number.isFinite(value) ? value : 0
        })
      : []
  )
}

export const heatmapClass = (value: number, maxValue: number) => {
  if (maxValue <= 0 || value <= 0) return 'bg-white'

  const intensity = value / maxValue
  if (intensity >= 0.66) return 'bg-success text-white fw-bold'
  if (intensity >= 0.33) return 'bg-warning text-dark fw-semibold'
  return 'bg-danger text-white'
}

export const probabilityBarClass = (key: ProbabilityKey) => {
  if (key === 'home_win') return 'bg-success'
  if (key === 'draw') return 'bg-warning text-dark'
  return 'bg-danger'
}

export const topScoreBadgeClass = (index: number) => {
  if (index === 0) return 'bg-success'
  if (index === 1) return 'bg-warning text-dark'
  return 'bg-danger'
}
