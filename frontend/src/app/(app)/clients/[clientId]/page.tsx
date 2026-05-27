'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import axios from 'axios'
import { getAccessToken } from '@/lib/auth'
import { Patient } from '@/types/domain'

export default function ClientDetailPage() {
  const { clientId } = useParams<{ clientId: string }>()
  const [patient, setPatient] = useState<Patient | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    axios
      .get<Patient>(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/patients/${clientId}`, {
        headers: { Authorization: `Bearer ${getAccessToken()}` },
      })
      .then((r) => setPatient(r.data))
      .catch(() => setError('Client not found.'))
      .finally(() => setLoading(false))
  }, [clientId])

  if (loading) return <p className="text-sm text-gray-500">Loading…</p>
  if (error || !patient) return <p className="text-sm text-red-600">{error ?? 'Not found.'}</p>

  const sections = [
    { href: 'soap-notes', label: 'SOAP Notes' },
    { href: 'prenatal-log', label: 'Prenatal / Postnatal Log' },
    { href: 'birth-log', label: 'Birth Log' },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">{patient.name}</h1>
        {patient.mco && <p className="mt-1 text-sm text-gray-500">MCO: {patient.mco}</p>}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {sections.map(({ href, label }) => (
          <Link
            key={href}
            href={`/clients/${clientId}/${href}`}
            className="block p-4 bg-white rounded-lg border border-gray-200 hover:border-blue-400 transition-colors"
          >
            <span className="text-sm font-medium">{label}</span>
          </Link>
        ))}
      </div>
    </div>
  )
}
