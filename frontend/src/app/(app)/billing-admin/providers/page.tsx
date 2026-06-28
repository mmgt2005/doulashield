'use client'

import { useEffect, useState } from 'react'
import axios from 'axios'
import { getAccessToken } from '@/lib/auth'

interface Provider {
  id: string
  full_name: string | null
  email: string
  npi: string | null
}

interface InviteRow {
  name: string
  email: string
  doula_type: string
}

interface InviteResult {
  created: { name: string; email: string }[]
  skipped: { name: string; email: string; reason: string }[]
}

const DOULA_TYPES = ['Birth Doula', 'Postpartum Doula', 'Perinatal Doula', 'Other']
const EMPTY_ROW: InviteRow = { name: '', email: '', doula_type: 'Birth Doula' }

export default function BillingAdminProvidersPage() {
  const api = process.env.NEXT_PUBLIC_API_URL
  const headers = { Authorization: `Bearer ${getAccessToken()}` }

  const [providers, setProviders] = useState<Provider[]>([])
  const [loading, setLoading] = useState(true)
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

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-gray-900">My Providers</h1>
        <p className="mt-0.5 text-sm text-gray-500">
          View your agency&apos;s provider roster and invite new doulas to DoulaShield.
        </p>
      </div>

      {/* Current roster */}
      <div>
        <h2 className="mb-3 text-sm font-semibold text-gray-700 uppercase tracking-wide">
          Current Roster — {providers.length} provider{providers.length !== 1 ? 's' : ''}
        </h2>
        {loading ? (
          <p className="text-sm text-gray-400">Loading…</p>
        ) : providers.length === 0 ? (
          <div className="rounded-lg border border-dashed border-gray-300 py-8 text-center text-sm text-gray-500">
            No providers yet. Use the form below to invite your first doula.
          </div>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 bg-gray-50 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
                  <th className="px-4 py-3">Name</th>
                  <th className="px-4 py-3">Email</th>
                  <th className="px-4 py-3">NPI</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {providers.map(p => (
                  <tr key={p.id} className="hover:bg-gray-50">
                    <td className="px-4 py-2.5 font-medium text-gray-900">{p.full_name ?? '—'}</td>
                    <td className="px-4 py-2.5 text-gray-600">{p.email}</td>
                    <td className="px-4 py-2.5 font-mono text-xs text-gray-500">{p.npi ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Invite form */}
      <div className="rounded-lg border border-gray-200 bg-white p-5">
        <h2 className="mb-1 text-sm font-semibold text-gray-900">Invite New Providers</h2>
        <p className="mb-4 text-xs text-gray-500">
          Each provider will receive a welcome email with a temporary password and a link to pay their deposit.
          Providers already registered in DoulaShield are skipped automatically.
        </p>

        {result ? (
          <div className="space-y-3">
            {result.created.length > 0 && (
              <div className="rounded-md border border-green-200 bg-green-50 p-3">
                <p className="mb-1 text-xs font-semibold text-green-800">
                  {result.created.length} invite(s) sent successfully
                </p>
                {result.created.map((c, i) => (
                  <p key={i} className="text-xs text-green-700">{c.name} — {c.email}</p>
                ))}
              </div>
            )}
            {result.skipped.length > 0 && (
              <div className="rounded-md border border-amber-200 bg-amber-50 p-3">
                <p className="mb-1 text-xs font-semibold text-amber-800">
                  {result.skipped.length} skipped
                </p>
                {result.skipped.map((s, i) => (
                  <p key={i} className="text-xs text-amber-700">{s.name || s.email} — {s.reason}</p>
                ))}
              </div>
            )}
            <button
              onClick={() => setResult(null)}
              className="text-xs text-blue-600 hover:underline"
            >
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
                    title="Remove row"
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>

            <div className="mt-3 flex items-center justify-between">
              <button onClick={addRow} className="text-xs text-blue-600 hover:underline">
                + Add another provider
              </button>
              <button
                onClick={handleSubmit}
                disabled={submitting || validRows.length === 0}
                className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
              >
                {submitting ? 'Sending invites…' : `Send ${validRows.length} Invite${validRows.length !== 1 ? 's' : ''}`}
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
