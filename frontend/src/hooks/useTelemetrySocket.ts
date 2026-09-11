import { useEffect, useRef, useState } from 'react'
import { wsUrl } from '../api/client'
import type { PipelineFrame } from '../types'

interface HookState {
  connected: boolean
  socketError: string | null
  latestState: Record<string, unknown> | null
}

export function useTelemetrySocket(onFrame: (frame: PipelineFrame) => void): HookState {
  const [connected, setConnected] = useState(false)
  const [socketError, setSocketError] = useState<string | null>(null)
  const [latestState, setLatestState] = useState<Record<string, unknown> | null>(null)
  const pingRef = useRef<number | null>(null)

  useEffect(() => {
    const ws = new WebSocket(wsUrl)

    ws.onopen = () => {
      setConnected(true)
      setSocketError(null)
      pingRef.current = window.setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send('ping')
        }
      }, 1500)
    }

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data)
        if (payload.type === 'state') {
          setLatestState(payload)
          return
        }
        onFrame(payload as PipelineFrame)
      } catch {
        setSocketError('Unable to parse telemetry payload')
      }
    }

    ws.onerror = () => {
      setSocketError('WebSocket connection error')
    }

    ws.onclose = () => {
      setConnected(false)
      if (pingRef.current !== null) {
        window.clearInterval(pingRef.current)
      }
    }

    return () => {
      if (pingRef.current !== null) {
        window.clearInterval(pingRef.current)
      }
      ws.close()
    }
  }, [onFrame])

  return {
    connected,
    socketError,
    latestState,
  }
}
