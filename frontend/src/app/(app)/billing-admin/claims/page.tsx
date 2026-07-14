'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import axios from 'axios'
import { getAccessToken } from '@/lib/auth'
import type { Claim } from '@/types/domain'
import CMS1500PreviewModal from '@/components/ui/CMS1500PreviewModal'
import FilePreviewModal from '@/components/ui/FilePreviewModal'

interface Provider {
  id: string
  email: string
  full_name: string | null
  npi: string | null
}

interface ClaimDocument {
  id: string
  claim_id: string
  uploaded_by: string | null
  file_name: string
  document_type: string | null
  created_at: string
}

interface VisitNotes {
  subjective: string | null
  objective: string | null
  assessment: string | null
  plan: string | null
  entry: string | null
  birth_notes: string | null
  ma91_status: string | null
  ma91_signed_at: string | null
  visit_date: string | null
  location_type: string | null
}

interface ClaimReviewDetail {
  claim: Claim
  claim_data: Record<string, unknown> | null
  visit: VisitNotes | null
  source_image_url: string | null
  documents: ClaimDocument[]
}

function claimStatusDisplay(status: string | null): { label: string; color: 'amber' | 'blue' | 'green' | 'red' | 'orange' } {
  const s = (status ?? '').toLowerCase()
  if (s === 'paid') return { label: 'Paid', color: 'green' }
  if (s === 'denied' || s === 'rejected') return { label: 'Denied', color: 'red' }
  if (s === 'processing' || s === 'accepted' || s === 'pended' || s === 'received') return { label: 'Processing', color: 'blue' }
  if (s === 'pending_billing_review') return { label: 'Pending Review', color: 'orange' }
  return { label: 'Submitted', color: 'amber' }
}

const STATUS_COLORS = {
  amber: 'border-amber-300 bg-amber-50 text-amber-700',
  blue: 'border-blue-300 bg-blue-50 text-blue-700',
  green: 'border-green-300 bg-green-50 text-green-800',
  red: 'border-red-300 bg-red-50 text-red-700',
  orange: 'border-orange-300 bg-orange-50 text-orange-700',
}

const DOC_TYPE_LABELS: Record<string, string> = {
  prior_auth: 'Prior Auth',
  eligibility: 'Eligibility',
  eob_received: 'EOB Received',
  other: 'Other',
}

function extractClaimData(claimData: Record<string, unknown> | null) {
  if (!claimData) return { procCode: null, modifier: null, diagCode: null, payerId: null }
  try {
    const lines = (claimData as any)?.claimInformation?.serviceLines
    const line0 = Array.isArray(lines) ? lines[0] : null
    const procCode = line0?.procedureCode?.procedureCode ?? null
    const modifiers: string[] = line0?.procedureCode?.procedureModifiers ?? []
    const modifier = modifiers.length > 0 ? modifiers.join(', ') : null
    const diagCodes = (claimData as any)?.claimInformation?.healthCareCodeInformation
    const diagCode = Array.isArray(diagCodes) && diagCodes[0]?.diagnosisCode ? diagCodes[0].diagnosisCode : null
    return { procCode, modifier, diagCode }
  } catch {
    return { procCode: null, modifier: null, diagCode: null }
  }
}

type Preset = 'this_month' | 'last_month' | '3m' | '6m' | '180d' | 'ytd' | 'last_year' | 'all' | 'custom'

const PRESETS: { key: Preset; label: string }[] = [
  { key: 'this_month', label: 'This Month' },
  { key: 'last_month', label: 'Last Month' },
  { key: '3m',         label: 'Last 3 Months' },
  { key: '6m',         label: 'Last 6 Months' },
  { key: '180d',       label: 'Last 180 Days' },
  { key: 'ytd',        label: 'Year to Date' },
  { key: 'last_year',  label: 'Last Year' },
  { key: 'all',        label: 'All Time' },
  { key: 'custom',     label: 'Custom' },
]

function fmtDate(d: Date): string {
  return d.toISOString().split('T')[0]
}

function subDays(d: Date, n: number): Date {
  const r = new Date(d)
  r.setDate(r.getDate() - n)
  return r
}

function subMonths(d: Date, n: number): Date {
  const r = new Date(d)
  r.setMonth(r.getMonth() - n)
  return r
}

