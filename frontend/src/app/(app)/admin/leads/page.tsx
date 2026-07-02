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
  cal_com: 'Setup Call',
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
  cal_com: 'bg-sky-100 text-sky-800',
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
  const [deleting, setDeleting] = useState(false)

  // Gmail
  const [gmailConnected, setGmailConnected] = useState(false)
  const [leadEmails, setLeadEmails] = useState<Array<{ id: string; subject: string; from: string; date: string; snippet: string; unread: boolean }>>([])
  const [emailsLoading, setEmailsLoading] = useState(false)
  const [expandedEmail, setExpandedEmail] = useState<string | null>(null)
  const [emailDetail, setEmailDetail] = useState<Record<string, { body: string; to: string; attachments?: Array<{ id: string | null; filename: string; mimeType: string; size: number }> }>>({})

  // Add lead modal
  const [showAdd, setShowAdd] = useState(false)
  const [addForm, setAddForm] = useState({
    first_name: '', last_name: '', email: '', phone: '', organization_name: '',
    provider_type: 'unknown' as LeadProviderType, notes: '',
  })
  const [addSaving, setAddSaving] = useState(false)
  const [showGuide, setShowGuide] = useState(false)

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

  useEffect(() => {
    fetchAll()
    axios.get(`${API}/api/v1/admin/gmail/status`, { headers: authHeaders() })
      .then(r => setGmailConnected(r.data.connected))
      .catch(() => {})
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

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
    setLeadEmails([])
    setExpandedEmail(null)
    setEmailDetail({})
    if (gmailConnected) {
      setEmailsLoading(true)
      axios.get(`${API}/api/v1/admin/gmail/messages`, {
        headers: authHeaders(),
        params: { email: lead.email },
      })
        .then(r => setLeadEmails(r.data))
        .catch(() => {})
        .finally(() => setEmailsLoading(false))
    }
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

  const deleteLead = async () => {
    if (!panel) return
    if (!confirm(`Delete "${panel.first_name} ${panel.last_name}"? This cannot be undone.`)) return
    setDeleting(true)
    try {
      await axios.delete(`${API}/api/v1/admin/leads/${panel.lead.id}`, { headers: authHeaders() })
      setPanel(null)
      await fetchAll()
    } catch (e) {
      const msg = axios.isAxiosError(e) ? e.response?.data?.detail ?? e.message : String(e)
      alert(`Delete failed: ${msg}`)
    } finally {
      setDeleting(false)
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
        <div className="flex gap-2">
          <button
            onClick={() => setShowGuide(true)}
            className="rounded border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50"
          >
            How It Works
          </button>
          <button
            onClick={() => setShowAdd(true)}
            className="rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
          >
            + Add Lead
          </button>
        </div>
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

            {gmailConnected && (
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">
                  Emails
                  {!emailsLoading && leadEmails.length > 0 && (
                    <span className="ml-1 text-gray-400">({leadEmails.length})</span>
                  )}
                </label>
                {emailsLoading ? (
                  <p className="text-xs text-gray-400">Loading emails…</p>
                ) : leadEmails.length === 0 ? (
                  <p className="text-xs text-gray-400">No emails found with {panel.lead.email}</p>
                ) : (
                  <div className="divide-y divide-gray-100 rounded border border-gray-200 bg-white max-h-64 overflow-y-auto">
                    {leadEmails.map(em => (
                      <div key={em.id}>
                        <button
                          onClick={async () => {
                            if (expandedEmail === em.id) { setExpandedEmail(null); return }
                            setExpandedEmail(em.id)
                            if (!emailDetail[em.id]) {
                              try {
                                const r = await axios.get(`${API}/api/v1/admin/gmail/messages/${em.id}`, { headers: authHeaders() })
                                setEmailDetail(prev => ({ ...prev, [em.id]: { body: r.data.body, to: r.data.to, attachments: r.data.attachments } }))
                              } catch { /* ignore */ }
                            }
                          }}
                          className="w-full text-left px-3 py-2 hover:bg-gray-50 transition-colors"
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div className="min-w-0 flex-1">
                              <p className={`text-xs truncate ${em.unread ? 'font-semibold text-gray-900' : 'font-medium text-gray-700'}`}>
                                {em.subject || '(no subject)'}
                              </p>
                              <p className="text-xs text-gray-400 truncate mt-0.5">{em.snippet}</p>
                            </div>
                            <p className="shrink-0 text-xs text-gray-400">{em.date.slice(0, 11)}</p>
                          </div>
                        </button>
                        {expandedEmail === em.id && (
                          <div className="border-t border-gray-100 bg-gray-50 px-3 py-2 text-xs space-y-1">
                            <p className="text-gray-500"><span className="font-medium">From:</span> {em.from}</p>
                            {emailDetail[em.id]?.to && (
                              <p className="text-gray-500"><span className="font-medium">To:</span> {emailDetail[em.id].to}</p>
                            )}
                            <div className="mt-1.5 rounded border border-gray-200 bg-white p-2 whitespace-pre-wrap text-gray-700 max-h-40 overflow-y-auto">
                              {emailDetail[em.id]?.body || em.snippet}
                            </div>
                            {(emailDetail[em.id]?.attachments?.length ?? 0) > 0 && (
                              <div className="mt-1 flex flex-wrap gap-1">
                                {emailDetail[em.id].attachments!.map((att, i) => (
                                  att.id ? (
                                    <a
                                      key={i}
                                      href={`${API}/api/v1/admin/gmail/messages/${em.id}/attachments/${att.id}?filename=${encodeURIComponent(att.filename)}&mime_type=${encodeURIComponent(att.mimeType)}`}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="inline-flex items-center gap-0.5 rounded border border-gray-200 bg-white px-1.5 py-0.5 text-xs text-gray-700 hover:bg-gray-50"
                                      download={att.filename}
                                    >
                                      {att.filename}
                                    </a>
                                  ) : (
                                    <span key={i} className="rounded border border-gray-200 px-1.5 py-0.5 text-xs text-gray-500">{att.filename}</span>
                                  )
                                ))}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {process.env.NEXT_PUBLIC_SETUP_CALL_URL && (
              <a
                href={`${process.env.NEXT_PUBLIC_SETUP_CALL_URL}?email=${encodeURIComponent(panel.lead.email)}&name=${encodeURIComponent(`${panel.first_name} ${panel.last_name}`.trim())}`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 rounded bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700"
              >
                Book Setup Call →
              </a>
            )}

            {panel.lead.lead_data?.cal_booking ? (() => {
              const b = panel.lead.lead_data.cal_booking as Record<string, unknown>
              const startTime = b.startTime as string | undefined
              const meetingUrl = (b.videoCallData as Record<string, unknown> | undefined)?.url as string | undefined
              const bookingStatus = b.status as string | undefined
              return (
                <div className="rounded border border-sky-200 bg-sky-50 p-3 space-y-1">
                  <p className="text-xs font-semibold text-sky-800">Cal.com Booking</p>
                  {startTime && (
                    <p className="text-xs text-gray-600">
                      📅 {new Date(startTime).toLocaleString()}
                    </p>
                  )}
                  {bookingStatus && (
                    <p className="text-xs text-gray-600">
                      Status: <span className="font-medium">{bookingStatus}</span>
                    </p>
                  )}
                  {meetingUrl && (
                    <a
                      href={meetingUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-blue-600 hover:underline block"
                    >
                      Join Meeting →
                    </a>
                  )}
                </div>
              )
            })() : null}

            {panel.lead.lead_data?.cal_recording ? (() => {
              const r = panel.lead.lead_data.cal_recording as Record<string, unknown>
              const recordingUrl = (r.recordingUrl ?? r.downloadLink ?? r.url) as string | undefined
              return (
                <div className="rounded border border-violet-200 bg-violet-50 p-3 space-y-1">
                  <p className="text-xs font-semibold text-violet-800">Recording</p>
                  {recordingUrl ? (
                    <a
                      href={recordingUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-blue-600 hover:underline block"
                    >
                      Watch Recording →
                    </a>
                  ) : (
                    <p className="text-xs text-gray-500">Recording URL not yet available</p>
                  )}
                </div>
              )
            })() : null}

            {panel.lead.lead_data?.cal_transcript ? (() => {
              const t = panel.lead.lead_data.cal_transcript as Record<string, unknown>
              const td = t.transcriptData as Record<string, unknown> | undefined
              const text = (td?.text ?? t.text) as string | undefined
              const segments = (td?.segments ?? t.segments) as Array<Record<string, unknown>> | undefined
              return (
                <div className="rounded border border-amber-200 bg-amber-50 p-3 space-y-2">
                  <p className="text-xs font-semibold text-amber-800">Transcript</p>
                  {segments && segments.length > 0 ? (
                    <div className="space-y-1.5 max-h-48 overflow-y-auto">
                      {segments.map((seg, i) => (
                        <div key={i} className="text-xs">
                          <span className="font-medium text-amber-900">{String(seg.speaker ?? 'Speaker')}: </span>
                          <span className="text-gray-700">{String(seg.text ?? '')}</span>
                        </div>
                      ))}
                    </div>
                  ) : text ? (
                    <p className="text-xs text-gray-700 max-h-48 overflow-y-auto whitespace-pre-wrap">{text}</p>
                  ) : (
                    <p className="text-xs text-gray-500">Transcript data not yet available</p>
                  )}
                </div>
              )
            })() : null}

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

            {panel.lead.source === 'manual' && (
              <button
                onClick={deleteLead}
                disabled={deleting}
                className="w-full rounded border border-red-200 py-2 text-sm font-medium text-red-600 hover:bg-red-50 disabled:opacity-50"
              >
                {deleting ? 'Deleting…' : 'Delete Lead'}
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

      {/* How It Works guide */}
      {showGuide && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
          onClick={() => setShowGuide(false)}
        >
          <div
            className="bg-white rounded-xl shadow-2xl w-full max-w-4xl max-h-[92vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-start justify-between rounded-t-xl z-10">
              <div>
                <h2 className="text-base font-semibold text-gray-900">Leads — How It Works</h2>
                <p className="text-xs text-gray-500 mt-0.5">Track prospective providers from first contact through conversion to a DoulaShield account.</p>
              </div>
              <button onClick={() => setShowGuide(false)} className="text-gray-400 hover:text-gray-600 text-xl leading-none ml-6 mt-0.5">×</button>
            </div>
            <div className="px-6 py-5 space-y-6">
              <div className="rounded-lg border border-blue-100 bg-blue-50 p-4">
                <h3 className="text-sm font-semibold text-blue-800 mb-2">What Are Leads?</h3>
                <ul className="space-y-1 text-xs text-blue-700 list-disc list-inside">
                  <li>Prospective doula providers who have expressed interest in joining DoulaShield</li>
                  <li>Captured automatically from webinar registrations, quiz submissions, and contact forms — or entered manually by admin staff</li>
                  <li>Source-specific data (quiz answers, webinar topic) is stored on the lead and visible in the edit panel</li>
                </ul>
              </div>
              <div className="rounded-lg border border-gray-100 bg-gray-50 p-4">
                <h3 className="text-sm font-semibold text-gray-800 mb-2">Lead Sources</h3>
                <div className="grid grid-cols-2 gap-2 text-xs text-gray-700">
                  <div><span className="inline-block rounded-full bg-blue-100 px-2 py-0.5 text-blue-700 font-medium mr-1">Webinar</span> Demo or informational webinar registration</div>
                  <div><span className="inline-block rounded-full bg-green-100 px-2 py-0.5 text-green-700 font-medium mr-1">Quiz</span> "Are you ready for Medicaid billing?" lead magnet</div>
                  <div><span className="inline-block rounded-full bg-gray-200 px-2 py-0.5 text-gray-700 font-medium mr-1">Contact Form</span> General interest form from the marketing site</div>
                  <div><span className="inline-block rounded-full bg-purple-100 px-2 py-0.5 text-purple-700 font-medium mr-1">Manual</span> In-person or direct outreach entered by admin</div>
                </div>
              </div>
              <div className="rounded-lg border border-amber-100 bg-amber-50 p-4">
                <h3 className="text-sm font-semibold text-amber-800 mb-2">Status Pipeline</h3>
                <div className="flex flex-wrap items-center gap-1 text-xs text-amber-700 mb-2">
                  {['New', 'Contacted', 'Qualified', 'Demo Scheduled', 'Converted', 'Not Interested'].map((s, i, arr) => (
                    <span key={s} className="flex items-center gap-1">
                      <span className="rounded bg-amber-100 border border-amber-300 px-2 py-0.5 font-medium">{s}</span>
                      {i < arr.length - 1 && <span>→</span>}
                    </span>
                  ))}
                </div>
                <p className="text-xs text-amber-700">Update status via the edit slide-out panel. Only <strong>Qualified</strong> and <strong>Demo Scheduled</strong> leads show the Convert button.</p>
              </div>
              <div className="rounded-lg border border-green-100 bg-green-50 p-4">
                <h3 className="text-sm font-semibold text-green-800 mb-2">Follow-Up & Notes</h3>
                <ul className="space-y-1 text-xs text-green-700 list-disc list-inside">
                  <li>Set a follow-up date in the edit panel — it shows in the table so nothing slips</li>
                  <li>Add notes to track calls, emails, and next steps; notes are internal only</li>
                  <li>Provider type (Independent / Agency / Unknown) helps prioritize outreach</li>
                </ul>
              </div>
              <div className="rounded-lg border border-purple-100 bg-purple-50 p-4">
                <h3 className="text-sm font-semibold text-purple-800 mb-2">Converting a Lead</h3>
                <ol className="space-y-1 text-xs text-purple-700 list-decimal list-inside">
                  <li>Move the lead to <strong>Qualified</strong> or <strong>Demo Scheduled</strong> status</li>
                  <li>Click <strong>Convert → Create Account</strong> in the edit panel</li>
                  <li>System creates a DoulaShield provider account and sends a welcome + deposit email</li>
                  <li>Lead is marked <strong>Converted</strong> with a link to the new user record</li>
                  <li>Cannot be undone — but the provider account can be deactivated separately if needed</li>
                </ol>
              </div>
              <div className="rounded-lg bg-gray-50 border border-gray-200 p-4">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-3">Key Rules & Reminders</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs text-gray-700">
                  <div><strong>Conversion is irreversible:</strong> Once a lead is converted, the provider account exists and must be managed from the Users page.</div>
                  <div><strong>Duplicate emails:</strong> The system prevents converting a lead whose email already exists as a DoulaShield user.</div>
                  <div><strong>Search:</strong> The search bar matches against name, email, and organization name simultaneously.</div>
                  <div><strong>Conversion rate:</strong> Calculated as converted leads ÷ total leads; updates in real time as statuses change.</div>
                </div>
              </div>
            </div>
            <div className="sticky bottom-0 bg-white border-t border-gray-200 px-6 py-3 flex justify-end rounded-b-xl">
              <button onClick={() => setShowGuide(false)} className="rounded border border-gray-300 px-4 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50">Close</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
