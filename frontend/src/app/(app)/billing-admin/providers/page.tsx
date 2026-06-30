'use client'

import { useEffect, useRef, useState } from 'react'
import axios from 'axios'
import Papa from 'papaparse'
import { getAccessToken } from '@/lib/auth'

const ALL_MCOS = [
  'AmeriHealth Caritas', 'Keystone First', 'UPMC For You', 'Geisinger Health Plan',
  'Health Partners Plans', 'Aetna Better Health', 'UnitedHealthcare Community Plan',
  'Highmark Wholecare', 'FFS',
]

interface McoContract { mco: string; contract_date: string | null }
interface CsvRow {
  name: string; email: string; npi?: string; doula_type?: string
  mco_contracts?: McoContract[]
  _errors: string[]; _warnings: string[]
}

function parseCsvRows(raw: Record<string, string>[]): CsvRow[] {
  const DOULA_TYPES = ['Birth Doula', 'Postpartum Doula', 'Perinatal Doula', 'Other']
  return raw.map(r => {
    const errors: string[] = []
    const warnings: string[] = []
    const name = r.name?.trim() ?? ''
    const email = r.email?.trim().toLowerCase() ?? ''
    if (!name) errors.push('Name required')
    if (!email || !email.includes('@')) errors.push('Valid email required')
    const npi = r.npi?.trim()
    if (npi && !/^\d{10}$/.test(npi)) warnings.push('NPI must be 10 digits')
    const rawType = r.doula_type?.trim()
    const doula_type = DOULA_TYPES.includes(rawType ?? '') ? rawType : 'Birth Doula'
    const mco_contracts: McoContract[] = []
    for (let i = 1; i <= 9; i++) {
      const mco = r[`mco_${i}`]?.trim()
      if (!mco) break
      const normalized = ALL_MCOS.find(m => m.toLowerCase() === mco.toLowerCase())
      if (!normalized) { warnings.push(`Unknown MCO: "${mco}"`); continue }
      mco_contracts.push({ mco: normalized, contract_date: r[`mco_${i}_date`]?.trim() || null })
    }
    return { name, email, npi: npi || undefined, doula_type, mco_contracts: mco_contracts.length ? mco_contracts : undefined, _errors: errors, _warnings: warnings }
  })
}

