'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import axios from 'axios'
import { marked } from 'marked'
import { getAccessToken } from '@/lib/auth'
import { useAuthStore } from '@/store/auth-store'
import { useRouter } from 'next/navigation'

type Preset = 'this_month' | 'last_month' | '3m' | '6m' | 'ytd' | 'last_year' | 'all' | 'custom'

const PRESETS: { key: Preset; label: string }[] = [
  { key: 'this_month', label: 'This Month' },
  { key: 'last_month', label: 'Last Month' },
  { key: '3m', label: 'Last 3 Months' },
  { key: '6m', label: 'Last 6 Months' },
  { key: 'ytd', label: 'Year to Date' },
  { key: 'last_year', label: 'Last Year' },
  { key: 'all', label: 'All Time' },
  { key: 'custom', label: 'Custom' },
]

function fmt(d: Date) { return d.toISOString().split('T')[0] }

function presetDates(p: Preset): { from: string | null; to: string | null } {
  const today = new Date()
  switch (p) {
    case 'this_month':
      return { from: fmt(new Date(today.getFullYear(), today.getMonth(), 1)), to: fmt(today) }
    case 'last_month': {
      const f = new Date(today.getFullYear(), today.getMonth() - 1, 1)
      const t = new Date(today.getFullYear(), today.getMonth(), 0)
      return { from: fmt(f), to: fmt(t) }
    }
    case '3m': {
      const f = new Date(today); f.setMonth(f.getMonth() - 3); return { from: fmt(f), to: fmt(today) }
    }
    case '6m': {
      const f = new Date(today); f.setMonth(f.getMonth() - 6); return { from: fmt(f), to: fmt(today) }
    }
    case 'ytd':
      return { from: fmt(new Date(today.getFullYear(), 0, 1)), to: fmt(today) }
    case 'last_year': {
      const y = today.getFullYear() - 1
      return { from: `${y}-01-01`, to: `${y}-12-31` }
    }
    default: return { from: null, to: null }
  }
}

function fmtMoney(n: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n)
}

function StatCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <p className="text-xs text-gray-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-gray-900">{value}</p>
      {sub && <p className="mt-0.5 text-xs text-gray-400">{sub}</p>}
    </div>
  )
}

function SectionHeader({ title, sub }: { title: string; sub?: string }) {
  return (
    <div className="mb-3">
      <h2 className="text-sm font-semibold text-gray-800">{title}</h2>
      {sub && <p className="text-xs text-gray-400">{sub}</p>}
    </div>
  )
}

const VISIT_TYPE_LABELS: Record<string, string> = {
  labor: 'Labor (T1033)',
  prenatal_1: 'Prenatal 1', prenatal_2: 'Prenatal 2', prenatal_3: 'Prenatal 3',
  prenatal_4: 'Prenatal 4', prenatal_5: 'Prenatal 5', prenatal_6: 'Prenatal 6',
  postnatal_1: 'Postnatal 1', postnatal_2: 'Postnatal 2', postnatal_3: 'Postnatal 3',
  postnatal_4: 'Postnatal 4', postnatal_5: 'Postnatal 5', postnatal_6: 'Postnatal 6',
  crisis_loss_1: 'Crisis/Bereavement 1', crisis_loss_2: 'Crisis/Bereavement 2',
}

const STAGE_LABELS: Record<string, string> = {
  pcb: 'PCB Certification',
  nppes_setup: 'NPPES / NPI Setup',
  promise_stage2: 'Enrollment Stage 2',
  mco_stage3: 'MCO Contracting',
}

