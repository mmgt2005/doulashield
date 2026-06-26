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

export default function EnrollmentStatusPage() {
  const router = useRouter()
  const { user } = useAuthStore()
  const [services, setServices] = useState<EnrollmentServiceDetail[]>([])
  const [loading, setLoading] = useState(true)
  const [activeStage, setActiveStage] = useState<string>('pcb')
  const [uploadingTask, setUploadingTask] = useState<{ serviceId: string; taskId: string } | null>(null)
  const [openingDoc, setOpeningDoc] = useState<string | null>(null)
  const [toast, setToast] = useState<string | null>(null)

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
    loadServices()
  }, [user]) // eslint-disable-line react-hooks/exhaustive-deps

  const loadServices = async () => {
    setLoading(true)
    try {
      const res = await axios.get<EnrollmentServiceDetail[]>(
        `${api}/api/v1/enrollment/me`,
        { headers }
      )
      setServices(res.data)
      // Auto-select the first stage that has a service
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
