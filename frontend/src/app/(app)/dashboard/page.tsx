'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import axios from 'axios'
import { getAccessToken } from '@/lib/auth'
import { useAuthStore } from '@/store/auth-store'

export default function DashboardPage() {
  const { isAuthenticated } = useAuthStore()
  const [caqhDaysRemaining, setCaqhDaysRemaining] = useState<number | null | undefined>(undefined)

  useEffect(() => {
    if (!isAuthenticated) return
    const headers = { Authorization: `Bearer ${getAccessToken()}` }
    axios
      .get<{ caqh_days_remaining: number | null }>(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/me/provider-settings`,
        { headers }
      )
      .then((r) => setCaqhDaysRemaining(r.data.caqh_days_remaining))
      .catch(() => setCaqhDaysRemaining(null))
  }, [isAuthenticated])

  const showCaqhBanner = caqhDaysRemaining !== undefined && caqhDaysRemaining !== null && caqhDaysRemaining <= 14

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
