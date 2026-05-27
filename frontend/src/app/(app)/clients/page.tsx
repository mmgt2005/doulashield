'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import axios from 'axios'
import { getAccessToken } from '@/lib/auth'
import { Patient } from '@/types/domain'

export default function ClientsPage() {
  const [patients, setPatients] = useState<Patient[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    axios
      .get<Patient[]>(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/patients`, {
        headers: { Authorization: `Bearer ${getAccessToken()}` },
      })
      .then((r) => setPatients(r.data))
      .catch(() => setError('Failed to load clients.'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <p className="text-sm text-gray-500">Loading…</p>
  if (error) return <p className="text-sm text-red-600">{error}</p>

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Clients</h1>
        <Link
          href="/clients/new"
          className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          Add client
        </Link>
      </div>

      {patients.length === 0 ? (
        <p className="text-sm text-gray-500">No clients yet.</p>
      ) : (
        <div className="bg-white rounded-lg border border-gray-200 divide-y divide-gray-100">
          {patients.map((p) => (
            <Link
              key={p.id}
              href={`/clients/${p.id}`}
              className="flex items-center justify-between px-4 py-3 hover:bg-gray-50"
            >
              <span className="text-sm font-medium text-gray-900">{p.name}</span>
              <span className="text-xs text-gray-400">{p.mco ?? '—'}</span>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
