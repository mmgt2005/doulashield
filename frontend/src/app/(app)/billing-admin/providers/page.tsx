'use client'

import { useEffect, useState } from 'react'
import axios from 'axios'
import { getAccessToken } from '@/lib/auth'

interface CredentialExpiry {
  expires_on: string | null
  days_remaining: number | null
}

interface Provider {
  id: string
  full_name: string | null
  email: string
  npi: string | null
  deposit_paid: boolean
  enrollment_stages: {
    pcb: string | null
    nppes_setup: string | null
    enrollment: string | null
    mco_contracting: string | null
  }
  credentials: {
    pcb: CredentialExpiry
    promise: CredentialExpiry
    caqh: CredentialExpiry
    liability: CredentialExpiry
  }
}

interface InviteRow { name: string; email: string; doula_type: string }
interface InviteResult {
  created: { name: string; email: string }[]
  skipped: { name: string; email: string; reason: string }[]
}

const DOULA_TYPES = ['Birth Doula', 'Postpartum Doula', 'Perinatal Doula', 'Other']
const EMPTY_ROW: InviteRow = { name: '', email: '', doula_type: 'Birth Doula' }

const STAGE_LABELS: Record<string, string> = {
  pcb: 'PCB',
  nppes_setup: 'NPPES',
  enrollment: 'Enrollment',
  mco_contracting: 'MCO',
}

const CRED_LABELS: Record<string, string> = {
  pcb: 'PCB Cert',
  promise: 'PROMISe™',
  caqh: 'CAQH',
  liability: 'Liability Ins.',
}

function stageBadge(status: string | null) {
  if (!status) return <span className="inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-medium bg-gray-100 text-gray-400">—</span>
  if (status === 'complete') return <span className="inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-medium bg-green-100 text-green-700">✓</span>
  if (status === 'in_progress') return <span className="inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-medium bg-yellow-100 text-yellow-700">…</span>
  return <span className="inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-medium bg-gray-100 text-gray-400">○</span>
}

function expiryChip(label: string, info: CredentialExpiry) {
  if (!info.expires_on) {
    return (
      <div key={label} className="flex flex-col">
        <span className="text-[10px] font-medium text-gray-400 uppercase tracking-wide">{label}</span>
        <span className="text-xs text-gray-400">Not recorded</span>
      </div>
    )
  }
  const d = info.days_remaining!
  const color = d < 0 ? 'text-red-600' : d < 30 ? 'text-red-500' : d < 60 ? 'text-amber-600' : 'text-green-700'
  const label2 = d < 0 ? `Expired ${Math.abs(d)}d ago` : `${d}d left`
  return (
    <div key={label} className="flex flex-col">
      <span className="text-[10px] font-medium text-gray-400 uppercase tracking-wide">{label}</span>
      <span className={`text-xs font-medium ${color}`}>{label2}</span>
      <span className="text-[10px] text-gray-400">{new Date(info.expires_on).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}</span>
    </div>
  )
}

function enrollmentReadyBadge(provider: Provider) {
  const stages = provider.enrollment_stages
  const allComplete = ['pcb', 'nppes_setup', 'enrollment', 'mco_contracting'].every(
    s => stages[s as keyof typeof stages] === 'complete'
  )
  const anyActive = ['pcb', 'nppes_setup', 'enrollment', 'mco_contracting'].some(
    s => stages[s as keyof typeof stages] === 'in_progress'
  )
  if (allComplete) return <span className="inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold bg-green-100 text-green-700">Ready to bill</span>
  if (anyActive) return <span className="inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold bg-yellow-100 text-yellow-700">In progress</span>
  return <span className="inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold bg-gray-100 text-gray-500">Not started</span>
}

