'use client'

import { useEffect, useState } from 'react'
import axios from 'axios'
import { getAccessToken } from '@/lib/auth'
import type { BillingProvider } from '@/types/domain'

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

  const statsMap = new Map(stats.map(s => [s.billing_provider_id, s]))

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">Billing Providers</h1>
        <button
          onClick={openCreate}
          className="rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
        >
          + Add Billing Provider
        </button>
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
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                        <button
                          onClick={() => openEdit(bp)}
                          className="rounded border border-gray-300 px-2 py-1 text-xs font-medium text-gray-600 hover:bg-gray-50"
                        >
                          Edit
                        </button>
                        <a
                          href={`/billing-admin/claims?bp_id=${bp.id}`}
                          className="rounded border border-blue-200 px-2 py-1 text-xs font-medium text-blue-700 hover:bg-blue-50"
                        >
                          View Claims
                        </a>
                        <a
                          href={`/billing-admin/settings?bp_id=${bp.id}`}
                          className="rounded border border-blue-200 px-2 py-1 text-xs font-medium text-blue-700 hover:bg-blue-50"
                        >
                          Settings
                        </a>
                        {!['active', 'trialing'].includes(bp.subscription_status ?? '') && (
                          <button
                            onClick={() => startSubscription(bp)}
                            disabled={actionLoading === `sub-${bp.id}`}
                            className="rounded border border-green-300 px-2 py-1 text-xs font-medium text-green-700 hover:bg-green-50 disabled:opacity-50"
                          >
                            {actionLoading === `sub-${bp.id}` ? '…' : 'Start Sub'}
                          </button>
                        )}
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

      {/* Toast */}
      {toast && (
        <div className="fixed bottom-6 right-6 z-50 rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm font-medium text-green-800 shadow-lg">
          {toast}
        </div>
      )}
    </div>
  )
}
