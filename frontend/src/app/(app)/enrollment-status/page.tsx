'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import axios from 'axios'
import { getAccessToken } from '@/lib/auth'
import { useAuthStore } from '@/store/auth-store'

interface EnrollmentTask {
  id: string
  service_id: string
  task_key: string
  required_pathway: string
  label: string
  description: string | null
  status: 'not_started' | 'in_progress' | 'complete'
  task_data: Record<string, unknown> | null
  notes: string | null
  sort_order: number
  completed_at: string | null
  created_at: string
}

interface EnrollmentDocument {
  id: string
  service_id: string
  task_id: string | null
  uploaded_by: string | null
  file_name: string
  document_type: string | null
  created_at: string
}

interface EnrollmentService {
  id: string
  stage: string
  status: string
  pcb_pathway: string | null
  intake_data: Record<string, unknown> | null
  pcb_cert_date: string | null
  created_at: string
}

interface EnrollmentServiceDetail {
  service: EnrollmentService
  tasks: EnrollmentTask[]
  documents: EnrollmentDocument[]
}

const STAGE_ORDER = ['pcb', 'nppes_setup', 'enrollment', 'mco_contracting']

const STAGE_TABS: { key: string; label: string }[] = [
  { key: 'pcb', label: 'PCB Certification' },
  { key: 'nppes_setup', label: 'NPPES / NPI Setup' },
  { key: 'enrollment', label: 'Enrollment — Stage 2' },
  { key: 'mco_contracting', label: 'MCO Contracting — Stage 3' },
]

const STATUS_COLORS: Record<string, string> = {
  not_started: 'bg-gray-100 text-gray-500',
  in_progress: 'bg-yellow-100 text-yellow-700',
  complete: 'bg-green-100 text-green-700',
}

const SERVICE_STATUS_COLORS: Record<string, string> = {
  in_progress: 'bg-blue-100 text-blue-700',
  submitted: 'bg-yellow-100 text-yellow-700',
  complete: 'bg-green-100 text-green-700',
  cancelled: 'bg-gray-100 text-gray-500',
}

const TASK_DOWNLOAD_LINKS: Record<string, { label: string; href: string }> = {
  pcb_client_eval_1: { label: 'Download PCB Client Evaluation Form', href: '/docs/pcb-client-evaluation.pdf' },
  pcb_client_eval_2: { label: 'Download PCB Client Evaluation Form', href: '/docs/pcb-client-evaluation.pdf' },
  pcb_client_eval_3: { label: 'Download PCB Client Evaluation Form', href: '/docs/pcb-client-evaluation.pdf' },
  pcb_ref_letter_1: { label: 'Download Recommendation Letter Template', href: '/docs/pcb-recommendation-letter-template.pdf' },
  pcb_ref_letter_2: { label: 'Download Recommendation Letter Template', href: '/docs/pcb-recommendation-letter-template.pdf' },
  pcb_ref_letter_3: { label: 'Download Recommendation Letter Template', href: '/docs/pcb-recommendation-letter-template.pdf' },
}

const AGREEMENT_SECTIONS = [
  {
    title: '1. Appointment of Agent and Surrogate Authority',
    body: `By executing this Agreement and opting into the Managed Registration Service, the Provider (hereafter referred to as "Provider," "User," or "Doula") explicitly appoints DoulaShield (hereafter referred to as the "Agency") as their authorized administrative delegate and surrogate clerk for the limited purpose of obtaining, managing, and maintaining professional healthcare identifiers and credentials.

This appointment grants the Agency explicit authority to act on the Provider's behalf within the following federal and state systems:

• The National Plan and Provider Enumeration System (NPPES)
• The Centers for Medicare & Medicaid Services (CMS) Identity & Access Management (I&A) System
• The Council for Affordable Quality Healthcare (CAQH) ProView® platform
• The Pennsylvania Department of Human Services PROMISe™ enrollment portal`,
  },
  {
    title: '2. Scope of Authorized Actions',
    body: `The Provider authorizes the Agency and its designated personnel to perform the following administrative actions in the Provider's name:

• Establish, register, and configure user accounts and profiles within the NPPES, I&A, and CAQH systems.
• Select and apply the appropriate healthcare taxonomy codes, including but not limited to Taxonomy Code 374J00000X (Doula).
• Submit applications for a National Provider Identifier (NPI Type 1) number using the personal data submitted by the Provider to the Agency's onboarding portal.
• Electronically sign administrative forms, attestations, and compliance renewals solely required for credentialing, NPI generation, and network enrollment pathways.`,
  },
  {
    title: '3. Provider Attestation and Data Accuracy',
    body: `The Provider acknowledges and agrees that they are legally responsible for the validity, truthfulness, and accuracy of all personal information, identification numbers, tax documents, and certifications uploaded or inputted into the Agency's portal. The Provider understands that the Agency relies entirely on this data to file federal and state applications. Any intentional misrepresentation, omission, or fraudulent data provided by the Provider may constitute a violation of federal law under 18 U.S.C. § 1001 and will result in the immediate termination of this Agreement.`,
  },
  {
    title: '4. Privacy and Security of Sensitive Information',
    body: `The Agency agrees to process, store, and transmit all highly sensitive personal information—including Social Security Numbers (SSN), Employer Identification Numbers (EIN), and government-issued identification—in strict compliance with industry-standard data protection protocols. The Agency shall use this information solely for the credentialing and registration purposes authorized in Section 2 and will never sell, distribute, or disclose this data to unauthorized third parties.`,
  },
  {
    title: '5. Limitation of Liability and Indemnification',
    body: `The Provider agrees to indemnify, defend, and hold harmless the Agency, its officers, employees, and tech platforms from any claims, regulatory penalties, loss of income, claim rejections, or liabilities arising out of:

• Delays or rejections by federal or state agencies (including NPPES or CMS) in issuing numbers or credentials.
• Errors or processing backlogs within external insurance networks or Managed Care Organizations (MCOs).
• Inaccuracies in documentation provided by the User that cause structural compliance delays.`,
  },
  {
    title: '6. Revocation of Authority',
    body: `This administrative surrogate authorization shall remain active and in full force until the Provider's onboarding pipeline is complete, or until either party terminates the business relationship. The Provider retains the absolute right to revoke this proxy at any time by submitting a formal written request via email to support@doulashield.com. Upon receipt of a revocation notice, the Agency will cease all surrogate activity within 48 business hours and hand over all primary credentials to the Provider.`,
  },
]

