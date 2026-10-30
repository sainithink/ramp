import { useCallback, useEffect, useRef, useState } from 'react'

/** The states main.py broadcasts over the socket, plus a local 'offline'. */
export type VoiceState =
  | 'offline'
  | 'wake'
  | 'listening'
  | 'always_on'
  | 'thinking'
  | 'speaking'
  | 'error'

export type ListeningMode = 'saira' | 'always_on'

export type LogKind = 'info' | 'transcript' | 'tool' | 'error'

export type LogEntry = {
  id: number
  at: string
  text: string
  kind: LogKind
}

export type MicStatus = 'idle' | 'active' | 'denied'

type Options = {
  /** Called once per completed exchange so the usage meter can move. */
  onExchange?: () => void
}

const MAX_LOG = 60

export function useVoiceSession({ onExchange }: Options = {}) {
  const [state, setState] = useState<VoiceState>('offline')
  const [connected, setConnected] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [response, setResponse] = useState('')
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [queries, setQueries] = useState(0)
  const [tools, setTools] = useState(0)
  const [quota, setQuota] = useState<string | null>(null)
  const [micStatus, setMicStatus] = useState<MicStatus>('idle')
  const [micLevel, setMicLevel] = useState(0)
  const [listeningMode, setListeningMode] = useState<ListeningMode>('saira')
  const [heard, setHeard] = useState(false)

  const wsRef = useRef<WebSocket | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const playerRef = useRef<HTMLAudioElement | null>(null)
  const chunksRef = useRef<BlobPart[]>([])
  const playTimerRef = useRef<number | null>(null)
  const heardTimerRef = useRef<number | null>(null)
  const retryRef = useRef<number | null>(null)
  const logIdRef = useRef(0)
  /** Set when a 'thinking' arrives, cleared when the exchange lands. */
  const pendingRef = useRef(false)
  // Held in a ref so the socket effect never has to re-run when the caller
  // passes a new closure.
  const onExchangeRef = useRef(onExchange)
  useEffect(() => {
    onExchangeRef.current = onExchange
  }, [onExchange])

  const log = useCallback((text: string, kind: LogKind = 'info') => {
    setLogs((prev) => {
      const entry: LogEntry = {
        id: ++logIdRef.current,
        at: new Date().toTimeString().slice(0, 8),
        text,
        kind,
      }
      return [entry, ...prev].slice(0, MAX_LOG)
    })
  }, [])

  // ── Audio playback ─────────────────────────────────────────────────────────
  // Chunks arrive faster than they can be handed to the element one by one, so
  // they are collected and flushed as a single blob once the stream goes quiet.
  const flushAudio = useCallback(() => {
    const player = playerRef.current
    if (!player || chunksRef.current.length === 0) return
    const blob = new Blob(chunksRef.current, { type: 'audio/mpeg' })
    chunksRef.current = []
    const url = URL.createObjectURL(blob)
    if (player.src) URL.revokeObjectURL(player.src)
    player.src = url
    void player.play().catch(() => {})
  }, [])

  const resetAudio = useCallback(() => {
    if (playTimerRef.current) window.clearTimeout(playTimerRef.current)
    chunksRef.current = []
    const player = playerRef.current
    if (player?.src) URL.revokeObjectURL(player.src)
  }, [])

  const killAudio = useCallback(() => {
    if (playTimerRef.current) window.clearTimeout(playTimerRef.current)
    chunksRef.current = []
    const player = playerRef.current
    if (!player) return
    try {
      player.pause()
      player.currentTime = 0
    } catch {
      /* a src-less element throws; nothing to stop in that case */
    }
    if (player.src) {
      URL.revokeObjectURL(player.src)
      player.removeAttribute('src')
      player.load()
    }
  }, [])

  const stop = useCallback(() => {
    killAudio()
    const ws = wsRef.current
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: 'stop' }))
    log('Stopped by user', 'tool')
  }, [killAudio, log])

  const toggleMode = useCallback(() => {
    setListeningMode((prev) => {
      const next: ListeningMode = prev === 'saira' ? 'always_on' : 'saira'
      const ws = wsRef.current
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'set_listening_mode', mode: next }))
      }
      log(next === 'always_on' ? 'Switched to always-on' : 'Switched to wake-word mode')
      return next
    })
  }, [log])

  // ── Socket ─────────────────────────────────────────────────────────────────
  useEffect(() => {
    let cancelled = false

    const handle = (event: MessageEvent) => {
      if (event.data instanceof ArrayBuffer) {
        chunksRef.current.push(event.data)
        if (playTimerRef.current) window.clearTimeout(playTimerRef.current)
        playTimerRef.current = window.setTimeout(flushAudio, 280)
        return
      }

      const msg = JSON.parse(event.data as string)

      switch (msg.type) {
        case 'quota':
          setQuota(msg.message)
          log(msg.message, 'error')
          break

        case 'stop_audio':
          killAudio()
          log('Response interrupted', 'tool')
          break

        case 'status':
          setState(msg.state as VoiceState)
          if (msg.state === 'thinking') {
            pendingRef.current = true
            setQueries((n) => n + 1)
          }
          if (msg.state === 'wake' || msg.state === 'always_on') {
            if (pendingRef.current) {
              pendingRef.current = false
              onExchangeRef.current?.()
            }
            flushAudio()
          }
          break

        case 'transcript':
          setTranscript(msg.text)
          setResponse('')
          setHeard(true)
          if (heardTimerRef.current) window.clearTimeout(heardTimerRef.current)
          heardTimerRef.current = window.setTimeout(() => setHeard(false), 900)
          log(msg.text.slice(0, 70), 'transcript')
          resetAudio()
          break

        case 'response_chunk':
          setResponse((prev) => prev + msg.text)
          break

        case 'preference':
          log(`Learned: ${msg.text}`, 'tool')
          break

        case 'tool_call':
          setTools((n) => n + 1)
          log(`Tool: ${msg.name}`, 'tool')
          break
      }
    }

    const connect = () => {
      if (cancelled) return
      const scheme = location.protocol === 'https:' ? 'wss' : 'ws'
      const ws = new WebSocket(`${scheme}://${location.host}/ws/voice`)
      ws.binaryType = 'arraybuffer'
      wsRef.current = ws

      ws.onopen = () => {
        if (cancelled) return
        setConnected(true)
        setState('wake')
        log('Connected')
      }

      ws.onclose = (ev) => {
        if (cancelled) return
        setConnected(false)
        // Set by main.py before accept() when there is no valid session.
        if (ev.code === 4401) {
          window.location.href = '/login'
          return
        }
        if (ev.code === 4403) {
          setQuota('This account has been disabled.')
          return
        }
        setState('error')
        log('Connection lost — retrying', 'error')
        retryRef.current = window.setTimeout(connect, 3000)
      }

      ws.onmessage = handle
      ws.onerror = () => {}
    }

    connect()

    return () => {
      cancelled = true
      if (retryRef.current) window.clearTimeout(retryRef.current)
      if (playTimerRef.current) window.clearTimeout(playTimerRef.current)
      if (heardTimerRef.current) window.clearTimeout(heardTimerRef.current)
      const ws = wsRef.current
      if (ws) {
        ws.onclose = null
        ws.close()
      }
      wsRef.current = null
    }
  }, [flushAudio, killAudio, log, resetAudio])

  // ── Microphone ─────────────────────────────────────────────────────────────
  const startMic = useCallback(async () => {
    if (micStatus === 'active') return
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false })
      const actx = new AudioContext()
      const source = actx.createMediaStreamSource(stream)
      const analyser = actx.createAnalyser()
      analyser.fftSize = 1024
      source.connect(analyser)
      analyserRef.current = analyser

      const mime = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : 'audio/webm'
      const recorder = new MediaRecorder(stream, { mimeType: mime })
      recorder.ondataavailable = (e) => {
        const ws = wsRef.current
        if (e.data.size > 0 && ws && ws.readyState === WebSocket.OPEN) ws.send(e.data)
      }
      recorder.start(100)
      setMicStatus('active')
      log('Microphone live')

      const buf = new Uint8Array(analyser.frequencyBinCount)
      const tick = () => {
        if (!analyserRef.current) return
        analyser.getByteFrequencyData(buf)
        let sum = 0
        for (let i = 0; i < buf.length; i++) sum += buf[i]
        setMicLevel(Math.min(1, (sum / buf.length) / 50))
        requestAnimationFrame(tick)
      }
      tick()
    } catch {
      setMicStatus('denied')
    }
  }, [log, micStatus])

  // Browsers need a gesture before audio plays; the first click covers both the
  // microphone and unmuting the output element.
  useEffect(() => {
    let done = false
    const onFirstGesture = () => {
      if (done) return
      done = true
      const player = playerRef.current
      if (player) {
        player.muted = true
        void player.play().catch(() => {})
        player.pause()
        player.muted = false
      }
      void startMic()
    }
    window.addEventListener('pointerdown', onFirstGesture, { once: true })
    window.addEventListener('keydown', onFirstGesture, { once: true })

    // If permission was granted earlier, no gesture is needed.
    navigator.permissions
      ?.query({ name: 'microphone' as PermissionName })
      .then((r) => {
        if (r.state === 'granted') void startMic()
      })
      .catch(() => {})

    return () => {
      window.removeEventListener('pointerdown', onFirstGesture)
      window.removeEventListener('keydown', onFirstGesture)
    }
  }, [startMic])

  // Space or Escape stops her mid-sentence, as the old page did.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement | null
      if (el && /^(INPUT|TEXTAREA|SELECT)$/.test(el.tagName)) return
      if (e.code === 'Space' || e.code === 'Escape') {
        e.preventDefault()
        stop()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [stop])

  return {
    state,
    connected,
    transcript,
    response,
    logs,
    queries,
    tools,
    quota,
    micStatus,
    micLevel,
    listeningMode,
    heard,
    analyserRef,
    playerRef,
    stop,
    toggleMode,
    startMic,
  }
}
