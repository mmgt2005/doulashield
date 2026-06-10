'use client'

import { useEffect, useState } from 'react'
import axios from 'axios'
import { getAccessToken } from '@/lib/auth'

interface BillingProvider {
  id: string
  name: string
  npi: string
  taxonomy_code: string | null
  address: string | null
  city: string | null
  state: string | null
  zip_code: string | null
  phone: string | null
  tax_id_connected: boolean
  created_at: string
}

interface FormState {
  name: string
  npi: string
  taxonomy_code: string
  address: string
  city: string
  state: string
  zip_code: string
  phone: string
  tax_id: string
}

const EMPTY_FORM: FormState = {
  name: '',
  npi: '',
  taxonomy_code: '',
  address: '',
  city: '',
  state: '',
  zip_code: '',
  phone: '',
  tax_id: '',
}

export default function BillingProvidersPage() {
  const [providers, setProviders] = useState<BillingProvider[]>([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [editing, setEditing] = useState<BillingProvider | null>(null)
  const [form, setForm] = useState<FormState>(EMPTY_FORM)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [toast, setToast] = useState<string | null>(null)

  const base = process.env.NEXT_PUBLIC_API_URL
  const headers = { Authorization: `Bearer ${getAccessToken()}` }

  const showToast = (msg: string) => {
    setToast(msg)
    setTimeout(() => setToast(null), 3000)
  }

  const load = async () => {
    try {
      const res = await axios.get<BillingProvider[]>(
        `${base}/api/v1/admin/billing-providers`,
        { headers }
      )
      setProviders(res.data)
    } catch {
      // silently fail — error shown in empty state
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const openCreate = () => {
    setEditing(null)
    setForm(EMPTY_FORM)
    setError(null)
    setShowModal(true)
  }

  const openEdit = (bp: BillingProvider) => {
    setEditing(bp)
    setForm({
      name: bp.name,
      npi: bp.npi,
      taxonomy_code: bp.taxonomy_code ?? '',
      address: bp.address ?? '',
      city: bp.city ?? '',
      state: bp.state ?? '',
      zip_code: bp.zip_code ?? '',
      phone: bp.phone ?? '',
      tax_id: '',
    })
    setError(null)
    setShowModal(true)
  }

  const handleSave = async () => {
    if (!form.name.trim() || !form.npi.trim()) {
      setError('Name and NPI are required.')
      return
    }
    setSaving(true)
    setError(null)
    try {
      const body: Record<string, string | null> = {
        name: form.name.trim(),
        npi: form.npi.trim(),
        taxonomy_code: form.taxonomy_code.trim() || null,
        address: form.address.trim() || null,
        city: form.city.trim() || null,
        state: form.state.trim() || null,
        zip_code: form.zip_code.trim() || null,
        phone: form.phone.trim() || null,
        tax_id: form.tax_id.trim() || null,
      }
      if (editing) {
        await axios.put(`${base}/api/v1/admin/billing-providers/${editing.id}`, body, { headers })
        showToast('Billing provider updated.')
      } else {
        await axios.post(`${base}/api/v1/admin/billing-providers`, body, { headers })
        showToast('Billing provider created.')
      }
      setShowModal(false)
      await load()
    } catch (e: unknown) {
      const msg = axios.isAxiosError(e) ? e.response?.data?.detail : 'Failed to save'
      setError(typeof msg === 'string' ? msg : 'Failed to save')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (bp: BillingProvider) => {
    if (!confirm(`Delete billing provider "${bp.name}"? Linked providers will lose their billing assignment.`)) return
    try {
      await axios.delete(`${base}/api/v1/admin/billing-providers/${bp.id}`, { headers })
      showToast('Billing provider deleted.')
      await load()
    } catch {
      showToast('Failed to delete billing provider.')
    }
  }

  return (
    <div className="max-w-4xl space-y-6 p-4 lg:p-6">
      {toast && (
        <div className="fixed top-4 right-4 z-50 rounded-lg border border-green-200 bg-green-50 px-4 py-2 text-sm font-medium text-green-800 shadow">
          {toast}
        </div>
      )}

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Billing Providers</h1>
          <p className="mt-0.5 text-sm text-gray-500">
            Shared billing entities (group NPI). When assigned to a provider, the agency NPI
            appears in Box 33a of the CMS 1500 and in Availity claims.
          </p>
        </div>
        <button
          onClick={openCreate}
          className="rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
        >
          + Add Billing Provider
        </button>
      </div>

      {loading ? (
        <p className="text-sm text-gray-500">Loading…</p>
      ) : providers.length === 0 ? (
        <div className="rounded-lg border border-dashed border-gray-300 p-8 text-center">
          <p className="text-sm text-gray-500">No billing providers yet.</p>
          <p className="mt-1 text-xs text-gray-400">
            Create one to let doulas submit claims under an agency group NPI.
          </p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border border-gray-200 bg-white">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">
              <tr>
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">NPI</th>
                <th className="px-4 py-3">Location</th>
                <th className="px-4 py-3">Tax ID</th>
                <th className="px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {providers.map((bp) => (
                <tr key={bp.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{bp.name}</td>
                  <td className="px-4 py-3 font-mono text-gray-700">{bp.npi}</td>
                  <td className="px-4 py-3 text-gray-600">
                    {[bp.city, bp.state].filter(Boolean).join(', ') || '—'}
                  </td>
                  <td className="px-4 py-3">
                    {bp.tax_id_connected ? (
                      <span className="rounded-full bg-green-50 px-2 py-0.5 text-xs font-medium text-green-700 border border-green-200">
                        ✓ On file
                      </span>
                    ) : (
                      <span className="text-gray-400 text-xs">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-2">
                      <button
                        onClick={() => openEdit(bp)}
                        className="text-xs font-medium text-blue-600 hover:underline"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleDelete(bp)}
                        className="text-xs font-medium text-red-500 hover:underline"
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Create / Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/30 p-4">
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl space-y-4">
            <h2 className="text-base font-semibold text-gray-900">
              {editing ? 'Edit Billing Provider' : 'Add Billing Provider'}
            </h2>

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-700">Name *</label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm(f => ({ ...f, name: e.target.value }))}
                  placeholder="Doula Agency Inc."
                  className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:outline-none focus:border-blue-400"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700">NPI (Group) *</label>
                <input
                  type="text"
                  value={form.npi}
                  onChange={(e) => setForm(f => ({ ...f, npi: e.target.value }))}
                  placeholder="10-digit group NPI"
                  maxLength={10}
                  className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm font-mono focus:outline-none focus:border-blue-400"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700">Address</label>
                  <input
                    type="text"
                    value={form.address}
                    onChange={(e) => setForm(f => ({ ...f, address: e.target.value }))}
                    className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:outline-none focus:border-blue-400"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700">City</label>
                  <input
                    type="text"
                    value={form.city}
                    onChange={(e) => setForm(f => ({ ...f, city: e.target.value }))}
                    className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:outline-none focus:border-blue-400"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700">State</label>
                  <input
                    type="text"
                    value={form.state}
                    onChange={(e) => setForm(f => ({ ...f, state: e.target.value }))}
                    maxLength={2}
                    placeholder="PA"
                    className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm uppercase focus:outline-none focus:border-blue-400"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700">ZIP Code</label>
                  <input
                    type="text"
                    value={form.zip_code}
                    onChange={(e) => setForm(f => ({ ...f, zip_code: e.target.value }))}
                    className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:outline-none focus:border-blue-400"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700">Phone</label>
                  <input
                    type="text"
                    value={form.phone}
                    onChange={(e) => setForm(f => ({ ...f, phone: e.target.value }))}
                    className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:outline-none focus:border-blue-400"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700">Taxonomy Code</label>
                  <input
                    type="text"
                    value={form.taxonomy_code}
                    onChange={(e) => setForm(f => ({ ...f, taxonomy_code: e.target.value }))}
                    placeholder="374J00000X"
                    className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm font-mono focus:outline-none focus:border-blue-400"
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700">
                  EIN (Tax ID) — Box 25
                  {editing?.tax_id_connected && (
                    <span className="ml-2 font-normal text-green-600">✓ currently on file</span>
                  )}
                </label>
                <input
                  type="password"
                  value={form.tax_id}
                  onChange={(e) => setForm(f => ({ ...f, tax_id: e.target.value }))}
                  placeholder={editing?.tax_id_connected ? 'Leave blank to keep existing' : 'XX-XXXXXXX'}
                  className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:outline-none focus:border-blue-400"
                />
                <p className="mt-0.5 text-xs text-gray-400">Stored encrypted. Never displayed after save.</p>
              </div>
            </div>

            {error && <p className="text-xs text-red-600">{error}</p>}

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setShowModal(false)}
                className="rounded border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSave}
                disabled={saving}
                className="rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {saving ? 'Saving…' : editing ? 'Save Changes' : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