function presetDates(p: Preset): { from: string | null; to: string | null } {
  const today = new Date()
  switch (p) {
    case 'this_month':
      return { from: fmtDate(new Date(today.getFullYear(), today.getMonth(), 1)), to: fmtDate(today) }
    case 'last_month': {
      const f = new Date(today.getFullYear(), today.getMonth() - 1, 1)
      const t = new Date(today.getFullYear(), today.getMonth(), 0)
      return { from: fmtDate(f), to: fmtDate(t) }
    }
    case '3m':
      return { from: fmtDate(subMonths(today, 3)), to: fmtDate(today) }
    case '6m':
      return { from: fmtDate(subMonths(today, 6)), to: fmtDate(today) }
    case '180d':
      return { from: fmtDate(subDays(today, 179)), to: fmtDate(today) }
    case 'ytd':
      return { from: fmtDate(new Date(today.getFullYear(), 0, 1)), to: fmtDate(today) }
    case 'last_year': {
      const y = today.getFullYear() - 1
      return { from: `${y}-01-01`, to: `${y}-12-31` }
    }
    default:
      return { from: null, to: null }
  }
}

export default function BillingAdminClaimsPage() {
  const searchParams = useSearchParams()
  const bpId = searchParams.get('bp_id')

  const [claims, setClaims] = useState<Claim[]>([])
  const [providers, setProviders] = useState<Provider[]>([])
  const [agencyName, setAgencyName] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [filterProvider, setFilterProvider] = useState('')
  const [filterStatus, setFilterStatus] = useState('')
  const [submitting, setSubmitting] = useState<string | null>(null)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [expandedClaimId, setExpandedClaimId] = useState<string | null>(null)
  const [previewClaim, setPreviewClaim] = useState<{ id: string; visitType: string } | null>(null)
  const [filePreview, setFilePreview] = useState<{
    title: string
    fetchUrl?: string
    directUrl?: string
    contentType?: 'pdf' | 'image' | 'auto'
    fileName?: string
  } | null>(null)
  const [manualFormClaimId, setManualFormClaimId] = useState<string | null>(null)
  const [manualFormStatus, setManualFormStatus] = useState<'submitted' | 'paid' | 'denied'>('submitted')
  const [manualFormPaid, setManualFormPaid] = useState('')
  const [manualFormDenial, setManualFormDenial] = useState('')
  const [manualFormNotes, setManualFormNotes] = useState('')
  const [manualSaving, setManualSaving] = useState(false)
  const [showGuide, setShowGuide] = useState(false)
  const [reviewData, setReviewData] = useState<Record<string, ClaimReviewDetail | null>>({})
  const [reviewLoading, setReviewLoading] = useState<Record<string, boolean>>({})
  const [docUploading, setDocUploading] = useState<Record<string, boolean>>({})

  const [preset, setPreset] = useState<Preset>('all')
  const [customFrom, setCustomFrom] = useState('')
  const [customTo, setCustomTo] = useState('')

  const fileInputRef = useRef<HTMLInputElement>(null)
  const uploadingClaimIdRef = useRef<string | null>(null)

  const api = process.env.NEXT_PUBLIC_API_URL
  const headers = { Authorization: `Bearer ${getAccessToken()}` }

  const bpParam = bpId ? `?bp_id=${bpId}` : ''

  const fetchReview = async (claimId: string) => {
    if (reviewData[claimId] !== undefined || reviewLoading[claimId]) return
    setReviewLoading(prev => ({ ...prev, [claimId]: true }))
    try {
      const res = await axios.get<ClaimReviewDetail>(
        `${api}/api/v1/billing-admin/claims/${claimId}/review`,
        { headers }
      )
      setReviewData(prev => ({ ...prev, [claimId]: res.data }))
    } catch {
      setReviewData(prev => ({ ...prev, [claimId]: null }))
    } finally {
      setReviewLoading(prev => ({ ...prev, [claimId]: false }))
    }
  }

  const toggleExpand = (claim: Claim) => {
    const next = expandedClaimId === claim.id ? null : claim.id
    setExpandedClaimId(next)
    if (next) fetchReview(next)
  }

  const handleSubmitClaim = async (claimId: string) => {
    setSubmitting(claimId)
    setSubmitError(null)
    try {
      const res = await axios.post<Claim>(
        `${api}/api/v1/billing-admin/claims/${claimId}/submit`,
        {},
        { headers }
      )
      setClaims(prev => prev.map(c => c.id === claimId ? res.data : c))
    } catch {
      setSubmitError('Failed to submit claim — check agency Availity credentials in Agency Settings.')
    } finally {
      setSubmitting(null)
    }
  }

  const handleManualStatus = async (claimId: string) => {
    setManualSaving(true)
    try {
      const claim = claims.find(c => c.id === claimId)
      const res = await axios.put<Claim>(
        `${api}/api/v1/billing-admin/claims/${claimId}/status`,
        {
          status: manualFormStatus,
          service_date: claim?.service_date ?? new Date().toISOString().split('T')[0],
          paid_amount: manualFormStatus === 'paid' && manualFormPaid ? Number(manualFormPaid) : undefined,
          denial_reason: manualFormStatus === 'denied' && manualFormDenial ? manualFormDenial : undefined,
        },
        { headers }
      )
      setClaims(prev => prev.map(c => c.id === claimId ? res.data : c))
      setManualFormClaimId(null)
    } catch {
      setSubmitError('Failed to update claim status.')
    } finally {
      setManualSaving(false)
    }
  }

  const handlePreviewDoc = async (claimId: string, doc: ClaimDocument) => {
    try {
      const res = await axios.get<{ url: string }>(
        `${api}/api/v1/billing-admin/claims/${claimId}/documents/${doc.id}/file`,
        { headers }
      )
      const isImage = /\.(jpg|jpeg|png|gif|webp)(\?|$)/i.test(res.data.url) ||
        doc.file_name.match(/\.(jpg|jpeg|png|gif|webp)$/i)
      setFilePreview({
        title: doc.file_name,
        directUrl: res.data.url,
        contentType: isImage ? 'image' : 'pdf',
        fileName: doc.file_name,
      })
    } catch {
      setSubmitError('Failed to load document.')
    }
  }

  const handleDocUpload = async (claimId: string, file: File, documentType: string) => {
    setDocUploading(prev => ({ ...prev, [claimId]: true }))
    try {
      const form = new FormData()
      form.append('file', file)
      form.append('document_type', documentType)
      await axios.post(
        `${api}/api/v1/billing-admin/claims/${claimId}/documents`,
        form,
        { headers: { ...headers, 'Content-Type': 'multipart/form-data' } }
      )
      // Refresh review data
      setReviewData(prev => {
        const copy = { ...prev }
        delete copy[claimId]
        return copy
      })
      await fetchReview(claimId)
    } catch {
      setSubmitError('Failed to upload document.')
    } finally {
      setDocUploading(prev => ({ ...prev, [claimId]: false }))
    }
  }

  const loadClaims = useCallback(async (from: string | null, to: string | null) => {
    setLoading(true)
    const h = { Authorization: `Bearer ${getAccessToken()}` }
    const params: Record<string, string> = {}
    if (from) params.date_from = from
    if (to) params.date_to = to
    try {
      const res = await axios.get<Claim[]>(
        `${api}/api/v1/billing-admin/claims${bpParam}`,
        { headers: h, params },
      )
      setClaims(res.data)
    } catch {
      setClaims([])
    } finally {
      setLoading(false)
    }
  }, [api, bpParam])

  // One-time fetch for providers and agency name (not date-scoped)
  useEffect(() => {
    const h = { Authorization: `Bearer ${getAccessToken()}` }
    const requests = [
      axios.get<Provider[]>(`${api}/api/v1/billing-admin/providers${bpParam}`, { headers: h }),
      ...(bpId ? [axios.get(`${api}/api/v1/billing-admin/agency-settings${bpParam}`, { headers: h })] : []),
    ]
    Promise.allSettled(requests).then(results => {
      if (results[0].status === 'fulfilled') setProviders((results[0] as PromiseFulfilledResult<{ data: Provider[] }>).value.data)
      if (bpId && results[1]?.status === 'fulfilled') {
        const settingsResult = results[1] as PromiseFulfilledResult<{ data: { name: string } }>
        setAgencyName(settingsResult.value.data.name)
      }
    })
  }, [bpId]) // eslint-disable-line react-hooks/exhaustive-deps

  // Reload claims whenever the date filter changes
  useEffect(() => {
    if (preset === 'custom') {
      if (customFrom && customTo) loadClaims(customFrom, customTo)
      return
    }
    const { from, to } = presetDates(preset)
    loadClaims(from, to)
  }, [preset, customFrom, customTo, loadClaims])

  const providerMap = new Map(providers.map(p => [p.id, p]))

  const filtered = claims.filter(c => {
    if (filterProvider && c.provider_id !== filterProvider) return false
    if (filterStatus) {
      if (filterStatus === 'pending_billing_review') {
        if ((c.status ?? '').toLowerCase() !== 'pending_billing_review') return false
      } else {
        const norm = claimStatusDisplay(c.status).label.toLowerCase()
        if (!norm.includes(filterStatus.toLowerCase())) return false
      }
    }
    return true
  })

  const today = new Date().toISOString().split('T')[0]
  const pendingReviewCount = claims.filter(c => (c.status ?? '').toLowerCase() === 'pending_billing_review').length

  const totalBilled = filtered.reduce((a, c) => a + Number(c.billed_amount ?? 0), 0)
  const totalPaid = filtered.reduce((a, c) => a + Number(c.paid_amount ?? 0), 0)
  const paidCount = filtered.filter(c => claimStatusDisplay(c.status).color === 'green').length
  const deniedCount = filtered.filter(c => claimStatusDisplay(c.status).color === 'red').length

  return (
    <div className="space-y-6">
      {previewClaim && (
        <CMS1500PreviewModal
          claimId={previewClaim.id}
          visitType={previewClaim.visitType}
          onClose={() => setPreviewClaim(null)}
        />
      )}
      {filePreview && (
        <FilePreviewModal
          title={filePreview.title}
          fetchUrl={filePreview.fetchUrl}
          directUrl={filePreview.directUrl}
          contentType={filePreview.contentType}
          fileName={filePreview.fileName}
          onClose={() => setFilePreview(null)}
        />
      )}

      {/* Hidden file input for document uploads */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.jpg,.jpeg,.png"
        className="hidden"
        onChange={async e => {
          const file = e.target.files?.[0]
          const claimId = uploadingClaimIdRef.current
          if (!file || !claimId) return
          e.target.value = ''
          const type = (e.target as HTMLInputElement & { dataset: { docType?: string } }).dataset.docType ?? 'other'
          await handleDocUpload(claimId, file, type)
        }}
      />

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Agency Claims</h1>
          {bpId && agencyName && (
            <p className="mt-0.5 text-xs text-blue-600 font-medium">
              Viewing as admin: {agencyName}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowGuide(true)}
            className="rounded border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50"
          >
            How It Works
          </button>
          {pendingReviewCount > 0 && (
            <span className="rounded-full bg-orange-100 px-3 py-1 text-xs font-semibold text-orange-700">
              {pendingReviewCount} pending review
            </span>
          )}
        </div>
      </div>

      {submitError && (
        <div className="rounded border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
          {submitError}
        </div>
      )}

      {/* Summary cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <p className="text-xs text-gray-500">Total Claims</p>
          <p className="mt-1 text-2xl font-bold text-gray-900">{filtered.length}</p>
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <p className="text-xs text-gray-500">Total Billed</p>
          <p className="mt-1 text-2xl font-bold text-gray-900">
            ${totalBilled.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </p>
        </div>
        <div className="rounded-lg border border-green-100 bg-green-50 p-4">
          <p className="text-xs text-green-600">Total Paid</p>
          <p className="mt-1 text-2xl font-bold text-green-700">
            ${totalPaid.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </p>
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <p className="text-xs text-gray-500">Paid / Denied</p>
          <p className="mt-1 text-2xl font-bold text-gray-900">{paidCount} / {deniedCount}</p>
        </div>
      </div>

      {/* Date range filter */}
      <div className="space-y-2">
        <div className="flex flex-wrap gap-1.5">
          {PRESETS.map(p => (
            <button
              key={p.key}
              type="button"
              onClick={() => setPreset(p.key)}
              className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
                preset === p.key
                  ? 'border-blue-600 bg-blue-600 text-white'
                  : 'border-gray-200 text-gray-600 hover:bg-gray-50'
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
        {preset === 'custom' && (
          <div className="flex items-center gap-2">
            <input
              type="date"
              value={customFrom}
              max={customTo || today}
              onChange={e => setCustomFrom(e.target.value)}
              className="rounded border border-gray-200 px-2 py-1 text-xs text-gray-700 focus:outline-none focus:ring-1 focus:ring-blue-400"
            />
            <span className="text-xs text-gray-400">to</span>
            <input
              type="date"
              value={customTo}
              min={customFrom || undefined}
              max={today}
              onChange={e => setCustomTo(e.target.value)}
              className="rounded border border-gray-200 px-2 py-1 text-xs text-gray-700 focus:outline-none focus:ring-1 focus:ring-blue-400"
            />
          </div>
        )}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <select
          value={filterProvider}
          onChange={e => setFilterProvider(e.target.value)}
          className="rounded border border-gray-300 px-3 py-1.5 text-sm text-gray-700"
        >
          <option value="">All providers</option>
          {providers.map(p => (
            <option key={p.id} value={p.id}>{p.full_name || p.email}</option>
          ))}
        </select>
        <select
          value={filterStatus}
          onChange={e => setFilterStatus(e.target.value)}
          className="rounded border border-gray-300 px-3 py-1.5 text-sm text-gray-700"
        >
          <option value="">All statuses</option>
          <option value="pending_billing_review">Pending Review</option>
          <option value="submitted">Submitted</option>
          <option value="processing">Processing</option>
          <option value="paid">Paid</option>
          <option value="denied">Denied</option>
        </select>
        {(filterProvider || filterStatus) && (
          <button
            onClick={() => { setFilterProvider(''); setFilterStatus('') }}
            className="text-xs text-blue-600 hover:underline"
          >
            Clear filters
          </button>
        )}
      </div>

      {loading ? (
        <p className="text-sm text-gray-500">Loading…</p>
      ) : filtered.length === 0 ? (
        <div className="rounded-lg border border-dashed border-gray-300 bg-white p-8 text-center">
          <p className="text-sm text-gray-500">No claims found.</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
                <th className="px-4 py-3">Provider</th>
                <th className="px-4 py-3">Visit Type</th>
                <th className="px-4 py-3">Service Date</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Billed</th>
                <th className="px-4 py-3">Paid</th>
                <th className="px-4 py-3">Denial Reason</th>
                <th className="px-4 py-3">Claim ID</th>
                <th className="px-4 py-3">Submitted</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filtered.map(c => {
                const prov = providerMap.get(c.provider_id)
                const { label, color } = claimStatusDisplay(c.status)
                const isExpanded = expandedClaimId === c.id
                const showManualEntry = manualFormClaimId === c.id
                const review = reviewData[c.id]
                const isReviewLoading = reviewLoading[c.id]
                const isDocUploading = docUploading[c.id]
                return (
                  <>
                    <tr
                      key={c.id}
                      className="hover:bg-gray-50 cursor-pointer"
                      onClick={() => toggleExpand(c)}
                    >
                      <td className="px-4 py-3">
                        <p className="font-medium text-gray-900 text-xs">{prov?.full_name || prov?.email || '—'}</p>
                        {prov?.npi && <p className="text-gray-400 text-xs font-mono">{prov.npi}</p>}
                      </td>
                      <td className="px-4 py-3 text-gray-600 text-xs">{c.visit_type ?? '—'}</td>
                      <td className="px-4 py-3 text-gray-600 tabular-nums text-xs">{c.service_date ?? '—'}</td>
                      <td className="px-4 py-3">
                        <span className={`rounded border px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[color]}`}>
                          {label}
                        </span>
                      </td>
                      <td className="px-4 py-3 tabular-nums text-xs">
                        {c.billed_amount != null ? `$${Number(c.billed_amount).toFixed(2)}` : '—'}
                      </td>
                      <td className="px-4 py-3 tabular-nums text-xs text-green-700">
                        {c.paid_amount != null ? `$${Number(c.paid_amount).toFixed(2)}` : '—'}
                      </td>
                      <td className="px-4 py-3 text-xs text-red-700 max-w-xs">
                        {c.denial_reason ? (
                          <span title={c.denial_reason}>
                            {c.denial_reason.length > 40 ? c.denial_reason.slice(0, 40) + '…' : c.denial_reason}
                          </span>
                        ) : '—'}
                      </td>
                      <td className="px-4 py-3 font-mono text-xs text-gray-400">
                        {c.availity_claim_id
                          ? c.availity_claim_id.slice(0, 12) + '…'
                          : c.is_manual ? <span className="text-gray-400">manual</span> : '—'}
                      </td>
                      <td className="px-4 py-3 text-gray-400 tabular-nums text-xs">
                        {c.submitted_at ? new Date(c.submitted_at).toLocaleDateString() : '—'}
                      </td>
                      <td className="px-4 py-3 text-right text-gray-400 text-xs select-none">
                        {isExpanded ? '▲' : '▼'}
                      </td>
                    </tr>
                    {isExpanded && (
                      <tr key={`${c.id}-detail`} className="bg-gray-50">
                        <td colSpan={10} className="px-6 py-5">
                          {isReviewLoading ? (
                            <p className="text-xs text-gray-400">Loading review…</p>
                          ) : (
                            <div className="space-y-5" onClick={e => e.stopPropagation()}>

                              {/* Claim billing details */}
                              {review && (() => {
                                const { procCode, modifier, diagCode } = extractClaimData(review.claim_data)
                                return (
                                  <div className="rounded border border-gray-200 bg-white p-4">
                                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Claim Details</p>
                                    <div className="flex flex-wrap gap-5 text-xs text-gray-600">
                                      <span><span className="font-medium text-gray-500">Payer:</span> {c.payer_id ?? '—'}</span>
                                      <span><span className="font-medium text-gray-500">Proc code:</span> {procCode ?? '—'}{modifier ? ` (${modifier})` : ''}</span>
                                      <span><span className="font-medium text-gray-500">Diag:</span> {diagCode ?? '—'}</span>
                                      <span><span className="font-medium text-gray-500">Billed:</span> {c.billed_amount != null ? `$${Number(c.billed_amount).toFixed(2)}` : '—'}</span>
                                      <span><span className="font-medium text-gray-500">Resubmits:</span> {review.claim.resubmit_count}</span>
                                      {review.visit?.ma91_status && (
                                        <span>
                                          <span className="font-medium text-gray-500">MA 91:</span>{' '}
                                          <span className={review.visit.ma91_status === 'signed' ? 'text-green-700 font-medium' : 'text-orange-700'}>
                                            {review.visit.ma91_status === 'signed' ? '✓ Signed' : review.visit.ma91_status}
                                          </span>
                                        </span>
                                      )}
                                      <span><span className="font-medium text-gray-500">Provider NPI:</span> {prov?.npi ?? '—'}</span>
                                      {c.availity_claim_id && (
                                        <span><span className="font-medium text-gray-500">Availity ID:</span> <span className="font-mono">{c.availity_claim_id}</span></span>
                                      )}
                                      {c.denial_reason && (
                                        <span className="text-red-700"><span className="font-medium">Denial:</span> {c.denial_reason}</span>
                                      )}
                                    </div>
                                  </div>
                                )
                              })()}

                              {/* Visit Notes / SOAP */}
                              {review !== null && (
                                <div className="rounded border border-gray-200 bg-white p-4">
                                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Visit Notes</p>
                                  {review === undefined || review?.visit === undefined ? (
                                    <p className="text-xs text-gray-400">Loading…</p>
                                  ) : review?.visit === null ? (
                                    <p className="text-xs text-gray-400">No visit record found.</p>
                                  ) : (
                                    <div className="grid grid-cols-1 gap-2 text-xs">
                                      {([
                                        ['Subjective', review.visit.subjective],
                                        ['Objective', review.visit.objective],
                                        ['Assessment', review.visit.assessment],
                                        ['Plan', review.visit.plan],
                                        ['Entry notes', review.visit.entry],
                                        ['Birth notes', review.visit.birth_notes],
                                      ] as [string, string | null][]).filter(([, v]) => v).map(([lbl, val]) => (
                                        <div key={lbl}>
                                          <span className="font-medium text-gray-500">{lbl}:</span>{' '}
                                          <span className="text-gray-700 whitespace-pre-wrap">{val}</span>
                                        </div>
                                      ))}
                                      {![review.visit.subjective, review.visit.objective, review.visit.assessment, review.visit.plan, review.visit.entry, review.visit.birth_notes].some(Boolean) && (
                                        <p className="text-gray-400">No notes recorded for this visit.</p>
                                      )}
                                    </div>
                                  )}
                                </div>
                              )}

                              {/* Documents panel */}
                              <div className="rounded border border-gray-200 bg-white p-4">
                                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Documents</p>

                                {/* Standard documents row */}
                                <div className="flex flex-wrap gap-2 mb-4">
                                  <button
                                    onClick={() => setPreviewClaim({ id: c.id, visitType: c.visit_type ?? 'claim' })}
                                    className="rounded border border-gray-300 bg-white px-3 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50"
                                  >
                                    Preview CMS 1500
                                  </button>
                                  <button
                                    onClick={() => setFilePreview({
                                      title: `Audit Packet — ${c.visit_type ?? 'claim'}`,
                                      fetchUrl: `/api/v1/billing-admin/claims/${c.id}/audit-packet.pdf`,
                                      contentType: 'pdf',
                                      fileName: `audit-packet-${c.visit_type ?? 'claim'}.pdf`,
                                    })}
                                    className="rounded border border-gray-300 bg-white px-3 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50"
                                  >
                                    Audit Packet
                                  </button>
                                  {review?.source_image_url && (
                                    <button
                                      onClick={() => setFilePreview({
                                        title: 'Source Document',
                                        directUrl: review.source_image_url!,
                                        contentType: 'auto',
                                        fileName: 'source-document',
                                      })}
                                      className="rounded border border-gray-300 bg-white px-3 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50"
                                    >
                                      Source Image ↗
                                    </button>
                                  )}
                                  {(c.status ?? '').toLowerCase() === 'pending_billing_review' && (
                                    <button
                                      onClick={() => handleSubmitClaim(c.id)}
                                      disabled={submitting === c.id}
                                      className="rounded border border-blue-300 bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700 hover:bg-blue-100 disabled:opacity-50"
                                    >
                                      {submitting === c.id ? '…' : 'Submit to Availity ↗'}
                                    </button>
                                  )}
                                  <button
                                    onClick={() => {
                                      setManualFormClaimId(showManualEntry ? null : c.id)
                                      setManualFormStatus('submitted')
                                      setManualFormPaid('')
                                      setManualFormDenial('')
                                      setManualFormNotes('')
                                    }}
                                    className="rounded border border-gray-300 bg-white px-3 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50"
                                  >
                                    {showManualEntry ? 'Cancel' : 'Log Manual Submission'}
                                  </button>
                                </div>

                                {/* Manual status form */}
                                {showManualEntry && (
                                  <div className="rounded border border-gray-200 bg-gray-50 p-3 mb-4 space-y-3">
                                    <div className="flex flex-wrap gap-4 items-end">
                                      <div>
                                        <label className="block text-xs font-medium text-gray-600 mb-1">Status</label>
                                        <select
                                          value={manualFormStatus}
                                          onChange={e => setManualFormStatus(e.target.value as 'submitted' | 'paid' | 'denied')}
                                          className="rounded border border-gray-300 px-2 py-1.5 text-xs text-gray-700"
                                        >
                                          <option value="submitted">Submitted</option>
                                          <option value="paid">Paid</option>
                                          <option value="denied">Denied</option>
                                        </select>
                                      </div>
                                      {manualFormStatus === 'paid' && (
                                        <div>
                                          <label className="block text-xs font-medium text-gray-600 mb-1">Paid amount</label>
                                          <input
                                            type="number"
                                            step="0.01"
                                            placeholder="0.00"
                                            value={manualFormPaid}
                                            onChange={e => setManualFormPaid(e.target.value)}
                                            className="rounded border border-gray-300 px-2 py-1.5 text-xs w-28"
                                          />
                                        </div>
                                      )}
                                      {manualFormStatus === 'denied' && (
                                        <div className="flex-1 min-w-48">
                                          <label className="block text-xs font-medium text-gray-600 mb-1">Denial reason</label>
                                          <input
                                            type="text"
                                            placeholder="Reason for denial…"
                                            value={manualFormDenial}
                                            onChange={e => setManualFormDenial(e.target.value)}
                                            className="rounded border border-gray-300 px-2 py-1.5 text-xs w-full"
                                          />
                                        </div>
                                      )}
                                      <button
                                        onClick={() => handleManualStatus(c.id)}
                                        disabled={manualSaving}
                                        className="rounded bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                                      >
                                        {manualSaving ? 'Saving…' : 'Save'}
                                      </button>
                                    </div>
                                  </div>
                                )}

                                {/* Admin-uploaded documents */}
                                <div>
                                  <p className="text-xs font-medium text-gray-500 mb-2">Supporting Documents</p>
                                  {review && review.documents.length > 0 ? (
                                    <ul className="space-y-1 mb-3">
                                      {review.documents.map(doc => (
                                        <li key={doc.id} className="flex items-center gap-2 text-xs">
                                          <span className="text-gray-700 truncate max-w-xs" title={doc.file_name}>{doc.file_name}</span>
                                          {doc.document_type && (
                                            <span className="rounded border border-gray-200 bg-gray-50 px-1.5 py-0.5 text-gray-500">
                                              {DOC_TYPE_LABELS[doc.document_type] ?? doc.document_type}
                                            </span>
                                          )}
                                          <button
                                            onClick={() => handlePreviewDoc(c.id, doc)}
                                            className="text-blue-600 hover:underline"
                                          >
                                            Preview
                                          </button>
                                        </li>
                                      ))}
                                    </ul>
                                  ) : (
                                    <p className="text-xs text-gray-400 mb-3">No supporting documents uploaded.</p>
                                  )}

                                  {/* Upload button group */}
                                  <div className="flex flex-wrap gap-1.5">
                                    {[
                                      { type: 'prior_auth', label: 'Prior Auth' },
                                      { type: 'eligibility', label: 'Eligibility' },
                                      { type: 'eob_received', label: 'EOB Received' },
                                      { type: 'other', label: 'Other' },
                                    ].map(({ type, label }) => (
                                      <button
                                        key={type}
                                        disabled={isDocUploading}
                                        onClick={() => {
                                          uploadingClaimIdRef.current = c.id
                                          if (fileInputRef.current) {
                                            fileInputRef.current.dataset.docType = type
                                            fileInputRef.current.click()
                                          }
                                        }}
                                        className="rounded border border-gray-300 bg-white px-2.5 py-1 text-xs text-gray-600 hover:bg-gray-50 disabled:opacity-50"
                                      >
                                        {isDocUploading ? '…' : `+ ${label}`}
                                      </button>
                                    ))}
                                  </div>
                                </div>
                              </div>

                            </div>
                          )}
                        </td>
                      </tr>
                    )}
                  </>
                )
              })}
            </tbody>
          </table>
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
                <h2 className="text-base font-semibold text-gray-900">Agency Claims — How It Works</h2>
                <p className="text-xs text-gray-500 mt-0.5">Review, submit, and track insurance claims on behalf of your agency's providers.</p>
              </div>
              <button onClick={() => setShowGuide(false)} className="text-gray-400 hover:text-gray-600 text-xl leading-none ml-6 mt-0.5">×</button>
            </div>
            <div className="px-6 py-5 space-y-6">
              <div className="rounded-lg border border-blue-100 bg-blue-50 p-4">
                <h3 className="text-sm font-semibold text-blue-800 mb-2">What This Page Shows</h3>
                <ul className="space-y-1 text-xs text-blue-700 list-disc list-inside">
                  <li>All insurance claims submitted on behalf of your agency's providers</li>
                  <li>Claims are created automatically when providers complete and submit a visit in DoulaShield</li>
                  <li>Use the provider and status filters to narrow the list; click any row to expand details</li>
                </ul>
              </div>
              <div className="rounded-lg border border-amber-100 bg-amber-50 p-4">
                <h3 className="text-sm font-semibold text-amber-800 mb-2">Claim Status Flow</h3>
                <div className="flex flex-wrap items-center gap-1 text-xs text-amber-800 mb-2">
                  {[
                    { label: 'Pending Review', color: 'bg-orange-100 text-orange-700 border-orange-300' },
                    { label: 'Submitted', color: 'bg-amber-100 text-amber-700 border-amber-300' },
                    { label: 'Processing', color: 'bg-blue-100 text-blue-700 border-blue-300' },
                    { label: 'Paid', color: 'bg-green-100 text-green-700 border-green-300' },
                    { label: 'Denied', color: 'bg-red-100 text-red-700 border-red-300' },
                  ].map((s, i, arr) => (
                    <span key={s.label} className="flex items-center gap-1">
                      <span className={`rounded border px-2 py-0.5 font-medium text-xs ${s.color}`}>{s.label}</span>
                      {i < arr.length - 1 && i !== 2 && <span className="text-amber-600">→</span>}
                      {i === 2 && <span className="text-amber-600">→</span>}
                    </span>
                  ))}
                </div>
                <p className="text-xs text-amber-700">Paid and Denied are terminal states. Denied claims can be corrected and resubmitted (resubmit count tracks attempts).</p>
              </div>
              <div className="rounded-lg border border-green-100 bg-green-50 p-4">
                <h3 className="text-sm font-semibold text-green-800 mb-2">Expanding a Claim</h3>
                <ul className="space-y-1 text-xs text-green-700 list-disc list-inside">
                  <li>Click any claim row to expand full billing details</li>
                  <li>Shows: procedure code, diagnosis code, billed/paid amounts, resubmit count, Availity tracking ID</li>
                  <li>Visit notes (SOAP format: Subjective, Objective, Assessment, Plan) are pulled from the provider's visit record</li>
                  <li>MA 91 signature status and prior authorization info appear when applicable</li>
                </ul>
              </div>
              <div className="rounded-lg border border-indigo-100 bg-indigo-50 p-4">
                <h3 className="text-sm font-semibold text-indigo-800 mb-2">Submitting to Availity</h3>
                <ol className="space-y-1 text-xs text-indigo-700 list-decimal list-inside">
                  <li>Claims arrive in <strong>Pending Review</strong> — verify billing codes and visit notes are correct</li>
                  <li>Click <strong>Submit to Availity</strong> to post the claim electronically</li>
                  <li>The system records the Availity tracking ID automatically</li>
                  <li>Status moves to <strong>Submitted</strong> then advances as the carrier responds</li>
                </ol>
              </div>
              <div className="rounded-lg border border-gray-100 bg-gray-50 p-4">
                <h3 className="text-sm font-semibold text-gray-800 mb-2">Logging Manual Status</h3>
                <ul className="space-y-1 text-xs text-gray-700 list-disc list-inside">
                  <li>If Availity isn't syncing, use the <strong>Log Claim Status</strong> form in the expanded row</li>
                  <li>Mark <strong>Paid</strong> and enter the reimbursed amount, or mark <strong>Denied</strong> and enter the denial reason</li>
                  <li>Manual entries update the claim record and provider's remittance history</li>
                </ul>
              </div>
              <div className="rounded-lg border border-teal-100 bg-teal-50 p-4">
                <h3 className="text-sm font-semibold text-teal-800 mb-2">Documents & Audit Packet</h3>
                <ul className="space-y-1 text-xs text-teal-700 list-disc list-inside">
                  <li>View supporting documents uploaded by the provider (prior auth, eligibility, EOB)</li>
                  <li>Upload additional files directly to a claim for payer disputes or audit purposes</li>
                  <li><strong>CMS 1500 Preview</strong> shows the electronic claim form as it was submitted</li>
                  <li><strong>Download Audit Packet</strong> bundles all claim documents into a single PDF</li>
                </ul>
              </div>
              <div className="rounded-lg bg-gray-50 border border-gray-200 p-4">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-3">Key Rules & Reminders</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs text-gray-700">
                  <div><strong>180-day filing deadline:</strong> PA Medicaid requires claims to be filed within 180 days of the date of service; DoulaShield sends deadline reminders to providers.</div>
                  <div><strong>Resubmissions:</strong> Corrected claims have a 365-day deadline from the service date; resubmit count tracks how many times a claim has been sent.</div>
                  <div><strong>Secondary claims:</strong> Providers with other insurance must file a secondary claim within 60 days of the EOB payment date.</div>
                  <div><strong>SOAP notes:</strong> Availity requires complete visit notes at submission; providers should complete SOAP notes before you submit.</div>
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
