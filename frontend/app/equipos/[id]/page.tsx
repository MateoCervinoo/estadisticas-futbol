"use client"

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import {
  getEquipoPerfil, getComparacion,
  EquipoPerfil, Comparacion,
} from '../../../src/services/api'
import TeamComparison from './_components/TeamComparison'
import TeamSummaryCards from './_components/TeamSummaryCards'
import UpcomingMatches from './_components/UpcomingMatches'

export default function EquipoPage() {
  const params = useParams()
  const equipoId = Number(params.id)
  const [perfil, setPerfil] = useState<EquipoPerfil | null>(null)
  const [loading, setLoading] = useState(true)
  const [compareId, setCompareId] = useState<string>('')
  const [comparacion, setComparacion] = useState<Comparacion | null>(null)
  const [compLoading, setCompLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    getEquipoPerfil(equipoId).then((data) => {
      setPerfil(data)
      setLoading(false)
    })
  }, [equipoId])

  const handleCompare = async () => {
    const id2 = Number(compareId)
    if (!id2 || id2 === equipoId) return
    setCompLoading(true)
    const data = await getComparacion(equipoId, id2)
    setComparacion(data)
    setCompLoading(false)
  }

  if (loading) return <main className="container py-4"><div className="text-muted">Cargando perfil...</div></main>
  if (!perfil) return <main className="container py-4"><div className="text-muted">Equipo no encontrado.</div></main>

  const radarData = [
    { label: 'Goles', v1: perfil.stats.gf, v2: comparacion?.equipo2.stats.gf ?? 0 },
    { label: 'Ataque', v1: perfil.stats.gf / Math.max(perfil.stats.pj, 1), v2: comparacion ? (comparacion.equipo2.stats.gf / Math.max(comparacion.equipo2.stats.pj, 1)) : 0 },
    { label: 'Defensa', v1: -perfil.stats.gc / Math.max(perfil.stats.pj, 1), v2: comparacion ? (-comparacion.equipo2.stats.gc / Math.max(comparacion.equipo2.stats.pj, 1)) : 0 },
    { label: 'Puntos', v1: perfil.stats.pts, v2: comparacion?.equipo2.stats.pts ?? 0 },
  ]
  const maxRadar = Math.max(...radarData.map((point) => Math.max(Math.abs(point.v1), Math.abs(point.v2))), 1)

  return (
    <main className="container py-4">
      <div className="d-flex align-items-center gap-3 mb-4">
        <Link href="/" className="btn btn-outline-secondary btn-sm">&larr; Volver</Link>
        <h3 className="mb-0">
          {perfil.codigo_bandera && <span className={`fi fi-${perfil.codigo_bandera} me-2`} />}
          {perfil.nombre}
        </h3>
      </div>

      <TeamSummaryCards perfil={perfil} />
      <UpcomingMatches proximos={perfil.proximos} />
      <TeamComparison
        compareId={compareId}
        comparacion={comparacion}
        compLoading={compLoading}
        radarData={radarData}
        maxRadar={maxRadar}
        onCompareIdChange={setCompareId}
        onCompare={handleCompare}
      />
    </main>
  )
}
