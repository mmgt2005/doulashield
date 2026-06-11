'use client'

import { useEffect, useState } from 'react'
import axios from 'axios'
import { getAccessToken } from '@/lib/auth'
import { BillingProvider } from '@/types/domain'

export default function BillingProvidersPage() {
  const [providers, setProviders] = useState<BillingProvider[]>([])
  const [stats, setStats] = useState<Record<string, unknown>[]>([])
  const [loading, setLoading] = useState(true)
  const [toast, setToast] = useState<string | null>(null)
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState({ name: '', group_npi: '', address: '', city: '', state: '', zip: '', phone: '' })
  const [formError, setFormError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  const [editingId, setEditingId] = useState<string | null>(null)
  const [editForm, setEditForm] = useState({ name: '', group_npi: '', address: '', city: '', state: '', zip: '', phone: '' })

  const headers = { Authorization: `Bearer ${getAccessToken()}` }
  const api = process.env.NEXT_PUBLIC_API_URL

  const showToast = (msg: string) => {
    setToast(msg)
    setTimeout(() => setToast(null), 4000)
  }

  const reload = async () => {
    const [bpRes, statsRes] = await Promise.allSettled([
      axios.get<BillingProvider[]>(`${api}/api/v1/admin/billing-providers`, { headers }),
      axios.get<Record<string, unknown>[]>(`${api}/api/v1/admin/stats/billing-providers`, { headers }),
    ])
    if (bpRes.status === 'fulfilled') setProviders(bpRes.value.data)
    if (statsRes.status === 'fulfilled') setStats(statsRes.value.data)
  }

  useEffect(() => {
    reload().finally(() => setLoading(false))
  }, [])

  const createProvider = async () => {
    if (!form.name.trim()) { setFormError('Name is required'); return }
    setSaving(true)
    setFormError(null)
    try {
      await axios.post(`${api}/api/v1/admin/billing-providers`, {
        name: form.name.trim(),
        group_npi: form.group_npi.trim() || null,
        address: form.address.trim() || null,
        city: form.city.trim() || null,
        state: form.state.trim() || null,
        zip: form.zip.trim() || null,
        phone: form.phone.trim() || null,
      }, { headers })
      setShowCreate(false)
      setForm({ name: '', group_npi: '', address: '', city: '', state: '', zip: '', phone: '' })
      showToast('Billing provider created')
      await reload()
    } catch (e: unknown) {
      const msg = axios.isAxiosError(e) ? e.response?.data?.detail : 'Failed to create'
      setFormError(String(msg))
    } finally {
      setSaving(false)
    }
  }

  const saveEdit = async (id: string) => {
    setSaving(true)
    try {
      await axios.put(`${api}/api/v1/admin/billing-providers/${id}`, {
        name: editForm.name.trim() || null,
        group_npi: editForm.group_npi.trim() || null,
        address: editForm.address.trim() || null,
        city: editForm.city.trim() || null,
        state: editForm.state.trim() || null,
        zip: editForm.zip.trim() || null,
        phone: editForm.phone.trim() || null,
      }, { headers })
      setEditingId(null)
      showToast('Updated')
      await reload()
    } catch (e: unknown) {
      const msg = axios.isAxiosError(e) ? e.response?.data?.detail : 'Failed to update'
      showToast(`Error: ${msg}`)
    } finally {
      setSaving(false)
    }
  }

  const deleteProvider = async (id: string, name: string) => {
    if (!confirm(`Delete "${name}"? This cannot be undone.`)) return
    setActionLoading(`del-${id}`)
    try {
      await axios.delete(`${api}/api/v1/admin/billing-providers/${id}`, { headers })
      showToast(`Deleted ${name}`)
      await reload()
    } catch (e: unknown) {
      const msg = axios.isAxiosError(e) ? e.response?.data?.detail : 'Failed to delete'
      showToast(`Error: ${msg}`)
    } finally {
      setActionLoading(null)
    }
  }

  const startSubscription = async (id: string, name: string) => {
    setActionLoading(`sub-${id}`)
    try {
      await axios.post(`${api}/api/v1/admin/billing-providers/${id}/start-subscription`, {}, { headers })
      showToast(`Subscription started for ${name}`)
      await reload()
    } catch (e: unknown) {
      const msg = axios.isAxiosError(e) ? e.response?.data?.detail : 'Failed to start subscription'
      showToast(`Error: ${msg}`)
    } finally {
      setActionLoading(null)
    }
  }

  const getStatsFor = (id: string) => stats.find((s) => s.billing_provider_id === id)

  const subBadge = (status: string | null) => {
    if (status === 'active' || status === 'trialing')
      return <span className="inline-flex items-center rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">Active</span>
    if (status === 'past_due')
      return <span className="inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700">Past Due</span>
    if (status === 'canceled')
      return <span className="inline-flex items-center rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">Canceled</span>
    return <span className="text-xs text-gray-400">None</span>
  }

  if (loading) return <p className="text-sm text-gray-500">Loading…</p>

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">Billing Providers</h1>
        <button
          onClick={() => { setShowCreate(true); setFormError(null) }}
          className="rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
        >
          + Add Agency
        </button>
      </div>

      {toast && (
        <div className="rounded-lg bg-blue-50 border border-blue-200 px-4 py-2 text-sm text-blue-800">{toast}</div>
      )}

      {/* Stats summary */}
      {stats.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="rounded-lg border border-gray-200 bg-white px-4 py-3">
            <p className="text-xs text-gray-500">Agencies</p>
            <p className="text-lg font-bold text-gray-900">{stats.length}</p>
          </div>
          <div className="rounded-lg border border-gray-200 bg-white px-4 py-3">
            <p className="text-xs text-gray-500">Total Providers</p>
            <p className="text-lg font-bold text-gray-900">{stats.reduce((a, s) => a + Number(s.provider_count ?? 0), 0)}</p>
          </div>
          <div className="rounded-lg border border-gray-200 bg-white px-4 py-3">
            <p className="text-xs text-gray-500">Total Billed</p>
            <p className="text-lg font-bold text-gray-900">${Number(stats.reduce((a, s) => a + Number(s.total_billed ?? 0), 0)).toFixed(2)}</p>
          </div>
          <div className="rounded-lg border border-gray-200 bg-white px-4 py-3">
            <p className="text-xs text-gray-500">Total Paid</p>
            <p className="text-lg font-bold text-gray-900">${Number(stats.reduce((a, s) => a + Number(s.total_paid ?? 0), 0)).toFixed(2)}</p>
          </div>
        </div>
      )}

      <div className="bg-white rounded-lg border border-gray-200 overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              {['Name', 'Group NPI', 'Providers', 'Claims', 'Billed', 'Paid', 'Denial %', 'Subscription', 'Actions'].map((h) => (
                <th key={h} className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase whitespace-nowrap">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {providers.length === 0 && (
              <tr><td colSpan={9} className="px-4 py-6 text-center text-sm text-gray-400">No billing providers yet</td></tr>
            )}
            {providers.map((bp) => {
              const s = getStatsFor(bp.id)
              const isSubActive = bp.subscription_status === 'active' || bp.subscription_status === 'trialing'
              if (editingId === bp.id) {
                return (
                  <tr key={bp.id} className="bg-blue-50">
                    <td className="px-3 py-2" colSpan={8}>
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-2">
                        {(['name', 'group_npi', 'address', 'city', 'state', 'zip', 'phone'] as const).map((f) => (
                          <input
                            key={f}
                            value={editForm[f]}
                            onChange={(e) => setEditForm((prev) => ({ ...prev, [f]: e.target.value }))}
                            placeholder={f.replace('_', ' ')}
                            className="rounded border border-gray-300 px-2 py-1 text-xs focus:border-blue-500 focus:outline-none"
                          />
                        ))}
                      </div>
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex gap-2">
                        <button onClick={() => saveEdit(bp.id)} disabled={saving} className="rounded bg-blue-600 px-2 py-1 text-xs text-white hover:bg-blue-700 disabled:opacity-50">Save</button>
                        <button onClick={() => setEditingId(null)} className="rounded border border-gray-300 px-2 py-1 text-xs text-gray-600 hover:bg-gray-50">Cancel</button>
                      </div>
                    </td>
                  </tr>
                )
              }
              return (
                <tr key={bp.id}>
                  <td className="px-4 py-3 font-medium text-gray-900">{bp.name}</td>
                  <td className="px-4 py-3 text-gray-500">{bp.group_npi ?? '—'}</td>
                  <td className="px-4 py-3 text-gray-700">{s ? String(s.provider_count) : String(bp.provider_count)}</td>
                  <td className="px-4 py-3 text-gray-700">{s ? String(s.total_claims) : '—'}</td>
                  <td className="px-4 py-3 text-gray-700">{s ? `$${Number(s.total_billed).toFixed(2)}` : '—'}</td>
                  <td className="px-4 py-3 text-gray-700">{s ? `$${Number(s.total_paid).toFixed(2)}` : '—'}</td>
                  <td className="px-4 py-3 text-gray-700">{s && s.denial_rate != null ? `${s.denial_rate}%` : '—'}</td>
                  <td className="px-4 py-3">{subBadge(bp.subscription_status)}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2 flex-wrap">
                      {!isSubActive && (
                        <button
                          onClick={() => startSubscription(bp.id, bp.name)}
                          disabled={actionLoading === `sub-${bp.id}`}
                          className="rounded bg-green-600 px-2 py-1 text-xs text-white hover:bg-green-700 disabled:opacity-50 whitespace-nowrap"
                        >
                          {actionLoading === `sub-${bp.id}` ? 'Starting…' : 'Start Sub'}
                        </button>
                      )}
                      <button
                        onClick={() => { setEditingId(bp.id); setEditForm({ name: bp.name, group_npi: bp.group_npi ?? '', address: bp.address ?? '', city: bp.city ?? '', state: bp.state ?? '', zip: bp.zip ?? '', phone: bp.phone ?? '' }) }}
                        className="rounded border border-gray-300 px-2 py-1 text-xs text-gray-600 hover:bg-gray-50 whitespace-nowrap"
                      >
                        Edit
                      </button>
                      {bp.provider_count === 0 && (
                        <button
                          onClick={() => deleteProvider(bp.id, bp.name)}
                          disabled={actionLoading === `del-${bp.id}`}
                          className="rounded border border-red-300 px-2 py-1 text-xs text-red-600 hover:bg-red-50 disabled:opacity-50 whitespace-nowrap"
                        >
                          Delete
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Create modal */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md space-y-4">
            <h3 className="text-base font-semibold text-gray-900">Add Billing Agency</h3>
            <div className="space-y-3">
              {([
                ['name', 'Agency Name *', 'text'],
                ['group_npi', 'Group NPI', 'text'],
                ['address', 'Street Address', 'text'],
                ['city', 'City', 'text'],
                ['state', 'State', 'text'],
                ['zip', 'ZIP', 'text'],
                ['phone', 'Phone', 'tel'],
              ] as [keyof typeof form, string, string][]).map(([field, label, type]) => (
                <div key={field}>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
                  <input
                    type={type}
                    value={form[field]}
                    onChange={(e) => setForm((prev) => ({ ...prev, [field]: e.target.value }))}
                    className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>
              ))}
            </div>
            {formError && <p className="text-xs text-red-600">{formError}</p>}
            <div className="flex items-center justify-end gap-3 pt-1">
              <button onClick={() => setShowCreate(false)} disabled={saving} className="rounded border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50">
                Cancel
              </button>
              <button onClick={createProvider} disabled={saving} className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
                {saving ? 'Creating…' : 'Create Agency'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
