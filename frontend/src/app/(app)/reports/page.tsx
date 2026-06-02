'use client'

import { useEffect, useState } from 'react'
import axios from 'axios'
import { getAccessToken } from '@/lib/auth'

interface ClaimBucket {
  count: number
  billed: number
  paid?: number
}

interface Stats {
  total_patients: number
  visits_completed: number
  visits_documented: number
  claims: {
    submitted: ClaimBucket
    processing: ClaimBucket
    paid: ClaimBucket
    denied: ClaimBucket
  }
  revenue: {
    total_billed: number
    total_paid: number
  }
  mco_breakdown: Array<{
    mco: string | null
    patients: number
    claims: number
    billed: number
    paid: number
  }>
}

interface McoContract {
  mco: string
  contract_date: string | null
}

function fmt(n: number): string {
  return n.toLocaleString('en-US', { style: 'currency', currency: 'USD' })
}

const BUCKET_STYLES = {
  submitted:  { border: 'border-amber-300',  bg: 'bg-amber-50',  text: 'text-amber-700',  label: 'Submitted' },
  processing: { border: 'border-blue-300',   bg: 'bg-blue-50',   text: 'text-blue-700',   label: 'Processing' },
  paid:       { border: 'border-green-300',  bg: 'bg-green-50',  text: 'text-green-800',  label: 'Paid' },
  denied:     { border: 'border-red-300',    bg: 'bg-red-50',    text: 'text-red-700',    label: 'Denied' },
} as const

