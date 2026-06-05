'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import axios from 'axios'
import { getAccessToken } from '@/lib/auth'
import { useAuthStore } from '@/store/auth-store'

export default function DashboardPage() {
  const { isAuthenticated } = useAuthStore()
  const [caqhDaysRemaining, setCaqhDaysRemaining] = useState<number | null | undefined>(undefined)
  const [promiseDaysRemaining, setPromiseDaysRemaining] = useState<number | null | undefined>(undefined)
  const [pcbDaysRemaining, setPcbDaysRemaining] = useState<number | null | undefined>(undefined)
  const [liabilityDaysRemaining, setLiabilityDaysRemaining] = useState<number | null | undefined>(undefined)
  const [claimDeadlineSummary, setClaimDeadlineSummary] = useState<{ overdue_count: number; urgent_count: number; unfiled_past_30_days: number } | null>(null)

  useEffect(() => {
    if (!isAuthenticated) return
    const headers = { Authorization: `Bearer ${getAccessToken()}` }
    axios
      .get<{ claim_deadline_summary: { overdue_count: number; urgent_count: number; unfiled_past_30_days: number } }>(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/stats/summary`,
        { headers }
      )
      .then((r) => setClaimDeadlineSummary(r.data.claim_deadline_summary))
      .catch(() => {})
  }, [isAuthenticated])

  useEffect(() => {
    if (!isAuthenticated) return
    const headers = { Authorization: `Bearer ${getAccessToken()}` }
    axios
      .get<{ caqh_days_remaining: number | null; promise_days_remaining: number | null; pcb_days_remaining: number | null; liability_days_remaining: number | null }>(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/me/provider-settings`,
        { headers }
      )
      .then((r) => {
        setCaqhDaysRemaining(r.data.caqh_days_remaining)
        setPromiseDaysRemaining(r.data.promise_days_remaining)
        setPcbDaysRemaining(r.data.pcb_days_remaining)
        setLiabilityDaysRemaining(r.data.liability_days_remaining)
      })
      .catch(() => {
        setCaqhDaysRemaining(null)
        setPromiseDaysRemaining(null)
        setPcbDaysRemaining(null)
        setLiabilityDaysRemaining(null)
      })
  }, [isAuthenticated])

  const showCaqhBanner = caqhDaysRemaining !== undefined && caqhDaysRemaining !== null && caqhDaysRemaining <= 14
  const showPromiseBanner = promiseDaysRemaining !== undefined && promiseDaysRemaining !== null && promiseDaysRemaining <= 90
  const showPcbBanner = pcbDaysRemaining !== undefined && pcbDaysRemaining !== null && pcbDaysRemaining <= 60
  const showLiabilityBanner = liabilityDaysRemaining !== undefined && liabilityDaysRemaining !== null && liabilityDaysRemaining <= 30

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>

      {showCaqhBanner && (
        <div className={`rounded-lg border p-4 ${caqhDaysRemaining <= 0 ? 'border-red-300 bg-red-50' : 'border-amber-300 bg-amber-50'}`}>
          <p className={`text-sm font-medium ${caqhDaysRemaining <= 0 ? 'text-red-800' : 'text-amber-800'}`}>
            {caqhDaysRemaining <= 0
              ? `⚠ CAQH attestation overdue by ${Math.abs(caqhDaysRemaining)} day${Math.abs(caqhDaysRemaining) !== 1 ? 's' : ''} — re-attest now to stay enrolled in MCO directories`
              : `⏰ CAQH attestation due in ${caqhDaysRemaining} day${caqhDaysRemaining !== 1 ? 's' : ''}`}
          </p>
          <div className="mt-2 flex items-center gap-4">
            <a
              href="https://proview.caqh.org"
              target="_blank"
              rel="noopener noreferrer"
              className={`text-xs font-medium underline ${caqhDaysRemaining <= 0 ? 'text-red-700' : 'text-amber-700'}`}
            >
              Re-attest on CAQH ProView →
            </a>
            <Link
              href="/settings"
              className={`text-xs font-medium underline ${caqhDaysRemaining <= 0 ? 'text-red-700' : 'text-amber-700'}`}
            >
              Update date in Settings →
            </Link>
          </div>
        </div>
      )}

      {showPromiseBanner && (
        <div className={`rounded-lg border p-4 ${promiseDaysRemaining <= 0 ? 'border-red-300 bg-red-50' : 'border-amber-300 bg-amber-50'}`}>
          <p className={`text-sm font-medium ${promiseDaysRemaining <= 0 ? 'text-red-800' : 'text-amber-800'}`}>
            {promiseDaysRemaining <= 0
              ? `⚠ PROMISe™ re-enrollment overdue by ${Math.abs(promiseDaysRemaining)} day${Math.abs(promiseDaysRemaining) !== 1 ? 's' : ''} — re-enroll now to maintain FFS billing`
              : `⏰ PROMISe™ re-enrollment due in ${promiseDaysRemaining} day${promiseDaysRemaining !== 1 ? 's' : ''}`}
          </p>
          <div className="mt-2 flex items-center gap-4">
            <a
              href="https://promise.dhs.pa.gov"
              target="_blank"
              rel="noopener noreferrer"
              className={`text-xs font-medium underline ${promiseDaysRemaining <= 0 ? 'text-red-700' : 'text-amber-700'}`}
            >
              Re-enroll on PROMISe™ →
            </a>
            <Link
              href="/settings"
              className={`text-xs font-medium underline ${promiseDaysRemaining <= 0 ? 'text-red-700' : 'text-amber-700'}`}
            >
              Update date in Settings →
            </Link>
          </div>
        </div>
      )}

      {showPcbBanner && (
        <div className={`rounded-lg border p-4 ${pcbDaysRemaining <= 0 ? 'border-red-300 bg-red-50' : 'border-amber-300 bg-amber-50'}`}>
          <p className={`text-sm font-medium ${pcbDaysRemaining <= 0 ? 'text-red-800' : 'text-amber-800'}`}>
            {pcbDaysRemaining <= 0
              ? `⚠ PCB Perinatal Certification overdue by ${Math.abs(pcbDaysRemaining)} day${Math.abs(pcbDaysRemaining) !== 1 ? 's' : ''} — renew to maintain billing eligibility`
              : `⏰ PCB Perinatal Certification due in ${pcbDaysRemaining} day${pcbDaysRemaining !== 1 ? 's' : ''}`}
          </p>
          <div className="mt-2 flex items-center gap-4">
            <a
              href="https://www.pacertboard.org"
              target="_blank"
              rel="noopener noreferrer"
              className={`text-xs font-medium underline ${pcbDaysRemaining <= 0 ? 'text-red-700' : 'text-amber-700'}`}
            >
              Renew on PCB Portal →
            </a>
            <Link
              href="/settings"
              className={`text-xs font-medium underline ${pcbDaysRemaining <= 0 ? 'text-red-700' : 'text-amber-700'}`}
            >
              Update date in Settings →
            </Link>
          </div>
        </div>
      )}

      {showLiabilityBanner && (
        <div className={`rounded-lg border p-4 ${liabilityDaysRemaining <= 0 ? 'border-red-300 bg-red-50' : 'border-amber-300 bg-amber-50'}`}>
          <p className={`text-sm font-medium ${liabilityDaysRemaining <= 0 ? 'text-red-800' : 'text-amber-800'}`}>
            {liabilityDaysRemaining <= 0
              ? `⚠ Liability insurance expired ${Math.abs(liabilityDaysRemaining)} day${Math.abs(liabilityDaysRemaining) !== 1 ? 's' : ''} ago — update your policy immediately`
              : `⏰ Liability insurance expires in ${liabilityDaysRemaining} day${liabilityDaysRemaining !== 1 ? 's' : ''} — renew soon`}
          </p>
          <div className="mt-2">
            <Link
              href="/settings"
              className={`text-xs font-medium underline ${liabilityDaysRemaining <= 0 ? 'text-red-700' : 'text-amber-700'}`}
            >
              Update expiry date in Settings →
            </Link>
          </div>
        </div>
      )}

      {claimDeadlineSummary?.overdue_count != null && claimDeadlineSummary.overdue_count > 0 && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3">
          <p className="text-sm font-medium text-red-800">
            ⚠ {claimDeadlineSummary.overdue_count} claim{claimDeadlineSummary.overdue_count !== 1 ? 's' : ''} past the 180-day PA Medicaid filing deadline
          </p>
          <div className="mt-1.5">
            <Link href="/clients" className="text-xs font-medium underline text-red-700">
              View clients to file or correct →
            </Link>
          </div>
        </div>
      )}

      {claimDeadlineSummary?.urgent_count != null && claimDeadlineSummary.urgent_count > 0 && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-3">
          <p className="text-sm font-medium text-amber-800">
            ⏰ {claimDeadlineSummary.urgent_count} claim{claimDeadlineSummary.urgent_count !== 1 ? 's' : ''} within 30 days of the PA Medicaid 180-day filing deadline
          </p>
          <div className="mt-1.5">
            <Link href="/clients" className="text-xs font-medium underline text-amber-700">
              File now →
            </Link>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Link
          href="/clients"
          className="block p-6 bg-white rounded-lg border border-gray-200 hover:border-blue-400 transition-colors"
        >
          <h2 className="text-lg font-semibold">Clients</h2>
          <p className="mt-1 text-sm text-gray-500">View and manage client records</p>
        </Link>
        <Link
          href="/reports"
          className="block p-6 bg-white rounded-lg border border-gray-200 hover:border-blue-400 transition-colors"
        >
          <h2 className="text-lg font-semibold">Reports</h2>
          <p className="mt-1 text-sm text-gray-500">Billing pipeline, revenue, and MCO breakdown</p>
        </Link>
      </div>
    </div>
  )
}
