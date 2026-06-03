'use client'

import { useEffect, useState } from 'react'
import { getAccessToken } from '@/lib/auth'

export interface NpiVerifiedResult {
  name: string
  taxonomy: string | null
}

interface Props {
  npi: string
  onVerified?: (result: NpiVerifiedResult) => void
  /** 'sm' for settings page, 'xs' for inline visit form */
  size?: 'sm' | 'xs'
}

export default function NpiLookup({ npi, onVerified, size = 'sm' }: Props) {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<NpiVerifiedResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  // Clear result whenever the NPI value changes
  useEffect(() => {
    setResult(null)
    setError(null)
  }, [npi])

  const isValid10Digits = /^\d{10}$/.test(npi)

  const handleLookup = async () => {
    if (!isValid10Digits) return
    setLoading(true)
    setResult(null)
    setError(null)
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/npi/lookup?number=${npi}`,
        { headers: { Authorization: `Bearer ${getAccessToken()}` } }
      )
      if (res.status === 404) {
        setError('NPI not found in NPPES registry')
        return
      }
      if (!res.ok) {
        setError('Lookup failed — please try again')
        return
      }
      const data: NpiVerifiedResult = await res.json()
      setResult(data)
      onVerified?.(data)
    } catch {
      setError('Lookup failed — check your connection')
    } finally {
      setLoading(false)
    }
  }

  const btnBase =
    size === 'xs'
      ? 'rounded border border-blue-300 bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700 hover:bg-blue-100 disabled:opacity-50'
      : 'rounded border border-blue-300 bg-blue-50 px-3 py-1.5 text-sm font-medium text-blue-700 hover:bg-blue-100 disabled:opacity-50'

  return (
    <div className="mt-1 space-y-1">
      <button
        type="button"
        onClick={handleLookup}
        disabled={!isValid10Digits || loading}
        className={btnBase}
      >
        {loading ? (
          <span className="flex items-center gap-1.5">
            <span className="h-3 w-3 animate-spin rounded-full border-2 border-blue-400 border-t-transparent" />
            Looking up…
          </span>
        ) : (
          'Verify NPI'
        )}
      </button>

      {result && (
        <p className={size === 'xs' ? 'text-xs text-green-700' : 'text-sm text-green-700'}>
          ✓ {result.name}
          {result.taxonomy && (
            <span className="text-gray-500"> · {result.taxonomy}</span>
          )}
        </p>
      )}

      {error && (
        <p className={size === 'xs' ? 'text-xs text-red-600' : 'text-sm text-red-600'}>
          {error}
        </p>
      )}
    </div>
  )
}