export default function ReportsPage() {
  const [stats, setStats] = useState<Stats | null>(null)
  const [contracts, setContracts] = useState<McoContract[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const base = process.env.NEXT_PUBLIC_API_URL
    const headers = { Authorization: `Bearer ${getAccessToken()}` }

    Promise.all([
      axios.get<Stats>(`${base}/api/v1/stats/summary`, { headers }),
      axios.get<{ mco_contracts: McoContract[] | null }>(`${base}/api/v1/auth/me/provider-settings`, { headers }),
    ])
      .then(([statsRes, settingsRes]) => {
        setStats(statsRes.data)
        setContracts(settingsRes.data.mco_contracts ?? [])
      })
      .catch(() => setError('Failed to load report data.'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
      </div>
    )
  }

  if (error || !stats) {
    return <p className="text-sm text-red-600">{error ?? 'No data.'}</p>
  }

  const totalClaimsCount = Object.values(stats.claims).reduce((s, b) => s + b.count, 0)
  const collectionRate =
    stats.revenue.total_billed > 0
      ? (stats.revenue.total_paid / stats.revenue.total_billed) * 100
      : null

  // Build MCO table rows: contracted MCOs first, then any from claims not in contracts
  const contractMap = new Map(contracts.map((c) => [c.mco, c]))
  const breakdownMap = new Map(stats.mco_breakdown.map((r) => [r.mco ?? '(None)', r]))

  const contractedMcos = contracts.map((c) => c.mco)
  const claimMcos = stats.mco_breakdown.map((r) => r.mco ?? '(None)')
  const uncontractedClaimMcos = claimMcos.filter((m) => !contractMap.has(m))

  const tableRows: Array<{ mco: string; contract: McoContract | null; data: Stats['mco_breakdown'][0] | null }> = [
    ...contractedMcos.map((mco) => ({
      mco,
      contract: contractMap.get(mco) ?? null,
      data: breakdownMap.get(mco) ?? null,
    })),
    ...uncontractedClaimMcos.map((mco) => ({
      mco,
      contract: null,
      data: breakdownMap.get(mco) ?? null,
    })),
  ]

  return (
    <div className="space-y-6 max-w-5xl">
      <h1 className="text-2xl font-bold text-gray-900">Reports</h1>

      {/* Row 1 — Stat cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Clients</p>
          <p className="mt-1 text-3xl font-bold text-gray-900">{stats.total_patients}</p>
          <p className="text-xs text-gray-400">active</p>
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Visits</p>
          <p className="mt-1 text-3xl font-bold text-gray-900">{stats.visits_completed}</p>
          <p className="text-xs text-gray-400">
            completed · {stats.visits_documented} documented
          </p>
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Claims</p>
          <p className="mt-1 text-3xl font-bold text-gray-900">{totalClaimsCount}</p>
          <p className="text-xs text-gray-400">total</p>
        </div>
      </div>

      {/* Row 2 — Claim pipeline tiles */}
      <div>
        <h2 className="mb-3 text-sm font-semibold text-gray-700">Claim Pipeline</h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {(Object.entries(BUCKET_STYLES) as Array<[keyof typeof BUCKET_STYLES, typeof BUCKET_STYLES[keyof typeof BUCKET_STYLES]]>).map(([key, style]) => {
            const bucket = stats.claims[key]
            return (
              <div key={key} className={`rounded-lg border ${style.border} ${style.bg} p-4`}>
                <p className={`text-xs font-semibold uppercase tracking-wide ${style.text}`}>{style.label}</p>
                <p className={`mt-1 text-2xl font-bold ${style.text}`}>{bucket.count}</p>
                <p className={`text-xs ${style.text}`}>
                  {key === 'paid' && bucket.paid != null
                    ? `${fmt(bucket.paid)} paid`
                    : `${fmt(bucket.billed)} billed`}
                </p>
              </div>
            )
          })}
        </div>
      </div>

      {/* Row 3 — Revenue summary */}
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <h2 className="mb-3 text-sm font-semibold text-gray-700">Revenue Summary</h2>
        <div className="flex flex-wrap gap-6">
          <div>
            <p className="text-xs text-gray-500">Total Billed</p>
            <p className="text-lg font-bold text-gray-900">{fmt(stats.revenue.total_billed)}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Total Collected</p>
            <p className="text-lg font-bold text-green-700">{fmt(stats.revenue.total_paid)}</p>
          </div>
          {collectionRate !== null && (
            <div>
              <p className="text-xs text-gray-500">Collection Rate</p>
              <p className="text-lg font-bold text-gray-900">{collectionRate.toFixed(1)}%</p>
            </div>
          )}
        </div>
      </div>

      {/* Row 4 — MCO Breakdown table */}
      <div>
        <h2 className="mb-3 text-sm font-semibold text-gray-700">MCO Breakdown</h2>
        {tableRows.length === 0 ? (
          <p className="text-sm text-gray-400">No MCO data yet. Claims will appear here once submitted.</p>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-gray-200">
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">MCO</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">Contracted</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide">Patients</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide">Claims</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide">Billed</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide">Paid</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase tracking-wide">Collection %</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-100">
                {tableRows.map(({ mco, contract, data }) => {
                  const billed = data?.billed ?? 0
                  const paid = data?.paid ?? 0
                  const rate = billed > 0 ? (paid / billed) * 100 : null
                  return (
                    <tr key={mco} className="hover:bg-gray-50">
                      <td className="px-4 py-3 font-medium text-gray-900">{mco || '(None)'}</td>
                      <td className="px-4 py-3">
                        {contract ? (
                          <span className="inline-flex items-center gap-1 text-green-700">
                            <span>✓</span>
                            {contract.contract_date && (
                              <span className="text-xs text-green-600">{contract.contract_date}</span>
                            )}
                          </span>
                        ) : (
                          <span className="text-gray-400">—</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right text-gray-700">{data?.patients ?? 0}</td>
                      <td className="px-4 py-3 text-right text-gray-700">{data?.claims ?? 0}</td>
                      <td className="px-4 py-3 text-right text-gray-700">{fmt(billed)}</td>
                      <td className="px-4 py-3 text-right text-gray-700">{fmt(paid)}</td>
                      <td className="px-4 py-3 text-right text-gray-700">
                        {rate !== null ? `${rate.toFixed(1)}%` : '—'}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
