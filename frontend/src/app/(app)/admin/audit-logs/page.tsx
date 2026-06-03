'use client'

import { useState } from 'react'
import axios from 'axios'
import { getAccessToken } from '@/lib/auth'
import { AuditLogEntry } from '@/types/domain'

interface Filters {
  action: string
  user_email: string
  start_date: string
  end_date: string
}

const EMPTY_FILTERS: Filters = { action: '', user_email: '', start_date: '', end_date: '' }

export default function AuditLogsPage() {
  const [logs, setLogs] = useState<AuditLogEntry[]>([])
  const [loading, setLoading] = useState(false)
  const [fetched, setFetched] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS)
  const [applied, setApplied] = useState<Filters>(EMPTY_FILTERS)

  const fetchLogs = async (f: Filters) => {
    setLoading(true)
    setError(null)
    const params = new URLSearchParams()
    if (f.action) params.set('action', f.action)
    if (f.user_email) params.set('user_email', f.user_email)
    if (f.start_date) params.set('start_date', f.start_date)
    if (f.end_date) params.set('end_date', f.end_date)
    params.set('limit', '200')

    const url = `${process.env.NEXT_PUBLIC_API_URL}/api/v1/admin/audit-logs${params.toString() ? `?${params}` : ''}`
    try {
      const r = await axios.get<AuditLogEntry[]>(url, {
        headers: { Authorization: `Bearer ${getAccessToken()}` },
      })
      setLogs(r.data)
      setFetched(true)
    } catch (e) {
      const msg = axios.isAxiosError(e) ? e.response?.data?.detail ?? e.message : String(e)
      setError(`Failed to load audit logs: ${msg}`)
    } finally {
      setLoading(false)
    }
  }

  const handleApply = () => {
    setApplied(filters)
    fetchLogs(filters)
  }

  const handleReset = () => {
    setFilters(EMPTY_FILTERS)
    setApplied(EMPTY_FILTERS)
    fetchLogs(EMPTY_FILTERS)
  }

  const hasFilters = Object.values(applied).some(Boolean)

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-gray-900">Audit Log</h1>

      {/* Filter bar */}
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Action type</label>
            <input
              type="text"
              value={filters.action}
              onChange={(e) => setFilters((f) => ({ ...f, action: e.target.value }))}
              onKeyDown={(e) => e.key === 'Enter' && handleApply()}
              placeholder="e.g. LOGIN, SIGN_MA91_IN_PERSON"
              className="w-full rounded border border-gray-300 px-2 py-1.5 text-xs text-gray-700 focus:border-blue-400 focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">User email</label>
            <input
              type="text"
              value={filters.user_email}
              onChange={(e) => setFilters((f) => ({ ...f, user_email: e.target.value }))}
              onKeyDown={(e) => e.key === 'Enter' && handleApply()}
              placeholder="partial email match"
              className="w-full rounded border border-gray-300 px-2 py-1.5 text-xs text-gray-700 focus:border-blue-400 focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">From date</label>
            <input
              type="date"
              value={filters.start_date}
              onChange={(e) => setFilters((f) => ({ ...f, start_date: e.target.value }))}
              className="w-full rounded border border-gray-300 px-2 py-1.5 text-xs text-gray-700 focus:border-blue-400 focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">To date</label>
            <input
              type="date"
              value={filters.end_date}
              onChange={(e) => setFilters((f) => ({ ...f, end_date: e.target.value }))}
              className="w-full rounded border border-gray-300 px-2 py-1.5 text-xs text-gray-700 focus:border-blue-400 focus:outline-none"
            />
          </div>
        </div>
        <div className="mt-3 flex items-center gap-2">
          <button
            type="button"
            onClick={handleApply}
            disabled={loading}
            className="rounded bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Loading…' : 'Apply filters'}
          </button>
          {hasFilters && (
            <button
              type="button"
              onClick={handleReset}
              className="rounded border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50"
            >
              Reset
            </button>
          )}
          {hasFilters && (
            <span className="text-xs text-gray-400">Filters active</span>
          )}
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3">
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              {['Timestamp', 'User', 'Action', 'Resource', 'IP'].map((h) => (
                <th key={h} className="whitespace-nowrap px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {!fetched ? (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-sm text-gray-400">
                  Use the filters above and click "Apply filters" to load audit log entries.
                </td>
              </tr>
            ) : logs.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-sm text-gray-400">
                  {hasFilters ? 'No entries match the current filters.' : 'No audit log entries yet. Actions that touch patient data or credentials will appear here.'}
                </td>
              </tr>
            ) : (
              logs.map((log) => (
                <tr key={log.id} className="hover:bg-gray-50">
                  <td className="whitespace-nowrap px-4 py-3 text-xs text-gray-400">
                    {new Date(log.timestamp).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-500">
                    {log.user_id?.slice(0, 8) ?? '—'}
                  </td>
                  <td className="px-4 py-3">
                    <span className="inline-block rounded bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700">
                      {log.action}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-600">
                    {log.resource_type ?? '—'}
                    {log.resource_id && (
                      <span className="ml-1 font-mono text-xs text-gray-400">{log.resource_id.slice(0, 8)}</span>
                    )}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-400">{log.ip_address ?? '—'}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
        {fetched && logs.length > 0 && (
          <div className="border-t border-gray-100 px-4 py-2 text-xs text-gray-400">
            {logs.length} {logs.length === 1 ? 'entry' : 'entries'}{logs.length === 200 ? ' (limit reached — narrow filters to see more)' : ''}
          </div>
        )}
      </div>
    </div>
  )
}
