'use client'

import { useEffect, useState } from 'react'
import axios from 'axios'
import { getAccessToken } from '@/lib/auth'
import { Claim } from '@/types/domain'
import ImageUploadScanner from '@/components/ui/ImageUploadScanner'

export default function BillingAdminClaimsPage() {
  const [claims, setClaims] = useState<Claim[]>([])
  const [loading, setLoading] = useState(true)
  const [toast, setToast] = useState<string | null>(null)
  const [scanning, setScanning] = useState<string | null>(null) // claim id being scanned
  const [eobError, setEobError] = useState<string | null>(null)

  const headers = { Authorization: `Bearer ${getAccessToken()}` }
  const api = process.env.NEXT_PUBLIC_API_URL

  const showToast = (msg: string) => {
    setToast(msg)
    setTimeout(() => setToast(null), 4000)
  }

  const reload = async () => {
    const res = await axios.get<Claim[]>(`${api}/api/v1/billing-admin/claims`, { headers })
    setClaims(res.data)
  }

  useEffect(() => {
    reload().finally(() => setLoading(false))
  }, [])

  const handleEobScanned = async (claim: Claim, data: Record<string, unknown>): Promise<void> => {
    setEobError(null)
    const statusMap: Record<string, string> = {
      paid: 'paid', partially_paid: 'paid', denied: 'denied', pending: 'submitted',
    }
    const rawStatus = String(data.claim_status ?? '')
    const claimStatus = statusMap[rawStatus] ?? 'submitted'
    const payload: Record<string, unknown> = {
      status: claimStatus,
      service_date: claim.service_date,
    }
    if (data.paid_amount) payload.paid_amount = data.paid_amount
    if (data.denial_reason) payload.denial_reason = data.denial_reason
    try {
      await axios.put(
        `${api}/api/v1/billing-admin/patients/${claim.patient_id}/visits/${claim.visit_type}/claims/manual`,
        payload,
        { headers }
      )
      setScanning(null)
      showToast('Claim updated from EOB')
      await reload()
    } catch {
      setEobError('Failed to update claim — please try again.')
    }
  }

  const statusBadge = (status: string | null) => {
    if (!status) return <span className="text-gray-400 text-xs">—</span>
    const map: Record<string, string> = {
      paid: 'bg-green-100 text-green-700',
      submitted: 'bg-blue-100 text-blue-700',
      denied: 'bg-red-100 text-red-700',
      pending: 'bg-gray-100 text-gray-600',
    }
    return (
      <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium capitalize ${map[status] ?? 'bg-gray-100 text-gray-600'}`}>
        {status}
      </span>
    )
  }

  const deadlineBadge = (claim: Claim) => {
    const days = claim.days_until_filing_deadline
    if (days == null) return null
    const cls =
      days <= 7 ? 'bg-red-100 text-red-700' :
      days <= 30 ? 'bg-amber-100 text-amber-700' :
      'bg-gray-100 text-gray-500'
    const label =
      days < 0 ? `Deadline ${Math.abs(days)}d overdue` :
      days === 0 ? 'Deadline today' :
      `Deadline in ${days}d`
    return <span className={`ml-1 inline-flex items-center rounded-full px-1.5 py-0.5 text-xs font-medium ${cls}`}>{label}</span>
  }

  if (loading) return <p className="text-sm text-gray-500">Loading…</p>

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-gray-900">Agency Claims</h1>

      {toast && (
        <div className="rounded-lg bg-blue-50 border border-blue-200 px-4 py-2 text-sm text-blue-800">{toast}</div>
      )}

      {eobError && (
        <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-2 text-sm text-red-700">{eobError}</div>
      )}

      <div className="bg-white rounded-lg border border-gray-200 overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              {['Visit', 'Service Date', 'MCO', 'Status', 'Billed', 'Paid', 'Denial', 'Actions'].map((h) => (
                <th key={h} className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase whitespace-nowrap">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {claims.length === 0 && (
              <tr><td colSpan={8} className="px-4 py-6 text-center text-sm text-gray-400">No claims found</td></tr>
            )}
            {claims.map((c) => (
              <>
                <tr key={c.id}>
                  <td className="px-4 py-3 text-gray-700">
                    {c.visit_type?.replace(/_/g, ' ')}
                    {deadlineBadge(c)}
                  </td>
                  <td className="px-4 py-3 text-gray-500 whitespace-nowrap">{c.service_date ?? '—'}</td>
                  <td className="px-4 py-3 text-gray-500">{c.payer_id ?? '—'}</td>
                  <td className="px-4 py-3">{statusBadge(c.status)}</td>
                  <td className="px-4 py-3 text-gray-700">{c.billed_amount ? `$${Number(c.billed_amount).toFixed(2)}` : '—'}</td>
                  <td className="px-4 py-3 text-gray-700">{c.paid_amount ? `$${Number(c.paid_amount).toFixed(2)}` : '—'}</td>
                  <td className="px-4 py-3 text-gray-500 text-xs max-w-32 truncate">{c.denial_reason ?? '—'}</td>
                  <td className="px-4 py-3">
                    {c.is_manual && (
                      <button
                        onClick={() => { setScanning(c.id); setEobError(null) }}
                        className="rounded border border-gray-300 px-2 py-1 text-xs text-gray-600 hover:bg-gray-50 whitespace-nowrap"
                      >
                        Scan EOB
                      </button>
                    )}
                  </td>
                </tr>
                {scanning === c.id && (
                  <tr key={`scan-${c.id}`}>
                    <td colSpan={8} className="px-4 pb-3">
                      <div className="rounded-lg border border-gray-200 bg-gray-50 p-3">
                        <ImageUploadScanner
                          endpoint="/api/v1/ocr/handbook"
                          extraFields={{ page_type: 'remittance_eob' }}
                          label="Scan Remittance / EOB"
                          acceptPdf
                          onExtracted={(data) => handleEobScanned(c, data)}
                        />
                        <button
                          onClick={() => setScanning(null)}
                          className="mt-2 text-xs text-gray-400 hover:text-gray-600"
                        >
                          Cancel
                        </button>
                      </div>
                    </td>
                  </tr>
                )}
              </>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
