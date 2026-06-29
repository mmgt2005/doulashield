'use client'

import { useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import axios from 'axios'
import Papa from 'papaparse'
import { getAccessToken } from '@/lib/auth'
import type { BillingProvider } from '@/types/domain'

const DOULA_TYPES = ['Birth Doula', 'Postpartum Doula', 'Perinatal Doula', 'Other']
const ALL_MCOS = [
  'AmeriHealth Caritas',
  'Keystone First',
  'UPMC For You',
  'Geisinger Health Plan',
  'Health Partners Plans',
  'Aetna Better Health',
  'UnitedHealthcare Community Plan',
  'Highmark Wholecare',
  'FFS',
]

interface McoContract { mco: string; contract_date: string | null }
interface CsvRow {
  name: string; email: string; npi?: string; doula_type?: string
  mco_contracts?: McoContract[]
  _errors: string[]; _warnings: string[]
}

function parseCsvRows(raw: Record<string, string>[]): CsvRow[] {
  return raw.map(r => {
    const errors: string[] = []
    const warnings: string[] = []
    const name = r.name?.trim() ?? ''
    const email = r.email?.trim().toLowerCase() ?? ''
    if (!name) errors.push('Name required')
    if (!email || !email.includes('@')) errors.push('Valid email required')
    const npi = r.npi?.trim()
    if (npi && !/^\d{10}$/.test(npi)) warnings.push('NPI must be 10 digits')
    const rawType = r.doula_type?.trim()
    const doula_type = DOULA_TYPES.includes(rawType ?? '') ? rawType : 'Birth Doula'
    const mco_contracts: McoContract[] = []
    for (let i = 1; i <= 9; i++) {
      const mco = r[`mco_${i}`]?.trim()
      if (!mco) break
      const normalized = ALL_MCOS.find(m => m.toLowerCase() === mco.toLowerCase())
      if (!normalized) { warnings.push(`Unknown MCO: "${mco}"`); continue }
      mco_contracts.push({ mco: normalized, contract_date: r[`mco_${i}_date`]?.trim() || null })
    }
    return { name, email, npi: npi || undefined, doula_type, mco_contracts: mco_contracts.length ? mco_contracts : undefined, _errors: errors, _warnings: warnings }
  })
}

function downloadTemplate() {
  const lines = [
    'name,email,npi,doula_type,mco_1,mco_1_date,mco_2,mco_2_date',
    'Maria Gonzalez,maria@example.com,1234567890,Birth Doula,AmeriHealth Caritas,2024-01-15,Keystone First,',
  ]
  const blob = new Blob([lines.join('\n')], { type: 'text/csv' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = 'doulashield-provider-import-template.csv'
  a.click()
  URL.revokeObjectURL(a.href)
}

interface Stats {
  billing_provider_id: string
  name: string
  subscription_status: string | null
  provider_count: number
  total_claims: number
  total_billed: number
  total_paid: number
  denial_rate: number | null
}

const EMPTY_FORM = {
  name: '',
  group_npi: '',
  address: '',
  city: '',
  state: '',
  zip: '',
  phone: '',
}

type FormData = typeof EMPTY_FORM

function subBadge(status: string | null) {
  if (!status) return <span className="text-xs text-gray-400">None</span>
  const color =
    status === 'active' ? 'green' :
    status === 'trialing' ? 'blue' :
    status === 'past_due' ? 'amber' : 'red'
  return (
    <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium bg-${color}-50 text-${color}-700 border border-${color}-200`}>
      {status}
    </span>
  )
}

export default function BillingProvidersPage() {
  const [providers, setProviders] = useState<BillingProvider[]>([])
  const [stats, setStats] = useState<Stats[]>([])
  const [loading, setLoading] = useState(true)
  const [toast, setToast] = useState<string | null>(null)
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  // Create / Edit modal
  const [modal, setModal] = useState<{ mode: 'create' | 'edit'; bp?: BillingProvider } | null>(null)
  const [form, setForm] = useState<FormData>(EMPTY_FORM)
  const [formError, setFormError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  // Delete confirm
  const [deleteConfirm, setDeleteConfirm] = useState<BillingProvider | null>(null)

  // Weekly compliance email modal
  const [complianceModal, setComplianceModal] = useState(false)
  const [complianceStep, setComplianceStep] = useState<'preview' | 'done'>('preview')
  const [compliancePreview, setCompliancePreview] = useState<{ sent: number; skipped: number; total_admins: number } | null>(null)
  const [complianceSending, setComplianceSending] = useState(false)

  const openComplianceModal = async () => {
    setComplianceModal(true)
    setComplianceStep('preview')
    setCompliancePreview(null)
    setComplianceSending(true)
    try {
      const res = await axios.post<{ sent: number; skipped: number; total_admins: number }>(
        `${api}/api/v1/admin/jobs/send-weekly-compliance?dry_run=true`,
        {},
        { headers },
      )
      setCompliancePreview(res.data)
    } catch {
      showToast('Failed to load preview.')
      setComplianceModal(false)
    } finally {
      setComplianceSending(false)
    }
  }

  const sendComplianceEmails = async () => {
    setComplianceSending(true)
    try {
      const res = await axios.post<{ sent: number; skipped: number; total_admins: number }>(
        `${api}/api/v1/admin/jobs/send-weekly-compliance`,
        {},
        { headers },
      )
      setCompliancePreview(res.data)
      setComplianceStep('done')
    } catch (e: unknown) {
      const msg = axios.isAxiosError(e) ? e.response?.data?.detail : 'Send failed'
      showToast(typeof msg === 'string' ? msg : 'Send failed')
    } finally {
      setComplianceSending(false)
    }
  }

  // Bulk invite modal
  interface InviteRow { name: string; email: string; doula_type: string }
  const [inviteModal, setInviteModal] = useState<BillingProvider | null>(null)
  const [inviteTab, setInviteTab] = useState<'manual' | 'csv'>('manual')
  const [inviteRows, setInviteRows] = useState<InviteRow[]>([{ name: '', email: '', doula_type: 'Birth Doula' }])
  const [inviteResult, setInviteResult] = useState<{ created: { name: string; email: string }[]; skipped: { name: string; email: string; reason: string }[] } | null>(null)
  const [inviting, setInviting] = useState(false)
  const [csvRows, setCsvRows] = useState<CsvRow[]>([])
  const [csvShowGuide, setCsvShowGuide] = useState(false)
  const csvInputRef = useRef<HTMLInputElement>(null)

  const openInviteModal = (bp: BillingProvider) => {
    setInviteModal(bp)
    setInviteTab('manual')
    setInviteRows([{ name: '', email: '', doula_type: 'Birth Doula' }])
    setInviteResult(null)
    setCsvRows([])
    setCsvShowGuide(false)
  }

  const handleCsvFile = (file: File) => {
    Papa.parse<Record<string, string>>(file, {
      header: true,
      skipEmptyLines: true,
      complete: (result) => setCsvRows(parseCsvRows(result.data)),
    })
  }

  const updateInviteRow = (idx: number, field: keyof InviteRow, value: string) =>
    setInviteRows(rows => rows.map((r, i) => i === idx ? { ...r, [field]: value } : r))

  const addInviteRow = () => setInviteRows(rows => [...rows, { name: '', email: '', doula_type: 'Birth Doula' }])

  const removeInviteRow = (idx: number) => setInviteRows(rows => rows.filter((_, i) => i !== idx))

  const submitInvites = async () => {
    if (!inviteModal) return
    const valid = inviteRows.filter(r => r.name.trim() && r.email.trim())
    if (!valid.length) return
    setInviting(true)
    setInviteResult(null)
    try {
      const res = await axios.post<{ created: { name: string; email: string }[]; skipped: { name: string; email: string; reason: string }[] }>(
        `${api}/api/v1/admin/billing-providers/${inviteModal.id}/bulk-invite-providers`,
        { providers: valid },
        { headers }
      )
      setInviteResult(res.data)
      await reload()
    } catch (e: unknown) {
      const msg = axios.isAxiosError(e) ? e.response?.data?.detail : 'Invite failed'
      showToast(typeof msg === 'string' ? msg : 'Invite failed')
    } finally {
      setInviting(false)
    }
  }

  const submitCsvInvites = async () => {
    if (!inviteModal) return
    const importable = csvRows.filter(r => r._errors.length === 0)
    if (!importable.length) return
    setInviting(true)
    setInviteResult(null)
    try {
      const res = await axios.post<{ created: { name: string; email: string }[]; skipped: { name: string; email: string; reason: string }[] }>(
        `${api}/api/v1/admin/billing-providers/${inviteModal.id}/bulk-invite-providers`,
        { providers: importable.map(({ _errors: _e, _warnings: _w, ...rest }) => rest) },
        { headers }
      )
      setInviteResult(res.data)
      await reload()
    } catch (e: unknown) {
      const msg = axios.isAxiosError(e) ? e.response?.data?.detail : 'Import failed'
      showToast(typeof msg === 'string' ? msg : 'Import failed')
    } finally {
      setInviting(false)
    }
  }

  const api = process.env.NEXT_PUBLIC_API_URL
  const headers = { Authorization: `Bearer ${getAccessToken()}` }

  const showToast = (msg: string) => {
    setToast(msg)
    setTimeout(() => setToast(null), 4000)
  }

  const reload = async () => {
    setLoading(true)
    try {
      const [bpRes, statsRes] = await Promise.allSettled([
        axios.get<BillingProvider[]>(`${api}/api/v1/admin/billing-providers`, { headers }),
        axios.get<Stats[]>(`${api}/api/v1/admin/stats/billing-providers`, { headers }),
      ])
      if (bpRes.status === 'fulfilled') setProviders(bpRes.value.data)
      if (statsRes.status === 'fulfilled') setStats(statsRes.value.data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { reload() }, [])

  const openCreate = () => {
    setForm(EMPTY_FORM)
    setFormError(null)
    setModal({ mode: 'create' })
  }

  const openEdit = (bp: BillingProvider) => {
    setForm({
      name: bp.name,
      group_npi: bp.group_npi ?? '',
      address: bp.address ?? '',
      city: bp.city ?? '',
      state: bp.state ?? '',
      zip: bp.zip ?? '',
      phone: bp.phone ?? '',
    })
    setFormError(null)
    setModal({ mode: 'edit', bp })
  }

  const submitForm = async () => {
    if (!form.name.trim()) { setFormError('Name is required.'); return }
    setSaving(true)
    setFormError(null)
    const body = {
      name: form.name.trim(),
      group_npi: form.group_npi.trim() || null,
      address: form.address.trim() || null,
      city: form.city.trim() || null,
      state: form.state.trim() || null,
      zip: form.zip.trim() || null,
      phone: form.phone.trim() || null,
    }
    try {
      if (modal?.mode === 'create') {
        await axios.post(`${api}/api/v1/admin/billing-providers`, body, { headers })
        showToast('Billing provider created.')
      } else if (modal?.bp) {
        await axios.put(`${api}/api/v1/admin/billing-providers/${modal.bp.id}`, body, { headers })
        showToast('Billing provider updated.')
      }
      setModal(null)
      await reload()
    } catch (e: unknown) {
      const msg = axios.isAxiosError(e) ? e.response?.data?.detail : 'Save failed'
      setFormError(typeof msg === 'string' ? msg : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  const confirmDelete = async () => {
    if (!deleteConfirm) return
    setActionLoading(`del-${deleteConfirm.id}`)
    try {
      await axios.delete(`${api}/api/v1/admin/billing-providers/${deleteConfirm.id}`, { headers })
      showToast('Billing provider deleted.')
      setDeleteConfirm(null)
      await reload()
    } catch (e: unknown) {
      const msg = axios.isAxiosError(e) ? e.response?.data?.detail : 'Delete failed'
      showToast(`Error: ${typeof msg === 'string' ? msg : 'Delete failed'}`)
      setDeleteConfirm(null)
    } finally {
      setActionLoading(null)
    }
  }

  const startSubscription = async (bp: BillingProvider) => {
    setActionLoading(`sub-${bp.id}`)
    try {
      await axios.post(`${api}/api/v1/admin/billing-providers/${bp.id}/start-subscription`, {}, { headers })
      showToast('Subscription started.')
      await reload()
    } catch (e: unknown) {
      const msg = axios.isAxiosError(e) ? e.response?.data?.detail : 'Failed'
      showToast(`Error: ${typeof msg === 'string' ? msg : 'Failed'}`)
    } finally {
      setActionLoading(null)
    }
  }

  const toggleEnrollmentTier = async (bp: BillingProvider) => {
    const action = bp.enrollment_tier_enabled ? 'disable' : 'enable'
    setActionLoading(`tier-${bp.id}`)
    try {
      await axios.post(`${api}/api/v1/admin/billing-providers/${bp.id}/${action}-enrollment-tier`, {}, { headers })
      showToast(`Enrollment tier ${action}d.`)
      await reload()
    } catch (e: unknown) {
      const msg = axios.isAxiosError(e) ? e.response?.data?.detail : 'Failed'
      showToast(`Error: ${typeof msg === 'string' ? msg : 'Failed'}`)
    } finally {
      setActionLoading(null)
    }
  }

  const statsMap = new Map(stats.map(s => [s.billing_provider_id, s]))

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">Billing Providers</h1>
        <div className="flex gap-2">
          <button
            onClick={openComplianceModal}
            className="rounded border border-teal-300 bg-teal-50 px-3 py-1.5 text-sm font-medium text-teal-700 hover:bg-teal-100"
          >
            Send Weekly Compliance Email
          </button>
          <button
            onClick={openCreate}
            className="rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
          >
            + Add Billing Provider
          </button>
        </div>
      </div>

      {/* Stats cards */}
      {stats.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="rounded-lg border border-gray-200 bg-white p-4">
            <p className="text-xs text-gray-500">Agencies</p>
            <p className="mt-1 text-2xl font-bold text-gray-900">{providers.length}</p>
          </div>
          <div className="rounded-lg border border-gray-200 bg-white p-4">
            <p className="text-xs text-gray-500">Total Providers</p>
            <p className="mt-1 text-2xl font-bold text-gray-900">
              {stats.reduce((a, s) => a + s.provider_count, 0)}
            </p>
          </div>
          <div className="rounded-lg border border-gray-200 bg-white p-4">
            <p className="text-xs text-gray-500">Total Billed</p>
            <p className="mt-1 text-2xl font-bold text-gray-900">
              ${stats.reduce((a, s) => a + Number(s.total_billed), 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </p>
          </div>
          <div className="rounded-lg border border-gray-200 bg-white p-4">
            <p className="text-xs text-gray-500">Active Subscriptions</p>
            <p className="mt-1 text-2xl font-bold text-gray-900">
              {providers.filter(p => p.subscription_status === 'active').length}
            </p>
          </div>
        </div>
      )}

      {loading ? (
        <p className="text-sm text-gray-500">Loading…</p>
      ) : providers.length === 0 ? (
        <div className="rounded-lg border border-dashed border-gray-300 bg-white p-8 text-center">
          <p className="text-sm text-gray-500">No billing providers yet.</p>
          <button onClick={openCreate} className="mt-3 text-sm text-blue-600 hover:underline">
            Add the first one →
          </button>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
                <th className="px-4 py-3">Agency Name</th>
                <th className="px-4 py-3">Group NPI</th>
                <th className="px-4 py-3">Location</th>
                <th className="px-4 py-3">Providers</th>
                <th className="px-4 py-3">Claims</th>
                <th className="px-4 py-3">Billed</th>
                <th className="px-4 py-3">Paid</th>
                <th className="px-4 py-3">Denial %</th>
                <th className="px-4 py-3">Subscription</th>
                <th className="px-4 py-3">Monthly</th>
                <th className="px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {providers.map(bp => {
                const s = statsMap.get(bp.id)
                return (
                  <tr key={bp.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium text-gray-900">{bp.name}</td>
                    <td className="px-4 py-3 text-gray-600 font-mono text-xs">{bp.group_npi ?? '—'}</td>
                    <td className="px-4 py-3 text-gray-500 text-xs">
                      {[bp.city, bp.state].filter(Boolean).join(', ') || '—'}
                    </td>
                    <td className="px-4 py-3 text-center font-medium">{bp.provider_count}</td>
                    <td className="px-4 py-3 text-center">{s?.total_claims ?? 0}</td>
                    <td className="px-4 py-3 tabular-nums">
                      {s ? `$${Number(s.total_billed).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '—'}
                    </td>
                    <td className="px-4 py-3 tabular-nums text-green-700">
                      {s ? `$${Number(s.total_paid).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '—'}
                    </td>
                    <td className="px-4 py-3 tabular-nums">
                      {s?.denial_rate != null ? `${s.denial_rate}%` : '—'}
                    </td>
                    <td className="px-4 py-3">{subBadge(bp.subscription_status)}</td>
                    <td className="px-4 py-3 tabular-nums text-xs">
                      {['active', 'trialing'].includes(bp.subscription_status ?? '') ? (
                        <span className="text-gray-700">
                          {Math.max(3, bp.provider_count)} seats<br />
                          <span className="font-medium">${(Math.max(3, bp.provider_count) * 55).toLocaleString()}/mo</span>
                        </span>
                      ) : (
                        <span className="text-gray-400">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                        <button
                          onClick={() => openEdit(bp)}
                          className="rounded border border-gray-300 px-2 py-1 text-xs font-medium text-gray-600 hover:bg-gray-50"
                        >
                          Edit
                        </button>
                        <Link
                          href={`/billing-admin/claims?bp_id=${bp.id}`}
                          className="rounded border border-blue-200 px-2 py-1 text-xs font-medium text-blue-700 hover:bg-blue-50"
                        >
                          View Claims
                        </Link>
                        <Link
                          href={`/billing-admin/settings?bp_id=${bp.id}`}
                          className="rounded border border-blue-200 px-2 py-1 text-xs font-medium text-blue-700 hover:bg-blue-50"
                        >
                          Settings
                        </Link>
                        {!['active', 'trialing'].includes(bp.subscription_status ?? '') && (
                          <button
                            onClick={() => startSubscription(bp)}
                            disabled={actionLoading === `sub-${bp.id}`}
                            className="rounded border border-green-300 px-2 py-1 text-xs font-medium text-green-700 hover:bg-green-50 disabled:opacity-50"
                          >
                            {actionLoading === `sub-${bp.id}` ? '…' : 'Start Sub'}
                          </button>
                        )}
                        {['active', 'trialing'].includes(bp.subscription_status ?? '') && (
                          <button
                            onClick={() => toggleEnrollmentTier(bp)}
                            disabled={actionLoading === `tier-${bp.id}`}
                            className={`rounded border px-2 py-1 text-xs font-medium disabled:opacity-50 ${
                              bp.enrollment_tier_enabled
                                ? 'border-amber-200 text-amber-700 hover:bg-amber-50'
                                : 'border-purple-200 text-purple-700 hover:bg-purple-50'
                            }`}
                          >
                            {actionLoading === `tier-${bp.id}` ? '…' : bp.enrollment_tier_enabled ? 'Disable Enroll Tier' : 'Enable Enroll Tier'}
                          </button>
                        )}
                        <button
                          onClick={() => openInviteModal(bp)}
                          className="rounded border border-indigo-200 px-2 py-1 text-xs font-medium text-indigo-700 hover:bg-indigo-50"
                        >
                          Invite Providers
                        </button>
                        <button
                          onClick={() => setDeleteConfirm(bp)}
                          disabled={bp.provider_count > 0}
                          title={bp.provider_count > 0 ? 'Unassign all providers first' : 'Delete'}
                          className="rounded border border-red-200 px-2 py-1 text-xs font-medium text-red-600 hover:bg-red-50 disabled:opacity-30 disabled:cursor-not-allowed"
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Create / Edit modal */}
      {modal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-lg rounded-xl bg-white p-6 shadow-xl">
            <h2 className="mb-4 text-base font-semibold text-gray-900">
              {modal.mode === 'create' ? 'Add Billing Provider' : 'Edit Billing Provider'}
            </h2>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Agency Name *</label>
                <input
                  type="text"
                  value={form.name}
                  onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                  className="w-full rounded border border-gray-300 px-3 py-1.5 text-sm"
                  placeholder="e.g. Philadelphia Doula Collective"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Group NPI</label>
                <input
                  type="text"
                  maxLength={10}
                  value={form.group_npi}
                  onChange={e => setForm(f => ({ ...f, group_npi: e.target.value }))}
                  className="w-full rounded border border-gray-300 px-3 py-1.5 text-sm font-mono"
                  placeholder="10-digit group NPI"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Street Address</label>
                  <input
                    type="text"
                    value={form.address}
                    onChange={e => setForm(f => ({ ...f, address: e.target.value }))}
                    className="w-full rounded border border-gray-300 px-3 py-1.5 text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">City</label>
                  <input
                    type="text"
                    value={form.city}
                    onChange={e => setForm(f => ({ ...f, city: e.target.value }))}
                    className="w-full rounded border border-gray-300 px-3 py-1.5 text-sm"
                  />
                </div>
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">State</label>
                  <input
                    type="text"
                    maxLength={2}
                    value={form.state}
                    onChange={e => setForm(f => ({ ...f, state: e.target.value.toUpperCase() }))}
                    className="w-full rounded border border-gray-300 px-3 py-1.5 text-sm uppercase"
                    placeholder="PA"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">ZIP</label>
                  <input
                    type="text"
                    value={form.zip}
                    onChange={e => setForm(f => ({ ...f, zip: e.target.value }))}
                    className="w-full rounded border border-gray-300 px-3 py-1.5 text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Phone</label>
                  <input
                    type="text"
                    value={form.phone}
                    onChange={e => setForm(f => ({ ...f, phone: e.target.value }))}
                    className="w-full rounded border border-gray-300 px-3 py-1.5 text-sm"
                  />
                </div>
              </div>
              {formError && <p className="text-xs text-red-600">{formError}</p>}
            </div>
            <div className="mt-5 flex justify-end gap-3">
              <button
                type="button"
                onClick={() => setModal(null)}
                className="rounded border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={submitForm}
                disabled={saving}
                className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {saving ? 'Saving…' : modal.mode === 'create' ? 'Create' : 'Save Changes'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Delete confirmation */}
      {deleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-sm rounded-xl bg-white p-6 shadow-xl">
            <h2 className="mb-2 text-base font-semibold text-gray-900">Delete Billing Provider</h2>
            <p className="text-sm text-gray-600">
              Are you sure you want to delete <strong>{deleteConfirm.name}</strong>? This cannot be undone.
            </p>
            <div className="mt-5 flex justify-end gap-3">
              <button
                onClick={() => setDeleteConfirm(null)}
                className="rounded border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={confirmDelete}
                disabled={actionLoading?.startsWith('del-')}
                className="rounded bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
              >
                {actionLoading?.startsWith('del-') ? 'Deleting…' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Bulk Invite / Import Providers modal */}
      {inviteModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-2xl rounded-xl bg-white p-6 shadow-xl">
            <h2 className="mb-1 text-base font-semibold text-gray-900">
              Invite Providers — {inviteModal.name}
            </h2>
            <p className="mb-3 text-xs text-gray-500">
              Each provider receives a welcome email with login credentials.
              Providers already in the system are skipped automatically.
            </p>

            {!inviteResult ? (
              <>
                {/* Tab switcher */}
                <div className="mb-4 flex gap-1 rounded-lg bg-gray-100 p-1 w-fit">
                  {(['manual', 'csv'] as const).map(tab => (
                    <button
                      key={tab}
                      onClick={() => setInviteTab(tab)}
                      className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${inviteTab === tab ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}
                    >
                      {tab === 'manual' ? 'Enter Manually' : 'Upload CSV'}
                    </button>
                  ))}
                </div>

                {inviteTab === 'manual' ? (
                  <>
                    <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
                      {inviteRows.map((row, idx) => (
                        <div key={idx} className="grid grid-cols-[1fr_1fr_140px_28px] gap-2 items-center">
                          <input type="text" placeholder="Full Name" value={row.name}
                            onChange={e => updateInviteRow(idx, 'name', e.target.value)}
                            className="rounded border border-gray-200 px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500" />
                          <input type="email" placeholder="Email address" value={row.email}
                            onChange={e => updateInviteRow(idx, 'email', e.target.value)}
                            className="rounded border border-gray-200 px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500" />
                          <select value={row.doula_type}
                            onChange={e => updateInviteRow(idx, 'doula_type', e.target.value)}
                            className="rounded border border-gray-200 px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500">
                            {DOULA_TYPES.map(t => <option key={t}>{t}</option>)}
                          </select>
                          <button onClick={() => removeInviteRow(idx)} disabled={inviteRows.length === 1}
                            className="text-gray-400 hover:text-red-500 disabled:opacity-30 text-lg leading-none" title="Remove row">×</button>
                        </div>
                      ))}
                    </div>
                    <button onClick={addInviteRow} className="mt-2 text-xs text-blue-600 hover:underline">+ Add another provider</button>
                    <div className="mt-5 flex justify-end gap-3">
                      <button onClick={() => setInviteModal(null)}
                        className="rounded border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">Cancel</button>
                      <button onClick={submitInvites}
                        disabled={inviting || !inviteRows.some(r => r.name.trim() && r.email.trim())}
                        className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50">
                        {inviting ? 'Inviting…' : `Send ${inviteRows.filter(r => r.name.trim() && r.email.trim()).length} Invite(s)`}
                      </button>
                    </div>
                  </>
                ) : (
                  <>
                    {/* Column guide */}
                    <div className="mb-3">
                      <button onClick={() => setCsvShowGuide(g => !g)}
                        className="text-xs text-blue-600 hover:underline">
                        {csvShowGuide ? '▲ Hide column guide' : '▼ Show column guide & valid values'}
                      </button>
                      {csvShowGuide && (
                        <div className="mt-2 rounded-md border border-gray-200 bg-gray-50 p-3 text-xs space-y-2">
                          <p className="font-medium text-gray-700">CSV columns (first row must be a header):</p>
                          <table className="w-full text-xs">
                            <thead><tr className="text-gray-500"><th className="text-left pr-3 pb-1">Column</th><th className="text-left pb-1">Notes</th></tr></thead>
                            <tbody className="text-gray-700">
                              <tr><td className="pr-3 font-mono py-0.5">name</td><td>Required. Provider full name.</td></tr>
                              <tr><td className="pr-3 font-mono py-0.5">email</td><td>Required. Must be unique.</td></tr>
                              <tr><td className="pr-3 font-mono py-0.5">npi</td><td>Optional. 10-digit NPI number.</td></tr>
                              <tr><td className="pr-3 font-mono py-0.5">doula_type</td><td>Optional. See valid values below.</td></tr>
                              <tr><td className="pr-3 font-mono py-0.5">mco_1 … mco_9</td><td>Optional. MCO name (see list below).</td></tr>
                              <tr><td className="pr-3 font-mono py-0.5">mco_1_date … mco_9_date</td><td>Optional. Contract date YYYY-MM-DD.</td></tr>
                            </tbody>
                          </table>
                          <div className="grid grid-cols-2 gap-2 pt-1">
                            <div>
                              <p className="font-medium text-gray-600 mb-1">Doula types</p>
                              {DOULA_TYPES.map(t => <p key={t} className="font-mono text-gray-700">{t}</p>)}
                            </div>
                            <div>
                              <p className="font-medium text-gray-600 mb-1">MCO names</p>
                              {ALL_MCOS.map(m => <p key={m} className="font-mono text-gray-700">{m}</p>)}
                            </div>
                          </div>
                        </div>
                      )}
                    </div>

                    {/* File picker */}
                    {csvRows.length === 0 ? (
                      <div
                        className="flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-gray-300 bg-gray-50 py-8 cursor-pointer hover:border-indigo-400 hover:bg-indigo-50 transition-colors"
                        onClick={() => csvInputRef.current?.click()}
                        onDragOver={e => e.preventDefault()}
                        onDrop={e => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f) handleCsvFile(f) }}
                      >
                        <p className="text-sm font-medium text-gray-700">Drop CSV here or click to browse</p>
                        <p className="mt-1 text-xs text-gray-400">One provider per row · .csv files only</p>
                        <input ref={csvInputRef} type="file" accept=".csv" className="hidden"
                          onChange={e => { const f = e.target.files?.[0]; if (f) handleCsvFile(f) }} />
                        <button onClick={e => { e.stopPropagation(); downloadTemplate() }}
                          className="mt-3 text-xs text-indigo-600 hover:underline">
                          Download template CSV →
                        </button>
                      </div>
                    ) : (
                      <>
                        {/* Preview table */}
                        <div className="max-h-64 overflow-y-auto rounded border border-gray-200 text-xs">
                          <table className="min-w-full">
                            <thead className="bg-gray-50 sticky top-0">
                              <tr className="text-gray-500 text-left">
                                <th className="px-2 py-1.5">Name</th>
                                <th className="px-2 py-1.5">Email</th>
                                <th className="px-2 py-1.5">NPI</th>
                                <th className="px-2 py-1.5">Type</th>
                                <th className="px-2 py-1.5">MCOs</th>
                                <th className="px-2 py-1.5">Status</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-100">
                              {csvRows.map((row, i) => (
                                <tr key={i} className={row._errors.length ? 'bg-red-50' : row._warnings.length ? 'bg-amber-50' : ''}>
                                  <td className="px-2 py-1.5">{row.name || <span className="text-red-400">—</span>}</td>
                                  <td className="px-2 py-1.5">{row.email || <span className="text-red-400">—</span>}</td>
                                  <td className="px-2 py-1.5 font-mono">{row.npi || <span className="text-gray-300">—</span>}</td>
                                  <td className="px-2 py-1.5">{row.doula_type}</td>
                                  <td className="px-2 py-1.5">{row.mco_contracts?.map(c => c.mco).join(', ') || <span className="text-gray-300">—</span>}</td>
                                  <td className="px-2 py-1.5">
                                    {row._errors.length ? (
                                      <span className="text-red-600" title={row._errors.join('; ')}>✗ {row._errors[0]}</span>
                                    ) : row._warnings.length ? (
                                      <span className="text-amber-600" title={row._warnings.join('; ')}>⚠ {row._warnings[0]}</span>
                                    ) : (
                                      <span className="text-green-600">✓</span>
                                    )}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                        <div className="mt-2 flex items-center gap-3 text-xs text-gray-500">
                          <span>{csvRows.filter(r => r._errors.length === 0).length} importable</span>
                          {csvRows.some(r => r._errors.length > 0) && <span className="text-red-500">{csvRows.filter(r => r._errors.length > 0).length} with errors (skipped)</span>}
                          {csvRows.some(r => r._warnings.length > 0 && r._errors.length === 0) && <span className="text-amber-500">{csvRows.filter(r => r._warnings.length > 0 && r._errors.length === 0).length} with warnings</span>}
                          <button onClick={() => { setCsvRows([]); if (csvInputRef.current) csvInputRef.current.value = '' }}
                            className="ml-auto text-gray-400 hover:text-gray-600">Choose different file</button>
                        </div>
                        <div className="mt-4 flex justify-end gap-3">
                          <button onClick={() => setInviteModal(null)}
                            className="rounded border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">Cancel</button>
                          <button onClick={submitCsvInvites}
                            disabled={inviting || csvRows.filter(r => r._errors.length === 0).length === 0}
                            className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50">
                            {inviting ? 'Importing…' : `Import ${csvRows.filter(r => r._errors.length === 0).length} Provider(s)`}
                          </button>
                        </div>
                      </>
                    )}
                    {csvRows.length === 0 && (
                      <div className="mt-4 flex justify-end">
                        <button onClick={() => setInviteModal(null)}
                          className="rounded border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">Cancel</button>
                      </div>
                    )}
                  </>
                )}
              </>
            ) : (
              <div className="space-y-3">
                {inviteResult.created.length > 0 && (
                  <div className="rounded-md border border-green-200 bg-green-50 p-3">
                    <p className="mb-1 text-xs font-semibold text-green-800">{inviteResult.created.length} provider(s) added</p>
                    {inviteResult.created.map((c, i) => (
                      <p key={i} className="text-xs text-green-700">{c.name} — {c.email}</p>
                    ))}
                  </div>
                )}
                {inviteResult.skipped.length > 0 && (
                  <div className="rounded-md border border-amber-200 bg-amber-50 p-3">
                    <p className="mb-1 text-xs font-semibold text-amber-800">{inviteResult.skipped.length} skipped</p>
                    {inviteResult.skipped.map((s, i) => (
                      <p key={i} className="text-xs text-amber-700">{s.name || s.email} — {s.reason}</p>
                    ))}
                  </div>
                )}
                <div className="flex justify-end">
                  <button onClick={() => setInviteModal(null)}
                    className="rounded bg-gray-800 px-4 py-2 text-sm font-medium text-white hover:bg-gray-900">Done</button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Weekly compliance email modal */}
      {complianceModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-sm rounded-xl bg-white p-6 shadow-xl">
            {complianceStep === 'preview' ? (
              <>
                <h2 className="mb-1 text-base font-semibold text-gray-900">Send Weekly Compliance Email</h2>
                <p className="mb-4 text-xs text-gray-500">
                  Sends a compliance digest to every billing admin with at least one credential warning
                  or enrollment action item. Admins whose roster is fully current are skipped.
                </p>
                {complianceSending ? (
                  <p className="text-sm text-gray-500">Loading preview…</p>
                ) : compliancePreview && (
                  <div className="rounded-md border border-gray-200 bg-gray-50 p-3 mb-4 text-sm space-y-1">
                    <p className="text-gray-700">
                      <span className="font-semibold text-teal-700">{compliancePreview.sent}</span> billing admin{compliancePreview.sent !== 1 ? 's' : ''} will receive an email
                    </p>
                    <p className="text-gray-500 text-xs">
                      {compliancePreview.skipped} skipped (all providers current) · {compliancePreview.total_admins} total
                    </p>
                  </div>
                )}
                <div className="flex justify-end gap-3">
                  <button
                    onClick={() => setComplianceModal(false)}
                    className="rounded border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={sendComplianceEmails}
                    disabled={complianceSending || !compliancePreview || compliancePreview.sent === 0}
                    className="rounded bg-teal-600 px-4 py-2 text-sm font-medium text-white hover:bg-teal-700 disabled:opacity-50"
                  >
                    {complianceSending ? 'Sending…' : `Send to ${compliancePreview?.sent ?? '…'}`}
                  </button>
                </div>
              </>
            ) : (
              <>
                <h2 className="mb-1 text-base font-semibold text-gray-900">Emails Sent</h2>
                <div className="rounded-md border border-green-200 bg-green-50 p-3 my-4 text-sm">
                  <p className="text-green-800 font-medium">
                    {compliancePreview?.sent} compliance email{compliancePreview?.sent !== 1 ? 's' : ''} sent successfully
                  </p>
                  {(compliancePreview?.skipped ?? 0) > 0 && (
                    <p className="text-green-700 text-xs mt-1">
                      {compliancePreview?.skipped} admin{compliancePreview?.skipped !== 1 ? 's' : ''} skipped — all providers current
                    </p>
                  )}
                </div>
                <div className="flex justify-end">
                  <button
                    onClick={() => setComplianceModal(false)}
                    className="rounded bg-gray-800 px-4 py-2 text-sm font-medium text-white hover:bg-gray-900"
                  >
                    Done
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* Toast */}
      {toast && (
        <div className="fixed bottom-6 right-6 z-50 rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm font-medium text-green-800 shadow-lg">
          {toast}
        </div>
      )}
    </div>
  )
}
