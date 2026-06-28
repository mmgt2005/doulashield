'use client'

import { useEffect, useState } from 'react'
import axios from 'axios'
import { getAccessToken } from '@/lib/auth'
import { Lead, LeadSource, LeadStatus, LeadProviderType } from '@/types/domain'

const SOURCE_LABELS: Record<string, string> = {
  webinar: 'Webinar',
  quiz: 'Quiz',
  manual: 'Manual',
  contact_form: 'Contact Form',
}

const STATUS_LABELS: Record<string, string> = {
  new: 'New',
  contacted: 'Contacted',
  qualified: 'Qualified',
  demo_scheduled: 'Demo Scheduled',
  converted: 'Converted',
  not_interested: 'Not Interested',
}

const SOURCE_COLORS: Record<string, string> = {
  webinar: 'bg-blue-100 text-blue-800',
  quiz: 'bg-purple-100 text-purple-800',
  manual: 'bg-gray-100 text-gray-700',
  contact_form: 'bg-teal-100 text-teal-800',
}

const STATUS_COLORS: Record<string, string> = {
  new: 'bg-yellow-100 text-yellow-800',
  contacted: 'bg-blue-100 text-blue-800',
  qualified: 'bg-green-100 text-green-800',
  demo_scheduled: 'bg-indigo-100 text-indigo-800',
  converted: 'bg-emerald-100 text-emerald-800',
  not_interested: 'bg-red-100 text-red-800',
}

interface Stats {
  total: number
  new_this_week: number
  converted: number
  conversion_rate: number
}

interface EditPanel {
  lead: Lead
  status: LeadStatus
  notes: string
  follow_up_at: string
  organization_name: string
  provider_type: LeadProviderType
  first_name: string
  last_name: string
  phone: string
}

const API = process.env.NEXT_PUBLIC_API_URL

function authHeaders() {
  return { Authorization: `Bearer ${getAccessToken()}` }
}

