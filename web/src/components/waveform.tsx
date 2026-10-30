import { useEffect, useRef } from 'react'
import type { RefObject } from 'react'

type Props = {
  analyserRef: RefObject<AnalyserNode | null>
  active: boolean
  className?: string
}

/**
 * Draws the microphone's live waveform, falling back to a slow idle sine so the
 * panel never looks dead while nobody is talking.
 */
export function Waveform({ analyserRef, active, className }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let raf = 0
    let phase = 0
    let buf: Uint8Array<ArrayBuffer> | null = null

    const resize = () => {
      const dpr = window.devicePixelRatio || 1
      const { width, height } = canvas.getBoundingClientRect()
      canvas.width = width * dpr
      canvas.height = height * dpr
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    }
    resize()
    const observer = new ResizeObserver(resize)
    observer.observe(canvas)

    const draw = () => {
      const { width, height } = canvas.getBoundingClientRect()
      ctx.clearRect(0, 0, width, height)
      const mid = height / 2
      const analyser = analyserRef.current

      if (active && analyser) {
        if (!buf || buf.length !== analyser.frequencyBinCount * 2) {
          buf = new Uint8Array(analyser.fftSize)
        }
        analyser.getByteTimeDomainData(buf)
        const grad = ctx.createLinearGradient(0, 0, width, 0)
        grad.addColorStop(0, 'rgba(0,200,131,0.55)')
        grad.addColorStop(0.5, 'rgba(60,245,160,1)')
        grad.addColorStop(1, 'rgba(120,250,220,0.55)')
        ctx.beginPath()
        ctx.strokeStyle = grad
        ctx.lineWidth = 2
        const step = width / buf.length
        for (let i = 0; i < buf.length; i++) {
          const y = (buf[i] / 128) * mid
          if (i === 0) ctx.moveTo(0, y)
          else ctx.lineTo(i * step, y)
        }
        ctx.stroke()
      } else {
        ctx.beginPath()
        ctx.strokeStyle = 'rgba(60,245,160,0.18)'
        ctx.lineWidth = 1.5
        for (let x = 0; x < width; x++) {
          const y = mid + Math.sin(x * 0.022 + phase) * 6 + Math.sin(x * 0.055 + phase * 1.3) * 2.5
          if (x === 0) ctx.moveTo(x, y)
          else ctx.lineTo(x, y)
        }
        ctx.stroke()
        phase += 0.028
      }

      raf = requestAnimationFrame(draw)
    }
    draw()

    return () => {
      cancelAnimationFrame(raf)
      observer.disconnect()
    }
  }, [analyserRef, active])

  return <canvas ref={canvasRef} className={className} />
}
