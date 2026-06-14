'use client'

import { useEffect, useState } from 'react'
import axios from 'axios'
import { getAccessToken } from '@/lib/auth'

interface Props {
  title: string
  fetchUrl?: string
  directUrl?: string
  contentType?: 'pdf' | 'image' | 'auto'
  fileName?: string
  onClose: () => void
}

export default function FilePreviewModal({ title, fetchUrl, directUrl, contentType = 'auto', fileName, onClose }: Props) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null)
  const [resolvedType, setResolvedType] = useState<'pdf' | 'image'>('pdf')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const api = process.env.NEXT_PUBLIC_API_URL

  useEffect(() => {
    let objectUrl: string | null = null

    const load = async () => {
      try {
        if (fetchUrl) {
          const res = await axios.get(`${api}${fetchUrl}`, {
            headers: { Authorization: `Bearer ${getAccessToken()}` },
            responseType: 'blob',
          })
          const mime: string = String(res.headers['content-type'] || '')
          const type = contentType !== 'auto' ? contentType : mime.includes('pdf') ? 'pdf' : 'image'
          setResolvedType(type)
          objectUrl = URL.createObjectURL(new Blob([res.data], { type: mime || 'application/octet-stream' }))
          setBlobUrl(objectUrl)
        } else if (directUrl) {
          const type = contentType !== 'auto'
            ? contentType
            : /\.(jpg|jpeg|png|gif|webp)(\?|$)/i.test(directUrl) ? 'image' : 'pdf'
          setResolvedType(type)
          setBlobUrl(directUrl)
        }
      } catch {
        setError('Failed to load file.')
      } finally {
        setLoading(false)
      }
    }

    load()
    return () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [fetchUrl, directUrl])

  const handleDownload = () => {
    if (!blobUrl) return
    const a = document.createElement('a')
    a.href = blobUrl
    a.download = fileName || 'document'
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
          <h3 className="text-base font-semibold text-gray-900">{title}</h3>
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
              Loading…
            </div>
          )}
          {error && !loading && (
            <div className="flex items-center justify-center h-40 text-sm text-red-600">{error}</div>
          )}
          {blobUrl && !loading && resolvedType === 'pdf' && (
            <>
              <iframe
                src={blobUrl}
                className="hidden md:block w-full rounded border border-gray-200"
                style={{ height: '560px' }}
                title={title}
              />
              <div className="block md:hidden rounded border border-gray-200 bg-gray-50 p-4 text-center">
                <p className="mb-3 text-sm text-gray-600">PDF preview is not supported on mobile browsers.</p>
                <a
                  href={blobUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-block rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
                >
                  Open PDF ↗
                </a>
              </div>
            </>
          )}
          {blobUrl && !loading && resolvedType === 'image' && (
            <div className="flex items-center justify-center">
              <img
                src={blobUrl}
                alt={title}
                className="max-w-full rounded border border-gray-200"
                style={{ maxHeight: '560px', objectFit: 'contain' }}
              />
            </div>
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
            disabled={!blobUrl}
            className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-40"
          >
            Download
          </button>
        </div>
      </div>
    </div>
  )
}
