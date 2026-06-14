'use client'

import { useEffect, useState } from 'react'
import axios from 'axios'
import { getAccessToken } from '@/lib/auth'

interface Props {
  claimId: string
  visitType: string
  onClose: () => void
}

export default function CMS1500PreviewModal({ claimId, visitType, onClose }: Props) {
  const [pdfUrl, setPdfUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const api = process.env.NEXT_PUBLIC_API_URL

  useEffect(() => {
    let objectUrl: string | null = null
    const load = async () => {
      try {
        const res = await axios.get(
          `${api}/api/v1/billing-admin/claims/${claimId}/cms1500.pdf`,
          {
            headers: { Authorization: `Bearer ${getAccessToken()}` },
            responseType: 'blob',
          }
        )
        objectUrl = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
        setPdfUrl(objectUrl)
      } catch {
        setError('Failed to load PDF. Check that the claim has valid provider data.')
      } finally {
        setLoading(false)
      }
    }
    load()
    return () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [claimId])

  const handleDownload = () => {
    if (!pdfUrl) return
    const a = document.createElement('a')
    a.href = pdfUrl
    a.download = `cms1500_${visitType}.pdf`
    a.click()
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-black/50 p-4 overflow-y-auto"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-lg shadow-xl w-full max-w-4xl my-8"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b px-6 py-4">
          <h3 className="text-base font-semibold text-gray-900">
            CMS 1500 Preview — <span className="font-mono text-sm text-gray-500">{visitType}</span>
          </h3>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-xl leading-none"
          >
            ×
          </button>
        </div>

        <div className="px-6 pt-4 pb-2">
          {loading && (
            <div className="flex items-center justify-center h-40 text-sm text-gray-500 gap-2">
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-blue-400 border-t-transparent" />
              Loading form…
            </div>
          )}
          {error && !loading && (
            <div className="flex items-center justify-center h-40 text-sm text-red-600">
              {error}
            </div>
          )}
          {pdfUrl && !loading && (
            <>
              {/* Desktop: inline iframe (blocked on iOS Safari) */}
              <iframe
                src={pdfUrl}
                className="hidden md:block w-full rounded border border-gray-200"
                style={{ height: '560px' }}
                title="CMS 1500 Preview"
              />
              {/* Mobile: open in new tab */}
              <div className="block md:hidden rounded border border-gray-200 bg-gray-50 p-4 text-center">
                <p className="mb-3 text-sm text-gray-600">PDF preview is not supported on mobile browsers.</p>
                <a
                  href={pdfUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-block rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
                >
                  Open PDF ↗
                </a>
              </div>
            </>
          )}
        </div>

        <div className="flex items-center justify-end gap-3 border-t px-6 py-4">
          <button
            type="button"
            onClick={onClose}
            className="rounded border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
          >
            Close
          </button>
          <button
            type="button"
            onClick={handleDownload}
            disabled={!pdfUrl}
            className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-40"
          >
            Download PDF
          </button>
        </div>
      </div>
    </div>
  )
}
