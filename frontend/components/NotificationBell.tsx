"use client"

import { useEffect, useState, useRef } from 'react'
import {
  getNotificacionesNoLeidasCount,
  getNotificaciones,
  marcarNotificacionLeida,
  marcarTodasLeidas,
  NotificacionItem,
} from '../src/services/api'

export default function NotificationBell() {
  const [count, setCount] = useState(0)
  const [notifs, setNotifs] = useState<NotificacionItem[]>([])
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  const fetchCount = () => {
    getNotificacionesNoLeidasCount().then(setCount).catch(() => {})
  }

  const fetchNotifs = () => {
    getNotificaciones(true).then(setNotifs).catch(() => {})
  }

  const handleMarkRead = async (id: number) => {
    await marcarNotificacionLeida(id)
    setNotifs((prev) => prev.filter((n) => n.id !== id))
    setCount((c) => Math.max(0, c - 1))
  }

  const handleMarkAllRead = async () => {
    const marked = await marcarTodasLeidas()
    setNotifs([])
    setCount((c) => Math.max(0, c - marked))
  }

  useEffect(() => {
    fetchCount()
    const interval = setInterval(fetchCount, 10000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    if (open) fetchNotifs()
  }, [open])

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws/matches'

  useEffect(() => {
    let ws: WebSocket | null = null
    let reconnectTimer: ReturnType<typeof setTimeout>
    let cancelled = false

    const connect = () => {
      if (cancelled) return
      ws = new WebSocket(WS_URL)
      ws.onopen = () => {
        fetchCount()
      }
      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data)
          if (msg.type === 'notification') {
            fetchCount()
          }
        } catch {}
      }
      ws.onclose = () => {
        if (!cancelled) reconnectTimer = setTimeout(connect, 5000)
      }
      ws.onerror = () => {
        ws?.close()
      }
    }

    connect()
    return () => {
      cancelled = true
      if (ws?.readyState === WebSocket.CONNECTING) {
        ws.onopen = () => ws?.close()
      } else {
        ws?.close()
      }
      clearTimeout(reconnectTimer)
    }
  }, [WS_URL])

  return (
    <div ref={ref} className="position-relative">
      <button
        className="btn btn-sm btn-outline-light position-relative me-2"
        onClick={() => setOpen(!open)}
        aria-label="Notificaciones"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="currentColor" viewBox="0 0 16 16">
          <path d="M8 16a2 2 0 0 0 2-2H6a2 2 0 0 0 2 2zm.995-14.901a1 1 0 1 0-1.99 0A5.002 5.002 0 0 0 3 6c0 1.098-.5 6-2 7h14c-1.5-1-2-5.902-2-7 0-2.42-1.72-4.44-4.005-4.901z"/>
        </svg>
        {count > 0 && (
          <span className="position-absolute top-0 start-100 translate-middle badge rounded-pill bg-danger" style={{ fontSize: '0.65rem' }}>
            {count > 99 ? '99+' : count}
          </span>
        )}
      </button>

      {open && (
        <div
          className="position-absolute end-0 mt-2 bg-white text-dark shadow rounded-3 border"
          style={{ width: '320px', maxHeight: '400px', overflowY: 'auto', zIndex: 1060 }}
        >
          <div className="d-flex justify-content-between align-items-center p-2 border-bottom">
            <span className="fw-semibold small">Notificaciones</span>
            {notifs.length > 0 && (
              <button className="btn btn-sm btn-link text-decoration-none p-0" onClick={handleMarkAllRead}>
                Marcar todas leídas
              </button>
            )}
          </div>
          {notifs.length === 0 ? (
            <div className="p-3 text-center text-muted small">Sin notificaciones nuevas</div>
          ) : (
            notifs.map((n) => (
              <div key={n.id} className="d-flex justify-content-between align-items-start p-2 border-bottom hover-bg-light">
                <div className="flex-grow-1 me-2">
                  <div className="small fw-semibold">{n.tipo === 'inicio' ? '▶ Empezó' : '⏹ Terminó'}</div>
                  <div className="small text-muted">{n.mensaje}</div>
                </div>
                <button
                  className="btn btn-sm btn-outline-secondary py-0 px-1"
                  onClick={() => handleMarkRead(n.id)}
                  title="Marcar leída"
                >
                  ✓
                </button>
              </div>
            ))
          )}
        </div>
      )}

    </div>
  )
}
