import { Dispatch, SetStateAction, useCallback, useEffect, useState } from 'react'
import { getFavorites, toggleFavorite } from '../../src/services/favorites'

export type ToastMessage = { id: number; msg: string }

export default function useFavorites() {
  const [favorites, setFavorites] = useState<number[]>([])
  const [toasts, setToasts] = useState<ToastMessage[]>([])
  const [showFavoritesOnly, setShowFavoritesOnly] = useState(false)

  useEffect(() => {
    setFavorites(getFavorites())
  }, [])

  useEffect(() => {
    if (toasts.length === 0) return
    const timer = setTimeout(() => setToasts((prev) => prev.slice(1)), 5000)
    return () => clearTimeout(timer)
  }, [toasts])

  const handleToggleFav = useCallback((partidoId: number) => {
    const nowFav = toggleFavorite(partidoId)
    setFavorites(getFavorites())
    if (nowFav) {
      setToasts((prev) => [...prev, { id: Date.now(), msg: 'Agregado a Mis Partidos' }])
    }
  }, [])

  return {
    favorites,
    toasts,
    setToasts: setToasts as Dispatch<SetStateAction<ToastMessage[]>>,
    showFavoritesOnly,
    setShowFavoritesOnly,
    handleToggleFav,
  }
}
