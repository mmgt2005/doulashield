'use client'

import { useCallback, useEffect, useState } from 'react'
import axios from 'axios'
import { getAccessToken } from '@/lib/auth'
import ImageUploadScanner from '@/components/ui/ImageUploadScanner'
import type { Patient, Claim } from '@/types/domain'

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

interface EobClaimLine {
  patient_name: string | null
  service_date: string | null
  procedure_code: string | null
  billed_amount: string | null
  paid_amount: string | null
  status: string
  denial_reason: string | null
  _patientId: string | null
  _visitType: string | null
  _matched: boolean
  _applied: boolean
}

function claimStatusDisplay(status: string | null): { label: string; color: 'amber' | 'blue' | 'green' | 'red' } {
  const s = (status ?? '').toLowerCase()
  if (s === 'paid') return { label: 'Paid', color: 'green' }
  if (s === 'denied' || s === 'rejected') return { label: 'Denied', color: 'red' }
  if (s === 'processing' || s === 'accepted' || s === 'pended' || s === 'received' || s === 'adjusted')
    return { label: 'Processing', color: 'blue' }
  return { label: 'Submitted', color: 'amber' }
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
  const [allPatients, setAllPatients] = useState<Patient[]>([])
  const [allClaims, setAllClaims] = useState<Claim[]>([])
  const [eobClaims, setEobClaims] = useState<EobClaimLine[] | null>(null)
  const [eobMeta, setEobMeta] = useState<{ check_number: string | null; payment_date: string | null } | null>(null)
  const [eobError, setEobError] = useState<string | null>(null)
  const [eobApplying, setEobApplying] = useState<number | null>(null)

  useEffect(() => {
    const base = process.env.NEXT_PUBLIC_API_URL
    const headers = { Authorization: `Bearer ${getAccessToken()}` }

    Promise.all([
      axios.get<Stats>(`${base}/api/v1/stats/summary`, { headers }),
      axios.get<{ mco_contracts: McoContract[] | null }>(`${base}/api/v1/auth/me/provider-settings`, { headers }),
      axios.get<Patient[]>(`${base}/api/v1/patients`, { headers }).catch(() => ({ data: [] as Patient[] })),
      axios.get<Claim[]>(`${base}/api/v1/claims`, { headers }).catch(() => ({ data: [] as Claim[] })),
    ])
      .then(([statsRes, settingsRes, patientsRes, claimsRes]) => {
        setStats(statsRes.data)
        setContracts(settingsRes.data.mco_contracts ?? [])
        setAllPatients(patientsRes.data)
        setAllClaims(claimsRes.data)
      })
      .catch(() => setError('Failed to load report data.'))
      .finally(() => setLoading(false))
  }, [])

  const handleEobScanned = useCallback((data: Record<string, unknown>) => {
    setEobError(null)
    const rawClaims = data.claims as Record<string, unknown>[] | undefined
    if (!Array.isArray(rawClaims)) {
      setEobError('Unexpected EOB format — could not extract claim lines.')
      return
    }

    const lines: EobClaimLine[] = rawClaims.map(c => {
      const eoName = String(c.patient_name ?? '').toLowerCase().trim()
      const firstToken = eoName.split(/\s+/)[0]

      const matchedPatient = firstToken.length >= 2
        ? allPatients.find(p => p.name.toLowerCase().includes(firstToken))
        : undefined

      const svcDate = String(c.service_date ?? '')
      let matchedClaim: Claim | undefined
      if (matchedPatient) {
        matchedClaim = allClaims.find(
          cl => cl.patient_id === matchedPatient.id &&
                (svcDate ? cl.service_date === svcDate : true)
        )
      }

      return {
        patient_name: (c.patient_name as string | null) ?? null,
        service_date: (c.service_date as string | null) ?? null,
        procedure_code: (c.procedure_code as string | null) ?? null,
        billed_amount: (c.billed_amount as string | null) ?? null,
        paid_amount: (c.paid_amount as string | null) ?? null,
        status: String(c.status ?? 'submitted'),
        denial_reason: (c.denial_reason as string | null) ?? null,
        _patientId: matchedPatient?.id ?? null,
        _visitType: matchedClaim?.visit_type ?? null,
        _matched: !!matchedPatient,
        _applied: false,
      }
    })

    setEobClaims(lines)
    setEobMeta({
      check_number: (data.check_number as string) || null,
      payment_date: (data.payment_date as string) || null,
    })
  }, [allPatients, allClaims])

  const _applyEobLine = useCallback(async (line: EobClaimLine, idx: number) => {
    if (!line._patientId || !line._visitType) return
    const base = process.env.NEXT_PUBLIC_API_URL
    const headers = { Authorization: `Bearer ${getAccessToken()}` }
    const statusMap: Record<string, string> = {
      paid: 'paid', adjusted: 'paid', denied: 'denied', pending: 'submitted',
    }
    const payload: Record<string, unknown> = {
      status: statusMap[line.status] ?? 'submitted',
      service_date: line.service_date ?? new Date().toISOString().split('T')[0],
    }
    if (line.paid_amount) payload.paid_amount = line.paid_amount
    if (line.denial_reason) payload.denial_reason = line.denial_reason

    setEobApplying(idx)
    try {
      await axios.put(
        `${base}/api/v1/patients/${line._patientId}/visits/${line._visitType}/claims/manual`,
        payload,
        { headers }
      )
      setEobClaims(prev => prev?.map((c, j) => j === idx ? { ...c, _applied: true } : c) ?? null)
    } catch {
      setEobError('Failed to apply claim — please try again.')
    } finally {
      setEobApplying(null)
    }
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

      {/* Central EOB Scanner */}
      <div>
        <h2 className="mb-3 text-sm font-semibold text-gray-700">Remittance / EOB Scan</h2>
        {eobClaims ? (
          <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 space-y-3">
            <div className="flex items-center justify-between">
              <p className="text-xs font-semibold text-blue-800">
                {eobClaims.length} claim{eobClaims.length !== 1 ? 's' : ''} found
                {eobMeta?.check_number ? ` · Check #${eobMeta.check_number}` : ''}
                {eobMeta?.payment_date ? ` · ${eobMeta.payment_date}` : ''}
              </p>
              <button
                type="button"
                onClick={() => { setEobClaims(null); setEobMeta(null); setEobError(null) }}
                className="text-xs text-blue-600 hover:underline"
              >
                Dismiss
              </button>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-left text-blue-700 border-b border-blue-200">
                    <th className="pb-1 pr-2">Patient on EOB</th>
                    <th className="pb-1 pr-2">Matched Client</th>
                    <th className="pb-1 pr-2">Date</th>
                    <th className="pb-1 pr-2">Status</th>
                    <th className="pb-1 pr-2">Paid</th>
                    <th className="pb-1"></th>
                  </tr>
                </thead>
                <tbody>
                  {eobClaims.map((line, i) => {
                    const matchedPt = line._patientId ? allPatients.find(p => p.id === line._patientId) : undefined
                    const { label, color } = claimStatusDisplay(line.status)
                    const colorClasses = {
                      amber: 'border-amber-300 bg-amber-50 text-amber-700',
                      blue: 'border-blue-300 bg-blue-50 text-blue-700',
                      green: 'border-green-300 bg-green-50 text-green-800',
                      red: 'border-red-300 bg-red-50 text-red-700',
                    }[color]
                    return (
                      <tr key={i} className={`border-t border-blue-100 ${line._matched ? 'bg-blue-100' : ''}`}>
                        <td className="py-1.5 pr-2 text-gray-700">{line.patient_name ?? '—'}</td>
                        <td className="py-1.5 pr-2 font-medium">
                          {matchedPt ? (
                            <a href={`/clients/${matchedPt.id}`} className="text-blue-700 hover:underline">
                              {matchedPt.name}
                            </a>
                          ) : (
                            <span className="text-gray-400">no match</span>
                          )}
                        </td>
                        <td className="py-1.5 pr-2 tabular-nums text-gray-700">{line.service_date ?? '—'}</td>
                        <td className="py-1.5 pr-2">
                          <span className={`rounded px-1 py-0.5 border text-xs ${colorClasses}`}>{label}</span>
                        </td>
                        <td className="py-1.5 pr-2 tabular-nums text-gray-700">
                          {line.paid_amount ? `$${line.paid_amount}` : '—'}
                        </td>
                        <td className="py-1.5 text-right whitespace-nowrap">
                          {line._applied ? (
                            <span className="text-green-600 font-medium">✓ Applied</span>
                          ) : line._matched && line._visitType ? (
                            <button
                              type="button"
                              disabled={eobApplying === i}
                              onClick={() => _applyEobLine(line, i)}
                              className="font-medium text-blue-600 hover:underline disabled:opacity-50"
                            >
                              {eobApplying === i ? '…' : 'Apply ↓'}
                            </button>
                          ) : line._matched ? (
                            <span className="text-amber-600 text-xs" title="No existing claim — submit from the visit page first">
                              no claim
                            </span>
                          ) : (
                            <span className="text-gray-400 text-xs">no match</span>
                          )}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
            <p className="text-xs text-blue-700">
              Highlighted rows matched a client in your roster. &ldquo;Apply ↓&rdquo; updates that visit&apos;s claim status.
              Rows showing &ldquo;no claim&rdquo; mean the claim was not yet submitted from the visit page.
            </p>
            {eobError && <p className="text-xs text-red-600">{eobError}</p>}
          </div>
        ) : (
          <div className="rounded-lg border border-gray-200 bg-white p-4">
            <p className="mb-3 text-xs text-gray-500">
              Scan a full paper remittance here — all claim lines will be matched against your client roster automatically.
            </p>
            <ImageUploadScanner
              endpoint="/api/v1/ocr/handbook"
              extraFields={{ page_type: 'remittance_eob' }}
              onExtracted={handleEobScanned}
              label="Scan Remittance / EOB"
            />
            {eobError && <p className="mt-2 text-xs text-red-600">{eobError}</p>}
          </div>
        )}
      </div>
    </div>
  )
}
