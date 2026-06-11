'use client'

import { useEffect, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import axios from 'axios'
import { getAccessToken } from '@/lib/auth'
import type { Claim } from '@/types/domain'

interface Provider {
  id: string
  email: string
  full_name: string | null
  npi: string | null
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

  const api = process.env.NEXT_PUBLIC_API_URL
  const headers = { Authorization: `Bearer ${getAccessToken()}` }

  const bpParam = bpId ? `?bp_id=${bpId}` : ''

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

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      const requests = [
        axios.get<Claim[]>(`${api}/api/v1/billing-admin/claims${bpParam}`, { headers }),
        axios.get<Provider[]>(`${api}/api/v1/billing-admin/providers${bpParam}`, { headers }),
        ...(bpId ? [axios.get(`${api}/api/v1/billing-admin/agency-settings${bpParam}`, { headers })] : []),
      ]
      const results = await Promise.allSettled(requests)
      if (results[0].status === 'fulfilled') setClaims((results[0] as PromiseFulfilledResult<{ data: Claim[] }>).value.data)
      if (results[1].status === 'fulfilled') setProviders((results[1] as PromiseFulfilledResult<{ data: Provider[] }>).value.data)
      if (bpId && results[2]?.status === 'fulfilled') {
        const settingsResult = results[2] as PromiseFulfilledResult<{ data: { name: string } }>
        setAgencyName(settingsResult.value.data.name)
      }
      setLoading(false)
    }
    load()
  }, [bpId])

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

  const pendingReviewCount = claims.filter(c => (c.status ?? '').toLowerCase() === 'pending_billing_review').length

  // Aggregate stats
  const totalBilled = filtered.reduce((a, c) => a + Number(c.billed_amount ?? 0), 0)
  const totalPaid = filtered.reduce((a, c) => a + Number(c.paid_amount ?? 0), 0)
  const paidCount = filtered.filter(c => claimStatusDisplay(c.status).color === 'green').length
  const deniedCount = filtered.filter(c => claimStatusDisplay(c.status).color === 'red').length

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Agency Claims</h1>
          {bpId && agencyName && (
            <p className="mt-0.5 text-xs text-blue-600 font-medium">
              Viewing as admin: {agencyName}
            </p>
          )}
        </div>
        {pendingReviewCount > 0 && (
          <span className="rounded-full bg-orange-100 px-3 py-1 text-xs font-semibold text-orange-700">
            {pendingReviewCount} pending review
          </span>
        )}
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
                return (
                  <tr key={c.id} className="hover:bg-gray-50">
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
                    <td className="px-4 py-3 text-right">
                      {(c.status ?? '').toLowerCase() === 'pending_billing_review' && (
                        <button
                          onClick={() => handleSubmitClaim(c.id)}
                          disabled={submitting === c.id}
                          className="rounded border border-blue-300 bg-blue-50 px-2 py-1 text-xs font-medium text-blue-700 hover:bg-blue-100 disabled:opacity-50"
                        >
                          {submitting === c.id ? '…' : 'Submit ↗'}
                        </button>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