export default function AdminLeadsPage() {
  const [leads, setLeads] = useState<Lead[]>([])
  const [stats, setStats] = useState<Stats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Filters
  const [source, setSource] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [providerType, setProviderType] = useState('')
  const [search, setSearch] = useState('')

  // Edit panel
  const [panel, setPanel] = useState<EditPanel | null>(null)
  const [saving, setSaving] = useState(false)
  const [converting, setConverting] = useState<string | null>(null)

  // Add lead modal
  const [showAdd, setShowAdd] = useState(false)
  const [addForm, setAddForm] = useState({
    first_name: '', last_name: '', email: '', phone: '', organization_name: '',
    provider_type: 'unknown' as LeadProviderType, notes: '',
  })
  const [addSaving, setAddSaving] = useState(false)

  const fetchAll = async () => {
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams()
      if (source) params.set('source', source)
      if (statusFilter) params.set('status', statusFilter)
      if (providerType) params.set('provider_type', providerType)
      if (search) params.set('search', search)

      const [leadsRes, statsRes] = await Promise.all([
        axios.get<Lead[]>(`${API}/api/v1/admin/leads${params.toString() ? `?${params}` : ''}`, {
          headers: authHeaders(),
        }),
        axios.get<Stats>(`${API}/api/v1/admin/leads/stats`, { headers: authHeaders() }),
      ])
      setLeads(leadsRes.data)
      setStats(statsRes.data)
    } catch (e) {
      const msg = axios.isAxiosError(e) ? e.response?.data?.detail ?? e.message : String(e)
      setError(`Failed to load leads: ${msg}`)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchAll() }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const openEdit = (lead: Lead) => {
    setPanel({
      lead,
      status: lead.status as LeadStatus,
      notes: lead.notes ?? '',
      follow_up_at: lead.follow_up_at ? lead.follow_up_at.slice(0, 16) : '',
      organization_name: lead.organization_name ?? '',
      provider_type: lead.provider_type as LeadProviderType,
      first_name: lead.first_name,
      last_name: lead.last_name,
      phone: lead.phone ?? '',
    })
  }

  const saveEdit = async () => {
    if (!panel) return
    setSaving(true)
    try {
      await axios.patch(
        `${API}/api/v1/admin/leads/${panel.lead.id}`,
        {
          status: panel.status,
          notes: panel.notes || null,
          follow_up_at: panel.follow_up_at || null,
          organization_name: panel.organization_name || null,
          provider_type: panel.provider_type,
          first_name: panel.first_name,
          last_name: panel.last_name,
          phone: panel.phone || null,
        },
        { headers: authHeaders() },
      )
      setPanel(null)
      await fetchAll()
    } catch (e) {
      const msg = axios.isAxiosError(e) ? e.response?.data?.detail ?? e.message : String(e)
      alert(`Save failed: ${msg}`)
    } finally {
      setSaving(false)
    }
  }

  const convertLead = async (leadId: string) => {
    if (!confirm('Convert this lead to a DoulaShield provider account? A welcome email will be sent.')) return
    setConverting(leadId)
    try {
      const res = await axios.post<{ user_id: string; email: string; checkout_url: string | null }>(
        `${API}/api/v1/admin/leads/${leadId}/convert`,
        {},
        { headers: authHeaders() },
      )
      const { user_id, checkout_url } = res.data
      let msg = `Account created (user ID: ${user_id}). Welcome email sent.`
      if (checkout_url) msg += `\n\nDeposit link: ${checkout_url}`
      alert(msg)
      await fetchAll()
    } catch (e) {
      const msg = axios.isAxiosError(e) ? e.response?.data?.detail ?? e.message : String(e)
      alert(`Convert failed: ${msg}`)
    } finally {
      setConverting(null)
    }
  }

  const submitAdd = async () => {
    setAddSaving(true)
    try {
      await axios.post(
        `${API}/api/v1/admin/leads`,
        { ...addForm, source: 'manual' },
        { headers: authHeaders() },
      )
      setShowAdd(false)
      setAddForm({ first_name: '', last_name: '', email: '', phone: '', organization_name: '', provider_type: 'unknown', notes: '' })
      await fetchAll()
    } catch (e) {
      const msg = axios.isAxiosError(e) ? e.response?.data?.detail ?? e.message : String(e)
      alert(`Failed to add lead: ${msg}`)
    } finally {
      setAddSaving(false)
    }
  }

  const canConvert = (lead: Lead) =>
    (lead.status === 'qualified' || lead.status === 'demo_scheduled') && !lead.converted_user_id

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">Leads</h1>
        <button
          onClick={() => setShowAdd(true)}
          className="rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
        >
          + Add Lead
        </button>
      </div>

      {/* Stats bar */}
      {stats && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[
            { label: 'Total Leads', value: stats.total },
            { label: 'New This Week', value: stats.new_this_week },
            { label: 'Converted', value: stats.converted },
            { label: 'Conversion Rate', value: `${stats.conversion_rate}%` },
          ].map((s) => (
            <div key={s.label} className="rounded-lg border border-gray-200 bg-white p-4">
              <p className="text-xs text-gray-500">{s.label}</p>
              <p className="mt-1 text-2xl font-bold text-gray-900">{s.value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Filter bar */}
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <div className="flex flex-wrap gap-3">
          <select
            value={source}
            onChange={(e) => setSource(e.target.value)}
            className="rounded border border-gray-300 px-2 py-1.5 text-sm text-gray-700 focus:border-blue-400 focus:outline-none"
          >
            <option value="">All Sources</option>
            {Object.entries(SOURCE_LABELS).map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
            ))}
          </select>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded border border-gray-300 px-2 py-1.5 text-sm text-gray-700 focus:border-blue-400 focus:outline-none"
          >
            <option value="">All Statuses</option>
            {Object.entries(STATUS_LABELS).map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
            ))}
          </select>
          <select
            value={providerType}
            onChange={(e) => setProviderType(e.target.value)}
            className="rounded border border-gray-300 px-2 py-1.5 text-sm text-gray-700 focus:border-blue-400 focus:outline-none"
          >
            <option value="">All Types</option>
            <option value="independent">Independent</option>
            <option value="agency">Agency</option>
            <option value="unknown">Unknown</option>
          </select>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && fetchAll()}
            placeholder="Search name, email, org…"
            className="min-w-48 rounded border border-gray-300 px-2 py-1.5 text-sm text-gray-700 focus:border-blue-400 focus:outline-none"
          />
          <button
            onClick={fetchAll}
            className="rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
          >
            Apply
          </button>
          <button
            onClick={() => {
              setSource(''); setStatusFilter(''); setProviderType(''); setSearch('')
              setTimeout(fetchAll, 0)
            }}
            className="rounded border border-gray-300 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50"
          >
            Reset
          </button>
        </div>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      {/* Table */}
      <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50">
            <tr>
              {['Name', 'Email', 'Phone', 'Source', 'Type', 'Status', 'Created', 'Follow-up', 'Actions'].map((h) => (
                <th key={h} className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading ? (
              <tr><td colSpan={9} className="px-4 py-6 text-center text-gray-400">Loading…</td></tr>
            ) : leads.length === 0 ? (
              <tr><td colSpan={9} className="px-4 py-6 text-center text-gray-400">No leads found.</td></tr>
            ) : (
              leads.map((lead) => (
                <tr key={lead.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900 whitespace-nowrap">
                    {lead.first_name} {lead.last_name}
                    {lead.organization_name && (
                      <div className="text-xs text-gray-500">{lead.organization_name}</div>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-600">{lead.email}</td>
                  <td className="px-4 py-3 text-gray-600">{lead.phone ?? '—'}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${SOURCE_COLORS[lead.source] ?? 'bg-gray-100 text-gray-700'}`}>
                      {SOURCE_LABELS[lead.source] ?? lead.source}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-600 capitalize">{lead.provider_type}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[lead.status] ?? 'bg-gray-100 text-gray-700'}`}>
                      {STATUS_LABELS[lead.status] ?? lead.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-500 whitespace-nowrap">
                    {new Date(lead.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3 text-gray-500 whitespace-nowrap">
                    {lead.follow_up_at ? new Date(lead.follow_up_at).toLocaleDateString() : '—'}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => openEdit(lead)}
                        className="text-xs text-blue-600 hover:underline"
                      >
                        Edit
                      </button>
                      {canConvert(lead) && (
                        <button
                          onClick={() => convertLead(lead.id)}
                          disabled={converting === lead.id}
                          className="rounded bg-emerald-600 px-2 py-0.5 text-xs font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
                        >
                          {converting === lead.id ? '…' : 'Convert →'}
                        </button>
                      )}
                      {lead.converted_user_id && (
                        <span className="text-xs text-emerald-600 font-medium">Converted</span>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Edit slide-out panel */}
      {panel && (
        <div className="fixed inset-0 z-50 flex">
          <div className="flex-1 bg-black/30" onClick={() => setPanel(null)} />
          <div className="w-full max-w-md overflow-y-auto bg-white shadow-xl p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900">Edit Lead</h2>
              <button onClick={() => setPanel(null)} className="text-gray-400 hover:text-gray-600 text-xl leading-none">&times;</button>
            </div>

            <p className="text-sm text-gray-500">{panel.lead.email}</p>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">First Name</label>
                <input
                  type="text"
                  value={panel.first_name}
                  onChange={(e) => setPanel((p) => p && { ...p, first_name: e.target.value })}
                  className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-blue-400 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Last Name</label>
                <input
                  type="text"
                  value={panel.last_name}
                  onChange={(e) => setPanel((p) => p && { ...p, last_name: e.target.value })}
                  className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-blue-400 focus:outline-none"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Phone</label>
              <input
                type="text"
                value={panel.phone}
                onChange={(e) => setPanel((p) => p && { ...p, phone: e.target.value })}
                className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-blue-400 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Organization</label>
              <input
                type="text"
                value={panel.organization_name}
                onChange={(e) => setPanel((p) => p && { ...p, organization_name: e.target.value })}
                className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-blue-400 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Provider Type</label>
              <select
                value={panel.provider_type}
                onChange={(e) => setPanel((p) => p && { ...p, provider_type: e.target.value as LeadProviderType })}
                className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-blue-400 focus:outline-none"
              >
                <option value="unknown">Unknown</option>
                <option value="independent">Independent</option>
                <option value="agency">Agency</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Status</label>
              <select
                value={panel.status}
                onChange={(e) => setPanel((p) => p && { ...p, status: e.target.value as LeadStatus })}
                className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-blue-400 focus:outline-none"
              >
                {Object.entries(STATUS_LABELS).map(([k, v]) => (
                  <option key={k} value={k}>{v}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Follow-up Date</label>
              <input
                type="datetime-local"
                value={panel.follow_up_at}
                onChange={(e) => setPanel((p) => p && { ...p, follow_up_at: e.target.value })}
                className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-blue-400 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Notes</label>
              <textarea
                rows={4}
                value={panel.notes}
                onChange={(e) => setPanel((p) => p && { ...p, notes: e.target.value })}
                className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-blue-400 focus:outline-none"
              />
            </div>

            {panel.lead.lead_data && (
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Source Data</label>
                <pre className="rounded bg-gray-50 p-2 text-xs text-gray-600 overflow-auto max-h-32">
                  {JSON.stringify(panel.lead.lead_data, null, 2)}
                </pre>
              </div>
            )}

            <div className="flex gap-3 pt-2">
              <button
                onClick={saveEdit}
                disabled={saving}
                className="flex-1 rounded bg-blue-600 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {saving ? 'Saving…' : 'Save Changes'}
              </button>
              <button
                onClick={() => setPanel(null)}
                className="flex-1 rounded border border-gray-300 py-2 text-sm text-gray-600 hover:bg-gray-50"
              >
                Cancel
              </button>
            </div>

            {canConvert(panel.lead) && (
              <button
                onClick={() => { setPanel(null); convertLead(panel.lead.id) }}
                className="w-full rounded bg-emerald-600 py-2 text-sm font-medium text-white hover:bg-emerald-700"
              >
                Convert → Create Account
              </button>
            )}
          </div>
        </div>
      )}

      {/* Add lead modal */}
      {showAdd && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4">
          <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-xl space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900">Add Lead</h2>
              <button onClick={() => setShowAdd(false)} className="text-gray-400 hover:text-gray-600 text-xl leading-none">&times;</button>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">First Name *</label>
                <input
                  type="text"
                  value={addForm.first_name}
                  onChange={(e) => setAddForm((f) => ({ ...f, first_name: e.target.value }))}
                  className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-blue-400 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Last Name *</label>
                <input
                  type="text"
                  value={addForm.last_name}
                  onChange={(e) => setAddForm((f) => ({ ...f, last_name: e.target.value }))}
                  className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-blue-400 focus:outline-none"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Email *</label>
              <input
                type="email"
                value={addForm.email}
                onChange={(e) => setAddForm((f) => ({ ...f, email: e.target.value }))}
                className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-blue-400 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Phone</label>
              <input
                type="text"
                value={addForm.phone}
                onChange={(e) => setAddForm((f) => ({ ...f, phone: e.target.value }))}
                className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-blue-400 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Organization</label>
              <input
                type="text"
                value={addForm.organization_name}
                onChange={(e) => setAddForm((f) => ({ ...f, organization_name: e.target.value }))}
                className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-blue-400 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Provider Type</label>
              <select
                value={addForm.provider_type}
                onChange={(e) => setAddForm((f) => ({ ...f, provider_type: e.target.value as LeadProviderType }))}
                className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-blue-400 focus:outline-none"
              >
                <option value="unknown">Unknown</option>
                <option value="independent">Independent</option>
                <option value="agency">Agency</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Notes</label>
              <textarea
                rows={3}
                value={addForm.notes}
                onChange={(e) => setAddForm((f) => ({ ...f, notes: e.target.value }))}
                className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-blue-400 focus:outline-none"
              />
            </div>

            <div className="flex gap-3 pt-2">
              <button
                onClick={submitAdd}
                disabled={addSaving || !addForm.first_name || !addForm.last_name || !addForm.email}
                className="flex-1 rounded bg-blue-600 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {addSaving ? 'Adding…' : 'Add Lead'}
              </button>
              <button
                onClick={() => setShowAdd(false)}
                className="flex-1 rounded border border-gray-300 py-2 text-sm text-gray-600 hover:bg-gray-50"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
