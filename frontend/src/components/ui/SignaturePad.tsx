'use client'

import { useEffect, useRef } from 'react'
import SignaturePadLib from 'signature_pad'

interface Props {
  onSave: (dataUrl: string) => void
  onClear: () => void
  disabled?: boolean
}

export default function SignaturePad({ onSave, onClear, disabled = false }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const padRef = useRef<SignaturePadLib | null>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ratio = Math.max(window.devicePixelRatio || 1, 1)
    canvas.width = canvas.offsetWidth * ratio
    canvas.height = canvas.offsetHeight * ratio
    const ctx = canvas.getContext('2d')
    if (ctx) ctx.scale(ratio, ratio)

    padRef.current = new SignaturePadLib(canvas, { backgroundColor: 'rgb(255,255,255)' })

    if (disabled) padRef.current.off()

    return () => {
      padRef.current?.off()
    }
  }, [disabled])

  const handleClear = () => {
    padRef.current?.clear()
    onClear()
  }

  const handleSave = () => {
    const pad = padRef.current
    if (!pad || pad.isEmpty()) return
    onSave(pad.toDataURL('image/png'))
  }

  return (
    <div className="space-y-2">
      <div className="rounded border-2 border-gray-300 bg-white overflow-hidden" style={{ height: '150px' }}>
        <canvas
          ref={canvasRef}
          className="w-full h-full touch-none"
          style={{ cursor: disabled ? 'not-allowed' : 'crosshair' }}
        />
      </div>
      <p className="text-xs text-gray-400 text-center">Draw signature above</p>
      <div className="flex gap-2">
        <button
          type="button"
          onClick={handleClear}
          disabled={disabled}
          className="rounded border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
        >
          Clear
        </button>
        <button
          type="button"
          onClick={handleSave}
          disabled={disabled}
          className="rounded bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          Save Signature
        </button>
      </div>
    </div>
  )
}
