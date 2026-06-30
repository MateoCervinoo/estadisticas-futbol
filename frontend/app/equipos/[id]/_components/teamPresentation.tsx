export const formaBadge = (resultado: string) => {
  const map: Record<string, string> = { H: 'bg-success', A: 'bg-danger', D: 'bg-warning text-dark' }
  return <span className={`badge ${map[resultado] || 'bg-secondary'} me-1`}>{resultado}</span>
}

export const formatShortDate = (date: string | null) => (
  date ? new Date(date).toLocaleDateString('es-AR') : '-'
)
