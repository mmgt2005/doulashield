'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import axios from 'axios'
import { getAccessToken } from '@/lib/auth'
import { Patient, Visit, VisitType } from '@/types/domain'
import { VISIT_SLOTS, VISIT_GROUPS } from '@/lib/visit-config'

export default function ClientDetailPage() {
  const { clientId } = useParams<{ clientId: string }>()
  const [patient, setPatient] = useState<Patient | null>(null)
  const [visitMap, setVisitMap] = useState<Map<VisitType, Visit>>(new Map())
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const headers = { Authorization: `Bearer ${getAccessToken()}` }
    const base = process.env.NEXT_PUBLIC_API_URL

    Promise.all([
      axios.get<Patient>(`${base}/api/v1/patients/${clientId}`, { headers }),
      axios.get<Visit[]>(`${base}/api/v1/patients/${clientId}/visits`, { headers }),
    ])
      .then(([patientRes, visitsRes]) => {
        setPatient(patientRes.data)
        const map = new Map<VisitType, Visit>()
        for (const v of visitsRes.data) map.set(v.visit_type, v)
        setVisitMap(map)
      })
      .catch(() => setError('Could not load client.'))
      .finally(() => setLoading(false))
  }, [clientId])

  if (loading) return <p className="text-sm text-gray-500">Loading…</p>
  if (error || !patient) return <p className="text-sm text-red-600">{error ?? 'Not found.'}</p>

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">{patient.name}</h1>
        {patient.mco && <p className="mt-1 text-sm text-gray-500">MCO: {patient.mco}</p>}
      </div>

      {VISIT_GROUPS.map(({ key, label }) => {
        const slots = VISIT_SLOTS.filter((s) => s.group === key)
        return (
          <div key={key}>
            <h2 className="text-xs font-semibold uppercase tracking-wide text-gray-400 mb-2">
              {label}
            </h2>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
              {slots.map((slot) => {
                const visit = visitMap.get(slot.visitType)
                const done = !!visit
                return (
                  <Link
                    key={slot.visitType}
                    href={`/clients/${clientId}/visits/${slot.visitType}`}
                    className={
                      done
                        ? 'block rounded-lg border border-gray-200 bg-gray-50 p-3 text-gray-500 hover:border-gray-300 transition-colors'
                        : 'block rounded-lg border border-blue-200 bg-white p-3 text-gray-800 hover:border-blue-400 transition-colors'
                    }
                  >
                    <div className="flex items-center gap-1">
                      {done && (
                        <svg className="h-3.5 w-3.5 shrink-0 text-green-500" viewBox="0 0 20 20" fill="currentColor">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                      )}
                      <span className="text-xs font-medium leading-tight">{slot.label}</span>
                    </div>
                    {done && visit?.visit_date && (
                      <p className="mt-0.5 text-xs text-gray-400">{visit.visit_date}</p>
                    )}
                  </Link>
                )
              })}
            </div>
          </div>
        )
      })}
    </div>
  )
}