function downloadTemplate() {
  const lines = [
    'name,email,npi,doula_type,mco_1,mco_1_date,mco_2,mco_2_date',
    'Maria Gonzalez,maria@example.com,1234567890,Birth Doula,AmeriHealth Caritas,2024-01-15,Keystone First,',
  ]
  const blob = new Blob([lines.join('\n')], { type: 'text/csv' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = 'doulashield-provider-import-template.csv'
  a.click()
  URL.revokeObjectURL(a.href)
}

interface CredentialExpiry {
  expires_on: string | null
  days_remaining: number | null
}

interface Provider {
  id: string
  full_name: string | null
  email: string
  npi: string | null
  deposit_paid: boolean
  enrollment_stages: {
    pcb: string | null
    nppes_setup: string | null
    enrollment: string | null
    mco_contracting: string | null
  }
  credentials: {
    pcb: CredentialExpiry
    promise: CredentialExpiry
    caqh: CredentialExpiry
    liability: CredentialExpiry
  }
}

interface EnrollmentService {
  id: string
  provider_id: string
  stage: string
  pcb_pathway: string | null
  status: string
  assigned_to_billing_admin: boolean
  created_at: string
}

interface EnrollmentTask {
  id: string
  service_id: string
  task_key: string
  label: string
  description: string | null
  status: string
  notes: string | null
  sort_order: number
  completed_at: string | null
}

interface EnrollmentServiceDetail {
  service: EnrollmentService
  tasks: EnrollmentTask[]
  documents: { id: string; task_id: string | null; file_name: string; document_type: string | null; created_at: string }[]
  provider_name: string | null
  provider_email: string | null
}

interface InviteRow { name: string; email: string; doula_type: string }
interface InviteResult {
  created: { name: string; email: string }[]
  skipped: { name: string; email: string; reason: string }[]
}

const DOULA_TYPES = ['Birth Doula', 'Postpartum Doula', 'Perinatal Doula', 'Other']
const EMPTY_ROW: InviteRow = { name: '', email: '', doula_type: 'Birth Doula' }

const STAGE_DISPLAY: Record<string, string> = {
  pcb: 'PCB Certification',
  nppes_setup: 'NPPES / NPI Setup',
  enrollment: 'PROMISe Enrollment',
  mco_contracting: 'MCO Contracting',
}

const STAGE_LABELS: Record<string, string> = {
  pcb: 'PCB',
  nppes_setup: 'NPPES',
  enrollment: 'Enrollment',
  mco_contracting: 'MCO',
}

const CRED_LABELS: Record<string, string> = {
  pcb: 'PCB Cert',
  promise: 'PROMISe™',
  caqh: 'CAQH',
  liability: 'Liability Ins.',
}

function stageBadge(status: string | null) {
  if (!status) return <span className="inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-medium bg-gray-100 text-gray-400">—</span>
  if (status === 'complete') return <span className="inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-medium bg-green-100 text-green-700">✓</span>
  if (status === 'in_progress') return <span className="inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-medium bg-yellow-100 text-yellow-700">…</span>
  return <span className="inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-medium bg-gray-100 text-gray-400">○</span>
}

function expiryChip(label: string, info: CredentialExpiry) {
  if (!info.expires_on) {
    return (
      <div key={label} className="flex flex-col">
        <span className="text-[10px] font-medium text-gray-400 uppercase tracking-wide">{label}</span>
        <span className="text-xs text-gray-400">Not recorded</span>
      </div>
    )
  }
  const d = info.days_remaining!
  const color = d < 0 ? 'text-red-600' : d < 30 ? 'text-red-500' : d < 60 ? 'text-amber-600' : 'text-green-700'
  const label2 = d < 0 ? `Expired ${Math.abs(d)}d ago` : `${d}d left`
  return (
    <div key={label} className="flex flex-col">
      <span className="text-[10px] font-medium text-gray-400 uppercase tracking-wide">{label}</span>
      <span className={`text-xs font-medium ${color}`}>{label2}</span>
      <span className="text-[10px] text-gray-400">{new Date(info.expires_on).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}</span>
    </div>
  )
}

function enrollmentReadyBadge(provider: Provider) {
  const stages = provider.enrollment_stages
  const allComplete = ['pcb', 'nppes_setup', 'enrollment', 'mco_contracting'].every(
    s => stages[s as keyof typeof stages] === 'complete'
  )
  const anyActive = ['pcb', 'nppes_setup', 'enrollment', 'mco_contracting'].some(
    s => stages[s as keyof typeof stages] === 'in_progress'
  )
  if (allComplete) return <span className="inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold bg-green-100 text-green-700">Ready to bill</span>
  if (anyActive) return <span className="inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold bg-yellow-100 text-yellow-700">In progress</span>
  return <span className="inline-flex rounded-full px-2 py-0.5 text-[10px] font-semibold bg-gray-100 text-gray-500">Not started</span>
}

export default function BillingAdminProvidersPage() {
  const api = process.env.NEXT_PUBLIC_API_URL
  const headers = { Authorization: `Bearer ${getAccessToken()}` }

  const [providers, setProviders] = useState<Provider[]>([])
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const [toast, setToast] = useState<string | null>(null)

  // Enrollment tier
  const [enrollmentTierEnabled, setEnrollmentTierEnabled] = useState(false)
  const [showGuide, setShowGuide] = useState(false)
  const [allServices, setAllServices] = useState<EnrollmentService[]>([])
  const [serviceDetails, setServiceDetails] = useState<Record<string, EnrollmentServiceDetail>>({})
  const [expandedService, setExpandedService] = useState<string | null>(null)
  const [taskSaving, setTaskSaving] = useState<string | null>(null)
  const [taskNotes, setTaskNotes] = useState<Record<string, string>>({})
  const [showStartService, setShowStartService] = useState<string | null>(null)
  const [startStage, setStartStage] = useState('pcb')
  const [startPathway, setStartPathway] = useState('education_training')
  const [startServiceLoading, setStartServiceLoading] = useState(false)

  const [inviteTab, setInviteTab] = useState<'manual' | 'csv'>('manual')
  const [rows, setRows] = useState<InviteRow[]>([{ ...EMPTY_ROW }])
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState<InviteResult | null>(null)
  const [csvRows, setCsvRows] = useState<CsvRow[]>([])
  const [csvShowGuide, setCsvShowGuide] = useState(false)
  const csvInputRef = useRef<HTMLInputElement>(null)

  const showToast = (msg: string) => {
    setToast(msg)
    setTimeout(() => setToast(null), 4000)
  }

  const loadProviders = async () => {
    setLoading(true)
    try {
      const [providersRes, settingsRes] = await Promise.all([
        axios.get<Provider[]>(`${api}/api/v1/billing-admin/providers`, { headers }),
        axios.get<{ enrollment_tier_enabled: boolean }>(`${api}/api/v1/billing-admin/agency-settings`, { headers }).catch(() => ({ data: { enrollment_tier_enabled: false } })),
      ])
      setProviders(providersRes.data)
      const tierEnabled = settingsRes.data.enrollment_tier_enabled ?? false
      setEnrollmentTierEnabled(tierEnabled)

      // Always fetch enrollment services — assigned services visible without enrollment tier
      const svcRes = await axios.get<EnrollmentService[]>(`${api}/api/v1/billing-admin/enrollment/services`, { headers }).catch(() => ({ data: [] as EnrollmentService[] }))
      setAllServices(svcRes.data)
      // Pre-load task details for services assigned to this agency by DoulaShield
      const assignedSvcs = svcRes.data.filter((s: EnrollmentService) => s.assigned_to_billing_admin)
      if (assignedSvcs.length > 0) {
        const detailResults = await Promise.all(
          assignedSvcs.map((s: EnrollmentService) =>
            axios.get<EnrollmentServiceDetail>(`${api}/api/v1/billing-admin/enrollment/services/${s.id}`, { headers }).catch(() => null)
          )
        )
        const preloaded: Record<string, EnrollmentServiceDetail> = {}
        const preloadedNotes: Record<string, string> = {}
        detailResults.forEach((res, i) => {
          if (res) {
            preloaded[assignedSvcs[i].id] = res.data
            res.data.tasks.forEach((t: EnrollmentTask) => { if (t.notes) preloadedNotes[t.id] = t.notes })
          }
        })
        setServiceDetails(preloaded)
        setTaskNotes(prev => ({ ...prev, ...preloadedNotes }))
      }
    } catch {
      showToast('Failed to load provider roster')
    } finally {
      setLoading(false)
    }
  }

  const loadServiceDetail = async (serviceId: string) => {
    if (serviceDetails[serviceId]) return
    try {
      const res = await axios.get<EnrollmentServiceDetail>(`${api}/api/v1/billing-admin/enrollment/services/${serviceId}`, { headers })
      setServiceDetails(prev => ({ ...prev, [serviceId]: res.data }))
      const notes: Record<string, string> = {}
      res.data.tasks.forEach(t => { if (t.notes) notes[t.id] = t.notes })
      setTaskNotes(prev => ({ ...prev, ...notes }))
    } catch {
      showToast('Failed to load service tasks')
    }
  }

  const toggleTask = async (task: EnrollmentTask) => {
    const next = task.status === 'complete' ? 'not_started' : 'complete'
    setTaskSaving(task.id)
    try {
      const res = await axios.patch<EnrollmentTask>(
        `${api}/api/v1/billing-admin/enrollment/tasks/${task.id}`,
        { status: next, notes: taskNotes[task.id] ?? null },
        { headers },
      )
      setServiceDetails(prev => {
        const detail = prev[task.service_id]
        if (!detail) return prev
        return { ...prev, [task.service_id]: { ...detail, tasks: detail.tasks.map(t => t.id === task.id ? res.data : t) } }
      })
    } catch (e: unknown) {
      if (axios.isAxiosError(e)) {
        const detail = e.response?.data?.detail
        const msg = typeof detail === 'string'
          ? detail
          : Array.isArray(detail)
          ? detail.map((d: { msg?: string }) => d.msg ?? String(d)).join('; ')
          : 'Failed to update task'
        showToast(msg)
      } else {
        showToast('Failed to update task')
      }
    } finally {
      setTaskSaving(null)
    }
  }

  const saveTaskNotes = async (task: EnrollmentTask) => {
    setTaskSaving(task.id)
    try {
      const res = await axios.patch<EnrollmentTask>(
        `${api}/api/v1/billing-admin/enrollment/tasks/${task.id}`,
        { notes: taskNotes[task.id] ?? '' },
        { headers },
      )
      setServiceDetails(prev => {
        const detail = prev[task.service_id]
        if (!detail) return prev
        return { ...prev, [task.service_id]: { ...detail, tasks: detail.tasks.map(t => t.id === task.id ? res.data : t) } }
      })
      showToast('Notes saved.')
    } catch {
      showToast('Failed to save notes')
    } finally {
      setTaskSaving(null)
    }
  }

  const taskDocsFor = (detail: EnrollmentServiceDetail, taskId: string) =>
    detail.documents.filter((d) => d.task_id === taskId)

  const downloadDocument = async (serviceId: string, docId: string, fileName: string) => {
    try {
      const res = await axios.get<{ url: string; file_name: string }>(
        `${api}/api/v1/billing-admin/enrollment/services/${serviceId}/documents/${docId}/url`,
        { headers },
      )
      const a = document.createElement('a')
      a.href = res.data.url
      a.download = fileName
      a.target = '_blank'
      a.rel = 'noopener'
      a.click()
    } catch {
      showToast('Failed to get download link')
    }
  }

  const handleDeleteDocument = async (serviceId: string, docId: string, fileName: string) => {
    if (!window.confirm(`Remove "${fileName}" from this task? This cannot be undone.`)) return
    try {
      await axios.delete(
        `${api}/api/v1/billing-admin/enrollment/services/${serviceId}/documents/${docId}`,
        { headers },
      )
      setServiceDetails((prev) => {
        const detail = prev[serviceId]
        if (!detail) return prev
        return { ...prev, [serviceId]: { ...detail, documents: detail.documents.filter((d) => d.id !== docId) } }
      })
      showToast(`${fileName} removed`)
    } catch {
      showToast('Failed to remove document')
    }
  }

  const startEnrollmentService = async (providerId: string) => {
    setStartServiceLoading(true)
    try {
      const res = await axios.post<EnrollmentServiceDetail>(
        `${api}/api/v1/billing-admin/enrollment/services`,
        { provider_id: providerId, stage: startStage, pcb_pathway: startStage === 'pcb' ? startPathway : null },
        { headers },
      )
      setAllServices(prev => [res.data.service, ...prev])
      setServiceDetails(prev => ({ ...prev, [res.data.service.id]: res.data }))
      setExpandedService(res.data.service.id)
      setShowStartService(null)
      showToast('Enrollment service started.')
    } catch (e: unknown) {
      if (axios.isAxiosError(e)) {
        const detail = e.response?.data?.detail
        const msg = typeof detail === 'string'
          ? detail
          : Array.isArray(detail)
          ? detail.map((d: { msg?: string }) => d.msg ?? String(d)).join('; ')
          : 'Failed to start service'
        showToast(msg)
      } else {
        showToast('Failed to start service')
      }
    } finally {
      setStartServiceLoading(false)
    }
  }

  useEffect(() => { loadProviders() }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const toggleExpand = (id: string) => {
    const isOpening = !expanded.has(id)
    setExpanded(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
    if (isOpening) {
      const assignedSvc = allServices.find(s => s.provider_id === id && s.assigned_to_billing_admin)
      if (assignedSvc) {
        setExpandedService(assignedSvc.id)
        loadServiceDetail(assignedSvc.id) // no-op if pre-loaded; fallback if pre-load failed
      }
    }
  }

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

  const handleCsvFile = (file: File) => {
    Papa.parse<Record<string, string>>(file, {
      header: true,
      skipEmptyLines: true,
      complete: (r) => setCsvRows(parseCsvRows(r.data)),
    })
  }

  const submitCsvInvites = async () => {
    const importable = csvRows.filter(r => r._errors.length === 0)
    if (!importable.length) return
    setSubmitting(true)
    setResult(null)
    try {
      const res = await axios.post<InviteResult>(
        `${api}/api/v1/billing-admin/roster/invite`,
        { providers: importable.map(({ _errors: _e, _warnings: _w, ...rest }) => rest) },
        { headers }
      )
      setResult(res.data)
      setCsvRows([])
      await loadProviders()
    } catch (e: unknown) {
      const msg = axios.isAxiosError(e) ? e.response?.data?.detail : 'Import failed'
      showToast(typeof msg === 'string' ? msg : 'Import failed')
    } finally {
      setSubmitting(false)
    }
  }

  const hasCredentialWarning = (p: Provider) =>
    Object.values(p.credentials).some(c => c.days_remaining !== null && c.days_remaining < 60)

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900">My Providers</h1>
          <p className="mt-0.5 text-sm text-gray-500">
            Provider roster, enrollment progress, and credential expiry reminders.
          </p>
        </div>
        <button
          onClick={() => setShowGuide(true)}
          className="rounded border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50 flex-shrink-0"
        >
          How It Works
        </button>
      </div>

      {/* Roster table */}
      <div>
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
            Roster — {providers.length} provider{providers.length !== 1 ? 's' : ''}
          </h2>
          {providers.length > 0 && (
            <span className="text-xs text-gray-400">Click a row to see enrollment & credential detail</span>
          )}
        </div>

        {loading ? (
          <p className="text-sm text-gray-400">Loading…</p>
        ) : providers.length === 0 ? (
          <div className="rounded-lg border border-dashed border-gray-300 py-8 text-center text-sm text-gray-500">
            No providers yet. Use the invite form below to add your first doula.
          </div>
        ) : (
          <div className="rounded-lg border border-gray-200 bg-white overflow-hidden">
            {providers.map((p, idx) => {
              const isOpen = expanded.has(p.id)
              const warn = hasCredentialWarning(p)
              return (
                <div key={p.id} className={idx > 0 ? 'border-t border-gray-100' : ''}>
                  {/* Summary row */}
                  <button
                    onClick={() => toggleExpand(p.id)}
                    className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-gray-50 transition-colors"
                  >
                    <span className="text-gray-400 text-xs w-3">{isOpen ? '▼' : '▶'}</span>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-sm font-medium text-gray-900">{p.full_name ?? '—'}</span>
                        {enrollmentReadyBadge(p)}
                        {warn && <span className="text-[10px] font-medium text-amber-600">⚠ credential expiring</span>}
                      </div>
                      <span className="text-xs text-gray-500">{p.email}{p.npi ? ` · NPI ${p.npi}` : ''}</span>
                    </div>

                    {/* Stage dots */}
                    <div className="hidden sm:flex items-center gap-1.5">
                      {Object.entries(STAGE_LABELS).map(([key, label]) => (
                        <div key={key} className="flex flex-col items-center gap-0.5">
                          {stageBadge(p.enrollment_stages[key as keyof typeof p.enrollment_stages])}
                          <span className="text-[9px] text-gray-400">{label}</span>
                        </div>
                      ))}
                    </div>
                  </button>

                  {/* Expanded detail */}
                  {isOpen && (
                    <div className="border-t border-gray-100 bg-gray-50 px-5 py-4 space-y-4">
                      {/* Enrollment stages */}
                      <div>
                        <p className="mb-2 text-xs font-semibold text-gray-500 uppercase tracking-wide">Credentialing Stages</p>
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                          {Object.entries(STAGE_LABELS).map(([key, label]) => {
                            const status = p.enrollment_stages[key as keyof typeof p.enrollment_stages]
                            const bg = status === 'complete'
                              ? 'border-green-200 bg-green-50'
                              : status === 'in_progress'
                              ? 'border-yellow-200 bg-yellow-50'
                              : 'border-gray-200 bg-white'
                            const text = status === 'complete'
                              ? 'text-green-700'
                              : status === 'in_progress'
                              ? 'text-yellow-700'
                              : 'text-gray-400'
                            const display = status === 'complete' ? 'Complete' : status === 'in_progress' ? 'In Progress' : status === 'not_started' ? 'Not Started' : 'Not Set Up'
                            return (
                              <div key={key} className={`rounded-md border p-2.5 ${bg}`}>
                                <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wide">{label}</p>
                                <p className={`text-xs font-medium mt-0.5 ${text}`}>{display}</p>
                              </div>
                            )
                          })}
                        </div>
                      </div>

                      {/* Credential expiry */}
                      <div>
                        <p className="mb-2 text-xs font-semibold text-gray-500 uppercase tracking-wide">Credential Expiry</p>
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                          {Object.entries(CRED_LABELS).map(([key, label]) =>
                            expiryChip(label, p.credentials[key as keyof typeof p.credentials])
                          )}
                        </div>
                      </div>

                      {/* Deposit status */}
                      {!p.deposit_paid && (
                        <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2.5 py-1.5">
                          Deposit not yet paid — provider cannot be billed until the $99 deposit is collected.
                        </p>
                      )}

                      {/* Enrollment services — assigned services always visible; Start Service requires enrollment tier */}
                      <div>
                        <div className="mb-2 flex items-center justify-between">
                          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Enrollment Services</p>
                          {enrollmentTierEnabled && (
                            <button
                              onClick={() => { setShowStartService(showStartService === p.id ? null : p.id); setStartStage('pcb'); setStartPathway('education_training') }}
                              className="text-xs text-indigo-600 hover:underline"
                            >
                              + Start Service
                            </button>
                          )}
                        </div>

                        {enrollmentTierEnabled && showStartService === p.id && (
                          <div className="mb-3 rounded-md border border-indigo-200 bg-indigo-50 p-3 space-y-2">
                            <p className="text-xs font-medium text-indigo-800">New Enrollment Service</p>
                            <div className="flex gap-2 flex-wrap">
                              <select value={startStage} onChange={e => setStartStage(e.target.value)}
                                className="rounded border border-gray-200 px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-indigo-400">
                                <option value="pcb">PCB Certification</option>
                                <option value="nppes_setup">NPPES / NPI Setup</option>
                                <option value="enrollment">PROMISe Enrollment</option>
                                <option value="mco_contracting">MCO Contracting</option>
                              </select>
                              {startStage === 'pcb' && (
                                <select value={startPathway} onChange={e => setStartPathway(e.target.value)}
                                  className="rounded border border-gray-200 px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-indigo-400">
                                  <option value="education_training">Education &amp; Training Pathway</option>
                                  <option value="experienced">Experienced Pathway</option>
                                </select>
                              )}
                            </div>
                            <div className="flex gap-2">
                              <button onClick={() => startEnrollmentService(p.id)} disabled={startServiceLoading}
                                className="rounded bg-indigo-600 px-3 py-1 text-xs font-medium text-white hover:bg-indigo-700 disabled:opacity-50">
                                {startServiceLoading ? 'Starting…' : 'Start'}
                              </button>
                              <button onClick={() => setShowStartService(null)} className="text-xs text-gray-500 hover:text-gray-700">Cancel</button>
                            </div>
                          </div>
                        )}

                        {(() => {
                            const providerServices = allServices.filter(s => s.provider_id === p.id)
                            if (providerServices.length === 0) {
                              return <p className="text-xs text-gray-400">No enrollment services yet.</p>
                            }
                            return (
                              <div className="space-y-2">
                                {providerServices.map(svc => {
                                  const isExpanded = expandedService === svc.id
                                  const detail = serviceDetails[svc.id]
                                  const statusColor = svc.status === 'complete'
                                    ? 'text-green-600 bg-green-50 border-green-200'
                                    : svc.status === 'in_progress'
                                    ? 'text-yellow-700 bg-yellow-50 border-yellow-200'
                                    : 'text-gray-500 bg-gray-50 border-gray-200'
                                  return (
                                    <div key={svc.id} className="rounded-md border border-gray-200 bg-white overflow-hidden">
                                      <button
                                        onClick={() => {
                                          if (!isExpanded) loadServiceDetail(svc.id)
                                          setExpandedService(isExpanded ? null : svc.id)
                                        }}
                                        className="w-full flex items-center justify-between px-3 py-2 text-left hover:bg-gray-50"
                                      >
                                        <div className="flex items-center gap-2">
                                          <span className="text-gray-400 text-[10px]">{isExpanded ? '▼' : '▶'}</span>
                                          <span className="text-xs font-medium text-gray-800">{STAGE_DISPLAY[svc.stage] ?? svc.stage}</span>
                                          {svc.pcb_pathway && (
                                            <span className="text-[10px] text-gray-500">
                                              ({svc.pcb_pathway === 'education_training' ? 'Educ. & Training' : 'Experienced'})
                                            </span>
                                          )}
                                          {svc.assigned_to_billing_admin && (
                                            <span className="inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-medium bg-indigo-50 text-indigo-600 border border-indigo-200">
                                              Assigned by DoulaShield
                                            </span>
                                          )}
                                        </div>
                                        <span className={`inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-medium border ${statusColor}`}>
                                          {svc.status === 'complete' ? 'Complete' : svc.status === 'in_progress' ? 'In Progress' : svc.status}
                                        </span>
                                      </button>
                                      {isExpanded && (
                                        <div className="border-t border-gray-100 px-3 py-2">
                                          {!detail ? (
                                            <p className="text-xs text-gray-400">Loading tasks…</p>
                                          ) : detail.tasks.length === 0 ? (
                                            <p className="text-xs text-gray-400">No tasks.</p>
                                          ) : (
                                            <div className="space-y-2">
                                              {detail.tasks.map(task => {
                                                const isComplete = task.status === 'complete'
                                                return (
                                                  <div key={task.id} className={`rounded border p-2 ${isComplete ? 'border-green-100 bg-green-50' : 'border-gray-100 bg-white'}`}>
                                                    <div className="flex items-start gap-2">
                                                      <button
                                                        onClick={() => toggleTask(task)}
                                                        disabled={taskSaving === task.id}
                                                        className={`mt-0.5 flex-shrink-0 h-4 w-4 rounded border flex items-center justify-center text-[10px] transition-colors disabled:opacity-50 ${isComplete ? 'bg-green-500 border-green-500 text-white' : 'border-gray-300 bg-white hover:border-green-400'}`}
                                                      >
                                                        {isComplete && '✓'}
                                                      </button>
                                                      <div className="flex-1 min-w-0">
                                                        <p className={`text-xs font-medium ${isComplete ? 'text-green-700 line-through' : 'text-gray-800'}`}>{task.label}</p>
                                                        {task.description && !isComplete && (
                                                          <p className="mt-0.5 text-[11px] text-gray-500 leading-relaxed">{task.description}</p>
                                                        )}
                                                        {!isComplete && (
                                                          <div className="mt-1 flex gap-1">
                                                            <input
                                                              type="text"
                                                              placeholder="Notes…"
                                                              value={taskNotes[task.id] ?? ''}
                                                              onChange={e => setTaskNotes(prev => ({ ...prev, [task.id]: e.target.value }))}
                                                              className="flex-1 rounded border border-gray-200 px-1.5 py-0.5 text-[11px] focus:outline-none focus:ring-1 focus:ring-blue-400"
                                                            />
                                                            <button
                                                              onClick={() => saveTaskNotes(task)}
                                                              disabled={taskSaving === task.id}
                                                              className="rounded border border-gray-200 px-1.5 py-0.5 text-[10px] text-gray-600 hover:bg-gray-50 disabled:opacity-50"
                                                            >
                                                              Save
                                                            </button>
                                                          </div>
                                                        )}
                                                        {isComplete && task.notes && (
                                                          <p className="mt-0.5 text-[11px] text-gray-500">Note: {task.notes}</p>
                                                        )}
                                                        {(() => {
                                                          const docs = taskDocsFor(detail, task.id)
                                                          return docs.length > 0 ? (
                                                            <div className="mt-1.5 space-y-1">
                                                              {docs.map((doc) => (
                                                                <div key={doc.id} className="flex items-center gap-2 text-[11px] text-gray-600">
                                                                  <span className="text-gray-400">📎</span>
                                                                  <button
                                                                    onClick={() => downloadDocument(svc.id, doc.id, doc.file_name)}
                                                                    className="text-blue-600 hover:underline text-left"
                                                                    title="Download document"
                                                                  >
                                                                    {doc.file_name}
                                                                  </button>
                                                                  <button
                                                                    onClick={() => handleDeleteDocument(svc.id, doc.id, doc.file_name)}
                                                                    title="Remove document"
                                                                    className="ml-auto rounded px-1.5 py-0.5 text-[10px] font-medium text-red-400 hover:bg-red-50 hover:text-red-600 border border-red-200 hover:border-red-400"
                                                                  >
                                                                    Remove
                                                                  </button>
                                                                </div>
                                                              ))}
                                                            </div>
                                                          ) : null
                                                        })()}
                                                      </div>
                                                    </div>
                                                  </div>
                                                )
                                              })}
                                            </div>
                                          )}
                                        </div>
                                      )}
                                    </div>
                                  )
                                })}
                              </div>
                            )
                        })()}
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Invite / Import form */}
      <div className="rounded-lg border border-gray-200 bg-white p-5">
        <h2 className="mb-1 text-sm font-semibold text-gray-900">Invite New Providers</h2>
        <p className="mb-3 text-xs text-gray-500">
          Each provider receives a welcome email with login credentials.
          Providers already in the system are skipped automatically.
        </p>

        {result ? (
          <div className="space-y-3">
            {result.created.length > 0 && (
              <div className="rounded-md border border-green-200 bg-green-50 p-3">
                <p className="mb-1 text-xs font-semibold text-green-800">{result.created.length} provider(s) added</p>
                {result.created.map((c, i) => <p key={i} className="text-xs text-green-700">{c.name} — {c.email}</p>)}
              </div>
            )}
            {result.skipped.length > 0 && (
              <div className="rounded-md border border-amber-200 bg-amber-50 p-3">
                <p className="mb-1 text-xs font-semibold text-amber-800">{result.skipped.length} skipped</p>
                {result.skipped.map((s, i) => <p key={i} className="text-xs text-amber-700">{s.name || s.email} — {s.reason}</p>)}
              </div>
            )}
            <button onClick={() => { setResult(null); setCsvRows([]) }} className="text-xs text-blue-600 hover:underline">
              Invite more providers →
            </button>
          </div>
        ) : (
          <>
            {/* Tab switcher */}
            <div className="mb-4 flex gap-1 rounded-lg bg-gray-100 p-1 w-fit">
              {(['manual', 'csv'] as const).map(tab => (
                <button key={tab} onClick={() => setInviteTab(tab)}
                  className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${inviteTab === tab ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}>
                  {tab === 'manual' ? 'Enter Manually' : 'Upload CSV'}
                </button>
              ))}
            </div>

            {inviteTab === 'manual' ? (
              <>
                <div className="space-y-2">
                  <div className="grid grid-cols-[1fr_1fr_140px_28px] gap-2 text-xs font-medium text-gray-500 uppercase tracking-wide pb-1 border-b border-gray-100">
                    <span>Full Name</span><span>Email Address</span><span>Doula Type</span><span />
                  </div>
                  {rows.map((row, idx) => (
                    <div key={idx} className="grid grid-cols-[1fr_1fr_140px_28px] gap-2 items-center">
                      <input type="text" placeholder="Full name" value={row.name}
                        onChange={e => updateRow(idx, 'name', e.target.value)}
                        className="rounded border border-gray-200 px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500" />
                      <input type="email" placeholder="Email address" value={row.email}
                        onChange={e => updateRow(idx, 'email', e.target.value)}
                        className="rounded border border-gray-200 px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500" />
                      <select value={row.doula_type} onChange={e => updateRow(idx, 'doula_type', e.target.value)}
                        className="rounded border border-gray-200 px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500">
                        {DOULA_TYPES.map(t => <option key={t}>{t}</option>)}
                      </select>
                      <button onClick={() => removeRow(idx)} disabled={rows.length === 1}
                        className="text-gray-400 hover:text-red-500 disabled:opacity-20 text-xl leading-none">×</button>
                    </div>
                  ))}
                </div>
                <div className="mt-3 flex items-center justify-between">
                  <button onClick={addRow} className="text-xs text-blue-600 hover:underline">+ Add another provider</button>
                  <button onClick={handleSubmit} disabled={submitting || validRows.length === 0}
                    className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50">
                    {submitting ? 'Sending…' : `Send ${validRows.length} Invite${validRows.length !== 1 ? 's' : ''}`}
                  </button>
                </div>
              </>
            ) : (
              <>
                {/* Column guide */}
                <div className="mb-3">
                  <button onClick={() => setCsvShowGuide(g => !g)} className="text-xs text-blue-600 hover:underline">
                    {csvShowGuide ? '▲ Hide column guide' : '▼ Show column guide & valid values'}
                  </button>
                  {csvShowGuide && (
                    <div className="mt-2 rounded-md border border-gray-200 bg-gray-50 p-3 text-xs space-y-2">
                      <p className="font-medium text-gray-700">CSV columns (first row must be a header):</p>
                      <table className="w-full text-xs">
                        <thead><tr className="text-gray-500"><th className="text-left pr-3 pb-1">Column</th><th className="text-left pb-1">Notes</th></tr></thead>
                        <tbody className="text-gray-700">
                          <tr><td className="pr-3 font-mono py-0.5">name</td><td>Required. Provider full name.</td></tr>
                          <tr><td className="pr-3 font-mono py-0.5">email</td><td>Required. Must be unique.</td></tr>
                          <tr><td className="pr-3 font-mono py-0.5">npi</td><td>Optional. 10-digit NPI number.</td></tr>
                          <tr><td className="pr-3 font-mono py-0.5">doula_type</td><td>Optional. See valid values below.</td></tr>
                          <tr><td className="pr-3 font-mono py-0.5">mco_1 … mco_9</td><td>Optional. MCO name — see list below.</td></tr>
                          <tr><td className="pr-3 font-mono py-0.5">mco_1_date … mco_9_date</td><td>Optional. Contract date YYYY-MM-DD.</td></tr>
                        </tbody>
                      </table>
                      <div className="grid grid-cols-2 gap-2 pt-1">
                        <div>
                          <p className="font-medium text-gray-600 mb-1">Doula types</p>
                          {DOULA_TYPES.map(t => <p key={t} className="font-mono text-gray-700">{t}</p>)}
                        </div>
                        <div>
                          <p className="font-medium text-gray-600 mb-1">MCO names</p>
                          {ALL_MCOS.map(m => <p key={m} className="font-mono text-gray-700">{m}</p>)}
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {csvRows.length === 0 ? (
                  <div className="flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-gray-300 bg-gray-50 py-8 cursor-pointer hover:border-indigo-400 hover:bg-indigo-50 transition-colors"
                    onClick={() => csvInputRef.current?.click()}
                    onDragOver={e => e.preventDefault()}
                    onDrop={e => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f) handleCsvFile(f) }}>
                    <p className="text-sm font-medium text-gray-700">Drop CSV here or click to browse</p>
                    <p className="mt-1 text-xs text-gray-400">One provider per row · .csv files only</p>
                    <input ref={csvInputRef} type="file" accept=".csv" className="hidden"
                      onChange={e => { const f = e.target.files?.[0]; if (f) handleCsvFile(f) }} />
                    <button onClick={e => { e.stopPropagation(); downloadTemplate() }}
                      className="mt-3 text-xs text-indigo-600 hover:underline">Download template CSV →</button>
                  </div>
                ) : (
                  <>
                    <div className="max-h-60 overflow-y-auto rounded border border-gray-200 text-xs">
                      <table className="min-w-full">
                        <thead className="bg-gray-50 sticky top-0">
                          <tr className="text-gray-500 text-left">
                            <th className="px-2 py-1.5">Name</th><th className="px-2 py-1.5">Email</th>
                            <th className="px-2 py-1.5">NPI</th><th className="px-2 py-1.5">Type</th>
                            <th className="px-2 py-1.5">MCOs</th><th className="px-2 py-1.5">Status</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                          {csvRows.map((row, i) => (
                            <tr key={i} className={row._errors.length ? 'bg-red-50' : row._warnings.length ? 'bg-amber-50' : ''}>
                              <td className="px-2 py-1.5">{row.name || <span className="text-red-400">—</span>}</td>
                              <td className="px-2 py-1.5">{row.email || <span className="text-red-400">—</span>}</td>
                              <td className="px-2 py-1.5 font-mono">{row.npi || <span className="text-gray-300">—</span>}</td>
                              <td className="px-2 py-1.5">{row.doula_type}</td>
                              <td className="px-2 py-1.5">{row.mco_contracts?.map(c => c.mco).join(', ') || <span className="text-gray-300">—</span>}</td>
                              <td className="px-2 py-1.5">
                                {row._errors.length ? <span className="text-red-600" title={row._errors.join('; ')}>✗ {row._errors[0]}</span>
                                  : row._warnings.length ? <span className="text-amber-600" title={row._warnings.join('; ')}>⚠ {row._warnings[0]}</span>
                                  : <span className="text-green-600">✓</span>}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    <div className="mt-2 flex items-center gap-3 text-xs text-gray-500">
                      <span>{csvRows.filter(r => r._errors.length === 0).length} importable</span>
                      {csvRows.some(r => r._errors.length > 0) && <span className="text-red-500">{csvRows.filter(r => r._errors.length > 0).length} with errors (skipped)</span>}
                      {csvRows.some(r => r._warnings.length > 0 && r._errors.length === 0) && <span className="text-amber-500">{csvRows.filter(r => r._warnings.length > 0 && r._errors.length === 0).length} with warnings</span>}
                      <button onClick={() => { setCsvRows([]); if (csvInputRef.current) csvInputRef.current.value = '' }}
                        className="ml-auto text-gray-400 hover:text-gray-600">Choose different file</button>
                    </div>
                    <div className="mt-4 flex justify-end">
                      <button onClick={submitCsvInvites}
                        disabled={submitting || csvRows.filter(r => r._errors.length === 0).length === 0}
                        className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50">
                        {submitting ? 'Importing…' : `Import ${csvRows.filter(r => r._errors.length === 0).length} Provider(s)`}
                      </button>
                    </div>
                  </>
                )}
              </>
            )}
          </>
        )}
      </div>

      {toast && (
        <div className="fixed bottom-6 right-6 z-50 rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm font-medium text-green-800 shadow-lg">
          {toast}
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
                <h2 className="text-base font-semibold text-gray-900">My Providers — How It Works</h2>
                <p className="text-xs text-gray-500 mt-0.5">Manage your agency's doula roster, credentialing tasks, and document access.</p>
              </div>
              <button onClick={() => setShowGuide(false)} className="text-gray-400 hover:text-gray-600 text-xl leading-none ml-6 mt-0.5">×</button>
            </div>
            <div className="px-6 py-5 space-y-6">
              <div className="rounded-lg border border-blue-100 bg-blue-50 p-4">
                <h3 className="text-sm font-semibold text-blue-800 mb-2">Your Roster</h3>
                <ul className="space-y-1 text-xs text-blue-700 list-disc list-inside">
                  <li>Lists all doula providers assigned to your agency</li>
                  <li>Click any provider row to expand their credentials, enrollment progress, and tasks</li>
                  <li>Credential chips (NPI, CAQH, PROMISe™, PCB, liability) show expiry status — amber = expiring soon, red = expired</li>
                </ul>
              </div>
              <div className="rounded-lg border border-purple-100 bg-purple-50 p-4">
                <h3 className="text-sm font-semibold text-purple-800 mb-2">Enrollment Tier</h3>
                <ul className="space-y-1 text-xs text-purple-700 list-disc list-inside">
                  <li>If enabled by DoulaShield admin, you can manage credentialing tasks directly from this page</li>
                  <li>Enrollment services appear under each provider row when a stage has been started</li>
                  <li>If the enrollment tier is not yet enabled for your agency, contact DoulaShield admin</li>
                </ul>
              </div>
              <div className="rounded-lg border border-amber-100 bg-amber-50 p-4">
                <h3 className="text-sm font-semibold text-amber-800 mb-2">Assigned by DoulaShield</h3>
                <ul className="space-y-1 text-xs text-amber-700 list-disc list-inside">
                  <li>When DoulaShield assigns a specific enrollment service to your agency, it is badged <strong>"Assigned by DoulaShield"</strong></li>
                  <li>Opening that provider's row automatically expands the assigned service's task list — no extra clicks needed</li>
                  <li>You can still manually expand other services for that provider</li>
                </ul>
              </div>
              <div className="rounded-lg border border-green-100 bg-green-50 p-4">
                <h3 className="text-sm font-semibold text-green-800 mb-2">Task Management</h3>
                <ol className="space-y-1 text-xs text-green-700 list-decimal list-inside">
                  <li>Expand a provider row, then click the enrollment service to see its tasks</li>
                  <li>Check the checkbox on each task to mark it complete (or uncheck to revert)</li>
                  <li>Add notes to any task — ATN numbers, CAQH IDs, submission dates, confirmation codes</li>
                  <li>Click <strong>Save</strong> next to the notes field; notes are visible to DoulaShield admin</li>
                </ol>
              </div>
              <div className="rounded-lg border border-gray-100 bg-gray-50 p-4">
                <h3 className="text-sm font-semibold text-gray-800 mb-2">Document Access</h3>
                <ul className="space-y-1 text-xs text-gray-700 list-disc list-inside">
                  <li>Documents uploaded by the provider appear as clickable download links on each task card</li>
                  <li>Click the file name to download — useful for re-uploading into CMS, CAQH, or PROMISe™ portals</li>
                  <li>Click <strong>Remove</strong> to delete a wrongly uploaded file (confirmation required, action is permanent)</li>
                </ul>
              </div>
              <div className="rounded-lg border border-teal-100 bg-teal-50 p-4">
                <h3 className="text-sm font-semibold text-teal-800 mb-2">Inviting New Providers & Billing</h3>
                <ul className="space-y-1 text-xs text-teal-700 list-disc list-inside">
                  <li>Use <strong>Invite New Providers</strong> at the bottom of the page to add providers manually or via CSV upload</li>
                  <li>New providers receive a welcome email and deposit link automatically</li>
                  <li>Seat count in your Stripe subscription updates automatically as providers are added or removed</li>
                  <li>Minimum 3 seats are always billed regardless of current roster size</li>
                </ul>
              </div>
              <div className="rounded-lg bg-gray-50 border border-gray-200 p-4">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-3">Key Rules & Reminders</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs text-gray-700">
                  <div><strong>Task completion:</strong> Only your agency and DoulaShield admin can mark tasks complete — providers cannot mark their own tasks.</div>
                  <div><strong>Document removal is permanent:</strong> Removed files are deleted from storage and cannot be recovered — the provider must re-upload.</div>
                  <div><strong>Credential expiry:</strong> CAQH re-attestation is due every 120 days; PROMISe™ re-enrollment every 5 years — reminders are sent by DoulaShield automatically.</div>
                  <div><strong>CSV import:</strong> The CSV Upload tab in the invite form pre-populates each provider's NPI, billing provider name, and MCO contracts on first login.</div>
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