function AgreementGate({ onSigned }: { onSigned: () => void }) {
  const [agreed, setAgreed] = useState(false)
  const [signing, setSigning] = useState(false)
  const api = process.env.NEXT_PUBLIC_API_URL
  const headers = { Authorization: `Bearer ${getAccessToken()}` }

  const handleSign = async () => {
    setSigning(true)
    try {
      await axios.post(`${api}/api/v1/enrollment/me/sign-agreement`, {}, { headers })
      onSigned()
    } catch {
      // if it fails (e.g. already signed), still proceed
      onSigned()
    } finally {
      setSigning(false)
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-gray-900">Authorization Agreement Required</h1>
        <p className="mt-1 text-sm text-gray-500">
          Before accessing your credentialing services, please read and sign the following
          Authorized Delegate and NPI Surrogate Authorization Agreement.
        </p>
      </div>

      <div className="rounded-lg border border-gray-200 bg-white">
        <div className="border-b border-gray-200 px-6 py-4">
          <h2 className="text-sm font-semibold text-gray-900 uppercase tracking-wide">
            Authorized Delegate and NPI Surrogate Authorization Agreement
          </h2>
          <p className="mt-1 text-xs text-gray-500">
            Between DoulaShield ("Agency") and the undersigned Provider ("You")
          </p>
        </div>

        <div className="max-h-[56vh] overflow-y-auto px-6 py-5 space-y-5">
          {AGREEMENT_SECTIONS.map((section) => (
            <div key={section.title}>
              <p className="text-xs font-semibold text-gray-800 mb-1.5">{section.title}</p>
              <p className="text-xs text-gray-600 leading-relaxed whitespace-pre-line">
                {section.body}
              </p>
            </div>
          ))}
        </div>

        <div className="border-t border-gray-200 px-6 py-5 space-y-4 bg-gray-50 rounded-b-lg">
          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={agreed}
              onChange={(e) => setAgreed(e.target.checked)}
              className="mt-0.5 h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span className="text-sm text-gray-700 leading-snug">
              I have read, understood, and agree to the terms of this Authorized Delegate and NPI
              Surrogate Authorization Agreement. I authorize DoulaShield to act as my administrative
              delegate for the purposes described above.
            </span>
          </label>

          <button
            onClick={handleSign}
            disabled={!agreed || signing}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            {signing ? (
              <>
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                Signing…
              </>
            ) : (
              'Sign & Continue'
            )}
          </button>
          <p className="text-xs text-gray-400">
            Your electronic signature and the date/time will be recorded securely.
          </p>
        </div>
      </div>
    </div>
  )
}

const PCB_FORM_FIELDS = [
  { key: 'legal_name', label: 'Full Legal Name (as it should appear on PCB certificate)', type: 'text', placeholder: 'Your name exactly as on certificate', colSpan: 2 },
  { key: 'phone', label: 'Phone', type: 'tel', placeholder: '', colSpan: 1 },
  { key: 'email', label: 'Email', type: 'email', placeholder: '', colSpan: 1 },
  { key: 'address_street', label: 'Street Address', type: 'text', placeholder: '', colSpan: 2 },
  { key: 'address_city', label: 'City', type: 'text', placeholder: '', colSpan: 1 },
] as const

interface SensitiveProfile {
  has_ssn: boolean
  ssn_last4: string | null
  has_dob: boolean
  dob: string | null
  has_tax_id: boolean
}

interface WorkHistoryRow {
  start_date: string
  end_date: string
  employer_name: string
  address: string
  job_title: string
  duties: string
}

interface GapEntry {
  start_date: string
  end_date: string
  duration_days: number
  explanation: string
}

const GENDER_OPTIONS = ['Female', 'Male', 'Non-binary / Gender non-conforming', 'Transgender female', 'Transgender male', 'Prefer not to say', 'Not listed']
const RACE_OPTIONS = ['American Indian or Alaska Native', 'Asian', 'Black or African American', 'Hispanic or Latino', 'Native Hawaiian or Other Pacific Islander', 'White', 'Two or more races', 'Prefer not to say']
const DOULA_TYPE_OPTIONS = ['Birth Doula', 'Postpartum Doula', 'Perinatal Doula', 'Other']

export default function EnrollmentStatusPage() {
  const router = useRouter()
  const { user } = useAuthStore()
  const [services, setServices] = useState<EnrollmentServiceDetail[]>([])
  const [loading, setLoading] = useState(true)
  const [activeStage, setActiveStage] = useState<string>('pcb')
  const [uploadingTask, setUploadingTask] = useState<{ serviceId: string; taskId: string } | null>(null)
  const [openingDoc, setOpeningDoc] = useState<string | null>(null)
  const [toast, setToast] = useState<string | null>(null)
  const [agreementStatus, setAgreementStatus] = useState<'loading' | 'unsigned' | 'signed'>('loading')
  const [agreementSignedAt, setAgreementSignedAt] = useState<string | null>(null)
  const [pcbForm, setPcbForm] = useState<Record<string, string>>({})
  const [pcbFormSaving, setPcbFormSaving] = useState(false)
  const [pcbFormSaved, setPcbFormSaved] = useState(false)
  const [downloadingPrefill, setDownloadingPrefill] = useState(false)
  const [sensitiveProfile, setSensitiveProfile] = useState<SensitiveProfile | null>(null)
  const [sensitiveForm, setSensitiveForm] = useState<{ ssn: string; dob: string; tax_id: string }>({ ssn: '', dob: '', tax_id: '' })
  const [sensitiveFormSaving, setSensitiveFormSaving] = useState(false)
  const [sensitiveFormSaved, setSensitiveFormSaved] = useState(false)
  const [showGuide, setShowGuide] = useState(false)
  const [bioInput, setBioInput] = useState<Record<string, string>>({})
  const [bioBuilding, setBioBuilding] = useState<Record<string, boolean>>({})
  const [bioResult, setBioResult] = useState<Record<string, { rows: WorkHistoryRow[]; gaps: GapEntry[] }>>({})
  const [showBioPrep, setShowBioPrep] = useState<Record<string, boolean>>({})

  const headers = { Authorization: `Bearer ${getAccessToken()}` }
  const api = process.env.NEXT_PUBLIC_API_URL

  const showToast = (msg: string) => {
    setToast(msg)
    setTimeout(() => setToast(null), 4000)
  }

  useEffect(() => {
    if (user && user.role !== 'provider' && user.role !== 'admin') {
      router.replace('/dashboard')
      return
    }
    // Admins skip the agreement gate
    if (user?.role === 'admin') {
      setAgreementStatus('signed')
      loadServices()
      return
    }
    checkAgreement()
  }, [user]) // eslint-disable-line react-hooks/exhaustive-deps

  // Sync PCB form data from task_data when the active PCB service changes
  useEffect(() => {
    const pcbDetail = services.find((d) => d.service.stage === 'pcb' && d.service.stage === activeStage)
    if (!pcbDetail) return
    const appFormTask = pcbDetail.tasks.find((t) => t.task_key === 'pcb_application_form')
    if (appFormTask?.task_data) {
      setPcbForm(
        Object.fromEntries(
          Object.entries(appFormTask.task_data).map(([k, v]) => [k, String(v ?? '')])
        )
      )
    }
  }, [services, activeStage])

  // Pre-populate bio builder result from saved task_data when services load
  useEffect(() => {
    const mcoDetail = services.find((d) => d.service.stage === 'mco_contracting')
    if (!mcoDetail) return
    const whTask = mcoDetail.tasks.find((t) => t.task_key === 'mco_work_history')
    if (!whTask?.task_data) return
    const td = whTask.task_data as Record<string, unknown>
    const rows = td.work_history_rows
    const gaps = td.gap_log
    const brainDump = td.brain_dump
    if (Array.isArray(rows) && rows.length > 0) {
      setBioResult((prev) => ({
        ...prev,
        [whTask.id]: { rows: rows as WorkHistoryRow[], gaps: Array.isArray(gaps) ? (gaps as GapEntry[]) : [] },
      }))
    }
    if (typeof brainDump === 'string' && brainDump) {
      setBioInput((prev) => ({ ...prev, [whTask.id]: brainDump }))
    }
  }, [services])

  const checkAgreement = async () => {
    try {
      const res = await axios.get<{ signed: boolean; signed_at: string | null }>(
        `${api}/api/v1/enrollment/me/agreement`,
        { headers }
      )
      if (res.data.signed) {
        setAgreementStatus('signed')
        setAgreementSignedAt(res.data.signed_at)
        loadServices()
      } else {
        setAgreementStatus('unsigned')
        setLoading(false)
      }
    } catch {
      // On error, show unsigned gate so provider can try signing
      setAgreementStatus('unsigned')
      setLoading(false)
    }
  }

  const handleAgreementSigned = () => {
    setAgreementStatus('signed')
    const now = new Date().toISOString()
    setAgreementSignedAt(now)
    loadServices()
  }

  const loadSensitiveProfile = async () => {
    try {
      const res = await axios.get<SensitiveProfile>(
        `${api}/api/v1/enrollment/me/sensitive-profile`,
        { headers }
      )
      setSensitiveProfile(res.data)
      setSensitiveForm({
        ssn: '',
        dob: res.data.dob ?? '',
        tax_id: '',
      })
    } catch {
      // Not critical — profile may not exist yet
    }
  }

  const handleSaveSensitiveProfile = async () => {
    setSensitiveFormSaving(true)
    setSensitiveFormSaved(false)
    const payload: { ssn?: string; dob?: string; tax_id?: string } = {}
    if (sensitiveForm.ssn) payload.ssn = sensitiveForm.ssn.replace(/\D/g, '')
    if (sensitiveForm.dob) payload.dob = sensitiveForm.dob
    if (sensitiveForm.tax_id) payload.tax_id = sensitiveForm.tax_id
    try {
      await axios.patch(
        `${api}/api/v1/enrollment/me/sensitive-profile`,
        payload,
        { headers }
      )
      setSensitiveFormSaved(true)
      setSensitiveForm((prev) => ({ ...prev, ssn: '' }))
      loadSensitiveProfile()
      setTimeout(() => setSensitiveFormSaved(false), 3000)
    } catch (e: unknown) {
      const msg = axios.isAxiosError(e) ? e.response?.data?.detail : null
      showToast(typeof msg === 'string' ? msg : 'Failed to save secure information')
    } finally {
      setSensitiveFormSaving(false)
    }
  }

  const handleSavePcbForm = async (serviceId: string, taskId: string) => {
    setPcbFormSaving(true)
    setPcbFormSaved(false)
    try {
      await axios.patch(
        `${api}/api/v1/enrollment/me/${serviceId}/tasks/${taskId}/data`,
        { task_data: pcbForm },
        { headers }
      )
      setServices((prev) =>
        prev.map((d) => {
          if (d.service.id !== serviceId) return d
          return {
            ...d,
            tasks: d.tasks.map((t) =>
              t.id === taskId
                ? { ...t, task_data: pcbForm, status: t.status === 'not_started' ? 'in_progress' : t.status }
                : t
            ),
          }
        })
      )
      setPcbFormSaved(true)
      setTimeout(() => setPcbFormSaved(false), 3000)
    } catch {
      showToast('Failed to save application info')
    } finally {
      setPcbFormSaving(false)
    }
  }

  const handleDownloadPrefill = async (serviceId: string) => {
    setDownloadingPrefill(true)
    try {
      const res = await axios.get(`${api}/api/v1/enrollment/me/${serviceId}/pcb-prefill.pdf`, {
        headers,
        responseType: 'blob',
      })
      const url = URL.createObjectURL(res.data as Blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'pcb-application-prefill.pdf'
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch {
      showToast('Could not generate pre-filled application')
    } finally {
      setDownloadingPrefill(false)
    }
  }

  const handleBioBuild = async (serviceId: string, taskId: string) => {
    const text = bioInput[taskId]?.trim()
    if (!text) return
    setBioBuilding((prev) => ({ ...prev, [taskId]: true }))
    try {
      const res = await axios.post<{ ok: boolean; rows: WorkHistoryRow[]; gaps: GapEntry[] }>(
        `${api}/api/v1/enrollment/me/${serviceId}/tasks/${taskId}/bio-build`,
        { brain_dump: text },
        { headers }
      )
      setBioResult((prev) => ({ ...prev, [taskId]: { rows: res.data.rows, gaps: res.data.gaps } }))
      setServices((prev) =>
        prev.map((d) => {
          if (d.service.id !== serviceId) return d
          return {
            ...d,
            tasks: d.tasks.map((t) =>
              t.id === taskId && t.status === 'not_started' ? { ...t, status: 'in_progress' } : t
            ),
          }
        })
      )
    } catch (e: unknown) {
      const msg = axios.isAxiosError(e) ? e.response?.data?.detail : null
      showToast(typeof msg === 'string' ? msg : 'AI processing failed — please try again or contact support.')
    } finally {
      setBioBuilding((prev) => ({ ...prev, [taskId]: false }))
    }
  }

  const loadServices = async () => {
    setLoading(true)
    try {
      const res = await axios.get<EnrollmentServiceDetail[]>(
        `${api}/api/v1/enrollment/me`,
        { headers }
      )
      setServices(res.data)
      const firstStage = STAGE_ORDER.find((s) => res.data.some((d) => d.service.stage === s))
      if (firstStage) setActiveStage(firstStage)
      if (res.data.some((d) => d.service.stage === 'pcb')) {
        loadSensitiveProfile()
      }
    } catch {
      showToast('Failed to load enrollment status')
    } finally {
      setLoading(false)
    }
  }

  const handleUpload = async (serviceId: string, taskId: string, file: File) => {
    setUploadingTask({ serviceId, taskId })
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('document_type', 'provider_upload')
      const res = await axios.post<EnrollmentDocument>(
        `${api}/api/v1/enrollment/me/${serviceId}/tasks/${taskId}/documents`,
        formData,
        { headers: { ...headers, 'Content-Type': 'multipart/form-data' } }
      )
      setServices((prev) =>
        prev.map((d) => {
          if (d.service.id !== serviceId) return d
          return {
            ...d,
            documents: [...d.documents, res.data],
            tasks: d.tasks.map((t) =>
              t.id === taskId && t.status === 'not_started' ? { ...t, status: 'in_progress' } : t
            ),
          }
        })
      )
      showToast(`${file.name} uploaded`)
    } catch (e: unknown) {
      const msg = axios.isAxiosError(e) ? e.response?.data?.detail : 'Upload failed'
      showToast(typeof msg === 'string' ? msg : 'Upload failed')
    } finally {
      setUploadingTask(null)
    }
  }

  const handleOpenDoc = async (serviceId: string, docId: string) => {
    setOpeningDoc(docId)
    try {
      const res = await axios.get<{ url: string }>(
        `${api}/api/v1/enrollment/me/${serviceId}/documents/${docId}/url`,
        { headers }
      )
      window.open(res.data.url, '_blank', 'noopener,noreferrer')
    } catch {
      showToast('Could not open document')
    } finally {
      setOpeningDoc(null)
    }
  }

  const taskDocsFor = (detail: EnrollmentServiceDetail, taskId: string) =>
    detail.documents.filter((d) => d.task_id === taskId)

  const activeDetail = services.find((d) => d.service.stage === activeStage) ?? null

  if (agreementStatus === 'loading') {
    return <div className="p-8 text-sm text-gray-500">Loading…</div>
  }

  if (agreementStatus === 'unsigned') {
    return <AgreementGate onSigned={handleAgreementSigned} />
  }

  if (loading) {
    return <div className="p-8 text-sm text-gray-500">Loading…</div>
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      {toast && (
        <div className="fixed top-4 right-4 z-50 rounded-lg bg-gray-900 px-4 py-2 text-sm text-white shadow-lg">
          {toast}
        </div>
      )}

      <div className="mb-6">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-xl font-semibold text-gray-900">My Credentialing Status</h1>
            <p className="mt-0.5 text-sm text-gray-500">
              Track your credentialing progress and upload required documents for each stage.
            </p>
          </div>
          <button
            onClick={() => setShowGuide(true)}
            className="rounded border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50 flex-shrink-0 ml-4"
          >
            How It Works
          </button>
        </div>
        {agreementSignedAt && (
          <p className="mt-1.5 text-xs text-green-700">
            Authorization agreement signed{' '}
            {new Date(agreementSignedAt).toLocaleDateString('en-US', {
              month: 'long',
              day: 'numeric',
              year: 'numeric',
            })}
            .
          </p>
        )}
      </div>

      {services.length === 0 ? (
        <div className="rounded-lg border border-dashed border-gray-300 py-16 text-center">
          <p className="text-sm text-gray-500">No enrollment services have been started yet.</p>
          <p className="mt-1 text-xs text-gray-400">Your agency will set up your credentialing stages — check back soon.</p>
        </div>
      ) : (
        <>
          {/* Stage tabs */}
          <div className="mb-4 flex gap-1 border-b border-gray-200 overflow-x-auto">
            {STAGE_TABS.map((tab) => {
              const hasService = services.some((d) => d.service.stage === tab.key)
              return (
                <button
                  key={tab.key}
                  onClick={() => hasService && setActiveStage(tab.key)}
                  disabled={!hasService}
                  className={`whitespace-nowrap px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                    activeStage === tab.key
                      ? 'border-blue-600 text-blue-700'
                      : hasService
                      ? 'border-transparent text-gray-500 hover:text-gray-700'
                      : 'border-transparent text-gray-300 cursor-not-allowed'
                  }`}
                >
                  {tab.label}
                </button>
              )
            })}
          </div>

          {/* Active stage detail */}
          {activeDetail ? (
            <div className="space-y-4">
              {/* Service header */}
              <div className="flex items-center gap-2">
                <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${SERVICE_STATUS_COLORS[activeDetail.service.status] ?? 'bg-gray-100 text-gray-600'}`}>
                  {activeDetail.service.status.replace('_', ' ')}
                </span>
                {activeDetail.service.status === 'complete' && activeDetail.service.stage === 'pcb' && activeDetail.service.pcb_cert_date && (
                  <span className="text-xs text-gray-500">Certified {activeDetail.service.pcb_cert_date}</span>
                )}
                {activeDetail.service.status === 'complete' && activeDetail.service.stage === 'nppes_setup' && !!activeDetail.service.intake_data?.npi && (
                  <span className="text-xs text-gray-500">NPI: {String(activeDetail.service.intake_data!.npi)}</span>
                )}
                {activeDetail.service.status === 'complete' && activeDetail.service.stage === 'enrollment' && !!activeDetail.service.intake_data?.promise_id && (
                  <span className="text-xs text-gray-500">PROMISe™ ID: {String(activeDetail.service.intake_data!.promise_id)}</span>
                )}
              </div>

              {/* Tasks */}
              <div className="space-y-3">
                {activeDetail.tasks.map((task, idx) => {
                  const docs = taskDocsFor(activeDetail, task.id)
                  const isUploading = uploadingTask?.serviceId === activeDetail.service.id && uploadingTask?.taskId === task.id

                  return (
                    <div key={task.id} className="rounded-lg border border-gray-200 bg-white p-4">
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex items-start gap-3 flex-1 min-w-0">
                          <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-gray-100 text-xs font-semibold text-gray-500">
                            {idx + 1}
                          </span>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-gray-800">{task.label}</p>
                            {task.description && (
                              <p className="mt-1 text-xs text-gray-500 leading-relaxed">{task.description}</p>
                            )}
                            {TASK_DOWNLOAD_LINKS[task.task_key] && (
                              <a
                                href={TASK_DOWNLOAD_LINKS[task.task_key].href}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="mt-1 inline-block text-xs text-blue-600 hover:underline"
                              >
                                {TASK_DOWNLOAD_LINKS[task.task_key].label} →
                              </a>
                            )}
                          </div>
                        </div>
                        <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[task.status]}`}>
                          {task.status.replace('_', ' ')}
                        </span>
                      </div>

                      {/* PCB Application Info form — only for pcb_application_form task */}
                      {task.task_key === 'pcb_application_form' && activeDetail.service.stage === 'pcb' && (
                        <div className="mt-4 space-y-3 border-t border-gray-100 pt-4">
                          <p className="text-xs font-semibold text-gray-700 uppercase tracking-wide">Your PCB Application Info</p>
                          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                            {PCB_FORM_FIELDS.map((f) => (
                              <div key={f.key} className={f.colSpan === 2 ? 'sm:col-span-2' : ''}>
                                <label className="block text-xs text-gray-500 mb-1">{f.label}</label>
                                <input
                                  type={f.type}
                                  value={pcbForm[f.key] ?? ''}
                                  placeholder={f.placeholder}
                                  onChange={(e) => setPcbForm((prev) => ({ ...prev, [f.key]: e.target.value }))}
                                  className="w-full rounded border border-gray-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                                />
                              </div>
                            ))}
                            {/* State + Zip on one row */}
                            <div className="grid grid-cols-2 gap-2">
                              <div>
                                <label className="block text-xs text-gray-500 mb-1">State</label>
                                <input
                                  type="text"
                                  maxLength={2}
                                  value={pcbForm.address_state ?? ''}
                                  placeholder="PA"
                                  onChange={(e) => setPcbForm((prev) => ({ ...prev, address_state: e.target.value.toUpperCase() }))}
                                  className="w-full rounded border border-gray-200 px-3 py-1.5 text-sm uppercase focus:outline-none focus:ring-2 focus:ring-blue-500"
                                />
                              </div>
                              <div>
                                <label className="block text-xs text-gray-500 mb-1">Zip Code</label>
                                <input
                                  type="text"
                                  maxLength={10}
                                  value={pcbForm.address_zip ?? ''}
                                  onChange={(e) => setPcbForm((prev) => ({ ...prev, address_zip: e.target.value }))}
                                  className="w-full rounded border border-gray-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                                />
                              </div>
                            </div>
                            <div>
                              <label className="block text-xs text-gray-500 mb-1">Gender</label>
                              <select
                                value={pcbForm.gender ?? ''}
                                onChange={(e) => setPcbForm((prev) => ({ ...prev, gender: e.target.value }))}
                                className="w-full rounded border border-gray-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                              >
                                <option value="">Select…</option>
                                {GENDER_OPTIONS.map((o) => <option key={o}>{o}</option>)}
                              </select>
                            </div>
                            <div>
                              <label className="block text-xs text-gray-500 mb-1">Race / Ethnicity</label>
                              <select
                                value={pcbForm.race_ethnicity ?? ''}
                                onChange={(e) => setPcbForm((prev) => ({ ...prev, race_ethnicity: e.target.value }))}
                                className="w-full rounded border border-gray-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                              >
                                <option value="">Select…</option>
                                {RACE_OPTIONS.map((o) => <option key={o}>{o}</option>)}
                              </select>
                            </div>
                            <div>
                              <label className="block text-xs text-gray-500 mb-1">Primary Language</label>
                              <input
                                type="text"
                                value={pcbForm.primary_language ?? ''}
                                placeholder="English"
                                onChange={(e) => setPcbForm((prev) => ({ ...prev, primary_language: e.target.value }))}
                                className="w-full rounded border border-gray-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                              />
                            </div>
                            <div>
                              <label className="block text-xs text-gray-500 mb-1">Doula Type</label>
                              <select
                                value={pcbForm.doula_type ?? ''}
                                onChange={(e) => setPcbForm((prev) => ({ ...prev, doula_type: e.target.value }))}
                                className="w-full rounded border border-gray-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                              >
                                <option value="">Select…</option>
                                {DOULA_TYPE_OPTIONS.map((o) => <option key={o}>{o}</option>)}
                              </select>
                            </div>
                          </div>

                          {/* Secure Information — stored encrypted, separate endpoint */}
                          <div className="mt-4 rounded-md border border-amber-200 bg-amber-50 p-3">
                            <p className="mb-2 text-xs font-semibold text-amber-800 uppercase tracking-wide">
                              Secure Information (encrypted at rest)
                            </p>
                            <p className="mb-3 text-xs text-amber-700">
                              SSN and date of birth are encrypted before storage and never appear in logs.
                              Enter your SSN as either the last 4 digits or your full 9-digit SSN — only the last 4 are printed on the pre-fill sheet.
                            </p>
                            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                              <div>
                                <label className="block text-xs text-gray-600 mb-1">
                                  Social Security Number
                                  {sensitiveProfile?.has_ssn && (
                                    <span className="ml-1 font-normal text-green-700">(saved — ending ••••{sensitiveProfile.ssn_last4})</span>
                                  )}
                                </label>
                                <input
                                  type="password"
                                  autoComplete="off"
                                  value={sensitiveForm.ssn}
                                  placeholder={sensitiveProfile?.has_ssn ? 'Enter to update' : 'Last 4 or full SSN'}
                                  maxLength={11}
                                  onChange={(e) => setSensitiveForm((prev) => ({ ...prev, ssn: e.target.value }))}
                                  className="w-full rounded border border-gray-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                                />
                              </div>
                              <div>
                                <label className="block text-xs text-gray-600 mb-1">
                                  Date of Birth
                                  {sensitiveProfile?.has_dob && !sensitiveForm.dob && (
                                    <span className="ml-1 font-normal text-green-700">(saved)</span>
                                  )}
                                </label>
                                <input
                                  type="date"
                                  value={sensitiveForm.dob}
                                  onChange={(e) => setSensitiveForm((prev) => ({ ...prev, dob: e.target.value }))}
                                  className="w-full rounded border border-gray-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                                />
                              </div>
                              <div className="sm:col-span-2">
                                <label className="block text-xs text-gray-600 mb-1">
                                  Tax ID / EIN (optional — used for agency tax reporting)
                                  {sensitiveProfile?.has_tax_id && (
                                    <span className="ml-1 font-normal text-green-700">(saved)</span>
                                  )}
                                </label>
                                <input
                                  type="password"
                                  autoComplete="off"
                                  value={sensitiveForm.tax_id}
                                  placeholder={sensitiveProfile?.has_tax_id ? 'Enter to update' : 'XX-XXXXXXX'}
                                  onChange={(e) => setSensitiveForm((prev) => ({ ...prev, tax_id: e.target.value }))}
                                  className="w-full rounded border border-gray-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                                />
                              </div>
                            </div>
                            <div className="mt-2 flex items-center gap-3">
                              <button
                                onClick={handleSaveSensitiveProfile}
                                disabled={sensitiveFormSaving || (!sensitiveForm.ssn && !sensitiveForm.dob && !sensitiveForm.tax_id)}
                                className="inline-flex items-center gap-1.5 rounded border border-amber-400 bg-white px-3 py-1.5 text-xs font-medium text-amber-800 hover:bg-amber-50 disabled:opacity-50"
                              >
                                {sensitiveFormSaving ? 'Saving…' : 'Save Secure Info'}
                              </button>
                              {sensitiveFormSaved && <span className="text-xs text-green-600">Saved securely ✓</span>}
                            </div>
                          </div>

                          <div className="flex flex-wrap items-center gap-3 pt-1">
                            <button
                              onClick={() => handleSavePcbForm(activeDetail.service.id, task.id)}
                              disabled={pcbFormSaving}
                              className="inline-flex items-center gap-1.5 rounded border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                            >
                              {pcbFormSaving ? 'Saving…' : 'Save Info'}
                            </button>
                            {pcbFormSaved && <span className="text-xs text-green-600">Saved ✓</span>}
                            <button
                              onClick={() => handleDownloadPrefill(activeDetail.service.id)}
                              disabled={downloadingPrefill}
                              className="inline-flex items-center gap-1.5 rounded bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                            >
                              {downloadingPrefill ? 'Generating…' : '↓ Download Pre-filled Application'}
                            </button>
                          </div>

                          <a
                            href="/docs/pcb-doula-application.pdf"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-block text-xs text-blue-600 hover:underline"
                          >
                            Download blank official PCB application →
                          </a>
                        </div>
                      )}

                      {/* Work History Bio-Builder — only for mco_work_history task */}
                      {task.task_key === 'mco_work_history' && task.status !== 'complete' && (
                        <div className="mt-4 space-y-3 border-t border-gray-100 pt-4">

                          {/* Collapsible prep guide */}
                          <div className="rounded border border-blue-100 bg-blue-50">
                            <button
                              onClick={() => setShowBioPrep((prev) => ({ ...prev, [task.id]: !prev[task.id] }))}
                              className="flex w-full items-center justify-between px-3 py-2 text-xs font-semibold text-blue-800"
                            >
                              <span>Before You Start — How to Gather Your Work History (4 steps)</span>
                              <span className="ml-2 shrink-0">{showBioPrep[task.id] ? '▲' : '▼'}</span>
                            </button>
                            {showBioPrep[task.id] && (
                              <div className="divide-y divide-blue-100 border-t border-blue-100 px-3 pb-3">
                                {[
                                  {
                                    title: 'Audit Digital Financial Trails',
                                    time: '~15 min',
                                    body: 'Log into tax portals (TurboTax, TaxSlayer, or IRS.gov) to pull W-2s or 1099s for the past 5 years. For private-pay work, search Stripe, PayPal, or bank statements for recurring client deposits to pin down active working months.',
                                  },
                                  {
                                    title: 'Scrape Birth Platforms & Calendars',
                                    time: '~15 min',
                                    body: 'Check your history on doula directories (DoulaMatch, local collectives) or digital client logs. Search Google Calendar or Apple Calendar for "birth," "prenatal," "postpartum," or "client" to find exact start and end dates for contract blocks.',
                                  },
                                  {
                                    title: 'Map Out the Gaps',
                                    time: '~10 min',
                                    body: 'Identify any months where no formal employment or active client cycles occurred. Note the reason — PA Medicaid will reject applications with unexplained timeline gaps over 30 days.',
                                  },
                                  {
                                    title: 'Execute the Brain Dump',
                                    time: '~5 min',
                                    body: "Don't worry about formatting or spelling. Write a messy chronological list of dates, organization names (or \"Independent Practice\"), addresses, and what you actually did — then paste it below.",
                                  },
                                ].map((step, i) => (
                                  <div key={i} className="py-2">
                                    <p className="text-xs font-medium text-blue-900">
                                      {i + 1}. {step.title}
                                      <span className="ml-1.5 font-normal text-blue-500">({step.time})</span>
                                    </p>
                                    <p className="mt-0.5 text-xs text-blue-700 leading-relaxed">{step.body}</p>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>

                          {!bioResult[task.id] ? (
                            /* Input mode */
                            <>
                              <p className="text-xs text-gray-500">
                                Type or paste your work history below — dates, employers, job titles, and what you did.
                                Rough notes are fine. Our AI will format them into the PROMISe™/MCO-compliant table.
                              </p>
                              <textarea
                                rows={8}
                                value={bioInput[task.id] ?? ''}
                                onChange={(e) => setBioInput((prev) => ({ ...prev, [task.id]: e.target.value }))}
                                placeholder="e.g. From Jan 2022 to Aug 2023 I worked at St. Luke's hospital doing shift doula work. Then I started my own practice 'Luna Birth Services' out of Pittsburgh. I didn't work at all in Fall 2023 because I was taking care of my sick mom..."
                                className="w-full rounded border border-gray-200 p-2 text-xs font-mono leading-relaxed focus:outline-none focus:ring-1 focus:ring-blue-500"
                              />
                              <button
                                onClick={() => handleBioBuild(activeDetail.service.id, task.id)}
                                disabled={bioBuilding[task.id] || !bioInput[task.id]?.trim()}
                                className="rounded bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                              >
                                {bioBuilding[task.id] ? 'Generating…' : 'Generate Work History with AI'}
                              </button>
                            </>
                          ) : (
                            /* Result mode */
                            <>
                              <div className="overflow-x-auto rounded border border-gray-200">
                                <table className="w-full text-xs">
                                  <thead className="bg-gray-50">
                                    <tr>
                                      {['Start', 'End', 'Employer', 'Address', 'Title', 'Duties'].map((h) => (
                                        <th key={h} className="px-2 py-1.5 text-left font-medium text-gray-600 whitespace-nowrap">{h}</th>
                                      ))}
                                    </tr>
                                  </thead>
                                  <tbody className="divide-y divide-gray-100">
                                    {bioResult[task.id].rows.map((row, i) => (
                                      <tr key={i}>
                                        <td className="px-2 py-1.5 whitespace-nowrap">{row.start_date}</td>
                                        <td className="px-2 py-1.5 whitespace-nowrap">{row.end_date}</td>
                                        <td className="px-2 py-1.5">{row.employer_name}</td>
                                        <td className="px-2 py-1.5">{row.address}</td>
                                        <td className="px-2 py-1.5">{row.job_title}</td>
                                        <td className="px-2 py-1.5 text-gray-600">{row.duties}</td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>

                              {bioResult[task.id].gaps.length > 0 && (
                                <div className="rounded border border-amber-200 bg-amber-50 p-3">
                                  <p className="text-xs font-semibold text-amber-800 mb-1.5">Gap Log — periods over 30 days</p>
                                  <div className="space-y-1">
                                    {bioResult[task.id].gaps.map((g, i) => (
                                      <p key={i} className="text-xs text-amber-700">
                                        <span className="font-medium">{g.start_date} – {g.end_date}</span>
                                        {g.duration_days ? ` (${g.duration_days} days)` : ''}: {g.explanation}
                                      </p>
                                    ))}
                                  </div>
                                </div>
                              )}

                              <div className="flex items-center gap-3">
                                <button
                                  onClick={() => setBioResult((prev) => { const n = { ...prev }; delete n[task.id]; return n })}
                                  className="rounded border border-gray-200 px-3 py-1 text-xs text-gray-600 hover:bg-gray-50"
                                >
                                  Edit / Regenerate
                                </button>
                                <p className="text-xs text-gray-400">
                                  Upload the final signed PDF below once verified.
                                </p>
                              </div>
                            </>
                          )}
                        </div>
                      )}

                      {/* Uploaded documents */}
                      {docs.length > 0 && (
                        <div className="mt-3 flex flex-wrap gap-2">
                          {docs.map((doc) => (
                            <button
                              key={doc.id}
                              onClick={() => handleOpenDoc(activeDetail.service.id, doc.id)}
                              disabled={openingDoc === doc.id}
                              className="inline-flex items-center gap-1.5 rounded border border-gray-200 bg-gray-50 px-2 py-1 text-xs text-gray-600 hover:bg-gray-100 disabled:opacity-50"
                            >
                              <span>📎</span>
                              <span className="max-w-[160px] truncate">{doc.file_name}</span>
                              {openingDoc === doc.id && <span className="text-gray-400">…</span>}
                            </button>
                          ))}
                        </div>
                      )}

                      {/* Upload button — only for incomplete tasks */}
                      {task.status !== 'complete' && task.task_key !== 'pcb_application_form' && (
                        <div className="mt-3">
                          <label className="cursor-pointer">
                            <input
                              type="file"
                              accept=".pdf,.jpg,.jpeg,.png"
                              className="hidden"
                              disabled={!!uploadingTask}
                              onChange={(e) => {
                                const file = e.target.files?.[0]
                                if (file) {
                                  handleUpload(activeDetail.service.id, task.id, file)
                                  e.target.value = ''
                                }
                              }}
                            />
                            <span className={`inline-flex items-center gap-1.5 rounded border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50 ${isUploading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}>
                              {isUploading ? 'Uploading…' : '+ Upload Document'}
                            </span>
                          </label>
                          <p className="mt-1 text-xs text-gray-400">PDF, JPEG, or PNG · max 20 MB</p>
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>

              {activeDetail.service.status === 'complete' && (
                <div className="rounded-lg border border-green-200 bg-green-50 p-4 text-sm text-green-800">
                  This stage is complete. Your agency will advance you to the next stage.
                </div>
              )}
            </div>
          ) : (
            <div className="rounded-lg border border-dashed border-gray-300 py-12 text-center text-sm text-gray-500">
              This stage has not been started yet.
            </div>
          )}
        </>
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
                <h2 className="text-base font-semibold text-gray-900">My Credentialing Status — How It Works</h2>
                <p className="text-xs text-gray-500 mt-0.5">A step-by-step guide to your four-stage credentialing and enrollment pipeline.</p>
              </div>
              <button onClick={() => setShowGuide(false)} className="text-gray-400 hover:text-gray-600 text-xl leading-none ml-6 mt-0.5">×</button>
            </div>
            <div className="px-6 py-5 space-y-6">
              <div className="rounded-lg border border-amber-100 bg-amber-50 p-4">
                <h3 className="text-sm font-semibold text-amber-800 mb-2">Step 0 — Authorization Agreement</h3>
                <ul className="space-y-1 text-xs text-amber-700 list-disc list-inside">
                  <li>Before enrollment begins, you must read and electronically sign the DoulaShield authorization agreement</li>
                  <li>This allows DoulaShield to act as your administrative delegate with CMS, CAQH, MCOs, and insurance carriers</li>
                  <li>You can revoke authorization at any time by contacting DoulaShield — this will pause all credentialing activity</li>
                </ul>
              </div>
              <div className="rounded-lg border border-blue-100 bg-blue-50 p-4">
                <h3 className="text-sm font-semibold text-blue-800 mb-2">Four-Stage Pipeline</h3>
                <div className="flex flex-wrap items-center gap-2 mb-3">
                  {[
                    { label: 'PCB Certification', color: 'bg-gray-100 text-gray-700 border-gray-300' },
                    { label: 'NPPES / NPI Setup', color: 'bg-indigo-100 text-indigo-700 border-indigo-300' },
                    { label: 'Enrollment — Stage 2', color: 'bg-blue-100 text-blue-700 border-blue-300' },
                    { label: 'MCO Contracting', color: 'bg-purple-100 text-purple-700 border-purple-300' },
                  ].map((s, i, arr) => (
                    <span key={s.label} className="flex items-center gap-2">
                      <span className={`rounded border px-2 py-0.5 text-xs font-medium ${s.color}`}>{s.label}</span>
                      {i < arr.length - 1 && <span className="text-blue-400">→</span>}
                    </span>
                  ))}
                </div>
                <p className="text-xs text-blue-700">Stages must complete in order. Each stage is set up and managed by DoulaShield or your billing admin — grayed-out tabs mean that stage hasn't been started for you yet.</p>
              </div>
              <div className="rounded-lg border border-green-100 bg-green-50 p-4">
                <h3 className="text-sm font-semibold text-green-800 mb-2">Task Status Indicators</h3>
                <div className="flex gap-4 text-xs text-green-700 mb-2">
                  <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-gray-300 inline-block"></span> Not Started</span>
                  <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-yellow-400 inline-block"></span> In Progress</span>
                  <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-green-500 inline-block"></span> Complete</span>
                </div>
                <p className="text-xs text-green-700">DoulaShield or your billing admin marks tasks complete as credentials are processed — you do not mark them yourself. Your role is to upload documents and provide information.</p>
              </div>
              <div className="rounded-lg border border-gray-100 bg-gray-50 p-4">
                <h3 className="text-sm font-semibold text-gray-800 mb-2">Uploading Documents</h3>
                <ul className="space-y-1 text-xs text-gray-700 list-disc list-inside">
                  <li>Each task has an <strong>Upload Document</strong> button — click to attach a PDF or image file</li>
                  <li>Accepted formats: PDF, JPG, JPEG, PNG</li>
                  <li>Your billing admin or DoulaShield can also upload on your behalf</li>
                  <li>If you uploaded the wrong file, contact DoulaShield to remove it</li>
                </ul>
              </div>
              <div className="rounded-lg border border-indigo-100 bg-indigo-50 p-4">
                <h3 className="text-sm font-semibold text-indigo-800 mb-2">Secure Information Storage</h3>
                <ul className="space-y-1 text-xs text-indigo-700 list-disc list-inside">
                  <li>Your SSN, date of birth, and tax ID are stored encrypted and never appear in logs</li>
                  <li>Enter them once in the <strong>Secure Info</strong> section — DoulaShield uses them to complete government forms (NPPES, PROMISe™, PECOS) without asking repeatedly</li>
                  <li>Only the last 4 digits of your SSN are displayed after saving</li>
                </ul>
              </div>
              <div className="rounded-lg border border-purple-100 bg-purple-50 p-4">
                <h3 className="text-sm font-semibold text-purple-800 mb-2">PCB Application Form</h3>
                <ol className="space-y-1 text-xs text-purple-700 list-decimal list-inside">
                  <li>Fill in your legal name, address, contact details, and demographic info on the first PCB task</li>
                  <li>Click <strong>Download Pre-filled Application</strong> to get a print-ready version of pages 6–8</li>
                  <li>You still need to sign pages 12–13 and have page 14 notarized before mailing the application to PCB</li>
                  <li>Mail the complete packet with a $50 check payable to "PCB" to info@pacertboard.org</li>
                </ol>
              </div>
              <div className="rounded-lg bg-gray-50 border border-gray-200 p-4">
                <h3 className="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-3">Key Rules & Reminders</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs text-gray-700">
                  <div><strong>Stage gates:</strong> Each stage unlocks only after the prior stage is fully complete — you cannot skip ahead.</div>
                  <div><strong>CAQH re-attestation:</strong> Due every 120 days; DoulaShield sends you a reminder email before it expires.</div>
                  <div><strong>PROMISe™ re-enrollment:</strong> Required every 5 years; DoulaShield tracks your enrollment date and reminds you in advance.</div>
                  <div><strong>PCB renewal:</strong> PCB certification renews every 2 years; reminders are sent starting 60 days before expiry.</div>
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
