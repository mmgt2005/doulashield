'use client'

import { useRef, useState } from 'react'
import axios from 'axios'
import { getAccessToken } from '@/lib/auth'

interface ImageUploadScannerProps {
  endpoint: string
  extraFields?: Record<string, string>
  onExtracted: (data: Record<string, unknown>) => void
  label?: string
}

export default function ImageUploadScanner({
  endpoint,
  extraFields,
  onExtracted,
  label = 'Scan image',
}: ImageUploadScannerProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [scanning, setScanning] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleFile = async (file: File) => {
    setError(null)
    setScanning(true)
    try {
      const form = new FormData()
      form.append('file', file)
      if (extraFields) {
        Object.entries(extraFields).forEach(([k, v]) => form.append(k, v))
      }

      const res = await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL}${endpoint}`,
        form,
        { headers: { Authorization: `Bearer ${getAccessToken()}` } }
      )
      onExtracted(res.data)
    } catch (err: unknown) {
      const status = axios.isAxiosError(err) ? err.response?.status : null
      setError(
        status === 422
          ? 'Could not read image — please try a clearer photo.'
          : 'Scan failed. Please try again.'
      )
    } finally {
      setScanning(false)
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  return (
    <div className="rounded-lg border border-dashed border-blue-300 bg-blue-50 p-4">
      <p className="mb-2 text-sm font-medium text-blue-700">{label}</p>
      <p className="mb-3 text-xs text-blue-500">
        Take a photo — fields will be pre-filled for you to review.
      </p>

      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png"
        capture="environment"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0]
          if (file) handleFile(file)
        }}
      />

      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        disabled={scanning}
        className="w-full rounded border border-blue-400 bg-white px-4 py-2 text-sm font-medium text-blue-700 hover:bg-blue-100 disabled:opacity-50 sm:w-auto"
      >
        {scanning ? (
          <span className="flex items-center gap-2">
            <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
            </svg>
            Scanning…
          </span>
        ) : (
          'Take photo'
        )}
      </button>

      {error && <p className="mt-2 text-xs text-red-600">{error}</p>}
    </div>
  )
}
