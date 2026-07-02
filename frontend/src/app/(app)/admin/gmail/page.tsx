'use client'

import { useEffect, useState, useCallback } from 'react'
import { useSearchParams } from 'next/navigation'
import axios from 'axios'
import { getAccessToken } from '@/lib/auth'

interface GmailMessage {
  id: string
  subject: string
  from: string
  to: string
  date: string
  snippet: string
  unread: boolean
}

interface GmailAttachment {
  id: string | null
  filename: string
  mimeType: string
  size: number
}

interface GmailMessageDetail extends GmailMessage {
  cc: string
  body: string
  attachments: GmailAttachment[]
}

export default function GmailPage() {
  const searchParams = useSearchParams()
  const api = process.env.NEXT_PUBLIC_API_URL
  const headers = { Authorization: `Bearer ${getAccessToken()}` }

  const [connected, setConnected] = useState<boolean | null>(null)
  const [connectedEmail, setConnectedEmail] = useState<string | null>(null)
  const [messages, setMessages] = useState<GmailMessage[]>([])
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')
  const [expanded, setExpanded] = useState<string | null>(null)
  const [detail, setDetail] = useState<GmailMessageDetail | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [toast, setToast] = useState<string | null>(null)
  const [disconnecting, setDisconnecting] = useState(false)

  const showToast = (msg: string) => {
    setToast(msg)
    setTimeout(() => setToast(null), 3500)
  }

  const loadStatus = useCallback(async () => {
    try {
      const res = await axios.get(`${api}/api/v1/admin/gmail/status`, { headers })
      setConnected(res.data.connected)
      setConnectedEmail(res.data.email)
    } catch {
      setConnected(false)
    }
  }, [api])

  const loadInbox = useCallback(async (q?: string) => {
    setLoading(true)
    try {
      const params = q ? { q } : {}
      const res = await axios.get<GmailMessage[]>(`${api}/api/v1/admin/gmail/inbox`, { headers, params })
      setMessages(res.data)
    } catch (e) {
      if (axios.isAxiosError(e) && e.response?.status !== 400) {
        showToast('Failed to load inbox')
      }
    } finally {
      setLoading(false)
    }
  }, [api])

  useEffect(() => {
    loadStatus()
  }, [loadStatus])

  useEffect(() => {
    if (connected) {
      loadInbox()
      if (searchParams.get('connected') === '1') {
        showToast('Gmail connected successfully!')
      }
    }
  }, [connected, loadInbox, searchParams])

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    loadInbox(search || undefined)
  }

  const handleExpand = async (id: string) => {
    if (expanded === id) {
      setExpanded(null)
      setDetail(null)
      return
    }
    setExpanded(id)
    setDetail(null)
    setDetailLoading(true)
    try {
      const res = await axios.get<GmailMessageDetail>(`${api}/api/v1/admin/gmail/messages/${id}`, { headers })
      setDetail(res.data)
    } catch {
      showToast('Failed to load message')
    } finally {
      setDetailLoading(false)
    }
  }

  const handleConnect = async () => {
    try {
      const res = await axios.get<{ auth_url: string }>(`${api}/api/v1/admin/gmail/auth-url`, { headers })
      window.location.href = res.data.auth_url
    } catch (e) {
      const msg = axios.isAxiosError(e) ? e.response?.data?.detail : 'Failed to start Gmail OAuth'
      showToast(typeof msg === 'string' ? msg : 'Failed to start Gmail OAuth')
    }
  }

  const downloadAttachment = async (messageId: string, att: GmailAttachment) => {
    if (!att.id) return
    try {
      const res = await axios.get(
        `${api}/api/v1/admin/gmail/messages/${messageId}/attachments/${att.id}`,
        {
          headers,
          params: { filename: att.filename, mime_type: att.mimeType },
          responseType: 'blob',
        }
      )
      const url = URL.createObjectURL(new Blob([res.data], { type: att.mimeType }))
      const a = document.createElement('a')
      a.href = url
      a.download = att.filename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch {
      showToast('Failed to download attachment')
    }
  }

  const handleDisconnect = async () => {
    if (!confirm('Disconnect Gmail? You will need to re-authorize to view emails again.')) return
    setDisconnecting(true)
    try {
      await axios.delete(`${api}/api/v1/admin/gmail/disconnect`, { headers })
      setConnected(false)
      setConnectedEmail(null)
      setMessages([])
      showToast('Gmail disconnected.')
    } catch {
      showToast('Failed to disconnect')
    } finally {
      setDisconnecting(false)
    }
  }

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-4">
      {toast && (
        <div className="fixed top-4 right-4 z-50 rounded-lg bg-gray-900 px-4 py-2 text-sm text-white shadow-lg">
          {toast}
        </div>
      )}

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-gray-900">Gmail</h1>
          {connected && connectedEmail && connectedEmail !== 'connected' && (
            <p className="text-xs text-gray-500 mt-0.5">Connected as {connectedEmail}</p>
          )}
        </div>
        {connected === false && (
          <button
            onClick={handleConnect}
            className="rounded bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700"
          >
            Connect Gmail
          </button>
        )}
        {connected && (
          <button
            onClick={handleDisconnect}
            disabled={disconnecting}
            className="rounded border border-red-200 px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50 disabled:opacity-50"
          >
            {disconnecting ? '…' : 'Disconnect'}
          </button>
        )}
      </div>

      {connected === null && (
        <p className="text-sm text-gray-400">Loading…</p>
      )}

      {connected === false && (
        <div className="rounded-lg border border-dashed border-gray-300 p-8 text-center">
          <p className="text-sm text-gray-500">Connect your Gmail account to view your inbox here.</p>
          <p className="mt-1 text-xs text-gray-400">DoulaShield only reads emails — it never sends or modifies them.</p>
          <button
            onClick={handleConnect}
            className="mt-4 rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            Connect Gmail →
          </button>
        </div>
      )}

      {connected && (
        <>
          <form onSubmit={handleSearch} className="flex gap-2">
            <input
              type="text"
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search inbox…"
              className="flex-1 rounded border border-gray-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-400"
            />
            <button
              type="submit"
              className="rounded bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700"
            >
              Search
            </button>
            {search && (
              <button
                type="button"
                onClick={() => { setSearch(''); loadInbox() }}
                className="rounded border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50"
              >
                Clear
              </button>
            )}
          </form>

          {loading ? (
            <p className="text-sm text-gray-400">Loading inbox…</p>
          ) : messages.length === 0 ? (
            <p className="text-sm text-gray-400">No messages found.</p>
          ) : (
            <div className="divide-y divide-gray-100 rounded-lg border border-gray-200 bg-white">
              {messages.map(msg => (
                <div key={msg.id}>
                  <button
                    onClick={() => handleExpand(msg.id)}
                    className="w-full text-left px-4 py-3 hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          {msg.unread && <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-blue-500" />}
                          <p className={`text-sm truncate ${msg.unread ? 'font-semibold text-gray-900' : 'font-medium text-gray-700'}`}>
                            {msg.subject}
                          </p>
                        </div>
                        <p className="text-xs text-gray-500 truncate mt-0.5">{msg.from}</p>
                        <p className="text-xs text-gray-400 truncate mt-0.5">{msg.snippet}</p>
                      </div>
                      <p className="shrink-0 text-xs text-gray-400 whitespace-nowrap">{msg.date.slice(0, 16)}</p>
                    </div>
                  </button>

                  {expanded === msg.id && (
                    <div className="border-t border-gray-100 bg-gray-50 px-4 py-4 text-xs">
                      {detailLoading ? (
                        <p className="text-gray-400">Loading…</p>
                      ) : detail ? (
                        <div className="space-y-2">
                          <div className="space-y-0.5 text-gray-600">
                            <p><span className="font-medium">From:</span> {detail.from}</p>
                            <p><span className="font-medium">To:</span> {detail.to}</p>
                            {detail.cc && <p><span className="font-medium">CC:</span> {detail.cc}</p>}
                            <p><span className="font-medium">Date:</span> {detail.date}</p>
                          </div>
                          <div className="mt-3 rounded border border-gray-200 bg-white p-3 whitespace-pre-wrap font-mono text-gray-700 max-h-96 overflow-y-auto">
                            {detail.body || detail.snippet}
                          </div>
                          {detail.attachments?.length > 0 && (
                            <div className="mt-2">
                              <p className="text-xs font-medium text-gray-500 mb-1">Attachments</p>
                              <div className="flex flex-wrap gap-1.5">
                                {detail.attachments.map((att, i) => (
                                  att.id ? (
                                    <button
                                      key={i}
                                      onClick={() => downloadAttachment(detail.id, att)}
                                      className="inline-flex items-center gap-1 rounded border border-gray-200 bg-white px-2 py-1 text-xs text-gray-700 hover:bg-gray-50"
                                    >
                                      <svg className="h-3 w-3 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
                                      {att.filename}
                                      {att.size > 0 && <span className="text-gray-400 ml-0.5">({(att.size / 1024).toFixed(0)} KB)</span>}
                                    </button>
                                  ) : (
                                    <span key={i} className="inline-flex items-center gap-1 rounded border border-gray-200 bg-white px-2 py-1 text-xs text-gray-500">
                                      {att.filename}
                                    </span>
                                  )
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      ) : null}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}
