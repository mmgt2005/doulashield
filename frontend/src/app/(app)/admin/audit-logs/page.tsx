'use client'

import { useEffect, useState } from 'react'
import axios from 'axios'
import { getAccessToken } from '@/lib/auth'
import { AuditLogEntry } from '@/types/domain'

export default function AuditLogsPage() {
  const [logs, setLogs] = useState<AuditLogEntry[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    axios
      .get<AuditLogEntry[]>(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/admin/audit-logs`, {
        headers: { Authorization: `Bearer ${getAccessToken()}` },
      })
      .then((r) => setLogs(r.data))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <p className="text-sm text-gray-500">Loading…</p>

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-gray-900">Audit Log</h1>
      <div className="bg-white rounded-lg border border-gray-200 overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              {['Timestamp', 'User', 'Action', 'Resource', 'IP'].map((h) => (
                <th key={h} className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase whitespace-nowrap">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {logs.map((log) => (
              <tr key={log.id}>
                <td className="px-4 py-3 text-gray-400 whitespace-nowrap text-xs">
                  {new Date(log.timestamp).toLocaleString()}
                </td>
                <td className="px-4 py-3 font-mono text-xs text-gray-500">
                  {log.user_id?.slice(0, 8) ?? '—'}
                </td>
                <td className="px-4 py-3">
                  <span className="inline-block px-2 py-0.5 rounded text-xs font-medium bg-blue-50 text-blue-700">
                    {log.action}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-600">
                  {log.resource_type ?? '—'}
                  {log.resource_id && (
                    <span className="ml-1 text-gray-400 font-mono text-xs">{log.resource_id.slice(0, 8)}</span>
                  )}
                </td>
                <td className="px-4 py-3 text-gray-400 font-mono text-xs">{log.ip_address ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
