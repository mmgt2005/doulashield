'use client'

import { useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import axios from 'axios'
import { getAccessToken } from '@/lib/auth'
import { useAuthStore } from '@/store/auth-store'
import TaskDescription from '@/components/ui/TaskDescription'

interface EnrollmentService {
  id: string
  provider_id: string
  created_by: string | null
  stage: string
  pcb_pathway: 'education_training' | 'experienced' | null
  status: string
  intake_data: Record<string, unknown> | null
  pcb_cert_date: string | null
  assigned_to_billing_admin: boolean
  created_at: string
  updated_at: string
}

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

interface EnrollmentServiceDetail {
  service: EnrollmentService
  tasks: EnrollmentTask[]
  documents: EnrollmentDocument[]
  provider_email: string | null
  provider_name: string | null
  provider_npi: string | null
}

interface Provider {
  id: string
  email: string
  full_name: string | null
  role: string
}

const PATHWAY_LABELS: Record<string, string> = {
  education_training: 'Education/Training',
  experienced: 'Experienced',
}

const STAGE_LABELS: Record<string, string> = {
  pcb: 'PCB',
  nppes_setup: 'NPPES / NPI',
  enrollment: 'Stage 2',
  mco_contracting: 'Stage 3',
}

const STAGE_BADGE_COLORS: Record<string, string> = {
  pcb: 'bg-gray-100 text-gray-600',
  nppes_setup: 'bg-indigo-100 text-indigo-700',
  enrollment: 'bg-blue-100 text-blue-700',
  mco_contracting: 'bg-purple-100 text-purple-700',
}

const STATUS_COLORS: Record<string, string> = {
  not_started: 'bg-gray-100 text-gray-600',
  in_progress: 'bg-yellow-100 text-yellow-700',
  complete: 'bg-green-100 text-green-700',
}

const SERVICE_STATUS_COLORS: Record<string, string> = {
  in_progress: 'bg-blue-100 text-blue-700',
  submitted: 'bg-yellow-100 text-yellow-700',
  complete: 'bg-green-100 text-green-700',
  cancelled: 'bg-gray-100 text-gray-500',
}

export default function EnrollmentServicesPage() {
  const router = useRouter()
  const { user: currentUser } = useAuthStore()
  const [services, setServices] = useState<EnrollmentService[]>([])
  const [providers, setProviders] = useState<Provider[]>([])
  const [loading, setLoading] = useState(true)
  const [toast, setToast] = useState<string | null>(null)

  // Stage filter
  const [activeStage, setActiveStage] = useState<'pcb' | 'nppes_setup' | 'enrollment' | 'mco_contracting'>('pcb')

  // New service form
  const newServiceFormRef = useRef<HTMLDivElement>(null)
  const [showNew, setShowNew] = useState(false)
  const [newProviderId, setNewProviderId] = useState('')
  const [newStage, setNewStage] = useState<'pcb' | 'nppes_setup' | 'enrollment' | 'mco_contracting'>('pcb')
  const [newPathway, setNewPathway] = useState<'education_training' | 'experienced'>('education_training')
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState<string | null>(null)

  // Expanded service detail
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [detailCache, setDetailCache] = useState<Record<string, EnrollmentServiceDetail>>({})
  const [detailLoading, setDetailLoading] = useState<Record<string, boolean>>({})

  // Task editing
  const [taskNotes, setTaskNotes] = useState<Record<string, string>>({})
  const [taskHours, setTaskHours] = useState<Record<string, string>>({})
  const [taskHipaaHours, setTaskHipaaHours] = useState<Record<string, string>>({})
  const [taskContractDates, setTaskContractDates] = useState<Record<string, string>>({})
  const [taskSaving, setTaskSaving] = useState<Record<string, boolean>>({})

  // PCB complete modal
  const [pcbCompleteModal, setPcbCompleteModal] = useState<{ serviceId: string } | null>(null)
  const [pcbCertDate, setPcbCertDate] = useState('')
  const [pcbSaving, setPcbSaving] = useState(false)

  // Stage 2 complete modal
  const [stage2Modal, setStage2Modal] = useState<{ serviceId: string } | null>(null)
  const [stage2PromiseDate, setStage2PromiseDate] = useState('')
  const [stage2PromiseId, setStage2PromiseId] = useState('')
  const [stage2CaqhId, setStage2CaqhId] = useState('')
  const [stage2LiabilityExpiry, setStage2LiabilityExpiry] = useState('')
  const [stage2Saving, setStage2Saving] = useState(false)

  // Stage 3 complete modal
  const [stage3Modal, setStage3Modal] = useState<{ serviceId: string } | null>(null)
  const [stage3ContractedOn, setStage3ContractedOn] = useState('')
  const [stage3Saving, setStage3Saving] = useState(false)

  // NPPES complete modal
  const [npesModal, setNpesModal] = useState<{ serviceId: string } | null>(null)
  const [npesNpi, setNpesNpi] = useState('')
  const [npesSaving, setNpesSaving] = useState(false)

  // Document upload
  const [uploadingTask, setUploadingTask] = useState<{ serviceId: string; taskId: string } | null>(null)

  // Walkthrough guide
  const [showGuide, setShowGuide] = useState(false)

  // Assign to billing admin
  const [assignLoading, setAssignLoading] = useState<string | null>(null)


  // doxy.me screen-share
  const [telehealthLink, setTelehealthLink] = useState<string | null>(null)
  const [screenshareLoading, setScreenshareLoading] = useState<string | null>(null)

  const headers = { Authorization: `Bearer ${getAccessToken()}` }
  const api = process.env.NEXT_PUBLIC_API_URL

  const showToast = (msg: string) => {
    setToast(msg)
    setTimeout(() => setToast(null), 4000)
  }

  useEffect(() => {
    if (currentUser && currentUser.role !== 'admin') {
      router.replace('/dashboard')
      return
    }
    loadData()
  }, [currentUser]) // eslint-disable-line react-hooks/exhaustive-deps

  const loadData = async () => {
    setLoading(true)
    try {
      const [svcRes, usersRes, settingsRes] = await Promise.all([
        axios.get<EnrollmentService[]>(`${api}/api/v1/admin/enrollment/services`, { headers }),
        axios.get<Provider[]>(`${api}/api/v1/admin/users`, { headers }),
        axios.get<{ telehealth_link: string | null }>(`${api}/api/v1/auth/me/provider-settings`, { headers }).catch(() => ({ data: { telehealth_link: null } })),
      ])
      setServices(svcRes.data)
      setProviders(usersRes.data.filter((u) => u.role === 'provider'))
      setTelehealthLink(settingsRes.data.telehealth_link)
    } catch {
      showToast('Failed to load data')
    } finally {
      setLoading(false)
    }
  }

  const handleAssign = async (serviceId: string) => {
    setAssignLoading(serviceId)
    try {
      const res = await axios.post<EnrollmentService>(
        `${api}/api/v1/admin/enrollment/services/${serviceId}/assign-to-billing-admin`,
        {},
        { headers },
      )
      setServices(prev => prev.map(s => s.id === serviceId ? { ...s, assigned_to_billing_admin: res.data.assigned_to_billing_admin } : s))
      showToast(res.data.assigned_to_billing_admin ? 'Assigned to billing agency.' : 'Unassigned from billing agency.')
      // Expand the service so the admin can see the task list immediately after assigning
      if (res.data.assigned_to_billing_admin && expandedId !== serviceId) {
        setExpandedId(serviceId)
        loadDetail(serviceId)
      }
    } catch (e: unknown) {
      const msg = axios.isAxiosError(e) ? e.response?.data?.detail : 'Failed'
      showToast(typeof msg === 'string' ? msg : 'Failed')
    } finally {
      setAssignLoading(null)
    }
  }

  const handleDeleteService = async (serviceId: string) => {
    if (!window.confirm('Delete this enrollment service? This also removes all its tasks and uploaded documents. This cannot be undone.')) return
    // Optimistic: remove immediately so the UI feels instant
    const removed = services.find(s => s.id === serviceId)
    const removedDetail = detailCache[serviceId]
    setServices(prev => prev.filter(s => s.id !== serviceId))
    setDetailCache(prev => { const n = { ...prev }; delete n[serviceId]; return n })
    if (expandedId === serviceId) setExpandedId(null)
    showToast('Enrollment service deleted.')
    try {
      await axios.delete(`${api}/api/v1/admin/enrollment/services/${serviceId}`, { headers })
    } catch (e: unknown) {
      // Rollback on failure
      if (removed) setServices(prev => [removed, ...prev])
      if (removedDetail) setDetailCache(prev => ({ ...prev, [serviceId]: removedDetail }))
      const msg = axios.isAxiosError(e) ? e.response?.data?.detail : 'Failed to delete'
      showToast(typeof msg === 'string' ? msg : 'Failed to delete')
    }
  }

  const startScreenShare = async (taskId: string, providerName: string | null) => {
    if (!telehealthLink) {
      showToast('Please add your doxy.me room link to your Settings page first.')
      return
    }
    setScreenshareLoading(taskId)
    try {
      await axios.post(
        `${api}/api/v1/admin/enrollment/tasks/${taskId}/screenshare-invite`,
        { doxy_me_url: telehealthLink },
        { headers },
      )
      window.open('https://doxy.me', '_blank', 'noopener')
      showToast(`Invitation sent to ${providerName ?? 'provider'}. Opening doxy.me…`)
    } catch {
      showToast('Failed to send invitation.')
    } finally {
      setScreenshareLoading(null)
    }
  }

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text).then(() => showToast(`${label} copied`)).catch(() => showToast('Copy failed'))
  }

  const handleDeleteDocument = async (serviceId: string, docId: string, fileName: string) => {
    if (!window.confirm(`Remove "${fileName}" from this task? This cannot be undone.`)) return
    try {
      await axios.delete(
        `${api}/api/v1/admin/enrollment/services/${serviceId}/documents/${docId}`,
        { headers },
      )
      setDetailCache((prev) => {
        const detail = prev[serviceId]
        if (!detail) return prev
        return { ...prev, [serviceId]: { ...detail, documents: detail.documents.filter((d) => d.id !== docId) } }
      })
      showToast(`${fileName} removed`)
    } catch {
      showToast('Failed to remove document')
    }
  }

  const downloadDocument = async (serviceId: string, docId: string, fileName: string) => {
    try {
      const res = await axios.get<{ url: string; file_name: string }>(
        `${api}/api/v1/admin/enrollment/services/${serviceId}/documents/${docId}/url`,
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

  const loadDetail = async (serviceId: string) => {
    if (detailCache[serviceId]) return
    setDetailLoading((prev) => ({ ...prev, [serviceId]: true }))
    try {
      const res = await axios.get<EnrollmentServiceDetail>(
        `${api}/api/v1/admin/enrollment/services/${serviceId}`,
        { headers },
      )
      setDetailCache((prev) => ({ ...prev, [serviceId]: res.data }))
    } catch {
      showToast('Failed to load service details')
    } finally {
      setDetailLoading((prev) => ({ ...prev, [serviceId]: false }))
    }
  }

  const toggleExpand = (serviceId: string) => {
    const next = expandedId === serviceId ? null : serviceId
    setExpandedId(next)
    if (next) loadDetail(next)
  }

  const quickStartNextStage = (
    providerId: string,
    stage: 'nppes_setup' | 'enrollment' | 'mco_contracting',
  ) => {
    setNewProviderId(providerId)
    setNewStage(stage)
    setActiveStage(stage)
    setCreateError(null)
    setShowNew(true)
    setTimeout(() => newServiceFormRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 50)
  }

  const handleCreate = async () => {
    if (!newProviderId) { setCreateError('Select a provider'); return }
    if (newStage === 'pcb' && !newPathway) { setCreateError('Select a pathway'); return }
    setCreating(true)
    setCreateError(null)
    try {
      const body: Record<string, unknown> = { provider_id: newProviderId, stage: newStage }
      if (newStage === 'pcb') body.pcb_pathway = newPathway
      const res = await axios.post<EnrollmentServiceDetail>(
        `${api}/api/v1/admin/enrollment/services`,
        body,
        { headers },
      )
      setServices((prev) => [res.data.service, ...prev])
      setDetailCache((prev) => ({ ...prev, [res.data.service.id]: res.data }))
      setExpandedId(res.data.service.id)
      setActiveStage(newStage)
      setShowNew(false)
      setNewProviderId('')
      showToast('Enrollment service created')
    } catch (e: unknown) {
      const msg = axios.isAxiosError(e) ? e.response?.data?.detail : 'Failed to create'
      setCreateError(typeof msg === 'string' ? msg : 'Failed to create')
    } finally {
      setCreating(false)
    }
  }

  const handleUpdateTask = async (
    serviceId: string,
    task: EnrollmentTask,
    newStatus: 'not_started' | 'in_progress' | 'complete',
  ) => {
    setTaskSaving((prev) => ({ ...prev, [task.id]: true }))
    try {
      const notes = taskNotes[task.id] ?? task.notes ?? undefined
      let task_data: Record<string, unknown> | undefined

      if (task.task_key === 'pcb_training_hours') {
        const h = parseInt(taskHours[task.id] ?? '0', 10)
        task_data = { ...(task.task_data ?? {}), hours: h }
      } else if (task.task_key === 'pcb_hipaa_cert') {
        const h = parseInt(taskHipaaHours[task.id] ?? '0', 10)
        task_data = { ...(task.task_data ?? {}), hours: h }
      } else if (taskContractDates[task.id] !== undefined) {
        task_data = { ...(task.task_data ?? {}), contract_date: taskContractDates[task.id] }
      }

      await axios.patch(
        `${api}/api/v1/admin/enrollment/tasks/${task.id}`,
        { status: newStatus, notes: notes ?? null, task_data: task_data ?? null },
        { headers },
      )

      setDetailCache((prev) => {
        const detail = prev[serviceId]
        if (!detail) return prev
        return {
          ...prev,
          [serviceId]: {
            ...detail,
            tasks: detail.tasks.map((t) =>
              t.id === task.id ? { ...t, status: newStatus, notes: notes ?? t.notes, task_data: task_data ?? t.task_data } : t,
            ),
          },
        }
      })
      showToast('Task updated')
    } catch (e: unknown) {
      const msg = axios.isAxiosError(e) ? e.response?.data?.detail : 'Failed to update task'
      showToast(typeof msg === 'string' ? msg : 'Failed to update task')
    } finally {
      setTaskSaving((prev) => ({ ...prev, [task.id]: false }))
    }
  }

  const handleCompletePcb = async () => {
    if (!pcbCompleteModal || !pcbCertDate) return
    setPcbSaving(true)
    try {
      const res = await axios.post<EnrollmentService>(
        `${api}/api/v1/admin/enrollment/services/${pcbCompleteModal.serviceId}/complete-pcb`,
        { cert_date: pcbCertDate },
        { headers },
      )
      setServices((prev) => prev.map((s) => (s.id === res.data.id ? res.data : s)))
      setDetailCache((prev) => {
        const detail = prev[pcbCompleteModal.serviceId]
        if (!detail) return prev
        return { ...prev, [pcbCompleteModal.serviceId]: { ...detail, service: res.data } }
      })
      setPcbCompleteModal(null)
      setPcbCertDate('')
      showToast('PCB certification recorded — provider profile updated')
    } catch (e: unknown) {
      const msg = axios.isAxiosError(e) ? e.response?.data?.detail : 'Failed to save'
      showToast(typeof msg === 'string' ? msg : 'Failed to save')
    } finally {
      setPcbSaving(false)
    }
  }

  const handleCompleteEnrollment = async () => {
    if (!stage2Modal || !stage2PromiseDate) return
    setStage2Saving(true)
    try {
      const body: Record<string, unknown> = { promise_enrolled_on: stage2PromiseDate }
      if (stage2PromiseId) body.promise_id = stage2PromiseId
      if (stage2CaqhId) body.caqh_id = stage2CaqhId
      if (stage2LiabilityExpiry) body.liability_insurance_expires_on = stage2LiabilityExpiry
      const res = await axios.post<EnrollmentService>(
        `${api}/api/v1/admin/enrollment/services/${stage2Modal.serviceId}/complete-enrollment`,
        body,
        { headers },
      )
      setServices((prev) => prev.map((s) => (s.id === res.data.id ? res.data : s)))
      setDetailCache((prev) => {
        const detail = prev[stage2Modal.serviceId]
        if (!detail) return prev
        return { ...prev, [stage2Modal.serviceId]: { ...detail, service: res.data } }
      })
      setStage2Modal(null)
      setStage2PromiseDate('')
      setStage2PromiseId('')
      setStage2CaqhId('')
      setStage2LiabilityExpiry('')
      showToast('Stage 2 enrollment complete — provider profile updated')
    } catch (e: unknown) {
      const msg = axios.isAxiosError(e) ? e.response?.data?.detail : 'Failed to save'
      showToast(typeof msg === 'string' ? msg : 'Failed to save')
    } finally {
      setStage2Saving(false)
    }
  }

  const handleCompleteMcoContracting = async () => {
    if (!stage3Modal || !stage3ContractedOn) return
    setStage3Saving(true)
    try {
      const res = await axios.post<EnrollmentService>(
        `${api}/api/v1/admin/enrollment/services/${stage3Modal.serviceId}/complete-mco-contracting`,
        { contracted_on: stage3ContractedOn },
        { headers },
      )
      setServices((prev) => prev.map((s) => (s.id === res.data.id ? res.data : s)))
      setDetailCache((prev) => {
        const detail = prev[stage3Modal.serviceId]
        if (!detail) return prev
        return { ...prev, [stage3Modal.serviceId]: { ...detail, service: res.data } }
      })
      setStage3Modal(null)
      setStage3ContractedOn('')
      showToast('MCO contracting marked complete')
    } catch (e: unknown) {
      const msg = axios.isAxiosError(e) ? e.response?.data?.detail : 'Failed to save'
      showToast(typeof msg === 'string' ? msg : 'Failed to save')
    } finally {
      setStage3Saving(false)
    }
  }

  const handleCompleteNppes = async () => {
    if (!npesModal || !npesNpi) return
    const trimmed = npesNpi.trim()
    if (!/^\d{10}$/.test(trimmed)) {
      showToast('NPI must be exactly 10 digits')
      return
    }
    setNpesSaving(true)
    try {
      const res = await axios.post<EnrollmentService>(
        `${api}/api/v1/admin/enrollment/services/${npesModal.serviceId}/complete-nppes`,
        { npi: trimmed },
        { headers },
      )
      setServices((prev) => prev.map((s) => (s.id === res.data.id ? res.data : s)))
      setDetailCache((prev) => {
        const detail = prev[npesModal.serviceId]
        if (!detail) return prev
        return { ...prev, [npesModal.serviceId]: { ...detail, service: res.data } }
      })
      setNpesModal(null)
      setNpesNpi('')
      showToast('NPI recorded — provider profile updated')
    } catch (e: unknown) {
      const msg = axios.isAxiosError(e) ? e.response?.data?.detail : 'Failed to save'
      showToast(typeof msg === 'string' ? msg : 'Failed to save')
    } finally {
      setNpesSaving(false)
    }
  }

  const handleUploadDocument = async (
    serviceId: string,
    taskId: string,
    file: File,
    documentType: string,
  ) => {
    setUploadingTask({ serviceId, taskId })
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('document_type', documentType)
      const res = await axios.post<EnrollmentDocument>(
        `${api}/api/v1/admin/enrollment/services/${serviceId}/tasks/${taskId}/documents`,
        formData,
        { headers: { ...headers, 'Content-Type': 'multipart/form-data' } },
      )
      setDetailCache((prev) => {
        const detail = prev[serviceId]
        if (!detail) return prev
        return { ...prev, [serviceId]: { ...detail, documents: [...detail.documents, res.data] } }
      })
      // Refresh task status (upload auto-transitions not_started → in_progress)
      const refreshed = detailCache[serviceId]
      if (refreshed) {
        setDetailCache((prev) => ({
          ...prev,
          [serviceId]: {
            ...refreshed,
            documents: [...refreshed.documents, res.data],
            tasks: refreshed.tasks.map((t) =>
              t.id === taskId && t.status === 'not_started' ? { ...t, status: 'in_progress' } : t,
            ),
          },
        }))
      }
      showToast(`${file.name} uploaded`)
    } catch (e: unknown) {
      const msg = axios.isAxiosError(e) ? e.response?.data?.detail : 'Upload failed'
      showToast(typeof msg === 'string' ? msg : 'Upload failed')
    } finally {
      setUploadingTask(null)
    }
  }

  const taskDocsFor = (detail: EnrollmentServiceDetail, taskId: string) =>
    detail.documents.filter((d) => d.task_id === taskId)

  const allComplete = (tasks: EnrollmentTask[]) =>
    tasks.length > 0 && tasks.every((t) => t.status === 'complete')

  const filteredServices = services.filter((s) => (s.stage || 'pcb') === activeStage)

  const STAGE_TABS: Array<{ key: 'pcb' | 'nppes_setup' | 'enrollment' | 'mco_contracting'; label: string }> = [
    { key: 'pcb', label: 'PCB Certification' },
    { key: 'nppes_setup', label: 'NPPES / NPI Setup' },
    { key: 'enrollment', label: 'Enrollment — Stage 2' },
    { key: 'mco_contracting', label: 'MCO Contracting — Stage 3' },
  ]

  if (loading) {
    return <div className="p-8 text-sm text-gray-500">Loading…</div>
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      {toast && (
        <div className="fixed top-4 right-4 z-50 rounded-lg bg-gray-900 px-4 py-2 text-sm text-white shadow-lg">
          {toast}
        </div>
      )}

      {/* Walkthrough Guide modal */}
      {showGuide && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
          onClick={() => setShowGuide(false)}
        >
          <div
            className="bg-white rounded-xl shadow-2xl w-full max-w-4xl max-h-[92vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal header */}
            <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-start justify-between rounded-t-xl z-10">
              <div>
                <h2 className="text-base font-semibold text-gray-900">Enrollment Services — How It Works</h2>
                <p className="text-xs text-gray-500 mt-0.5">A four-stage credentialing pipeline. Each stage gates the next. All management is admin-only; providers view status and upload documents.</p>
              </div>
              <button onClick={() => setShowGuide(false)} className="text-gray-400 hover:text-gray-600 text-xl leading-none ml-6 mt-0.5">×</button>
            </div>

            {/* Pipeline overview */}
            <div className="px-6 pt-5 pb-4">
              <div className="flex items-center gap-1 overflow-x-auto pb-1">
                {[
                  { label: 'PCB Certification', color: 'bg-gray-100 text-gray-700 border-gray-200', dot: 'bg-gray-400' },
                  { label: 'NPPES / NPI Setup', color: 'bg-indigo-50 text-indigo-700 border-indigo-200', dot: 'bg-indigo-500' },
                  { label: 'Enrollment — Stage 2', color: 'bg-blue-50 text-blue-700 border-blue-200', dot: 'bg-blue-500' },
                  { label: 'MCO Contracting — Stage 3', color: 'bg-purple-50 text-purple-700 border-purple-200', dot: 'bg-purple-500' },
                ].map((s, i) => (
                  <div key={i} className="flex items-center gap-1 shrink-0">
                    <span className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold ${s.color}`}>
                      <span className={`h-1.5 w-1.5 rounded-full ${s.dot}`} />
                      {s.label}
                    </span>
                    {i < 3 && <span className="text-gray-300 text-sm">→</span>}
                  </div>
                ))}
              </div>
            </div>

            <div className="px-6 pb-6 space-y-5">

              {/* Stage 1: PCB */}
              <div className="rounded-lg border border-gray-200 overflow-hidden">
                <div className="flex items-center gap-3 bg-gray-50 px-4 py-3 border-b border-gray-200">
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-gray-700 text-xs font-bold text-white">1</span>
                  <div className="flex-1">
                    <p className="text-sm font-semibold text-gray-900">PCB Certification</p>
                    <p className="text-xs text-gray-500">Pennsylvania Certification Board — Certified Perinatal Doula</p>
                  </div>
                  <span className="text-xs text-gray-400 italic">No gate — start here</span>
                </div>
                <div className="p-4 space-y-4">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div className="rounded-lg border border-gray-200 p-3">
                      <p className="text-xs font-semibold text-gray-700 mb-2">Education/Training Pathway (6 tasks)</p>
                      {[
                        'Training Certificate(s) — 24+ hours total',
                        'HIPAA/Confidentiality Training — 1+ hour',
                        'CPR Certification (adult + infant)',
                        'Client Evaluation #1',
                        'Client Evaluation #2',
                        'Client Evaluation #3',
                      ].map((t, i) => (
                        <div key={i} className="flex items-start gap-1.5 mt-1">
                          <span className="mt-0.5 h-3.5 w-3.5 shrink-0 rounded-full bg-gray-100 text-center text-[9px] font-bold text-gray-500 leading-3.5">{i + 1}</span>
                          <span className="text-xs text-gray-600">{t}</span>
                        </div>
                      ))}
                    </div>
                    <div className="rounded-lg border border-gray-200 p-3">
                      <p className="text-xs font-semibold text-gray-700 mb-2">Experienced Pathway (8 tasks)</p>
                      {[
                        'Proof of Active Doula Practice',
                        'CPR Certification (adult + infant)',
                        'Client Evaluation #1 (within last year)',
                        'Client Evaluation #2 (within last year)',
                        'Client Evaluation #3 (within last year)',
                        'Letter of Recommendation #1',
                        'Letter of Recommendation #2',
                        'Letter of Recommendation #3',
                      ].map((t, i) => (
                        <div key={i} className="flex items-start gap-1.5 mt-1">
                          <span className="mt-0.5 h-3.5 w-3.5 shrink-0 rounded-full bg-gray-100 text-center text-[9px] font-bold text-gray-500 leading-3.5">{i + 1}</span>
                          <span className="text-xs text-gray-600">{t}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="flex items-start gap-2 rounded-lg bg-amber-50 border border-amber-200 px-3 py-2.5">
                    <span className="text-amber-500 text-sm shrink-0">⚙</span>
                    <div>
                      <p className="text-xs font-semibold text-amber-800">How to complete this stage</p>
                      <ol className="mt-1 space-y-0.5 text-xs text-amber-700 list-decimal list-inside">
                        <li>Create a new enrollment service → select provider → select pathway (Education/Training or Experienced)</li>
                        <li>For each task: upload the document, add notes if needed, then click <strong>Mark Complete</strong></li>
                        <li>For training tasks: enter total hours — system warns if below 24 hrs (or 1 hr for HIPAA)</li>
                        <li>When all tasks are complete, click <strong>Mark PCB Certification Complete</strong> → enter the certificate issue date</li>
                        <li>DoulaShield writes the cert date to the provider's profile (<code>pcb_last_certified_on</code>) — visible in their Settings</li>
                      </ol>
                    </div>
                  </div>
                </div>
              </div>

              {/* Stage 2: NPPES */}
              <div className="rounded-lg border border-indigo-200 overflow-hidden">
                <div className="flex items-center gap-3 bg-indigo-50 px-4 py-3 border-b border-indigo-200">
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-indigo-600 text-xs font-bold text-white">2</span>
                  <div className="flex-1">
                    <p className="text-sm font-semibold text-gray-900">NPPES / NPI Setup</p>
                    <p className="text-xs text-indigo-600">Federal NPI application — agency acts as surrogate clerk</p>
                  </div>
                  <span className="inline-flex items-center gap-1 rounded-full bg-indigo-100 border border-indigo-200 px-2 py-0.5 text-xs text-indigo-700">
                    🔒 Requires PCB cert date on file
                  </span>
                </div>
                <div className="p-4 space-y-4">
                  <div className="rounded-lg border border-gray-200 p-3">
                    <p className="text-xs font-semibold text-gray-700 mb-2">7-Step NPI Application Workflow</p>
                    {[
                      ['Create I&A System Account', 'Use agency\'s existing I&A account + "Add Surrogate" — no new login needed per doula'],
                      ['Start NPI Application', 'Log in → Submit New NPI Application → Entity type: Type 1 (Individual)'],
                      ['Complete Provider Profile', 'Exact legal name as on SSN card; DOB, State/Country of Birth; Sole Proprietor: No'],
                      ['Enter Business Addresses', 'Mailing address (P.O. Box OK) + Practice location (P.O. Box not allowed)'],
                      ['Assign Taxonomy Code', 'Add Taxonomy → enter 374J00000X (Doula) — no PA state license number required'],
                      ['Contact Person & Identifiers', 'Leave Other Identifiers blank; add agency credentialing manager as Contact Person'],
                      ['Attest and Submit', 'Sign certification, click Submit — NPI issued via email within 1–5 business days'],
                    ].map(([label, detail], i) => (
                      <div key={i} className="flex items-start gap-2 mt-2">
                        <span className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-[9px] font-bold text-indigo-700 mt-0.5">{i + 1}</span>
                        <div>
                          <span className="text-xs font-medium text-gray-800">{label}</span>
                          <span className="text-xs text-gray-500"> — {detail}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                  <div className="flex items-start gap-2 rounded-lg bg-amber-50 border border-amber-200 px-3 py-2.5">
                    <span className="text-amber-500 text-sm shrink-0">⚙</span>
                    <div>
                      <p className="text-xs font-semibold text-amber-800">How to complete this stage</p>
                      <ol className="mt-1 space-y-0.5 text-xs text-amber-700 list-decimal list-inside">
                        <li>Create a new enrollment service → select provider → select stage <strong>NPPES / NPI Setup</strong></li>
                        <li>Work through the 7 tasks in order, uploading screenshots or confirmations as evidence</li>
                        <li>When the NPI arrives by email (usually within hours), record it in the task notes</li>
                        <li>When all 7 tasks are complete, click <strong>Mark NPI Setup Complete</strong> → enter the 10-digit NPI</li>
                        <li>DoulaShield writes the NPI to the provider's profile — visible in their Settings and used in all billing</li>
                      </ol>
                    </div>
                  </div>
                </div>
              </div>

              {/* Stage 3: Enrollment */}
              <div className="rounded-lg border border-blue-200 overflow-hidden">
                <div className="flex items-center gap-3 bg-blue-50 px-4 py-3 border-b border-blue-200">
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-blue-600 text-xs font-bold text-white">3</span>
                  <div className="flex-1">
                    <p className="text-sm font-semibold text-gray-900">Enrollment — Stage 2</p>
                    <p className="text-xs text-blue-600">PROMISe™ Type 13 & 130 + CAQH ProView enrollment</p>
                  </div>
                  <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 border border-blue-200 px-2 py-0.5 text-xs text-blue-700">
                    🔒 Requires NPI on file
                  </span>
                </div>
                <div className="p-4 space-y-4">
                  <div className="rounded-lg border border-gray-200 p-3">
                    <p className="text-xs font-semibold text-gray-700 mb-2">6 Required Documents & Actions</p>
                    {[
                      ['W-9 Form', 'IRS form — verify tax classification; must match provider\'s SSN or EIN'],
                      ['Government-Issued Photo ID', 'Driver\'s license or passport — name must match NPI application exactly'],
                      ['Liability Insurance Face Sheet', 'Must show provider name, policy number, coverage dates, and per-occurrence limits'],
                      ['PROMISe™ Type 13 Application', 'Medicaid FFS enrollment — submitted at promise.dhs.pa.gov using provider\'s NPI'],
                      ['PROMISe™ Type 130 Application', 'CHIP enrollment — same portal, separate application type'],
                      ['CAQH ProView Enrollment', 'Complete ProView profile; provider must attest every 120 days — set reminder'],
                    ].map(([label, detail], i) => (
                      <div key={i} className="flex items-start gap-2 mt-2">
                        <span className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-blue-100 text-[9px] font-bold text-blue-700 mt-0.5">{i + 1}</span>
                        <div>
                          <span className="text-xs font-medium text-gray-800">{label}</span>
                          <span className="text-xs text-gray-500"> — {detail}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                  <div className="flex items-start gap-2 rounded-lg bg-amber-50 border border-amber-200 px-3 py-2.5">
                    <span className="text-amber-500 text-sm shrink-0">⚙</span>
                    <div>
                      <p className="text-xs font-semibold text-amber-800">How to complete this stage</p>
                      <ol className="mt-1 space-y-0.5 text-xs text-amber-700 list-decimal list-inside">
                        <li>Create a new enrollment service → select provider → select stage <strong>Enrollment — Stage 2</strong></li>
                        <li>Collect W-9, photo ID, and liability face sheet from the provider; upload each to its task</li>
                        <li>Submit PROMISe™ Type 13 and 130 applications; upload confirmation screenshots</li>
                        <li>Complete CAQH ProView enrollment; note the CAQH ID in task notes</li>
                        <li>When all 6 tasks are complete, click <strong>Mark Enrollment Complete</strong> → enter PROMISe enrollment date + optional PROMISe ID and CAQH ID</li>
                        <li>DoulaShield writes <code>promise_last_enrolled_on</code> and <code>liability_insurance_expires_on</code> to the provider's profile</li>
                      </ol>
                    </div>
                  </div>
                </div>
              </div>

              {/* Stage 4: MCO Contracting */}
              <div className="rounded-lg border border-purple-200 overflow-hidden">
                <div className="flex items-center gap-3 bg-purple-50 px-4 py-3 border-b border-purple-200">
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-purple-600 text-xs font-bold text-white">4</span>
                  <div className="flex-1">
                    <p className="text-sm font-semibold text-gray-900">MCO Contracting — Stage 3</p>
                    <p className="text-xs text-purple-600">Join all 8 PA Medicaid managed care networks</p>
                  </div>
                  <span className="inline-flex items-center gap-1 rounded-full bg-purple-100 border border-purple-200 px-2 py-0.5 text-xs text-purple-700">
                    🔒 Requires Stage 2 complete
                  </span>
                </div>
                <div className="p-4 space-y-4">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div className="rounded-lg border border-gray-200 p-3">
                      <p className="text-xs font-semibold text-gray-700 mb-2">Supporting Documents (2 tasks)</p>
                      {['5-Year Work History', 'Resume / CV'].map((t, i) => (
                        <div key={i} className="flex items-start gap-1.5 mt-1">
                          <span className="mt-0.5 h-3.5 w-3.5 shrink-0 rounded-full bg-gray-100 text-center text-[9px] font-bold text-gray-500 leading-3.5">{i + 1}</span>
                          <span className="text-xs text-gray-600">{t}</span>
                        </div>
                      ))}
                    </div>
                    <div className="rounded-lg border border-gray-200 p-3">
                      <p className="text-xs font-semibold text-gray-700 mb-2">MCO Applications + LOI (8 tasks)</p>
                      {[
                        'AmeriHealth Caritas',
                        'Keystone First',
                        'UPMC For You',
                        'Geisinger Health Plan',
                        'Highmark Wholecare',
                        'UnitedHealthcare Community Plan',
                        'Aetna Better Health',
                        'Health Partners Plans',
                      ].map((mco, i) => (
                        <div key={i} className="flex items-start gap-1.5 mt-1">
                          <span className="mt-0.5 h-3.5 w-3.5 shrink-0 rounded-full bg-purple-100 text-center text-[9px] font-bold text-purple-600 leading-3.5">{i + 3}</span>
                          <span className="text-xs text-gray-600">{mco} — Application + LOI</span>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="flex items-start gap-2 rounded-lg bg-amber-50 border border-amber-200 px-3 py-2.5">
                    <span className="text-amber-500 text-sm shrink-0">⚙</span>
                    <div>
                      <p className="text-xs font-semibold text-amber-800">How to complete this stage</p>
                      <ol className="mt-1 space-y-0.5 text-xs text-amber-700 list-decimal list-inside">
                        <li>Create a new enrollment service → select provider → select stage <strong>MCO Contracting — Stage 3</strong></li>
                        <li>Collect the provider's 5-year work history and CV; upload each to its task</li>
                        <li>For each MCO: submit the credentialing application and Letter of Intent (LOI) through the MCO's provider portal</li>
                        <li>Note the application reference number and submission date in the task's notes field</li>
                        <li>Enter the contract date in the task row when a signed contract is returned; click <strong>Mark Complete</strong></li>
                        <li>When all 10 tasks are done, click <strong>Mark MCO Contracting Complete</strong></li>
                      </ol>
                    </div>
                  </div>
                </div>
              </div>

              {/* Key rules */}
              <div className="rounded-lg bg-gray-50 border border-gray-200 p-4">
                <p className="text-xs font-semibold text-gray-700 mb-2">Key Rules & Reminders</p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-1.5">
                  {[
                    ['Stage gates', 'Each stage can only be created once its prerequisite is met — DoulaShield enforces this automatically with a 422 error if you try to skip ahead'],
                    ['Multiple services', 'A provider can have one service per stage. Re-enrollment in a later stage requires the earlier stage\'s data to still be on file'],
                    ['Document uploads', 'Providers can upload their own documents from the Enrollment Status page — admins can also upload on their behalf from this page'],
                    ['Provider visibility', 'Providers see their task checklist and status in real time via Sidebar → Enrollment Status. They cannot mark tasks complete'],
                    ['NPI gate bypass', 'Providers who already have an NPI recorded in their profile can skip the NPPES Setup stage and go straight to Stage 2'],
                    ['CAQH re-attestation', 'Remind providers every 120 days. The CAQH Attestation Renewal banner on the Dashboard fires when ≤ 14 days remain'],
                  ].map(([label, text]) => (
                    <div key={label} className="flex items-start gap-1.5">
                      <span className="text-gray-400 mt-0.5 shrink-0">•</span>
                      <p className="text-xs text-gray-600"><span className="font-medium text-gray-800">{label}: </span>{text}</p>
                    </div>
                  ))}
                </div>
              </div>

            </div>

            <div className="sticky bottom-0 bg-white border-t border-gray-200 px-6 py-3 flex justify-end rounded-b-xl">
              <button
                onClick={() => setShowGuide(false)}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Enrollment Services</h1>
          <p className="mt-0.5 text-sm text-gray-500">
            Manage PCB certification, Medicaid enrollment, and MCO contracting for providers.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowGuide(true)}
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            How It Works
          </button>
          <button
            onClick={() => setShowNew(!showNew)}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            + New Enrollment Service
          </button>
        </div>
      </div>

      {/* New service form */}
      {showNew && (
        <div ref={newServiceFormRef} className="mb-6 rounded-lg border border-blue-200 bg-blue-50 p-5">
          <h2 className="mb-4 text-sm font-semibold text-blue-900">New Enrollment Service</h2>

          {/* Stage selection */}
          <div className="mb-4">
            <label className="mb-2 block text-xs font-medium text-gray-700">Stage</label>
            <div className="flex flex-wrap gap-3">
              {STAGE_TABS.map((tab) => (
                <label key={tab.key} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="newStage"
                    value={tab.key}
                    checked={newStage === tab.key}
                    onChange={() => setNewStage(tab.key as typeof newStage)}
                  />
                  <span className="text-sm font-medium text-gray-800">{tab.label}</span>
                </label>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-700">Provider</label>
              <select
                value={newProviderId}
                onChange={(e) => setNewProviderId(e.target.value)}
                className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              >
                <option value="">Select provider…</option>
                {providers.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.full_name ? `${p.full_name} (${p.email})` : p.email}
                  </option>
                ))}
              </select>
            </div>

            {newStage === 'pcb' && (
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-700">PCB Pathway</label>
                <div className="mt-1 space-y-2">
                  <label className="flex items-start gap-3 cursor-pointer">
                    <input
                      type="radio"
                      name="pathway"
                      value="education_training"
                      checked={newPathway === 'education_training'}
                      onChange={() => setNewPathway('education_training')}
                      className="mt-0.5"
                    />
                    <span className="text-sm">
                      <span className="font-medium text-gray-900">Education/Training</span>
                      <span className="block text-xs text-gray-500">Newly trained doula — no experience requirement</span>
                    </span>
                  </label>
                  <label className="flex items-start gap-3 cursor-pointer">
                    <input
                      type="radio"
                      name="pathway"
                      value="experienced"
                      checked={newPathway === 'experienced'}
                      onChange={() => setNewPathway('experienced')}
                      className="mt-0.5"
                    />
                    <span className="text-sm">
                      <span className="font-medium text-gray-900">Experienced</span>
                      <span className="block text-xs text-gray-500">Currently practicing doula</span>
                    </span>
                  </label>
                </div>
              </div>
            )}

            {newStage === 'nppes_setup' && (
              <div className="flex items-start">
                <p className="mt-3 text-xs text-gray-500">
                  Creates a 7-step NPPES checklist: I&amp;A account setup, NPI application, provider profile, business addresses,
                  taxonomy code (374J00000X), contact person, and attestation/submission.
                  Requires PCB certification to be on file. The issued NPI is recorded on completion.
                </p>
              </div>
            )}

            {newStage === 'enrollment' && (
              <div className="flex items-start">
                <p className="mt-3 text-xs text-gray-500">
                  Creates a Stage 2 checklist: W-9, Govt ID, Liability face sheet, PROMISe™ Type 13 &amp; 130 applications, and CAQH ProView enrollment.
                  Requires provider to have a PCB certification date and NPI on record.
                </p>
              </div>
            )}

            {newStage === 'mco_contracting' && (
              <div className="flex items-start">
                <p className="mt-3 text-xs text-gray-500">
                  Creates a Stage 3 checklist: 5-year work history, resume/CV, and individual applications for all 8 MCOs.
                  Requires a completed Stage 2 enrollment service for this provider.
                </p>
              </div>
            )}
          </div>

          {createError && <p className="mt-2 text-xs text-red-600">{createError}</p>}
          <div className="mt-4 flex gap-3">
            <button
              onClick={handleCreate}
              disabled={creating}
              className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {creating ? 'Creating…' : 'Create Service'}
            </button>
            <button
              onClick={() => { setShowNew(false); setCreateError(null) }}
              className="rounded border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Stage filter tabs */}
      <div className="mb-4 flex gap-1 border-b border-gray-200">
        {STAGE_TABS.map((tab) => {
          const count = services.filter((s) => (s.stage || 'pcb') === tab.key).length
          return (
            <button
              key={tab.key}
              onClick={() => setActiveStage(tab.key)}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeStage === tab.key
                  ? 'border-blue-600 text-blue-700'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {tab.label}
              {count > 0 && (
                <span className="ml-1.5 rounded-full bg-gray-100 px-1.5 py-0.5 text-xs text-gray-500">
                  {count}
                </span>
              )}
            </button>
          )
        })}
      </div>

      {/* Services list */}
      {filteredServices.length === 0 ? (
        <div className="rounded-lg border border-dashed border-gray-300 py-12 text-center text-sm text-gray-500">
          No {STAGE_TABS.find((t) => t.key === activeStage)?.label.toLowerCase()} services yet.{' '}
          Click &ldquo;+ New Enrollment Service&rdquo; to get started.
        </div>
      ) : (
        <div className="space-y-3">
          {filteredServices.map((svc) => {
            const detail = detailCache[svc.id]
            const isExpanded = expandedId === svc.id
            const isLoading = detailLoading[svc.id]
            const stage = svc.stage || 'pcb'

            return (
              <div key={svc.id} className="rounded-lg border border-gray-200 bg-white shadow-sm">
                {/* Row header */}
                <div className="flex items-stretch">
                  <button
                    onClick={() => toggleExpand(svc.id)}
                    className="flex flex-1 min-w-0 items-center justify-between px-4 py-3 text-left hover:bg-gray-50"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-gray-900">
                          {detail?.provider_name || detail?.provider_email || svc.provider_id.slice(0, 8) + '…'}
                        </p>
                        <p className="text-xs text-gray-500">
                          {detail?.provider_email || ''}
                          {svc.pcb_pathway ? ` · ${PATHWAY_LABELS[svc.pcb_pathway] ?? svc.pcb_pathway} pathway` : ''}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 ml-3">
                      {svc.assigned_to_billing_admin && (
                        <span className="rounded-full px-2 py-0.5 text-xs font-medium bg-indigo-100 text-indigo-700">
                          Agency
                        </span>
                      )}
                      {detail && (
                        <span className="text-xs text-gray-500">
                          {detail.tasks.filter((t) => t.status === 'complete').length}/{detail.tasks.length} tasks
                        </span>
                      )}
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STAGE_BADGE_COLORS[stage] ?? 'bg-gray-100 text-gray-600'}`}>
                        {STAGE_LABELS[stage] ?? stage}
                      </span>
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${SERVICE_STATUS_COLORS[svc.status] ?? 'bg-gray-100 text-gray-600'}`}>
                        {svc.status.replace('_', ' ')}
                      </span>
                      <span className="text-gray-400">{isExpanded ? '▲' : '▼'}</span>
                    </div>
                  </button>
                  {/* Assign to billing admin — separate from expand trigger */}
                  <div className="flex items-center gap-2 border-l border-gray-100 px-3">
                    <button
                      onClick={() => handleAssign(svc.id)}
                      disabled={assignLoading === svc.id}
                      title={svc.assigned_to_billing_admin ? 'Click to unassign from billing agency' : 'Hand this service off to the billing agency'}
                      className={`whitespace-nowrap rounded px-2 py-1 text-xs font-medium transition-colors disabled:opacity-50 ${
                        svc.assigned_to_billing_admin
                          ? 'bg-indigo-100 text-indigo-700 hover:bg-indigo-200'
                          : 'border border-gray-200 text-gray-500 hover:bg-gray-50 hover:text-indigo-600'
                      }`}
                    >
                      {assignLoading === svc.id ? '…' : svc.assigned_to_billing_admin ? '✓ Assigned to Agency' : 'Assign to Agency'}
                    </button>
                    {svc.status !== 'complete' && (
                      <button
                        onClick={() => handleDeleteService(svc.id)}
                        title="Delete this enrollment service"
                        className="rounded px-2 py-1 text-xs font-medium text-red-400 hover:bg-red-50 hover:text-red-600 transition-colors"
                      >
                        Delete
                      </button>
                    )}
                  </div>
                </div>

                {/* Expanded detail */}
                {isExpanded && (
                  <div className="border-t border-gray-100 px-4 pb-4 pt-3">
                    {isLoading ? (
                      <p className="text-sm text-gray-400">Loading…</p>
                    ) : detail ? (
                      <div className="space-y-4">
                        {/* Provider info copy bar */}
                        {(detail.provider_name || detail.provider_email || detail.provider_npi) && (
                          <div className="flex flex-wrap gap-2 rounded-lg border border-gray-100 bg-gray-50 px-3 py-2">
                            {detail.provider_name && (
                              <button
                                onClick={() => copyToClipboard(detail.provider_name!, 'Name')}
                                title="Copy provider name"
                                className="flex items-center gap-1.5 rounded border border-gray-200 bg-white px-2 py-1 text-xs text-gray-700 hover:bg-gray-100"
                              >
                                <svg className="h-3 w-3 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>
                                {detail.provider_name}
                              </button>
                            )}
                            {detail.provider_email && (
                              <button
                                onClick={() => copyToClipboard(detail.provider_email!, 'Email')}
                                title="Copy email"
                                className="flex items-center gap-1.5 rounded border border-gray-200 bg-white px-2 py-1 text-xs text-gray-700 hover:bg-gray-100"
                              >
                                <svg className="h-3 w-3 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>
                                {detail.provider_email}
                              </button>
                            )}
                            {detail.provider_npi && (
                              <button
                                onClick={() => copyToClipboard(detail.provider_npi!, 'NPI')}
                                title="Copy NPI"
                                className="flex items-center gap-1.5 rounded border border-gray-200 bg-white px-2 py-1 text-xs font-mono text-gray-700 hover:bg-gray-100"
                              >
                                <svg className="h-3 w-3 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>
                                NPI {detail.provider_npi}
                              </button>
                            )}
                          </div>
                        )}

                        {/* Tasks */}
                        <div>
                          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
                            Tasks
                          </p>
                          <div className="space-y-3">
                            {detail.tasks.map((task) => {
                              const docs = taskDocsFor(detail, task.id)
                              const isHours = task.task_key === 'pcb_training_hours'
                              const isHipaa = task.task_key === 'pcb_hipaa_cert'
                              const isMcoTask = task.task_key.startsWith('mco_') &&
                                task.task_key !== 'mco_work_history' &&
                                task.task_key !== 'mco_resume_cv'
                              const currentHours = taskHours[task.id] ??
                                String((task.task_data as Record<string, unknown> | null)?.hours ?? '')
                              const currentHipaaHours = taskHipaaHours[task.id] ??
                                String((task.task_data as Record<string, unknown> | null)?.hours ?? '')
                              const currentContractDate = taskContractDates[task.id] ??
                                String((task.task_data as Record<string, unknown> | null)?.contract_date ?? '')

                              return (
                                <div key={task.id} className="rounded border border-gray-100 bg-gray-50 p-3">
                                  <div className="flex items-start justify-between gap-2">
                                    <div className="flex-1 min-w-0">
                                      <p className="text-sm font-medium text-gray-800">{task.label}</p>
                                      {task.description && (
                                        <TaskDescription text={task.description} className="mt-0.5" />
                                      )}
                                    </div>
                                    <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[task.status]}`}>
                                      {task.status.replace('_', ' ')}
                                    </span>
                                  </div>

                                  {/* Hours inputs for training/HIPAA tasks */}
                                  {isHours && (
                                    <div className="mt-2 flex items-center gap-2">
                                      <label className="text-xs text-gray-600">Total training hours:</label>
                                      <input
                                        type="number"
                                        min={0}
                                        value={currentHours}
                                        onChange={(e) => setTaskHours((prev) => ({ ...prev, [task.id]: e.target.value }))}
                                        className="w-20 rounded border border-gray-300 px-2 py-1 text-xs focus:border-blue-500 focus:outline-none"
                                      />
                                      {parseInt(currentHours || '0', 10) < 24 && currentHours !== '' && (
                                        <span className="text-xs text-amber-600 font-medium">
                                          Needs {24 - parseInt(currentHours, 10)} more hour{24 - parseInt(currentHours, 10) !== 1 ? 's' : ''} to reach minimum
                                        </span>
                                      )}
                                      {parseInt(currentHours || '0', 10) >= 24 && (
                                        <span className="text-xs text-green-600 font-medium">✓ Meets 24-hour minimum</span>
                                      )}
                                    </div>
                                  )}
                                  {isHipaa && (
                                    <div className="mt-2 flex items-center gap-2">
                                      <label className="text-xs text-gray-600">HIPAA/confidentiality hours:</label>
                                      <input
                                        type="number"
                                        min={0}
                                        value={currentHipaaHours}
                                        onChange={(e) => setTaskHipaaHours((prev) => ({ ...prev, [task.id]: e.target.value }))}
                                        className="w-20 rounded border border-gray-300 px-2 py-1 text-xs focus:border-blue-500 focus:outline-none"
                                      />
                                      {parseInt(currentHipaaHours || '0', 10) < 1 && currentHipaaHours !== '' && (
                                        <span className="text-xs text-amber-600 font-medium">Needs ≥ 1 hour</span>
                                      )}
                                      {parseInt(currentHipaaHours || '0', 10) >= 1 && (
                                        <span className="text-xs text-green-600 font-medium">✓ Meets minimum</span>
                                      )}
                                    </div>
                                  )}

                                  {/* MCO contract date */}
                                  {isMcoTask && (
                                    <div className="mt-2 flex items-center gap-2">
                                      <label className="text-xs text-gray-600 whitespace-nowrap">Contract signed:</label>
                                      <input
                                        type="date"
                                        value={currentContractDate}
                                        onChange={(e) => setTaskContractDates((prev) => ({ ...prev, [task.id]: e.target.value }))}
                                        className="rounded border border-gray-300 px-2 py-1 text-xs focus:border-blue-500 focus:outline-none"
                                      />
                                    </div>
                                  )}

                                  {/* Notes */}
                                  <div className="mt-2 flex items-center gap-1">
                                    <input
                                      type="text"
                                      placeholder="Notes (optional)"
                                      value={taskNotes[task.id] ?? task.notes ?? ''}
                                      onChange={(e) => setTaskNotes((prev) => ({ ...prev, [task.id]: e.target.value }))}
                                      className="flex-1 rounded border border-gray-200 px-2 py-1 text-xs text-gray-700 placeholder-gray-400 focus:border-blue-500 focus:outline-none"
                                    />
                                    {(taskNotes[task.id] || task.notes) && (
                                      <button
                                        onClick={() => copyToClipboard(taskNotes[task.id] ?? task.notes ?? '', 'Notes')}
                                        title="Copy notes"
                                        className="shrink-0 rounded border border-gray-200 p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
                                      >
                                        <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" /></svg>
                                      </button>
                                    )}
                                  </div>

                                  {/* Documents */}
                                  {docs.length > 0 && (
                                    <div className="mt-2 space-y-1">
                                      {docs.map((doc) => (
                                        <div key={doc.id} className="group flex items-center gap-2 text-xs text-gray-600">
                                          <span className="text-gray-400">📎</span>
                                          <button
                                            onClick={() => downloadDocument(svc.id, doc.id, doc.file_name)}
                                            className="text-blue-600 hover:underline text-left"
                                            title="Download document"
                                          >
                                            {doc.file_name}
                                          </button>
                                          {doc.document_type && (
                                            <span className="rounded bg-gray-200 px-1 py-0.5 text-gray-500">
                                              {doc.document_type}
                                            </span>
                                          )}
                                          <button
                                            onClick={() => handleDeleteDocument(svc.id, doc.id, doc.file_name)}
                                            title="Remove document"
                                            className="ml-auto rounded px-1.5 py-0.5 text-xs font-medium text-red-400 hover:bg-red-50 hover:text-red-600 border border-red-200 hover:border-red-400"
                                          >
                                            Remove
                                          </button>
                                        </div>
                                      ))}
                                    </div>
                                  )}

                                  {/* Actions */}
                                  <div className="mt-3 flex flex-wrap items-center gap-2">
                                    <label className="cursor-pointer">
                                      <input
                                        type="file"
                                        accept=".pdf,.jpg,.jpeg,.png"
                                        className="hidden"
                                        disabled={!!uploadingTask}
                                        onChange={(e) => {
                                          const file = e.target.files?.[0]
                                          if (file) {
                                            handleUploadDocument(svc.id, task.id, file, task.task_key)
                                            e.target.value = ''
                                          }
                                        }}
                                      />
                                      <span className={`inline-flex cursor-pointer rounded border border-gray-300 px-2 py-1 text-xs font-medium text-gray-600 hover:bg-gray-100 ${uploadingTask?.taskId === task.id ? 'opacity-50' : ''}`}>
                                        {uploadingTask?.taskId === task.id ? 'Uploading…' : '+ Upload Document'}
                                      </span>
                                    </label>

                                    {task.status !== 'complete' && (
                                      <button
                                        onClick={() => handleUpdateTask(svc.id, task, 'complete')}
                                        disabled={taskSaving[task.id]}
                                        className="rounded border border-green-300 bg-green-50 px-2 py-1 text-xs font-medium text-green-700 hover:bg-green-100 disabled:opacity-50"
                                      >
                                        {taskSaving[task.id] ? 'Saving…' : 'Mark Complete'}
                                      </button>
                                    )}
                                    {task.status === 'complete' && (
                                      <button
                                        onClick={() => handleUpdateTask(svc.id, task, 'in_progress')}
                                        disabled={taskSaving[task.id]}
                                        className="rounded border border-gray-300 px-2 py-1 text-xs font-medium text-gray-600 hover:bg-gray-100 disabled:opacity-50"
                                      >
                                        {taskSaving[task.id] ? 'Saving…' : 'Reopen'}
                                      </button>
                                    )}

                                    {(task.task_key === 'nppes_ia_account' || task.task_key === 'caqh_provider_authorization') && task.status !== 'complete' && (
                                      <button
                                        onClick={() => startScreenShare(task.id, detail.provider_name)}
                                        disabled={screenshareLoading === task.id}
                                        className="flex items-center gap-1.5 rounded border border-blue-300 bg-blue-50 px-2 py-1 text-xs font-medium text-blue-700 hover:bg-blue-100 disabled:opacity-50"
                                      >
                                        <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                                            d="M15 10l4.553-2.069A1 1 0 0121 8.82v6.36a1 1 0 01-1.447.893L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                                        </svg>
                                        {screenshareLoading === task.id ? 'Sending…' : 'Start doxy.me Screen-Share'}
                                      </button>
                                    )}
                                  </div>
                                </div>
                              )
                            })}
                          </div>
                        </div>

                        {/* Stage-specific "Mark Complete" section */}
                        {svc.status !== 'complete' && allComplete(detail.tasks) && stage === 'nppes_setup' && (
                          <div className="rounded-lg border border-indigo-200 bg-indigo-50 p-4">
                            <p className="text-sm font-medium text-indigo-800">All tasks complete</p>
                            <p className="mt-0.5 text-xs text-indigo-700">
                              Once the NPI has been issued via email, record it here to update the provider&apos;s
                              profile and unlock Stage 2 enrollment.
                            </p>
                            <button
                              onClick={() => setNpesModal({ serviceId: svc.id })}
                              className="mt-3 rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
                            >
                              Mark NPI Setup Complete
                            </button>
                          </div>
                        )}

                        {svc.status !== 'complete' && allComplete(detail.tasks) && stage === 'pcb' && (
                          <div className="rounded-lg border border-green-200 bg-green-50 p-4">
                            <p className="text-sm font-medium text-green-800">All tasks complete</p>
                            <p className="mt-0.5 text-xs text-green-700">
                              Once you have received the PCB certificate, record the issue date to
                              update the provider&apos;s credentialing profile.
                            </p>
                            <button
                              onClick={() => setPcbCompleteModal({ serviceId: svc.id })}
                              className="mt-3 rounded bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700"
                            >
                              Mark PCB Certification Complete
                            </button>
                          </div>
                        )}

                        {svc.status !== 'complete' && allComplete(detail.tasks) && stage === 'enrollment' && (
                          <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
                            <p className="text-sm font-medium text-blue-800">All tasks complete</p>
                            <p className="mt-0.5 text-xs text-blue-700">
                              Record the PROMISe™ enrollment date and IDs to complete Stage 2 and unlock Stage 3.
                            </p>
                            <button
                              onClick={() => setStage2Modal({ serviceId: svc.id })}
                              className="mt-3 rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
                            >
                              Mark Enrollment Complete
                            </button>
                          </div>
                        )}

                        {svc.status !== 'complete' && allComplete(detail.tasks) && stage === 'mco_contracting' && (
                          <div className="rounded-lg border border-purple-200 bg-purple-50 p-4">
                            <p className="text-sm font-medium text-purple-800">All tasks complete</p>
                            <p className="mt-0.5 text-xs text-purple-700">
                              Record the final contracting completion date to close out Stage 3.
                            </p>
                            <button
                              onClick={() => setStage3Modal({ serviceId: svc.id })}
                              className="mt-3 rounded bg-purple-600 px-4 py-2 text-sm font-medium text-white hover:bg-purple-700"
                            >
                              Mark MCO Contracting Complete
                            </button>
                          </div>
                        )}

                        {/* Completion banners */}
                        {svc.status === 'complete' && stage === 'nppes_setup' && (
                          <div className="rounded bg-indigo-50 px-3 py-2 text-xs text-indigo-700 flex items-center justify-between gap-3">
                            <span>NPI setup complete{svc.intake_data?.npi ? ` · NPI: ${svc.intake_data.npi}` : ''} — provider profile updated.</span>
                            <button
                              onClick={() => quickStartNextStage(svc.provider_id, 'enrollment')}
                              className="shrink-0 rounded border border-indigo-400 bg-white px-2 py-0.5 text-xs font-medium text-indigo-700 hover:bg-indigo-100"
                            >
                              Start Stage 2 →
                            </button>
                          </div>
                        )}

                        {svc.status === 'complete' && stage === 'pcb' && svc.pcb_cert_date && (
                          <div className="rounded bg-green-50 px-3 py-2 text-xs text-green-700 flex items-center justify-between gap-3">
                            <span>PCB certified on {svc.pcb_cert_date} — provider profile updated.</span>
                            <button
                              onClick={() => quickStartNextStage(svc.provider_id, 'nppes_setup')}
                              className="shrink-0 rounded border border-green-400 bg-white px-2 py-0.5 text-xs font-medium text-green-700 hover:bg-green-100"
                            >
                              Start NPPES Setup →
                            </button>
                          </div>
                        )}
                        {svc.status === 'complete' && stage === 'enrollment' && (
                          <div className="rounded bg-blue-50 px-3 py-2 text-xs text-blue-700 flex items-center justify-between gap-3">
                            <span>
                              Stage 2 enrollment complete
                              {svc.intake_data?.promise_id ? ` · PROMISe ID: ${svc.intake_data.promise_id}` : ''}
                              {svc.intake_data?.caqh_id ? ` · CAQH ID: ${svc.intake_data.caqh_id}` : ''}
                            </span>
                            <button
                              onClick={() => quickStartNextStage(svc.provider_id, 'mco_contracting')}
                              className="shrink-0 rounded border border-blue-400 bg-white px-2 py-0.5 text-xs font-medium text-blue-700 hover:bg-blue-100"
                            >
                              Start MCO Contracting →
                            </button>
                          </div>
                        )}
                        {svc.status === 'complete' && stage === 'mco_contracting' && (
                          <div className="rounded bg-purple-50 px-3 py-2 text-xs text-purple-700">
                            MCO contracting complete
                            {svc.intake_data?.contracted_on ? ` · Contracted on ${svc.intake_data.contracted_on}` : ''}
                          </div>
                        )}
                      </div>
                    ) : null}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* NPPES Complete modal */}
      {npesModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
            <h3 className="text-base font-semibold text-gray-900">Record NPI Number</h3>
            <p className="mt-1 text-sm text-gray-500">
              Enter the 10-digit NPI issued by NPPES. This will be saved to the provider&apos;s
              profile and unlock Stage 2 enrollment.
            </p>
            <div className="mt-4">
              <label className="mb-1 block text-xs font-medium text-gray-700">
                National Provider Identifier (NPI)
              </label>
              <input
                type="text"
                inputMode="numeric"
                maxLength={10}
                placeholder="10-digit NPI"
                value={npesNpi}
                onChange={(e) => setNpesNpi(e.target.value.replace(/\D/g, '').slice(0, 10))}
                className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
              />
              {npesNpi.length > 0 && npesNpi.length < 10 && (
                <p className="mt-1 text-xs text-amber-600">{10 - npesNpi.length} more digit{10 - npesNpi.length !== 1 ? 's' : ''} needed</p>
              )}
            </div>
            <div className="mt-4 flex justify-end gap-3">
              <button
                onClick={() => { setNpesModal(null); setNpesNpi('') }}
                className="rounded border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleCompleteNppes}
                disabled={npesSaving || npesNpi.length !== 10}
                className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
              >
                {npesSaving ? 'Saving…' : 'Save & Complete'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* PCB Complete modal */}
      {pcbCompleteModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
            <h3 className="text-base font-semibold text-gray-900">Record PCB Certificate</h3>
            <p className="mt-1 text-sm text-gray-500">
              Enter the issue date from the PCB certificate. This will update the provider&apos;s
              profile and mark the enrollment service complete.
            </p>
            <div className="mt-4">
              <label className="mb-1 block text-xs font-medium text-gray-700">Certificate Issue Date</label>
              <input
                type="date"
                value={pcbCertDate}
                onChange={(e) => setPcbCertDate(e.target.value)}
                className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              />
            </div>
            <div className="mt-4 flex justify-end gap-3">
              <button
                onClick={() => { setPcbCompleteModal(null); setPcbCertDate('') }}
                className="rounded border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleCompletePcb}
                disabled={pcbSaving || !pcbCertDate}
                className="rounded bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
              >
                {pcbSaving ? 'Saving…' : 'Save & Complete'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Stage 2 Complete modal */}
      {stage2Modal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
            <h3 className="text-base font-semibold text-gray-900">Complete Stage 2 — Enrollment</h3>
            <p className="mt-1 text-sm text-gray-500">
              Record the PROMISe™ enrollment date and IDs. This updates the provider&apos;s profile
              and unlocks Stage 3 (MCO Contracting).
            </p>
            <div className="mt-4 space-y-3">
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-700">PROMISe™ Enrollment Date <span className="text-red-500">*</span></label>
                <input
                  type="date"
                  value={stage2PromiseDate}
                  onChange={(e) => setStage2PromiseDate(e.target.value)}
                  className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-700">PROMISe™ Provider ID / ATN <span className="text-gray-400">(optional)</span></label>
                <input
                  type="text"
                  placeholder="e.g. 1234567890 or ATN-XXXXXXXX"
                  value={stage2PromiseId}
                  onChange={(e) => setStage2PromiseId(e.target.value)}
                  className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-700">CAQH ProView ID <span className="text-gray-400">(optional)</span></label>
                <input
                  type="text"
                  placeholder="e.g. 12345678"
                  value={stage2CaqhId}
                  onChange={(e) => setStage2CaqhId(e.target.value)}
                  className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-700">Liability Insurance Expiry <span className="text-gray-400">(optional)</span></label>
                <input
                  type="date"
                  value={stage2LiabilityExpiry}
                  onChange={(e) => setStage2LiabilityExpiry(e.target.value)}
                  className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                />
              </div>
            </div>
            <div className="mt-5 flex justify-end gap-3">
              <button
                onClick={() => {
                  setStage2Modal(null)
                  setStage2PromiseDate('')
                  setStage2PromiseId('')
                  setStage2CaqhId('')
                  setStage2LiabilityExpiry('')
                }}
                className="rounded border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleCompleteEnrollment}
                disabled={stage2Saving || !stage2PromiseDate}
                className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {stage2Saving ? 'Saving…' : 'Complete Stage 2'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Stage 3 Complete modal */}
      {stage3Modal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
            <h3 className="text-base font-semibold text-gray-900">Complete Stage 3 — MCO Contracting</h3>
            <p className="mt-1 text-sm text-gray-500">
              Record the date all MCO contracting was finalized. Individual MCO contract dates
              are tracked in each task&apos;s &ldquo;Contract signed&rdquo; field.
            </p>
            <div className="mt-4">
              <label className="mb-1 block text-xs font-medium text-gray-700">Contracting Completion Date <span className="text-red-500">*</span></label>
              <input
                type="date"
                value={stage3ContractedOn}
                onChange={(e) => setStage3ContractedOn(e.target.value)}
                className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              />
            </div>
            <div className="mt-4 flex justify-end gap-3">
              <button
                onClick={() => { setStage3Modal(null); setStage3ContractedOn('') }}
                className="rounded border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleCompleteMcoContracting}
                disabled={stage3Saving || !stage3ContractedOn}
                className="rounded bg-purple-600 px-4 py-2 text-sm font-medium text-white hover:bg-purple-700 disabled:opacity-50"
              >
                {stage3Saving ? 'Saving…' : 'Complete Stage 3'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
