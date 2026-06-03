'use client'

import { useEffect, useState } from 'react'
import axios from 'axios'
import { getAccessToken } from '@/lib/auth'
import { AuditLogEntry } from '@/types/domain'

export default function AuditLogsPage() {
  const [logs, setLogs] = useState<AuditLogEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    axios
      .get<AuditLogEntry[]>(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/admin/audit-logs`, {
        headers: { Authorization: `Bearer ${getAccessToken()}` },
      })
      .then((r) => setLogs(r.data))
      .catch((e) => {
        const msg = axios.isAxiosError(e) ? e.response?.data?.detail ?? e.message : String(e)
        setError(`Failed to load audit logs: ${msg}`)
      })
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <p className="text-sm text-gray-500">Loading…</p>

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-gray-900">Audit Log</h1>

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
            {logs.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-sm text-gray-400">
                  {error ? 'Could not load entries.' : 'No audit log entries yet. Actions that touch patient data or credentials will appear here.'}
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
      </div>
    </div>
  )
}
