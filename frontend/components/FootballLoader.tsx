export default function FootballLoader() {
  return (
    <div className="football-loader my-4" role="status" aria-live="polite">
      <div className="football-loader-field">
        <div className="football-loader-ball" />
        <div className="football-loader-shadow" />
      </div>
      <div className="small text-muted text-center mt-2">Cargando partidos...</div>
    </div>
  )
}
