import './globals.css'
import Link from 'next/link'
import NotificationBell from '../components/NotificationBell'

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" className="h-full">
      <head>
        <link
          href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css"
          rel="stylesheet"
          integrity="sha384-QWTKZyjpPEjISv5WaRU9OFeRpok6YctnYmDr5pNlyT2bRjXh0JMhjY6hW+ALEwIH"
          crossOrigin="anonymous"
        />
        <link
          href="https://cdnjs.cloudflare.com/ajax/libs/flag-icon-css/6.6.6/css/flag-icons.min.css"
          rel="stylesheet"
        />
      </head>
      <body className="min-h-screen h-full antialiased app-body">
        <nav className="navbar navbar-expand-lg app-navbar sticky-top">
          <div className="container">
            <Link href="/" className="navbar-brand app-brand">
              <span className="app-brand-mark">PE</span>
              <span>Pizarrón Estadístico</span>
            </Link>
            <button className="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#mainNav">
              <span className="navbar-toggler-icon" />
            </button>
            <div className="collapse navbar-collapse" id="mainNav">
              <ul className="navbar-nav ms-auto align-items-lg-center gap-lg-1">
                <li className="nav-item"><Link href="/" className="nav-link app-nav-link">Calendario</Link></li>
                <li className="nav-item"><Link href="/torneos" className="nav-link app-nav-link">Torneos</Link></li>
                <li className="nav-item"><Link href="/analisis" className="nav-link app-nav-link">Análisis</Link></li>
                <li className="nav-item ms-2">
                  <NotificationBell />
                </li>
              </ul>
            </div>
          </div>
        </nav>
        {children}
        <script
          src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"
          crossOrigin="anonymous"
        ></script>
      </body>
    </html>
  )
}
