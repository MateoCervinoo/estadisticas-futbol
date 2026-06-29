"use client"

import React, { useEffect, useState } from 'react'
import Link from 'next/link'
import { getTorneos, Torneo } from '../../src/services/api'

export default function TorneosPage() {
  const [torneos, setTorneos] = useState<Torneo[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getTorneos().then(data => {
      setTorneos(data)
      setLoading(false)
    })
  }, [])

  const tipoIcon = (tipo: string) => {
    if (tipo === 'mundial') return '🏆'
    if (tipo === 'continental') return '🌍'
    if (tipo === 'liga') return '⚽'
    if (tipo === 'copa') return '🏅'
    return '📋'
  }

  return (
    <main className="container py-4">
      <h2 className="mb-4">Torneos</h2>
      {loading && <div className="text-muted">Cargando...</div>}
      <div className="row">
        {torneos.map(t => (
          <div key={t.id} className="col-12 col-md-6 col-lg-4 mb-3">
            <Link href={`/torneos/${t.id}`} className="text-decoration-none">
              <div className="card bg-white shadow-sm border-0 rounded-3 p-4 h-100">
                <div className="d-flex align-items-center gap-3">
                  <span className="fs-1">{tipoIcon(t.tipo)}</span>
                  <div>
                    <div className="fw-semibold text-dark">{t.nombre_canonico}</div>
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
    </main>
  )
}
