'use client'

import { useCallback, useEffect, useState } from 'react'
import axios from 'axios'
import { getAccessToken } from '@/lib/auth'
import { useRouter } from 'next/navigation'

interface McoRow {
  mco_name: string
  covered_patients: number
  provider_count: number
  total_claims: number
  total_billed: number
  total_paid: number
  collection_rate_pct: number
  denied_claims: number
  denial_rate_pct: number
  resubmitted_claims: number
  resubmission_rate_pct: number
  avg_days_to_pay: number | null
}

interface ReferringProvider {
  npi: string
  name: string | null
  total_patients: number
  doula_count: number
}

interface LocationRow {
  location_type: string
  visit_count: number
  provider_count: number
}

function fmtMoney(n: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n)
}

export default function McoReportPage() {
  const router = useRouter()
  const [mcoData, setMcoData] = useState<McoRow[]>([])
  const [referring, setReferring] = useState<ReferringProvider[]>([])
  const [locationSplit, setLocationSplit] = useState<LocationRow[]>([])
  const [loading, setLoading] = useState(true)
  const [exporting, setExporting] = useState(false)
  const [demoMode, setDemoMode] = useState(false)

  const api = process.env.NEXT_PUBLIC_API_URL

  const load = useCallback(async (demo: boolean) => {
    setLoading(true)
    const authHeader = { Authorization: `Bearer ${getAccessToken()}` }
    try {
      const params = demo ? '?include_demo=true' : ''
      const res = await axios.get(`${api}/api/v1/admin/executive/mco-report${params}`, { headers: authHeader })
      setMcoData(res.data.mco_breakdown ?? [])
      setReferring(res.data.referring_providers ?? [])
      setLocationSplit(res.data.location_split ?? [])
    } catch (e) {
      if (axios.isAxiosError(e)) {
        const status = e.response?.status
        if (status === 401) router.replace('/login')
        else if (status === 403) router.replace('/dashboard')
      }
    } finally {
      setLoading(false)
    }
  }, [api, router])

  useEffect(() => { load(demoMode) }, [load, demoMode])

  const handleExportCsv = async () => {
    setExporting(true)
    const authHeader = { Authorization: `Bearer ${getAccessToken()}` }
    try {
      const res = await fetch(`${api}/api/v1/admin/executive/mco-report.csv`, { headers: authHeader })
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      const today = new Date().toISOString().split('T')[0]
      a.download = `doulashield-mco-report-${today}.csv`
      a.click()
      URL.revokeObjectURL(url)
    } finally {
      setExporting(false)
    }
  }

  return (
    <div className="mx-auto max-w-6xl space-y-8 p-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">MCO Partnership Report</h1>
          <p className="mt-0.5 text-xs text-gray-400">
            Platform-wide claims data aggregated by Managed Care Organization — use for contract negotiations and partnership decks.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setDemoMode((d) => !d)}
            className={`rounded px-3 py-1.5 text-xs font-medium border transition-colors ${
              demoMode
                ? 'bg-amber-500 text-white border-amber-500 hover:bg-amber-600'
                : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
            }`}
          >
            {demoMode ? 'Exit Demo Mode' : 'Demo Mode'}
          </button>
          <button
            onClick={handleExportCsv}
            disabled={exporting || loading}
            className="flex items-center gap-1.5 rounded border border-gray-300 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            {exporting ? 'Exporting…' : '↓ Export CSV'}
          </button>
        </div>
      </div>

      {demoMode && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-800">
          <span className="font-semibold">Demo Mode active</span> — showing seeded demo data. Toggle off to return to live data.
        </div>
      )}

      {loading ? (
        <div className="py-16 text-center text-sm text-gray-400">Loading…</div>
      ) : (
        <>
          {/* MCO Negotiation Table */}
          <section>
            <p className="mb-1 text-xs font-medium text-gray-700">MCO Negotiation Data</p>
            <p className="mb-3 text-xs text-gray-400">
              Collection Rate, Denial Rate, and Avg Days to Pay are the three metrics MCOs respond to in contract discussions.
            </p>
            {mcoData.length === 0 ? (
              <p className="text-sm text-gray-400">No claim data yet.</p>
            ) : (
              <div className="overflow-x-auto rounded border border-gray-100">
                <table className="w-full text-xs">
                  <thead className="bg-gray-50">
                    <tr>
                      {[
                        'MCO', 'Covered Patients', 'Providers', 'Claims',
                        'Total Billed', 'Total Paid', 'Collection %',
                        'Denied', 'Denial %', 'Resubmitted', 'Resub %', 'Avg Days to Pay',
                      ].map((h) => (
                        <th key={h} className="px-3 py-2 text-left font-medium text-gray-500 whitespace-nowrap">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {mcoData.map((row, i) => (
                      <tr key={i} className="border-t border-gray-100 hover:bg-gray-50">
                        <td className="px-3 py-2 font-medium whitespace-nowrap">{row.mco_name}</td>
                        <td className="px-3 py-2">{row.covered_patients}</td>
                        <td className="px-3 py-2">{row.provider_count}</td>
                        <td className="px-3 py-2">{row.total_claims}</td>
                        <td className="px-3 py-2 whitespace-nowrap">{fmtMoney(row.total_billed)}</td>
                        <td className="px-3 py-2 whitespace-nowrap">{fmtMoney(row.total_paid)}</td>
                        <td className="px-3 py-2">
                          <span className={`font-medium ${
                            row.collection_rate_pct >= 80 ? 'text-green-700' :
                            row.collection_rate_pct >= 60 ? 'text-amber-600' : 'text-red-600'
                          }`}>{row.collection_rate_pct}%</span>
                        </td>
                        <td className="px-3 py-2">{row.denied_claims}</td>
                        <td className="px-3 py-2">
                          <span className={row.denial_rate_pct > 20 ? 'font-medium text-red-600' : ''}>
                            {row.denial_rate_pct}%
                          </span>
                        </td>
                        <td className="px-3 py-2">{row.resubmitted_claims}</td>
                        <td className="px-3 py-2">{row.resubmission_rate_pct}%</td>
                        <td className="px-3 py-2">
                          {row.avg_days_to_pay != null ? (
                            <span className={row.avg_days_to_pay > 45 ? 'font-medium text-amber-600' : ''}>
                              {row.avg_days_to_pay}d
                            </span>
                          ) : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <div className="mt-2 flex flex-wrap gap-4 text-xs text-gray-400">
              <span>
                <span className="inline-block h-2 w-2 rounded-full bg-green-500 mr-1" />
                Collection ≥80% (strong)
              </span>
              <span>
                <span className="font-medium text-red-600">Red denial %</span> = &gt;20% denial rate (leverage for renegotiation)
              </span>
              <span>
                <span className="font-medium text-amber-600">Amber days</span> = &gt;45 days to pay (cash flow argument)
              </span>
            </div>
          </section>

          {/* Service Delivery Profile */}
          {locationSplit.length > 0 && (
            <section>
              <p className="mb-2 text-xs font-medium text-gray-700">Service Delivery Profile</p>
              <div className="overflow-x-auto rounded border border-gray-100">
                <table className="w-full text-xs">
                  <thead className="bg-gray-50">
                    <tr>
                      {['Delivery Mode', 'Visit Count', 'Provider Count'].map((h) => (
                        <th key={h} className="px-3 py-2 text-left font-medium text-gray-500">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {locationSplit.map((row, i) => {
                      const total = locationSplit.reduce((s, r) => s + r.visit_count, 0)
                      return (
                        <tr key={i} className="border-t border-gray-100">
                          <td className="px-3 py-2 capitalize">{row.location_type.replace('_', '-')}</td>
                          <td className="px-3 py-2">
                            {row.visit_count}
                            <span className="ml-1.5 text-gray-400">({Math.round(100 * row.visit_count / Math.max(total, 1))}%)</span>
                          </td>
                          <td className="px-3 py-2">{row.provider_count}</td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {/* Referring Physician Analysis */}
          {referring.length > 0 && (
            <section>
              <p className="mb-1 text-xs font-medium text-gray-700">Hospital / Health System Partnerships — Referring Physicians</p>
              <p className="mb-3 text-xs text-gray-400">
                Physicians already referring patients to DoulaShield providers. Use this as warm intro evidence when approaching health systems.
              </p>
              <div className="overflow-x-auto rounded border border-gray-100">
                <table className="w-full text-xs">
                  <thead className="bg-gray-50">
                    <tr>
                      {['NPI', 'Name', 'Patients Referred', 'Doulas Serving Them'].map((h) => (
                        <th key={h} className="px-3 py-2 text-left font-medium text-gray-500">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {referring.map((row, i) => (
                      <tr key={i} className="border-t border-gray-100">
                        <td className="px-3 py-2 font-mono">{row.npi}</td>
                        <td className="px-3 py-2">{row.name ?? '—'}</td>
                        <td className="px-3 py-2 font-medium">{row.total_patients}</td>
                        <td className="px-3 py-2">{row.doula_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}
        </>
      )}
    </div>
  )
}
