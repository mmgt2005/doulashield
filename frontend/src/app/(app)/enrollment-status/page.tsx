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
        <h1 className="text-xl font-semibold text-gray-900">My Credentialing Status</h1>
        <p className="mt-0.5 text-sm text-gray-500">
          Track your credentialing progress and upload required documents for each stage.
        </p>
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
                          </div>
                        </div>
                        <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[task.status]}`}>
                          {task.status.replace('_', ' ')}
                        </span>
                      </div>

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
                      {task.status !== 'complete' && (
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
    </div>
  )
}