export default function BillingAdminProvidersPage() {
  const api = process.env.NEXT_PUBLIC_API_URL
  const headers = { Authorization: `Bearer ${getAccessToken()}` }

  const [providers, setProviders] = useState<Provider[]>([])
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const [toast, setToast] = useState<string | null>(null)

  const [rows, setRows] = useState<InviteRow[]>([{ ...EMPTY_ROW }])
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState<InviteResult | null>(null)

  const showToast = (msg: string) => {
    setToast(msg)
    setTimeout(() => setToast(null), 4000)
  }

  const loadProviders = async () => {
    setLoading(true)
    try {
      const res = await axios.get<Provider[]>(`${api}/api/v1/billing-admin/providers`, { headers })
      setProviders(res.data)
    } catch {
      showToast('Failed to load provider roster')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadProviders() }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const toggleExpand = (id: string) =>
    setExpanded(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })

  const updateRow = (idx: number, field: keyof InviteRow, value: string) =>
    setRows(rs => rs.map((r, i) => i === idx ? { ...r, [field]: value } : r))
  const addRow = () => setRows(rs => [...rs, { ...EMPTY_ROW }])
  const removeRow = (idx: number) => setRows(rs => rs.filter((_, i) => i !== idx))
  const validRows = rows.filter(r => r.name.trim() && r.email.trim())

  const handleSubmit = async () => {
    if (!validRows.length) return
    setSubmitting(true)
    setResult(null)
    try {
      const res = await axios.post<InviteResult>(
        `${api}/api/v1/billing-admin/roster/invite`,
        { providers: validRows },
        { headers }
      )
      setResult(res.data)
      setRows([{ ...EMPTY_ROW }])
      await loadProviders()
    } catch (e: unknown) {
      const msg = axios.isAxiosError(e) ? e.response?.data?.detail : 'Invite failed'
      showToast(typeof msg === 'string' ? msg : 'Invite failed')
    } finally {
      setSubmitting(false)
    }
  }

  const hasCredentialWarning = (p: Provider) =>
    Object.values(p.credentials).some(c => c.days_remaining !== null && c.days_remaining < 60)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-gray-900">My Providers</h1>
        <p className="mt-0.5 text-sm text-gray-500">
          Provider roster, enrollment progress, and credential expiry reminders.
        </p>
      </div>

      {/* Roster table */}
      <div>
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
            Roster — {providers.length} provider{providers.length !== 1 ? 's' : ''}
          </h2>
          {providers.length > 0 && (
            <span className="text-xs text-gray-400">Click a row to see enrollment & credential detail</span>
          )}
        </div>

        {loading ? (
          <p className="text-sm text-gray-400">Loading…</p>
        ) : providers.length === 0 ? (
          <div className="rounded-lg border border-dashed border-gray-300 py-8 text-center text-sm text-gray-500">
            No providers yet. Use the invite form below to add your first doula.
          </div>
        ) : (
          <div className="rounded-lg border border-gray-200 bg-white overflow-hidden">
            {providers.map((p, idx) => {
              const isOpen = expanded.has(p.id)
              const warn = hasCredentialWarning(p)
              return (
                <div key={p.id} className={idx > 0 ? 'border-t border-gray-100' : ''}>
                  {/* Summary row */}
                  <button
                    onClick={() => toggleExpand(p.id)}
                    className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-gray-50 transition-colors"
                  >
                    <span className="text-gray-400 text-xs w-3">{isOpen ? '▼' : '▶'}</span>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-sm font-medium text-gray-900">{p.full_name ?? '—'}</span>
                        {enrollmentReadyBadge(p)}
                        {warn && <span className="text-[10px] font-medium text-amber-600">⚠ credential expiring</span>}
                      </div>
                      <span className="text-xs text-gray-500">{p.email}{p.npi ? ` · NPI ${p.npi}` : ''}</span>
                    </div>

                    {/* Stage dots */}
                    <div className="hidden sm:flex items-center gap-1.5">
                      {Object.entries(STAGE_LABELS).map(([key, label]) => (
                        <div key={key} className="flex flex-col items-center gap-0.5">
                          {stageBadge(p.enrollment_stages[key as keyof typeof p.enrollment_stages])}
                          <span className="text-[9px] text-gray-400">{label}</span>
                        </div>
                      ))}
                    </div>
                  </button>

                  {/* Expanded detail */}
                  {isOpen && (
                    <div className="border-t border-gray-100 bg-gray-50 px-5 py-4 space-y-4">
                      {/* Enrollment stages */}
                      <div>
                        <p className="mb-2 text-xs font-semibold text-gray-500 uppercase tracking-wide">Credentialing Stages</p>
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                          {Object.entries(STAGE_LABELS).map(([key, label]) => {
                            const status = p.enrollment_stages[key as keyof typeof p.enrollment_stages]
                            const bg = status === 'complete'
                              ? 'border-green-200 bg-green-50'
                              : status === 'in_progress'
                              ? 'border-yellow-200 bg-yellow-50'
                              : 'border-gray-200 bg-white'
                            const text = status === 'complete'
                              ? 'text-green-700'
                              : status === 'in_progress'
                              ? 'text-yellow-700'
                              : 'text-gray-400'
                            const display = status === 'complete' ? 'Complete' : status === 'in_progress' ? 'In Progress' : status === 'not_started' ? 'Not Started' : 'Not Set Up'
                            return (
                              <div key={key} className={`rounded-md border p-2.5 ${bg}`}>
                                <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wide">{label}</p>
                                <p className={`text-xs font-medium mt-0.5 ${text}`}>{display}</p>
                              </div>
                            )
                          })}
                        </div>
                      </div>

                      {/* Credential expiry */}
                      <div>
                        <p className="mb-2 text-xs font-semibold text-gray-500 uppercase tracking-wide">Credential Expiry</p>
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                          {Object.entries(CRED_LABELS).map(([key, label]) =>
                            expiryChip(label, p.credentials[key as keyof typeof p.credentials])
                          )}
                        </div>
                      </div>

                      {/* Deposit status */}
                      {!p.deposit_paid && (
                        <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2.5 py-1.5">
                          Deposit not yet paid — provider cannot be billed until the $99 deposit is collected.
                        </p>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Invite form */}
      <div className="rounded-lg border border-gray-200 bg-white p-5">
        <h2 className="mb-1 text-sm font-semibold text-gray-900">Invite New Providers</h2>
        <p className="mb-4 text-xs text-gray-500">
          Each provider receives a welcome email with a temporary password and deposit link.
          Providers already in the system are skipped automatically.
        </p>

        {result ? (
          <div className="space-y-3">
            {result.created.length > 0 && (
              <div className="rounded-md border border-green-200 bg-green-50 p-3">
                <p className="mb-1 text-xs font-semibold text-green-800">{result.created.length} invite(s) sent</p>
                {result.created.map((c, i) => (
                  <p key={i} className="text-xs text-green-700">{c.name} — {c.email}</p>
                ))}
              </div>
            )}
            {result.skipped.length > 0 && (
              <div className="rounded-md border border-amber-200 bg-amber-50 p-3">
                <p className="mb-1 text-xs font-semibold text-amber-800">{result.skipped.length} skipped</p>
                {result.skipped.map((s, i) => (
                  <p key={i} className="text-xs text-amber-700">{s.name || s.email} — {s.reason}</p>
                ))}
              </div>
            )}
            <button onClick={() => setResult(null)} className="text-xs text-blue-600 hover:underline">
              Invite more providers →
            </button>
          </div>
        ) : (
          <>
            <div className="space-y-2">
              <div className="grid grid-cols-[1fr_1fr_140px_28px] gap-2 text-xs font-medium text-gray-500 uppercase tracking-wide pb-1 border-b border-gray-100">
                <span>Full Name</span>
                <span>Email Address</span>
                <span>Doula Type</span>
                <span />
              </div>
              {rows.map((row, idx) => (
                <div key={idx} className="grid grid-cols-[1fr_1fr_140px_28px] gap-2 items-center">
                  <input
                    type="text"
                    placeholder="Full name"
                    value={row.name}
                    onChange={e => updateRow(idx, 'name', e.target.value)}
                    className="rounded border border-gray-200 px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                  <input
                    type="email"
                    placeholder="Email address"
                    value={row.email}
                    onChange={e => updateRow(idx, 'email', e.target.value)}
                    className="rounded border border-gray-200 px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                  <select
                    value={row.doula_type}
                    onChange={e => updateRow(idx, 'doula_type', e.target.value)}
                    className="rounded border border-gray-200 px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                  >
                    {DOULA_TYPES.map(t => <option key={t}>{t}</option>)}
                  </select>
                  <button
                    onClick={() => removeRow(idx)}
                    disabled={rows.length === 1}
                    className="text-gray-400 hover:text-red-500 disabled:opacity-20 text-xl leading-none"
                  >×</button>
                </div>
              ))}
            </div>
            <div className="mt-3 flex items-center justify-between">
              <button onClick={addRow} className="text-xs text-blue-600 hover:underline">+ Add another provider</button>
              <button
                onClick={handleSubmit}
                disabled={submitting || validRows.length === 0}
                className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
              >
                {submitting ? 'Sending…' : `Send ${validRows.length} Invite${validRows.length !== 1 ? 's' : ''}`}
              </button>
            </div>
          </>
        )}
      </div>

      {toast && (
        <div className="fixed bottom-6 right-6 z-50 rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm font-medium text-green-800 shadow-lg">
          {toast}
        </div>
      )}
    </div>
  )
}
