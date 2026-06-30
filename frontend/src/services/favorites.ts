const FAVORITES_KEY = 'estadisticas_futbol_favorites'

export function getFavorites(): number[] {
  if (typeof window === 'undefined') return []
  try {
    return JSON.parse(localStorage.getItem(FAVORITES_KEY) || '[]')
  } catch {
    return []
  }
}

export function isFavorite(partidoId: number): boolean {
  return getFavorites().includes(partidoId)
}

export function toggleFavorite(partidoId: number): boolean {
  const favs = getFavorites()
  const idx = favs.indexOf(partidoId)
  if (idx >= 0) {
    favs.splice(idx, 1)
    localStorage.setItem(FAVORITES_KEY, JSON.stringify(favs))
    return false
  } else {
    favs.push(partidoId)
    localStorage.setItem(FAVORITES_KEY, JSON.stringify(favs))
    return true
  }
}
