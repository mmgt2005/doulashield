'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import axios from 'axios'
import { getAccessToken } from '@/lib/auth'
import { useAuthStore } from '@/store/auth-store'
import OnboardingChecklist from '@/components/ui/OnboardingChecklist'

interface TodayVisit {
  patient_id: string
  patient_name: string
  visit_type: string
  visit_label: string
  scheduled_at: string | null
  status: 'complete' | 'in_progress' | 'scheduled' | 'unscheduled'
}

interface EnrollmentTask {
  id: string
  status: 'not_started' | 'in_progress' | 'complete'
}

interface EnrollmentService {
  id: string
  stage: string
  status: string
}

interface EnrollmentServiceDetail {
  service: EnrollmentService
  tasks: EnrollmentTask[]
}

const STAGE_ORDER = ['pcb', 'nppes_setup', 'enrollment', 'mco_contracting']
const STAGE_LABELS: Record<string, string> = {
  pcb: 'PCB',
  nppes_setup: 'NPPES / NPI',
  enrollment: 'Stage 2',
  mco_contracting: 'Stage 3',
}

export default function DashboardPage() {
  const { isAuthenticated, user } = useAuthStore()
  const [caqhDaysRemaining, setCaqhDaysRemaining] = useState<number | null | undefined>(undefined)
  const [promiseDaysRemaining, setPromiseDaysRemaining] = useState<number | null | undefined>(undefined)
  const [pcbDaysRemaining, setPcbDaysRemaining] = useState<number | null | undefined>(undefined)
  const [liabilityDaysRemaining, setLiabilityDaysRemaining] = useState<number | null | undefined>(undefined)
  const [claimDeadlineSummary, setClaimDeadlineSummary] = useState<{ overdue_count: number; urgent_count: number; unfiled_past_30_days: number } | null>(null)
  const [enrollmentServices, setEnrollmentServices] = useState<EnrollmentServiceDetail[] | null>(null)
  const [todayVisits, setTodayVisits] = useState<TodayVisit[] | null>(null)
  const [checklistDismissed, setChecklistDismissed] = useState(false)
  const [checklistNpi, setChecklistNpi] = useState<string | null>(null)
  const [checklistBillingName, setChecklistBillingName] = useState<string | null>(null)
  const [checklistAddress, setChecklistAddress] = useState<string | null>(null)
  const [checklistHasSignature, setChecklistHasSignature] = useState(false)
  const [checklistZone, setChecklistZone] = useState<string | null>(null)
  const [checklistMcoCount, setChecklistMcoCount] = useState(0)
  const [adminBillingProviders, setAdminBillingProviders] = useState<Array<{ name: string | null; group_npi: string | null; availity_connected: boolean; provider_count: number }>>([])
  const [adminChecklistLoaded, setAdminChecklistLoaded] = useState(false)

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
      .get<EnrollmentServiceDetail[]>(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/enrollment/me`,
        { headers }
      )
      .then((r) => setEnrollmentServices(r.data))
      .catch(() => setEnrollmentServices([]))
  }, [isAuthenticated])

  useEffect(() => {
    if (!isAuthenticated) return
    const today = new Date().toISOString().slice(0, 10)
    axios
      .get<TodayVisit[]>(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/schedule`, {
        params: { date_from: today, date_to: today },
        headers: { Authorization: `Bearer ${getAccessToken()}` },
      })
      .then((r) => setTodayVisits(r.data))
      .catch(() => setTodayVisits([]))
  }, [isAuthenticated])

  useEffect(() => {
    if (!isAuthenticated) return
    const headers = { Authorization: `Bearer ${getAccessToken()}` }
    axios
      .get<{ caqh_days_remaining: number | null; promise_days_remaining: number | null; pcb_days_remaining: number | null; liability_days_remaining: number | null; npi: string | null; billing_provider_name: string | null; provider_address: string | null; has_signature: boolean; zone: string | null; mco_contracts: Array<{ mco: string }> | null }>(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/me/provider-settings`,
        { headers }
      )
      .then((r) => {
        setCaqhDaysRemaining(r.data.caqh_days_remaining)
        setPromiseDaysRemaining(r.data.promise_days_remaining)
        setPcbDaysRemaining(r.data.pcb_days_remaining)
        setLiabilityDaysRemaining(r.data.liability_days_remaining)
        setChecklistNpi(r.data.npi)
        setChecklistBillingName(r.data.billing_provider_name)
        setChecklistAddress(r.data.provider_address)
        setChecklistHasSignature(r.data.has_signature ?? false)
        setChecklistZone(r.data.zone)
        setChecklistMcoCount(r.data.mco_contracts?.length ?? 0)
      })
      .catch(() => {
        setCaqhDaysRemaining(null)
        setPromiseDaysRemaining(null)
        setPcbDaysRemaining(null)
        setLiabilityDaysRemaining(null)
      })
  }, [isAuthenticated])

  useEffect(() => {
    if (!isAuthenticated || user?.role !== 'admin') return
    axios
      .get<Array<{ name: string | null; group_npi: string | null; availity_connected: boolean; provider_count: number }>>(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/admin/billing-providers`,
        { headers: { Authorization: `Bearer ${getAccessToken()}` } }
      )
      .then((r) => { setAdminBillingProviders(r.data); setAdminChecklistLoaded(true) })
      .catch(() => setAdminChecklistLoaded(true))
  }, [isAuthenticated]) // eslint-disable-line react-hooks/exhaustive-deps

  const handleChecklistDismiss = async () => {
    setChecklistDismissed(true)
    try {
      await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/complete-onboarding`,
        {},
        { headers: { Authorization: `Bearer ${getAccessToken()}` } }
      )
    } catch { /* non-fatal */ }
  }

  const onboardingCompletedAt = user?.onboarding_completed_at ? new Date(user.onboarding_completed_at) : null
  const onboardingOlderThan30Days = onboardingCompletedAt
    ? (Date.now() - onboardingCompletedAt.getTime()) > 30 * 24 * 60 * 60 * 1000
    : false

  const providerChecklistItems = [
    { label: 'Enter your NPI number', done: !!checklistNpi, href: '/settings#npi' },
    { label: 'Set your billing name & address', done: !!(checklistBillingName && checklistAddress), href: '/settings#billing' },
    { label: 'Draw your provider signature', done: checklistHasSignature, href: '/settings#signature' },
    { label: 'Set your PA zone & counties', done: !!checklistZone, href: '/settings#zone' },
    { label: 'Add MCO contracts', done: checklistMcoCount > 0, href: '/settings#mco' },
  ]

  const adminBp = adminBillingProviders[0]
  const adminChecklistItems = [
    { label: 'Create a billing provider entity', done: adminBillingProviders.length > 0, href: '/admin/billing-providers' },
    { label: 'Set agency name & group NPI', done: !!(adminBp?.name && adminBp?.group_npi), href: '/admin/billing-providers' },
    { label: 'Add providers to your agency', done: (adminBp?.provider_count ?? 0) > 0, href: '/admin/users' },
    { label: 'Connect Availity credentials', done: adminBp?.availity_connected ?? false, href: '/admin/billing-providers' },
  ]

  const checklistItems = user?.role === 'admin' ? adminChecklistItems : providerChecklistItems
  const checklistReady = user?.role === 'admin' ? adminChecklistLoaded : true
  const showChecklist = (user?.role === 'provider' || user?.role === 'admin') && !checklistDismissed && !onboardingOlderThan30Days && checklistReady

  const showCaqhBanner = caqhDaysRemaining !== undefined && caqhDaysRemaining !== null && caqhDaysRemaining <= 14
  const showPromiseBanner = promiseDaysRemaining !== undefined && promiseDaysRemaining !== null && promiseDaysRemaining <= 90
  const showPcbBanner = pcbDaysRemaining !== undefined && pcbDaysRemaining !== null && pcbDaysRemaining <= 60
  const showLiabilityBanner = liabilityDaysRemaining !== undefined && liabilityDaysRemaining !== null && liabilityDaysRemaining <= 30

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>

      {showChecklist && (
        <OnboardingChecklist
          items={checklistItems}
          onDismiss={handleChecklistDismiss}
        />
      )}

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

      {enrollmentServices && enrollmentServices.length > 0 && (() => {
        // Find the most recent non-complete service, or fallback to most recent overall
        const active = enrollmentServices.find((d) => d.service.status !== 'complete') ?? enrollmentServices[0]
        const allTasks = active.tasks
        const completedCount = allTasks.filter((t) => t.status === 'complete').length

        // Build per-stage status for the pipeline pills
        const stageStatus: Record<string, 'complete' | 'in_progress' | 'none'> = {}
        for (const stage of STAGE_ORDER) {
          const svc = enrollmentServices.find((d) => d.service.stage === stage)
          if (!svc) stageStatus[stage] = 'none'
          else if (svc.service.status === 'complete') stageStatus[stage] = 'complete'
          else stageStatus[stage] = 'in_progress'
        }

        return (
          <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <p className="text-sm font-semibold text-gray-900">Credentialing Status</p>
              <Link href="/enrollment-status" className="text-xs font-medium text-blue-600 hover:underline">
                View details →
              </Link>
            </div>
            <div className="mb-3">
              <p className="text-xs text-gray-500">
                Current stage: <span className="font-medium text-gray-800">{STAGE_LABELS[active.service.stage] ?? active.service.stage}</span>
                <span className={`ml-2 rounded-full px-2 py-0.5 text-xs font-medium ${
                  active.service.status === 'complete' ? 'bg-green-100 text-green-700' :
                  active.service.status === 'in_progress' ? 'bg-blue-100 text-blue-700' :
                  'bg-gray-100 text-gray-600'
                }`}>
                  {active.service.status.replace('_', ' ')}
                </span>
              </p>
              {allTasks.length > 0 && (
                <p className="mt-1 text-xs text-gray-500">
                  Tasks: <span className="font-medium text-gray-800">{completedCount} of {allTasks.length} complete</span>
                </p>
              )}
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              {STAGE_ORDER.map((stage) => {
                const s = stageStatus[stage]
                return (
                  <span
                    key={stage}
                    className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${
                      s === 'complete' ? 'bg-green-100 text-green-700' :
                      s === 'in_progress' ? 'bg-blue-100 text-blue-700' :
                      'bg-gray-100 text-gray-400'
                    }`}
                  >
                    {s === 'complete' ? '✓' : s === 'in_progress' ? '●' : '○'}
                    {' '}{STAGE_LABELS[stage]}
                  </span>
                )
              })}
            </div>
          </div>
        )
      })()}

      {todayVisits && todayVisits.length > 0 && (
        <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm font-semibold text-gray-900">Today&apos;s Visits</p>
            <Link href="/schedule" className="text-xs font-medium text-blue-600 hover:underline">
              Full schedule →
            </Link>
          </div>
          <div className="space-y-2">
            {todayVisits.map((v) => (
              <Link
                key={`${v.patient_id}-${v.visit_type}`}
                href={`/clients/${v.patient_id}/visits/${v.visit_type}`}
                className="flex items-center justify-between rounded border border-gray-100 px-3 py-2 text-sm hover:bg-gray-50 transition-colors"
              >
                <div className="min-w-0">
                  <span className="font-medium text-gray-800">{v.visit_label}</span>
                  <span className="ml-2 text-gray-500 text-xs">{v.patient_name}</span>
                </div>
                <span className={`ml-3 flex-shrink-0 text-xs font-medium ${
                  v.status === 'complete' ? 'text-green-600' :
                  v.status === 'in_progress' ? 'text-amber-600' : 'text-blue-600'
                }`}>
                  {v.status === 'complete' ? 'Done' :
                   v.status === 'in_progress' ? 'In progress' :
                   v.scheduled_at
                     ? new Date(v.scheduled_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                     : 'Today'}
                </span>
              </Link>
            ))}
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
