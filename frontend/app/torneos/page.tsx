"use client"

import React, { useEffect, useState } from 'react'
import Link from 'next/link'
import { getTorneos, Torneo } from '../../src/services/api'

export default function TorneosPage() {
  const [torneos, setTorneos] = useState<Torneo[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true
    setLoading(true)
    setError(null)
    getTorneos()
      .then(data => {
        if (!mounted) return
        setTorneos(data)
      })
      .catch((err) => {
        if (!mounted) return
        setError(err instanceof Error ? err.message : 'No se pudieron cargar los torneos')
      })
      .finally(() => {
        if (mounted) setLoading(false)
      })
    return () => { mounted = false }
  }, [])

  const tipoIcon = (tipo: string) => {
    if (tipo === 'mundial') return '🏆'
    if (tipo === 'continental') return '🌍'
    if (tipo === 'liga') return '⚽'
    if (tipo === 'copa') return '🏅'
    return '📋'
  }

  return (
    <main className="tournaments-shell min-vh-100 text-dark">
      <div className="container py-4 py-lg-5">
        <section className="app-surface p-4 mb-4">
          <span className="app-eyebrow dark">Torneos</span>
          <div className="d-flex flex-wrap align-items-end justify-content-between gap-3">
            <div>
              <h1 className="display-6 fw-black mb-2">Mapa competitivo</h1>
              <p className="text-muted mb-0">Accedé a calendarios, tablas, eliminatorias y leaders desde una vista consistente.</p>
            </div>
            {!loading && !error && (
              <span className="badge app-count-badge rounded-pill">{torneos.length} torneos</span>
            )}
          </div>
        </section>

        {error && (
          <div className="app-alert app-alert-danger mb-4">
            <strong>No pudimos cargar los torneos.</strong>
            <span>{error}</span>
          </div>
        )}
        {loading && <div className="app-empty-state"><strong>Cargando torneos...</strong><span>Preparando la cobertura disponible.</span></div>}
        {!loading && !error && torneos.length === 0 && <div className="app-empty-state"><strong>No hay torneos cargados</strong><span>Revisá la sincronización del backend.</span></div>}
        <div className="row g-3">
        {torneos.map(t => (
          <div key={t.id} className="col-12 col-md-6 col-lg-4">
            <Link href={`/torneos/${t.id}`} className="text-decoration-none">
              <div className="tournament-card h-100">
                <div className="d-flex align-items-center gap-3">
                  <span className="tournament-icon">{tipoIcon(t.tipo)}</span>
                  <div>
                    <div className="fw-bold text-dark">{t.nombre_canonico}</div>
                    <div className="small text-muted">
                      {t.categoria} · nivel {t.nivel ?? '-'} · {t.total_partidos} partidos
                    </div>
                  </div>
                </div>
              </div>
            </Link>
          </div>
        ))}
        </div>
      </div>
    </main>
  )
}