export default function ExecutiveDashboard() {
  const { user } = useAuthStore()
  const router = useRouter()
  const [preset, setPreset] = useState<Preset>('all')
  const [customFrom, setCustomFrom] = useState('')
  const [customTo, setCustomTo] = useState('')
  const [data, setData] = useState<Record<string, unknown> | null>(null)
  const [loading, setLoading] = useState(true)

  // Report state
  const [reportMarkdown, setReportMarkdown] = useState('')
  const [generatingReport, setGeneratingReport] = useState(false)
  const [showReport, setShowReport] = useState(false)
  const reportRef = useRef<HTMLDivElement>(null)

  const api = process.env.NEXT_PUBLIC_API_URL
  const headers = { Authorization: `Bearer ${getAccessToken()}` }

  const load = useCallback(async (from: string | null, to: string | null) => {
    setLoading(true)
    try {
      const params: Record<string, string> = {}
      if (from) params.date_from = from
      if (to) params.date_to = to
      const res = await axios.get(`${api}/api/v1/admin/executive/stats`, { headers, params })
      setData(res.data)
    } catch (e) {
      if (axios.isAxiosError(e) && e.response?.status === 403) {
        router.replace('/dashboard')
      }
    } finally {
      setLoading(false)
    }
  }, [api])

  useEffect(() => {
    if (preset === 'custom') {
      if (customFrom && customTo) load(customFrom, customTo)
      return
    }
    const { from, to } = presetDates(preset)
    load(from, to)
  }, [preset, customFrom, customTo, load])

  if (!user?.is_executive && user?.role !== 'admin') return null

  const currentDates = (): { from: string | null; to: string | null } => {
    if (preset === 'custom') return { from: customFrom || null, to: customTo || null }
    return presetDates(preset)
  }

  const handleGenerateReport = async () => {
    setGeneratingReport(true)
    setShowReport(true)
    setReportMarkdown('')
    setTimeout(() => reportRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100)

    try {
      const { from, to } = currentDates()
      const url = new URL(`${api}/api/v1/admin/executive/generate-report`)
      if (from) url.searchParams.set('date_from', from)
      if (to) url.searchParams.set('date_to', to)

      const res = await fetch(url.toString(), {
        headers: { Authorization: `Bearer ${getAccessToken()}` },
      })
      if (!res.ok || !res.body) {
        setReportMarkdown('*Failed to generate report — please try again.*')
        return
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        const chunk = decoder.decode(value, { stream: true })
        setReportMarkdown((prev) => prev + chunk)
      }
    } catch {
      setReportMarkdown('*Failed to generate report — please try again.*')
    } finally {
      setGeneratingReport(false)
    }
  }

  const ph = (data as Record<string, Record<string, number>> | null)?.platform_health ?? {}
  const cr = (data as Record<string, Record<string, unknown>> | null)?.claims_revenue ?? {}
  const lf = (data as Record<string, Record<string, unknown>> | null)?.lead_funnel ?? {}
  const ep = (data as Record<string, Record<string, unknown>> | null)?.enrollment_pipeline ?? {}
  const ch = (data as Record<string, Record<string, unknown>> | null)?.compliance_health ?? {}
  const latency = (data as Record<string, Record<string, unknown>> | null)?.first_claim_latency ?? {}
  const cohortRetention = ((data as Record<string, unknown[]> | null)?.cohort_retention ?? []) as Array<Record<string, unknown>>

  return (
    <div className="mx-auto max-w-6xl space-y-8 p-6">
      {/* Print styles — hide dashboard tiles and layout chrome when printing */}
      <style>{`
        @media print {
          /* Break the app shell's h-screen / overflow-hidden cage so the full
             report content renders across as many pages as needed. */
          html, body { height: auto !important; overflow: visible !important; }
          .h-screen { height: auto !important; }
          .overflow-hidden { overflow: visible !important; }
          .overflow-auto { overflow: visible !important; height: auto !important; }
          .flex-1 { flex: none !important; }

          /* Hide layout chrome */
          nav, aside, header, [data-sidebar], .sidebar { display: none !important; }
          #executive-dashboard-content { display: none !important; }
          #executive-report-section { border: none !important; padding: 0 !important; }
          #executive-report-section .no-print { display: none !important; }
          body { font-size: 11pt; }

          /* Ensure prose content breaks across pages cleanly */
          .prose h2 { page-break-after: avoid; break-after: avoid; }
          .prose p, .prose li { orphans: 3; widows: 3; }
        }
      `}</style>

      {/* Strategic Report — rendered above dashboard; pinned by ref */}
      {showReport && (
        <section
          id="executive-report-section"
          ref={reportRef}
          className="rounded-xl border border-gray-200 bg-white p-6"
        >
          <div className="no-print mb-4 flex items-center justify-between border-b border-gray-100 pb-3">
            <div>
              <p className="text-sm font-semibold text-gray-800">Strategic Report</p>
              <p className="text-xs text-gray-400">
                {PRESETS.find((p) => p.key === preset)?.label ?? 'All Time'} ·{' '}
                {generatingReport ? 'Generating…' : 'Complete'}
              </p>
            </div>
            <div className="flex gap-2">
              {!generatingReport && reportMarkdown && (
                <button
                  onClick={() => window.print()}
                  className="rounded border border-gray-300 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50"
                >
                  Print / Save PDF
                </button>
              )}
              <button
                onClick={() => setShowReport(false)}
                className="rounded border border-gray-200 bg-white px-3 py-1.5 text-xs text-gray-500 hover:bg-gray-50"
              >
                Close
              </button>
            </div>
          </div>

          {generatingReport && !reportMarkdown && (
            <div className="flex items-center gap-3 py-8 text-sm text-gray-400">
              <svg className="h-4 w-4 animate-spin text-blue-500" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
              </svg>
              Analyzing platform data…
            </div>
          )}

          {reportMarkdown && (
            <div
              className="prose prose-sm max-w-none
                prose-headings:font-semibold prose-headings:text-gray-900
                prose-h2:text-base prose-h2:mt-6 prose-h2:mb-2
                prose-p:text-gray-700 prose-p:leading-relaxed
                prose-li:text-gray-700
                prose-strong:text-gray-900
                prose-table:text-xs prose-th:bg-gray-50 prose-th:font-medium"
              dangerouslySetInnerHTML={{ __html: marked.parse(reportMarkdown) as string }}
            />
          )}
        </section>
      )}

      {/* Dashboard content — hidden during print when report is shown */}
      <div id="executive-dashboard-content">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-xl font-semibold text-gray-900">Executive Dashboard</h1>
            <p className="mt-0.5 text-xs text-gray-400">Platform-wide · All providers · All agencies</p>
          </div>
          <button
            onClick={handleGenerateReport}
            disabled={generatingReport || loading}
            className="flex items-center gap-1.5 rounded-lg border border-blue-200 bg-blue-50 px-3 py-1.5 text-xs font-medium text-blue-700 hover:bg-blue-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {generatingReport ? (
              <>
                <svg className="h-3 w-3 animate-spin" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
                </svg>
                Generating…
              </>
            ) : (
              '✦ Generate Strategic Report'
            )}
          </button>
        </div>

        {/* Date filter */}
        <div className="mt-6 space-y-2">
          <div className="flex flex-wrap gap-1.5">
            {PRESETS.map((p) => (
              <button key={p.key} onClick={() => setPreset(p.key)}
                className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
                  preset === p.key ? 'border-blue-600 bg-blue-600 text-white' : 'border-gray-200 text-gray-600 hover:bg-gray-50'
                }`}>
                {p.label}
              </button>
            ))}
          </div>
          {preset === 'custom' && (
            <div className="flex items-center gap-2">
              <input type="date" value={customFrom} onChange={(e) => setCustomFrom(e.target.value)}
                className="rounded border border-gray-200 px-2 py-1 text-xs" />
              <span className="text-xs text-gray-400">to</span>
              <input type="date" value={customTo} onChange={(e) => setCustomTo(e.target.value)}
                max={new Date().toISOString().split('T')[0]}
                className="rounded border border-gray-200 px-2 py-1 text-xs" />
            </div>
          )}
        </div>

        {loading ? (
          <div className="py-16 text-center text-sm text-gray-400">Loading…</div>
        ) : (
          <div className="mt-8 space-y-8">
            {/* ── Section A: Platform Health ─────────────────────────────── */}
            <section>
              <SectionHeader title="Platform Health" sub="All-time counts — not affected by date filter" />
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
                <StatCard label="Active Providers" value={ph.active_providers ?? 0} />
                <StatCard label="Subscribed" value={ph.subscribed_providers ?? 0}
                  sub={`${ph.past_due_providers ?? 0} past due`} />
                <StatCard label="New (30 days)" value={ph.new_providers_30d ?? 0}
                  sub={`${ph.new_providers_90d ?? 0} in 90 days`} />
                <StatCard label="Active Last 30d" value={ph.active_last_30d ?? 0}
                  sub={`${ph.active_last_90d ?? 0} in 90 days`} />
                <StatCard label="Agencies" value={ph.active_agencies ?? 0} />
              </div>

              {/* First-Claim Latency */}
              <div className="mt-4">
                <p className="mb-2 text-xs font-medium text-gray-600">Provider Activation (time to first submitted claim)</p>
                <div className="grid grid-cols-3 gap-3">
                  <StatCard label="Avg Days to First Claim"
                    value={latency.avg_days != null ? `${latency.avg_days}d` : '—'} />
                  <StatCard label="Median Days to First Claim"
                    value={latency.median_days != null ? `${latency.median_days}d` : '—'} />
                  <StatCard label="Providers Never Billed"
                    value={(latency.providers_never_billed as number) ?? 0}
                    sub="active, no claims" />
                </div>
              </div>

              {/* Cohort Retention */}
              {cohortRetention.length > 0 && (
                <div className="mt-4">
                  <p className="mb-2 text-xs font-medium text-gray-600">Provider Cohort Retention (last 12 months)</p>
                  <div className="overflow-x-auto rounded border border-gray-100">
                    <table className="w-full text-xs">
                      <thead className="bg-gray-50">
                        <tr>
                          {['Cohort Month', 'Signed Up', 'Still Active', 'Retention'].map((h) => (
                            <th key={h} className="px-3 py-2 text-left font-medium text-gray-500">{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {cohortRetention.map((row, i) => (
                          <tr key={i} className="border-t border-gray-100">
                            <td className="px-3 py-2">{String(row.cohort_month).slice(0, 7)}</td>
                            <td className="px-3 py-2">{String(row.cohort_size)}</td>
                            <td className="px-3 py-2">{String(row.still_active)}</td>
                            <td className="px-3 py-2">
                              <span className={`font-medium ${
                                Number(row.retention_pct) >= 70 ? 'text-green-700' :
                                Number(row.retention_pct) >= 40 ? 'text-amber-600' : 'text-red-600'
                              }`}>{String(row.retention_pct)}%</span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </section>

            {/* ── Section B: Lead Funnel ─────────────────────────────────── */}
            <section>
              <SectionHeader title="Lead Funnel" />
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 mb-4">
                <StatCard label="Total Leads" value={(lf.totals as Record<string, number>)?.total ?? 0} />
                <StatCard label="Converted" value={(lf.totals as Record<string, number>)?.converted ?? 0}
                  sub={`${(lf.totals as Record<string, number>)?.conversion_rate_pct ?? 0}% rate`} />
                <StatCard label="Demo Scheduled" value={(lf.totals as Record<string, number>)?.demo_scheduled ?? 0} />
                <StatCard label="New / Uncontacted" value={(lf.totals as Record<string, number>)?.new ?? 0} />
              </div>
              {((lf.by_source as unknown[]) ?? []).length > 0 && (
                <div className="overflow-x-auto rounded border border-gray-100">
                  <table className="w-full text-xs">
                    <thead className="bg-gray-50">
                      <tr>
                        {['Source', 'Total', 'New', 'Contacted', 'Qualified', 'Demo', 'Converted', 'Not Interested', 'Conv. Rate'].map((h) => (
                          <th key={h} className="px-3 py-2 text-left font-medium text-gray-500 whitespace-nowrap">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {(lf.by_source as Array<Record<string, unknown>>).map((row, i) => (
                        <tr key={i} className="border-t border-gray-100">
                          <td className="px-3 py-2 capitalize">{String(row.source).replace('_', ' ')}</td>
                          <td className="px-3 py-2 font-medium">{String(row.total)}</td>
                          <td className="px-3 py-2">{String(row.new)}</td>
                          <td className="px-3 py-2">{String(row.contacted)}</td>
                          <td className="px-3 py-2">{String(row.qualified)}</td>
                          <td className="px-3 py-2">{String(row.demo_scheduled)}</td>
                          <td className="px-3 py-2 text-green-700 font-medium">{String(row.converted)}</td>
                          <td className="px-3 py-2 text-gray-400">{String(row.not_interested)}</td>
                          <td className="px-3 py-2 font-medium">{String(row.conversion_rate_pct)}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>

            {/* ── Section C: Claims & Revenue ────────────────────────────── */}
            <section>
              <SectionHeader title="Platform Claims & Revenue" />
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5 mb-4">
                <StatCard label="Total Claims" value={(cr.total_claims as number) ?? 0} />
                <StatCard label="Total Billed" value={fmtMoney((cr.total_billed as number) ?? 0)} />
                <StatCard label="Total Collected" value={fmtMoney((cr.total_paid as number) ?? 0)} />
                <StatCard label="Collection Rate" value={`${(cr.collection_rate_pct as number) ?? 0}%`} />
                <StatCard label="Denial Rate" value={`${(cr.platform_denial_rate_pct as number) ?? 0}%`}
                  sub={`${(cr.denied_claims as number) ?? 0} claims denied`} />
              </div>

              {/* Revenue by Visit Type */}
              {((cr.visit_type_breakdown as unknown[]) ?? []).length > 0 && (
                <div className="mb-4">
                  <p className="mb-2 text-xs font-medium text-gray-600">Revenue by Visit Type</p>
                  <div className="overflow-x-auto rounded border border-gray-100">
                    <table className="w-full text-xs">
                      <thead className="bg-gray-50">
                        <tr>
                          {['Visit Type', 'Rate', 'Claims', 'Total Billed', 'Total Paid', 'Collection %'].map((h) => (
                            <th key={h} className="px-3 py-2 text-left font-medium text-gray-500 whitespace-nowrap">{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {(cr.visit_type_breakdown as Array<Record<string, unknown>>).map((row, i) => (
                          <tr key={i} className="border-t border-gray-100">
                            <td className="px-3 py-2">{VISIT_TYPE_LABELS[String(row.visit_type)] ?? String(row.visit_type)}</td>
                            <td className="px-3 py-2 text-gray-500">{row.rate_per_visit ? `$${row.rate_per_visit}` : '—'}</td>
                            <td className="px-3 py-2">{String(row.claim_count)}</td>
                            <td className="px-3 py-2">{fmtMoney(row.total_billed as number)}</td>
                            <td className="px-3 py-2">{fmtMoney(row.total_paid as number)}</td>
                            <td className="px-3 py-2 font-medium">{String(row.collection_rate_pct)}%</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Claim Aging Buckets */}
              {((cr.claim_aging as unknown[]) ?? []).length > 0 && (
                <div>
                  <p className="mb-2 text-xs font-medium text-gray-600">Unpaid Claim Aging</p>
                  <div className="overflow-x-auto rounded border border-gray-100">
                    <table className="w-full text-xs">
                      <thead className="bg-gray-50">
                        <tr>
                          {['Age (days from service)', 'Claims', 'Total Billed'].map((h) => (
                            <th key={h} className="px-3 py-2 text-left font-medium text-gray-500">{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {(cr.claim_aging as Array<Record<string, unknown>>).map((row, i) => (
                          <tr key={i} className={`border-t border-gray-100 ${
                            row.age_bucket === '121-180' ? 'bg-amber-50' :
                            row.age_bucket === '180+' ? 'bg-red-50' : ''
                          }`}>
                            <td className="px-3 py-2 font-medium">
                              {row.age_bucket === '121-180' && <span className="mr-1 text-amber-600">⚠</span>}
                              {row.age_bucket === '180+' && <span className="mr-1 text-red-600">⛔</span>}
                              {String(row.age_bucket)} days
                            </td>
                            <td className="px-3 py-2">{String(row.claim_count)}</td>
                            <td className="px-3 py-2">{fmtMoney(row.total_billed as number)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </section>

            {/* ── Section D: Enrollment Pipeline ────────────────────────── */}
            <section>
              <SectionHeader title="Enrollment Pipeline" sub="All-time" />
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 mb-4">
                <StatCard label="Enrollment Tier Agencies"
                  value={`${(ep.enrollment_tier as Record<string, number>)?.tier_enabled ?? 0} / ${(ep.enrollment_tier as Record<string, number>)?.active_agencies ?? 0}`}
                  sub={`${(ep.enrollment_tier as Record<string, number>)?.penetration_pct ?? 0}% penetration`} />
              </div>

              {((ep.stage_completion_time as unknown[]) ?? []).length > 0 && (
                <div className="mb-4">
                  <p className="mb-2 text-xs font-medium text-gray-600">Stage Completion Time</p>
                  <div className="overflow-x-auto rounded border border-gray-100">
                    <table className="w-full text-xs">
                      <thead className="bg-gray-50">
                        <tr>
                          {['Stage', 'Completed', 'Avg Days', 'Median Days'].map((h) => (
                            <th key={h} className="px-3 py-2 text-left font-medium text-gray-500">{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {(ep.stage_completion_time as Array<Record<string, unknown>>).map((row, i) => (
                          <tr key={i} className="border-t border-gray-100">
                            <td className="px-3 py-2">{STAGE_LABELS[String(row.stage)] ?? String(row.stage)}</td>
                            <td className="px-3 py-2">{String(row.completed_count)}</td>
                            <td className="px-3 py-2 font-medium">{row.avg_days != null ? `${row.avg_days}d` : '—'}</td>
                            <td className="px-3 py-2">{row.median_days != null ? `${row.median_days}d` : '—'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {((ep.by_stage as unknown[]) ?? []).length > 0 && (
                <div>
                  <p className="mb-2 text-xs font-medium text-gray-600">Services by Stage & Status</p>
                  <div className="overflow-x-auto rounded border border-gray-100">
                    <table className="w-full text-xs">
                      <thead className="bg-gray-50">
                        <tr>
                          {['Stage', 'Status', 'Count', 'Edu Pathway', 'Exp Pathway', 'Assigned to Agency'].map((h) => (
                            <th key={h} className="px-3 py-2 text-left font-medium text-gray-500 whitespace-nowrap">{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {(ep.by_stage as Array<Record<string, unknown>>).map((row, i) => (
                          <tr key={i} className="border-t border-gray-100">
                            <td className="px-3 py-2">{STAGE_LABELS[String(row.stage)] ?? String(row.stage)}</td>
                            <td className="px-3 py-2 capitalize">{String(row.status).replace('_', ' ')}</td>
                            <td className="px-3 py-2 font-medium">{String(row.count)}</td>
                            <td className="px-3 py-2">{String(row.edu_pathway)}</td>
                            <td className="px-3 py-2">{String(row.exp_pathway)}</td>
                            <td className="px-3 py-2">{String(row.assigned_to_agency)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </section>

            {/* ── Section E: Compliance Health ──────────────────────────── */}
            <section>
              <SectionHeader title="Compliance Health" />
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 mb-4">
                <div className={`rounded-lg border p-4 ${
                  ((ch.overdue_claims as number) ?? 0) > 0 ? 'border-red-200 bg-red-50' : 'border-gray-200 bg-white'
                }`}>
                  <p className="text-xs text-gray-500">Overdue Claims (180d+)</p>
                  <p className={`mt-1 text-2xl font-semibold ${((ch.overdue_claims as number) ?? 0) > 0 ? 'text-red-700' : 'text-gray-900'}`}>
                    {(ch.overdue_claims as number) ?? 0}
                  </p>
                </div>
                <div className={`rounded-lg border p-4 ${
                  ((ch.urgent_claims as number) ?? 0) > 0 ? 'border-amber-200 bg-amber-50' : 'border-gray-200 bg-white'
                }`}>
                  <p className="text-xs text-gray-500">Urgent (150–180d)</p>
                  <p className={`mt-1 text-2xl font-semibold ${((ch.urgent_claims as number) ?? 0) > 0 ? 'text-amber-700' : 'text-gray-900'}`}>
                    {(ch.urgent_claims as number) ?? 0}
                  </p>
                </div>
                <StatCard label="MA91 Compliance"
                  value={`${(ch.ma91 as Record<string, number>)?.compliance_rate_pct ?? 0}%`}
                  sub={`${(ch.ma91 as Record<string, number>)?.signed ?? 0} of ${(ch.ma91 as Record<string, number>)?.total_visits ?? 0} visits signed`} />
                <StatCard label="Resubmitted Claims"
                  value={(ch.resubmitted_claims as number) ?? 0}
                  sub="have been resubmitted ≥ once" />
              </div>
            </section>
          </div>
        )}
      </div>
    </div>
  )
}
