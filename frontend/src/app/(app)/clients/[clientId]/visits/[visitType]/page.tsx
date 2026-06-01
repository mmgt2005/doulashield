'use client'

import { useEffect, useState, useCallback } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import axios from 'axios'
import { getAccessToken } from '@/lib/auth'
import { geocodeAddress, haversineFeet } from '@/lib/geo'
import { Claim, Patient, Visit, VisitType } from '@/types/domain'
import { getSlotConfig, getPrevSlotInGroup } from '@/lib/visit-config'
import ImageUploadScanner from '@/components/ui/ImageUploadScanner'
import dynamic from 'next/dynamic'

const SignaturePad = dynamic(() => import('@/components/ui/SignaturePad'), { ssr: false })

function formatDuration(start: Date, end: Date): string {
  const mins = Math.round((end.getTime() - start.getTime()) / 60000)
  return mins >= 60 ? `${Math.floor(mins / 60)}h ${mins % 60}m` : `${mins}m`
}

function formatElapsed(secs: number): string {
  const h = Math.floor(secs / 3600)
  const m = Math.floor((secs % 3600) / 60)
  const s = secs % 60
  if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

const SOAP_PLACEHOLDERS: Record<string, string> = {
  subjective: 'How is the client feeling today? Did she report any specific concerns?',
  objective: 'What did you observe? (e.g., movement, mood, vitals, engagement level)',
  assessment: 'What is your professional assessment of her current status?',
  plan: 'What are the next steps for the client and the doula?',
}

const VISIT_BILLING = {
  prenatal:    { code: 'T1032', modifier: 'U7', rate: 100,  diag: ['Z32.2'], note: 'Document topics/support provided' },
  postnatal:   { code: 'T1032', modifier: 'U8', rate: 100,  diag: ['Z39.1'], note: 'Document physical/emotional recovery' },
  labor:       { code: 'T1033', modifier: '',   rate: 1000, diag: ['Z33.1'],           note: 'One per pregnancy — include time-in/out' },
  crisis_loss: { code: 'T1032', modifier: 'U9', rate: 175,  diag: ['Z39.2'],           note: 'Capped at 2 per year' },
} as const

function billingForVisit(vt: string) {
  if (vt === 'labor') return VISIT_BILLING.labor
  if (vt.startsWith('prenatal')) return VISIT_BILLING.prenatal
  if (vt.startsWith('postnatal')) return VISIT_BILLING.postnatal
  return VISIT_BILLING.crisis_loss
}

const MCO_CHANNEL: Record<string, 'availity' | 'uhc' | 'manual'> = {
  'AmeriHealth Caritas': 'availity',
  'Keystone First': 'availity',
  'Geisinger Health Plan': 'availity',
  'Highmark Wholecare': 'availity',
  'Aetna Better Health': 'availity',
  'UnitedHealthcare Community Plan': 'uhc',
  'UPMC For You': 'manual',
  'Health Partners Plans': 'manual',
  'FFS': 'manual',
}

const MCO_PORTAL: Record<string, { name: string; url: string }> = {
  'UPMC For You': { name: 'UPMC Provider Portal', url: 'https://provider.upmc.com/' },
  'Health Partners Plans': { name: 'HPPServe (Change Healthcare)', url: 'https://www.hppserve.com/' },
  'FFS': { name: 'PROMISe™ (PA DHS)', url: 'https://promise.dhs.pa.gov/portal/provider' },
}

function submissionChannel(mco: string | null | undefined): 'availity' | 'uhc' | 'manual' {
  if (!mco) return 'manual'
  return MCO_CHANNEL[mco] ?? 'manual'
}

const schema = z.object({
  visit_date: z.string().min(1, 'Visit date is required'),
  subjective: z.string().optional(),
  objective: z.string().optional(),
  assessment: z.string().optional(),
  plan: z.string().optional(),
  entry: z.string().optional(),
  birth_location: z.string().optional(),
  birth_notes: z.string().optional(),
  source_image_path: z.string().optional(),
  // Preprocess empty strings → undefined so Pydantic receives null (not "") for time/datetime columns
  birth_time: z.preprocess((v) => v === '' ? undefined : v, z.string().optional()),
  visit_started_at: z.preprocess((v) => v === '' ? undefined : v, z.string().optional()),
  visit_ended_at: z.preprocess((v) => v === '' ? undefined : v, z.string().optional()),
  provider_latitude: z.preprocess((v) => (v === '' || v == null) ? undefined : Number(v), z.number().optional()),
  provider_longitude: z.preprocess((v) => (v === '' || v == null) ? undefined : Number(v), z.number().optional()),
  location_type: z.enum(['in_person', 'telehealth']).default('in_person'),
  alternate_location: z.string().optional(),
  prior_auth_number: z.string().optional(),
})
type FormData = z.infer<typeof schema>

export default function VisitFormPage() {
  const { clientId, visitType } = useParams<{ clientId: string; visitType: string }>()
  const router = useRouter()
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [saveSuccess, setSaveSuccess] = useState(false)
  const [patient, setPatient] = useState<Patient | null>(null)
  const [referringNpi, setReferringNpi] = useState('')

  // Location type toggle
  const [locationType, setLocationType] = useState<'in_person' | 'telehealth'>('in_person')
  const [telehealthLink, setTelehealthLink] = useState<string | null>(null)
  const [telehealthStarted, setTelehealthStarted] = useState<Date | null>(null)

  // Start/end Visit state (in-person)
  const [visitStarted, setVisitStarted] = useState<Date | null>(null)
  const [visitEnded, setVisitEnded] = useState<Date | null>(null)
  const [elapsedSecs, setElapsedSecs] = useState(0)
  const [locating, setLocating] = useState(false)
  const [locationError, setLocationError] = useState<string | null>(null)
  const [distanceFt, setDistanceFt] = useState<number | null>(null)

  const slot = getSlotConfig(visitType)
  const forcedInPerson = visitType === 'prenatal_1'

  // Sequential enforcement
  const [blockedByPrev, setBlockedByPrev] = useState(false)

  // SOAP AI draft state
  const [translating, setTranslating] = useState(false)
  const [translateError, setTranslateError] = useState<string | null>(null)
  const [soapDraft, setSoapDraft] = useState<{ subjective: string | null; objective: string | null; assessment: string | null; plan: string | null } | null>(null)

  // MA 91 signature state
  const [ma91Status, setMa91Status] = useState<string | null>(null)
  const [ma91SignedByName, setMa91SignedByName] = useState<string | null>(null)
  const [ma91SignedAt, setMa91SignedAt] = useState<string | null>(null)
  const [ma91PatientName, setMa91PatientName] = useState('')
  const [ma91PatientEmail, setMa91PatientEmail] = useState('')
  const [ma91Submitting, setMa91Submitting] = useState(false)
  const [ma91Error, setMa91Error] = useState<string | null>(null)
  const [zipzignConnected, setZipzignConnected] = useState(false)

  // Claim state
  const [existingClaim, setExistingClaim] = useState<Claim | null>(null)
  const [claimSubmitting, setClaimSubmitting] = useState(false)
  const [claimError, setClaimError] = useState<string | null>(null)
  const [showCms1500, setShowCms1500] = useState(false)
  const [claimStatusChecking, setClaimStatusChecking] = useState(false)
  const [pdfPreviewUrl, setPdfPreviewUrl] = useState<string | null>(null)
  const [pdfLoading, setPdfLoading] = useState(false)
  const [uhcConnected, setUhcConnected] = useState(false)
  const [providerSsnConnected, setProviderSsnConnected] = useState(false)
  const [providerSignaturePath, setProviderSignaturePath] = useState<string | null>(null)

  const { register, handleSubmit, setValue, watch, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { location_type: 'in_person' },
  })

  useEffect(() => {
    if (!slot) return
    const headers = { Authorization: `Bearer ${getAccessToken()}` }
    const base = process.env.NEXT_PUBLIC_API_URL

    Promise.all([
      axios.get<Patient>(`${base}/api/v1/patients/${clientId}`, { headers }),
      axios.get<Visit>(`${base}/api/v1/patients/${clientId}/visits/${visitType}`, { headers }).catch(() => null),
      axios.get<{ npi: string | null; availity_connected: boolean; telehealth_link: string | null }>(
        `${base}/api/v1/auth/me/provider-settings`,
        { headers }
      ).catch(() => null),
      axios.get<Claim[]>(`${base}/api/v1/patients/${clientId}/claims`, { headers }).catch(() => null),
    ]).then(async ([patientRes, visitRes, settingsRes, claimsRes]) => {
      if (claimsRes?.data?.length) setExistingClaim(claimsRes.data[0])
      setPatient(patientRes.data)
      if (patientRes.data.referring_provider_npi) setReferringNpi(patientRes.data.referring_provider_npi)
      if (patientRes.data.email) setMa91PatientEmail(patientRes.data.email)
      if (settingsRes) {
        setTelehealthLink(settingsRes.data.telehealth_link ?? null)
        const s = settingsRes.data as { zipzign_connected?: boolean; uhc_connected?: boolean }
        setZipzignConnected(s.zipzign_connected ?? false)
        setUhcConnected(s.uhc_connected ?? false)
        setProviderSsnConnected(!!(s as { provider_ssn_connected?: boolean }).provider_ssn_connected)
        setProviderSignaturePath((s as { provider_signature_path?: string | null }).provider_signature_path ?? null)
      }
      if (visitRes) {
        const v = visitRes.data
        if (v.visit_date) {
          setValue('visit_date', v.visit_date)
        } else if (v.visit_started_at) {
          setValue('visit_date', v.visit_started_at.split('T')[0])
        }
        if (v.subjective) setValue('subjective', v.subjective)
        if (v.objective) setValue('objective', v.objective)
        if (v.assessment) setValue('assessment', v.assessment)
        if (v.plan) setValue('plan', v.plan)
        if (v.entry) setValue('entry', v.entry)
        if (v.birth_time) setValue('birth_time', v.birth_time)
        if (v.birth_location) setValue('birth_location', v.birth_location)
        if (v.birth_notes) setValue('birth_notes', v.birth_notes)
        if (v.source_image_path) setValue('source_image_path', v.source_image_path)
        if (v.alternate_location) setValue('alternate_location', v.alternate_location)
        if (v.prior_auth_number) setValue('prior_auth_number', v.prior_auth_number)
        if (v.location_type && visitType !== 'prenatal_1') {
          const lt = v.location_type as 'in_person' | 'telehealth'
          setLocationType(lt)
          setValue('location_type', lt)
        }
        if (v.ma91_status) setMa91Status(v.ma91_status)
        if (v.ma91_signed_by_name) {
          setMa91SignedByName(v.ma91_signed_by_name)
          setMa91PatientName(v.ma91_signed_by_name)
        }
        if (v.ma91_signed_at) setMa91SignedAt(v.ma91_signed_at)
        if (v.visit_ended_at) setVisitEnded(new Date(v.visit_ended_at))
        if (v.visit_started_at) {
          const started = new Date(v.visit_started_at)
          if (v.location_type === 'telehealth') {
            setTelehealthStarted(started)
          } else {
            setVisitStarted(started)
          }
          setValue('visit_started_at', v.visit_started_at)
          if (v.provider_latitude != null) setValue('provider_latitude', v.provider_latitude)
          if (v.provider_longitude != null) setValue('provider_longitude', v.provider_longitude)
          if (v.provider_latitude != null && v.provider_longitude != null && patientRes.data.latitude != null && patientRes.data.longitude != null) {
            setDistanceFt(haversineFeet(v.provider_latitude, v.provider_longitude, patientRes.data.latitude, patientRes.data.longitude))
          }
        }
      }

      // Check sequential enforcement: fetch previous visit in group
      const prevType = getPrevSlotInGroup(visitType as VisitType)
      if (prevType) {
        try {
          const prevRes = await axios.get<Visit>(
            `${base}/api/v1/patients/${clientId}/visits/${prevType}`,
            { headers }
          )
          if (!prevRes.data?.visit_ended_at) setBlockedByPrev(true)
        } catch {
          // 404 = previous visit never started → blocked
          setBlockedByPrev(true)
        }
      }
    }).catch(() => { /* non-blocking */ })
  }, [clientId, visitType, slot, setValue])

  // Live elapsed-time ticker — runs while visit is started but not ended
  useEffect(() => {
    const startTime = locationType === 'telehealth' ? telehealthStarted : visitStarted
    if (!startTime || visitEnded) return
    setElapsedSecs(Math.floor((Date.now() - startTime.getTime()) / 1000))
    const id = setInterval(() => {
      setElapsedSecs(Math.floor((Date.now() - startTime.getTime()) / 1000))
    }, 1000)
    return () => clearInterval(id)
  }, [visitStarted, telehealthStarted, visitEnded, locationType])

  const startTime = locationType === 'telehealth' ? telehealthStarted : visitStarted
  const durationMins = startTime && visitEnded
    ? Math.round((visitEnded.getTime() - startTime.getTime()) / 60000)
    : null
  const elapsedMins = Math.floor(elapsedSecs / 60)

  const handleStartVisit = useCallback(() => {
    setLocating(true)
    setLocationError(null)

    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const provLat = pos.coords.latitude
        const provLng = pos.coords.longitude
        const now = new Date()

        let dist: number | null = null
        if (patient?.latitude != null && patient?.longitude != null) {
          dist = haversineFeet(provLat, provLng, patient.latitude, patient.longitude)
        }

        setDistanceFt(dist)
        setVisitStarted(now)
        setValue('visit_started_at', now.toISOString())
        setValue('visit_date', now.toISOString().split('T')[0])
        setValue('provider_latitude', provLat)
        setValue('provider_longitude', provLng)
        setValue('location_type', 'in_person')
        setLocating(false)

        try {
          await axios.put(
            `${process.env.NEXT_PUBLIC_API_URL}/api/v1/patients/${clientId}/visits/${visitType}`,
            { visit_started_at: now.toISOString(), provider_latitude: provLat, provider_longitude: provLng, location_type: 'in_person' },
            { headers: { Authorization: `Bearer ${getAccessToken()}` } }
          )
        } catch { /* non-blocking */ }
      },
      (err) => {
        setLocating(false)
        setLocationError(err.code === 1 ? 'Location permission denied.' : 'Could not get location.')
      },
      { enableHighAccuracy: true, timeout: 10000 }
    )
  }, [patient, clientId, visitType, setValue])

  const handleStartTelehealth = useCallback(async () => {
    if (!telehealthLink) return
    window.open('https://doxy.me', '_blank', 'noopener')
    if (patient?.email) {
      const subject = encodeURIComponent('Your telehealth appointment link')
      const body = encodeURIComponent(
        `Hello,\n\nYour provider has started your telehealth appointment. Please click the link below to join:\n\n${telehealthLink}\n\nThank you.`
      )
      const a = document.createElement('a')
      a.href = `mailto:${patient.email}?subject=${subject}&body=${body}`
      a.click()
    }
    const now = new Date()
    setTelehealthStarted(now)
    setValue('visit_started_at', now.toISOString())
    setValue('visit_date', now.toISOString().split('T')[0])
    setValue('location_type', 'telehealth')
    try {
      await axios.put(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/patients/${clientId}/visits/${visitType}`,
        { visit_started_at: now.toISOString(), location_type: 'telehealth' },
        { headers: { Authorization: `Bearer ${getAccessToken()}` } }
      )
    } catch { /* non-blocking */ }
  }, [telehealthLink, patient, clientId, visitType, setValue])

  const handleEndVisit = useCallback(async () => {
    const now = new Date()
    setVisitEnded(now)
    setValue('visit_ended_at', now.toISOString())
    try {
      await axios.put(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/patients/${clientId}/visits/${visitType}`,
        { visit_ended_at: now.toISOString() },
        { headers: { Authorization: `Bearer ${getAccessToken()}` } }
      )
    } catch { /* non-blocking */ }
  }, [clientId, visitType, setValue])

  const handleScanned = async (data: Record<string, unknown>) => {
    const dateVal = data.entry_date ?? data.birth_date ?? data.visit_date
    if (dateVal) setValue('visit_date', String(dateVal))
    if (data.entry) setValue('entry', String(data.entry))
    if (data.birth_time) setValue('birth_time', String(data.birth_time))
    if (data.birth_location) setValue('birth_location', String(data.birth_location))
    if (data.notes) setValue('birth_notes', String(data.notes))
    if (data.subjective) setValue('subjective', String(data.subjective))
    if (data.objective) setValue('objective', String(data.objective))
    if (data.assessment) setValue('assessment', String(data.assessment))
    if (data.plan) setValue('plan', String(data.plan))
    if (data.image_path) setValue('source_image_path', String(data.image_path))

    const base = process.env.NEXT_PUBLIC_API_URL
    const headers = { Authorization: `Bearer ${getAccessToken()}` }

    if (data.address && patient) {
      try {
        const coords = await geocodeAddress(String(data.address))
        await axios.patch(
          `${base}/api/v1/patients/${clientId}`,
          { address: String(data.address), latitude: coords?.lat ?? null, longitude: coords?.lng ?? null },
          { headers }
        )
        setPatient((p) => p ? { ...p, address: String(data.address), latitude: coords?.lat ?? null, longitude: coords?.lng ?? null } : p)
      } catch { /* non-blocking */ }
    }

    if (data.date_of_birth && patient && !patient.date_of_birth) {
      try {
        await axios.patch(
          `${base}/api/v1/patients/${clientId}`,
          { date_of_birth: String(data.date_of_birth) },
          { headers }
        )
        setPatient((p) => p ? { ...p, date_of_birth: String(data.date_of_birth) } : p)
      } catch { /* non-blocking */ }
    }
  }

  const handleMa89Scanned = async (data: Record<string, unknown>) => {
    const updates: Record<string, unknown> = {}
    if (data.referring_provider_name) updates.referring_provider_name = String(data.referring_provider_name)
    if (data.referring_provider_npi) updates.referring_provider_npi = String(data.referring_provider_npi)
    if (Object.keys(updates).length > 0) {
      try {
        await axios.patch(
          `${process.env.NEXT_PUBLIC_API_URL}/api/v1/patients/${clientId}`,
          updates,
          { headers: { Authorization: `Bearer ${getAccessToken()}` } }
        )
        setPatient((p) => p ? { ...p, ...updates } as Patient : p)
      } catch { /* non-blocking */ }
    }
  }

  const handleDraftSoap = async () => {
    setTranslating(true)
    setTranslateError(null)
    setSoapDraft(null)
    try {
      const res = await axios.post<{ subjective: string | null; objective: string | null; assessment: string | null; plan: string | null }>(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/ocr/soap-translate`,
        {
          subjective: watch('subjective') || null,
          objective: watch('objective') || null,
          assessment: watch('assessment') || null,
          plan: watch('plan') || null,
          patient_id: clientId,
        },
        { headers: { Authorization: `Bearer ${getAccessToken()}` } }
      )
      setSoapDraft(res.data)
    } catch {
      setTranslateError('Translation failed — please try again.')
    } finally {
      setTranslating(false)
    }
  }

  const handleInPersonSign = async (dataUrl: string) => {
    setMa91Submitting(true)
    setMa91Error(null)
    try {
      await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/patients/${clientId}/visits/${visitType}/sign-in-person`,
        { signature_data_url: dataUrl, patient_name: ma91PatientName },
        { headers: { Authorization: `Bearer ${getAccessToken()}` } }
      )
      setMa91Status('signed')
      setMa91SignedByName(ma91PatientName)
      setMa91SignedAt(new Date().toISOString())
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setMa91Error(msg ?? 'Signature save failed — please try again.')
    } finally {
      setMa91Submitting(false)
    }
  }

  const handleRequestTelehealthSignature = async () => {
    setMa91Submitting(true)
    setMa91Error(null)
    try {
      await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/patients/${clientId}/visits/${visitType}/request-telehealth-signature`,
        { patient_email: ma91PatientEmail, patient_name: ma91PatientName, visit_date: watch('visit_date') || '' },
        { headers: { Authorization: `Bearer ${getAccessToken()}` } }
      )
      setMa91Status('pending')
      setMa91SignedByName(ma91PatientName)
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setMa91Error(msg ?? 'Failed to send signature request — please try again.')
    } finally {
      setMa91Submitting(false)
    }
  }

  const handleSubmitClaim = async () => {
    setClaimSubmitting(true)
    setClaimError(null)
    const billing = billingForVisit(visitType)
    const visitDate = watch('visit_date')
    const locType = watch('location_type') || locationType
    try {
      const res = await axios.post<Claim>(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/patients/${clientId}/claims`,
        {
          visit_type: visitType,
          service_date: visitDate,
          location_type: locType,
          diagnosis_codes: billing.diag,
        },
        { headers: { Authorization: `Bearer ${getAccessToken()}` } }
      )
      setExistingClaim(res.data)
      setShowCms1500(false)
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setClaimError(msg ?? 'Claim submission failed — please try again.')
    } finally {
      setClaimSubmitting(false)
    }
  }

  const handleCheckClaimStatus = async () => {
    if (!existingClaim) return
    setClaimStatusChecking(true)
    try {
      const res = await axios.post<Claim>(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/claims/${existingClaim.id}/status-check`,
        {},
        { headers: { Authorization: `Bearer ${getAccessToken()}` } }
      )
      setExistingClaim(res.data)
    } catch { /* non-blocking */ } finally {
      setClaimStatusChecking(false)
    }
  }

  const _fetchPdfBlob = async (): Promise<string> => {
    const res = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/api/v1/patients/${clientId}/visits/${visitType}/cms1500.pdf`,
      { headers: { Authorization: `Bearer ${getAccessToken()}` } }
    )
    if (!res.ok) throw new Error(await res.text())
    const blob = await res.blob()
    return URL.createObjectURL(blob)
  }

  const handleSaveReferringNpi = async (npi: string) => {
    if (!npi || npi === patient?.referring_provider_npi) return
    try {
      await axios.patch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/patients/${clientId}`,
        { referring_provider_npi: npi },
        { headers: { Authorization: `Bearer ${getAccessToken()}` } }
      )
      setPatient(p => p ? { ...p, referring_provider_npi: npi } : p)
    } catch { /* non-blocking */ }
  }

  const handleOpenCms1500 = async () => {
    setShowCms1500(true)
    setPdfLoading(true)
    setClaimError(null)
    try {
      const url = await _fetchPdfBlob()
      setPdfPreviewUrl(url)
    } catch {
      setClaimError('Could not load PDF preview — try "Download PDF" instead.')
    } finally {
      setPdfLoading(false)
    }
  }

  const handleCloseCms1500 = () => {
    setShowCms1500(false)
    if (pdfPreviewUrl) {
      URL.revokeObjectURL(pdfPreviewUrl)
      setPdfPreviewUrl(null)
    }
  }

  const handleDownloadPdf = async () => {
    try {
      const url = pdfPreviewUrl ?? await _fetchPdfBlob()
      const a = document.createElement('a')
      a.href = url
      a.download = `cms1500_${visitType}.pdf`
      a.click()
      if (!pdfPreviewUrl) URL.revokeObjectURL(url)
    } catch {
      setClaimError('PDF download failed — please try again.')
    }
  }

  const onSubmit = async (data: FormData) => {
    setSubmitError(null)
    try {
      await axios.put(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/patients/${clientId}/visits/${visitType}`,
        data,
        { headers: { Authorization: `Bearer ${getAccessToken()}` } }
      )
      setSaveSuccess(true)
      await new Promise((r) => setTimeout(r, 1500))
      router.push(`/clients/${clientId}`)
    } catch {
      setSubmitError('Failed to save visit. Please try again.')
    }
  }

  if (!slot) {
    return <p className="text-sm text-red-600">Unknown visit type.</p>
  }

  if (blockedByPrev) {
    const prevType = getPrevSlotInGroup(visitType as VisitType)
    const prevSlot = prevType ? getSlotConfig(prevType) : null
    return (
      <div className="max-w-2xl space-y-4">
        <div className="flex items-center gap-3">
          <button type="button" onClick={() => router.push(`/clients/${clientId}`)} className="text-sm text-gray-500 hover:text-gray-700">
            ← Back
          </button>
          <h1 className="text-xl font-bold text-gray-900">{slot.label}</h1>
        </div>
        <div className="rounded-lg border border-amber-300 bg-amber-50 p-4">
          <p className="text-sm font-medium text-amber-800">
            ⚠ You must end the previous visit before starting this one.
          </p>
          {prevType && prevSlot && (
            <a href={`/clients/${clientId}/visits/${prevType}`} className="mt-2 inline-block text-sm text-blue-600 hover:text-blue-800">
              → Go to {prevSlot.label}
            </a>
          )}
        </div>
      </div>
    )
  }

  const formatTime = (d: Date) =>
    d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

  const formatDist = (ft: number) =>
    ft >= 1000 ? `${(ft / 5280).toFixed(2)} mi` : `${Math.round(ft)} ft`

  return (
    <div className="max-w-2xl space-y-4">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => router.push(`/clients/${clientId}`)}
          className="text-sm text-gray-500 hover:text-gray-700"
        >
          ← Back
        </button>
        <h1 className="text-xl font-bold text-gray-900">{slot.label}</h1>
      </div>

      {/* Location type toggle */}
      <div className="flex rounded-lg border border-gray-200 overflow-hidden w-fit">
        <button
          type="button"
          onClick={() => { setLocationType('in_person'); setValue('location_type', 'in_person') }}
          className={`flex items-center gap-2 px-4 py-2 text-sm font-medium transition-colors ${
            locationType === 'in_person'
              ? 'bg-blue-600 text-white'
              : 'bg-white text-gray-700 hover:bg-gray-50'
          }`}
        >
          <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd" />
          </svg>
          In Person
        </button>
        <button
          type="button"
          onClick={() => { if (!forcedInPerson) { setLocationType('telehealth'); setValue('location_type', 'telehealth') } }}
          disabled={forcedInPerson}
          title={forcedInPerson ? 'First prenatal visit must be in-person' : undefined}
          className={`flex items-center gap-2 px-4 py-2 text-sm font-medium transition-colors border-l ${
            locationType === 'telehealth'
              ? 'bg-blue-600 text-white border-blue-600'
              : 'bg-white text-gray-700 border-gray-200'
          } ${forcedInPerson ? 'opacity-40 cursor-not-allowed' : 'hover:bg-gray-50'}`}
        >
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M15 10l4.553-2.069A1 1 0 0121 8.867v6.266a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
          </svg>
          Telehealth
        </button>
      </div>

      {/* In-person Start Visit panel */}
      {locationType === 'in_person' && (
        <>
          {!visitStarted ? (
            <div className="rounded-lg border border-gray-200 bg-white p-4">
              <p className="text-xs text-gray-500 mb-2">Record your arrival location and time before beginning the visit.</p>
              <button
                type="button"
                onClick={handleStartVisit}
                disabled={locating}
                className="flex items-center gap-2 rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                {locating ? 'Getting location…' : 'Start Visit'}
              </button>
              {locationError && <p className="mt-2 text-xs text-red-600">{locationError}</p>}
            </div>
          ) : distanceFt !== null && distanceFt > 500 ? (
            <div className="rounded-lg border border-amber-300 bg-amber-50 p-4">
              <p className="text-sm font-medium text-amber-800">
                ⚠ Started at {formatTime(visitStarted)}
              </p>
              <p className="text-xs text-amber-700 mt-0.5">
                You are {formatDist(distanceFt)} from the client's address — confirm you are at the correct location.
              </p>
              <p className="mt-2 text-xs font-medium text-amber-800">Are you meeting at a different location?</p>
              <input
                type="text"
                value={watch('alternate_location') ?? ''}
                onChange={(e) => setValue('alternate_location', e.target.value)}
                placeholder="Describe the location (e.g., clinic, hospital)"
                className="mt-1 w-full rounded border border-amber-300 bg-white px-3 py-1.5 text-sm focus:outline-none focus:border-amber-500"
              />
            </div>
          ) : (
            <div className="rounded-lg border border-green-200 bg-green-50 p-4">
              <p className="text-sm font-medium text-green-800">
                ✓ Started at {formatTime(visitStarted)}
                {distanceFt !== null
                  ? ` · ${formatDist(distanceFt)} from client`
                  : patient?.address
                    ? ' · Location not verified (address could not be geocoded)'
                    : ' · Location not verified (no address on file)'}
              </p>
              {visitEnded ? (
                <>
                  <p className={`mt-1 text-sm font-medium ${durationMins !== null && durationMins < 30 ? 'text-amber-700' : 'text-green-700'}`}>
                    ✓ Ended at {formatTime(visitEnded)} · Duration: {formatDuration(visitStarted, visitEnded)}
                    {durationMins !== null && durationMins < 30 && ' ⚠'}
                  </p>
                  {durationMins !== null && durationMins < 30 && (
                    <p className="mt-0.5 text-xs text-amber-600">Under 30 minutes — see billing warning below.</p>
                  )}
                </>
              ) : (
                <div className="mt-2 flex items-center gap-3">
                  <span className={`font-mono text-sm font-semibold tabular-nums ${elapsedMins < 30 ? 'text-amber-700' : 'text-green-700'}`}>
                    {formatElapsed(elapsedSecs)}
                    {elapsedMins < 30 && ` (${30 - elapsedMins} min to 30)`}
                  </span>
                  <button
                    type="button"
                    onClick={handleEndVisit}
                    className="rounded border border-red-300 bg-red-50 px-3 py-1.5 text-sm font-medium text-red-700 hover:bg-red-100"
                  >
                    End Visit
                  </button>
                </div>
              )}
            </div>
          )}
        </>
      )}

      {/* Telehealth panel */}
      {locationType === 'telehealth' && (
        <>
          {!telehealthLink ? (
            <div className="rounded-lg border border-gray-200 bg-white p-4">
              <p className="text-sm text-gray-600">Configure your telehealth meeting link in Settings before starting a telehealth session.</p>
              <a
                href="/settings"
                className="mt-2 inline-block text-sm text-blue-600 hover:text-blue-800"
              >
                → Go to Settings
              </a>
            </div>
          ) : !telehealthStarted ? (
            <div className="rounded-lg border border-gray-200 bg-white p-4">
              <p className="text-xs text-gray-500 mb-2">
                Opens doxy.me so you can log in and start your room. The client will receive their join link via email.
                {!patient?.email && (
                  <span className="block mt-1 text-amber-600">No client email on file — add one in the client profile to send the link automatically.</span>
                )}
              </p>
              <button
                type="button"
                onClick={handleStartTelehealth}
                className="flex items-center gap-2 rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
              >
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M15 10l4.553-2.069A1 1 0 0121 8.867v6.266a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
                Start Telehealth
              </button>
            </div>
          ) : (
            <div className="rounded-lg border border-green-200 bg-green-50 p-4">
              <p className="text-sm font-medium text-green-800">
                ✓ Telehealth session started at {formatTime(telehealthStarted)}
                {patient?.email && ' · Join link sent to client'}
              </p>
              {!patient?.email && (
                <p className="mt-1 text-xs text-amber-700">No client email on file — add one in the client profile to send the link automatically next time.</p>
              )}
              {visitEnded ? (
                <>
                  <p className={`mt-1 text-sm font-medium ${durationMins !== null && durationMins < 30 ? 'text-amber-700' : 'text-green-700'}`}>
                    ✓ Ended at {formatTime(visitEnded)} · Duration: {formatDuration(telehealthStarted, visitEnded)}
                    {durationMins !== null && durationMins < 30 && ' ⚠'}
                  </p>
                  {durationMins !== null && durationMins < 30 && (
                    <p className="mt-0.5 text-xs text-amber-600">Under 30 minutes — see billing warning below.</p>
                  )}
                </>
              ) : (
                <div className="mt-2 flex items-center gap-3">
                  <span className={`font-mono text-sm font-semibold tabular-nums ${elapsedMins < 30 ? 'text-amber-700' : 'text-green-700'}`}>
                    {formatElapsed(elapsedSecs)}
                    {elapsedMins < 30 && ` (${30 - elapsedMins} min to 30)`}
                  </span>
                  <button
                    type="button"
                    onClick={handleEndVisit}
                    className="rounded border border-red-300 bg-red-50 px-3 py-1.5 text-sm font-medium text-red-700 hover:bg-red-100"
                  >
                    End Visit
                  </button>
                </div>
              )}
            </div>
          )}
        </>
      )}

      <ImageUploadScanner
        endpoint="/api/v1/ocr/handbook"
        extraFields={{ page_type: slot.ocrPageType, patient_id: clientId }}
        onExtracted={handleScanned}
        label={`Scan ${slot.label} Page`}
      />

      {visitType === 'prenatal_1' && (
        <div className="rounded-lg border border-indigo-100 bg-indigo-50 p-3">
          <p className="mb-2 text-xs font-medium text-indigo-700">MA 89 — Physician Certification Form</p>
          <p className="mb-2 text-xs text-indigo-600">Scan the MA 89 to auto-fill the referring doctor name and NPI (Box 17 &amp; 17b on CMS 1500).</p>
          {patient?.referring_provider_name && (
            <p className="mb-2 text-xs text-green-700">✓ Referring doctor: {patient.referring_provider_name}{patient.referring_provider_npi ? ` · NPI ${patient.referring_provider_npi}` : ''}</p>
          )}
          <ImageUploadScanner
            endpoint="/api/v1/ocr/handbook"
            extraFields={{ page_type: 'ma_89', patient_id: clientId }}
            onExtracted={handleMa89Scanned}
            label="Scan MA 89 Form"
          />
        </div>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 bg-white p-4 rounded-lg border border-gray-200">
        <div>
          <label htmlFor="visit_date" className="block text-sm font-medium text-gray-700">Visit date</label>
          <input
            {...register('visit_date')}
            id="visit_date"
            type="date"
            className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm sm:w-48"
          />
          {errors.visit_date && <p className="mt-1 text-xs text-red-600">{errors.visit_date.message}</p>}
        </div>

        {slot.isLabor ? (
          <div className="space-y-4">
            <h2 className="text-sm font-semibold text-gray-700 border-b pb-1">Birth Details</h2>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label htmlFor="birth_time" className="block text-sm font-medium text-gray-700">Birth time</label>
                <input {...register('birth_time')} id="birth_time" type="time" className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm" />
              </div>
              <div>
                <label htmlFor="birth_location" className="block text-sm font-medium text-gray-700">Birth location</label>
                <input {...register('birth_location')} id="birth_location" type="text" className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm" />
              </div>
            </div>
            <div>
              <label htmlFor="birth_notes" className="block text-sm font-medium text-gray-700">Birth notes</label>
              <textarea {...register('birth_notes')} id="birth_notes" rows={3} className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm" />
            </div>
          </div>
        ) : (
          <div>
            <label htmlFor="entry" className="block text-sm font-medium text-gray-700">Visit notes</label>
            <textarea {...register('entry')} id="entry" rows={3} className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm" />
          </div>
        )}

        <div className="space-y-4">
          <div className="flex items-center gap-3 border-b pb-1">
            <h2 className="text-sm font-semibold text-gray-700">SOAP Note</h2>
            <button
              type="button"
              onClick={handleDraftSoap}
              disabled={translating}
              className="flex items-center gap-1.5 rounded border border-blue-300 bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700 hover:bg-blue-100 disabled:opacity-50"
            >
              {translating ? (
                <>
                  <span className="h-3 w-3 animate-spin rounded-full border-2 border-blue-400 border-t-transparent" />
                  Drafting…
                </>
              ) : (
                '✨ Draft SOAP Note'
              )}
            </button>
          </div>

          {translateError && <p className="text-xs text-red-600">{translateError}</p>}

          {soapDraft && (
            <div className="rounded-lg border border-blue-200 bg-blue-50 p-3 space-y-2">
              <p className="text-xs font-semibold text-blue-800">AI Clinical Draft — review before applying</p>
              {(['subjective', 'objective', 'assessment', 'plan'] as const).map((field) =>
                soapDraft[field] ? (
                  <div key={field}>
                    <p className="text-xs font-medium text-blue-700 capitalize">{field}</p>
                    <p className="text-xs text-blue-900 leading-relaxed">{soapDraft[field]}</p>
                  </div>
                ) : null
              )}
              <div className="flex gap-2 pt-1">
                <button
                  type="button"
                  onClick={() => {
                    if (soapDraft.subjective) setValue('subjective', soapDraft.subjective)
                    if (soapDraft.objective) setValue('objective', soapDraft.objective)
                    if (soapDraft.assessment) setValue('assessment', soapDraft.assessment)
                    if (soapDraft.plan) setValue('plan', soapDraft.plan)
                    setSoapDraft(null)
                  }}
                  className="rounded bg-blue-600 px-3 py-1 text-xs font-medium text-white hover:bg-blue-700"
                >
                  Apply to Form
                </button>
                <button
                  type="button"
                  onClick={() => setSoapDraft(null)}
                  className="rounded border border-blue-300 px-3 py-1 text-xs font-medium text-blue-700 hover:bg-blue-100"
                >
                  Dismiss
                </button>
              </div>
            </div>
          )}

          {(['subjective', 'objective', 'assessment', 'plan'] as const).map((field) => (
            <div key={field}>
              <label htmlFor={field} className="block text-sm text-gray-700">
                <span className="font-medium capitalize">{field}</span>
                <span className="ml-2 text-xs font-normal text-gray-400">— {SOAP_PLACEHOLDERS[field]}</span>
              </label>
              <textarea
                {...register(field)}
                id={field}
                rows={3}
                className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm"
              />
            </div>
          ))}
        </div>

        <input type="hidden" {...register('source_image_path')} />
        <input type="hidden" {...register('visit_started_at')} />
        <input type="hidden" {...register('visit_ended_at')} />
        <input type="hidden" {...register('provider_latitude')} />
        <input type="hidden" {...register('provider_longitude')} />
        <input type="hidden" {...register('location_type')} />
        <input type="hidden" {...register('alternate_location')} />
        <input type="hidden" {...register('prior_auth_number')} />

        {/* MA 91 Encounter Form Certification */}
        <div className="space-y-3 border-t pt-4">
          <h2 className="text-sm font-semibold text-gray-700">MA 91 Patient Certification</h2>
          <div className="rounded border border-gray-200 bg-gray-50 p-3">
            <p className="text-xs text-gray-600 leading-relaxed">
              <span className="font-medium">Official MA 91 Encounter Form Certification:</span>{' '}
              "My signature certifies that I received a service or item on the date listed above.
              I understand that payment for this service will be from Federal and State funds,
              and that any false claims or concealment of material may be prosecuted under Federal and State laws."
            </p>
          </div>

          {/* Signed status banner */}
          {ma91Status === 'signed' && (
            <div className="rounded-lg border border-green-200 bg-green-50 p-3">
              <p className="text-sm font-medium text-green-800">
                ✓ Signed by {ma91SignedByName}
                {ma91SignedAt && ` on ${new Date(ma91SignedAt).toLocaleDateString()}`}
              </p>
            </div>
          )}
          {ma91Status === 'pending' && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-3">
              <p className="text-sm font-medium text-amber-800">
                ⏳ Signature request sent to {ma91PatientName}
              </p>
              <p className="text-xs text-amber-700 mt-0.5">Patient will receive an email with the MA 91 form to sign.</p>
            </div>
          )}
          {ma91Status === 'declined' && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-3">
              <p className="text-sm font-medium text-red-800">✗ Patient declined the signature request</p>
            </div>
          )}

          {/* Patient name field — shown when not yet signed */}
          {ma91Status !== 'signed' && (
            <div>
              <label className="block text-sm font-medium text-gray-700">Patient name</label>
              <input
                type="text"
                value={ma91PatientName}
                onChange={(e) => setMa91PatientName(e.target.value)}
                placeholder="Patient's full name"
                className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
          )}

          {/* In-person canvas signature */}
          {locationType === 'in_person' && ma91Status !== 'signed' && (
            <div className="space-y-2">
              <p className="text-xs text-gray-500">Patient signs below on your device:</p>
              <SignaturePad
                onSave={handleInPersonSign}
                onClear={() => setMa91Error(null)}
                disabled={ma91Submitting || !ma91PatientName.trim()}
              />
              {!ma91PatientName.trim() && (
                <p className="text-xs text-gray-400">Enter patient name above before signing.</p>
              )}
            </div>
          )}

          {/* Telehealth e-signature via ZipZign */}
          {locationType === 'telehealth' && ma91Status !== 'signed' && ma91Status !== 'pending' && (
            <div className="space-y-2">
              {!zipzignConnected ? (
                <p className="text-xs text-gray-500">
                  Configure ZipZign in{' '}
                  <a href="/settings" className="text-blue-600 hover:text-blue-800">Settings</a>
                  {' '}to enable telehealth e-signatures.
                </p>
              ) : (
                <>
                  <label className="block text-sm font-medium text-gray-700">Patient email</label>
                  <input
                    type="email"
                    value={ma91PatientEmail}
                    onChange={(e) => setMa91PatientEmail(e.target.value)}
                    placeholder="patient@example.com"
                    className="block w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                  <button
                    type="button"
                    onClick={handleRequestTelehealthSignature}
                    disabled={ma91Submitting || !ma91PatientName.trim() || !ma91PatientEmail.trim()}
                    className="flex items-center gap-2 rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                  >
                    {ma91Submitting ? (
                      <>
                        <span className="h-3 w-3 animate-spin rounded-full border-2 border-white border-t-transparent" />
                        Sending…
                      </>
                    ) : (
                      '✉ Send MA 91 via Email'
                    )}
                  </button>
                </>
              )}
            </div>
          )}

          {ma91Error && <p className="text-xs text-red-600">{ma91Error}</p>}
        </div>

        {/* PA Medicaid Claim */}
        {(() => {
          const billing = billingForVisit(visitType)
          const channel = submissionChannel(patient?.mco)
          const submitLabel = channel === 'uhc' ? 'Submit to UnitedHealthcare' : 'Submit to Availity'
          return (
            <div className="space-y-3 border-t pt-4">
              <h2 className="text-sm font-semibold text-gray-700">PA Medicaid Claim</h2>

              {existingClaim ? (
                <div className="rounded-lg border border-green-200 bg-green-50 p-3 space-y-1">
                  <p className="text-sm font-medium text-green-800">
                    ✓ Claim {existingClaim.availity_claim_id ? `#${existingClaim.availity_claim_id}` : 'submitted'} · Status: {existingClaim.status ?? 'submitted'}
                  </p>
                  {existingClaim.submitted_at && (
                    <p className="text-xs text-green-700">
                      Submitted {new Date(existingClaim.submitted_at).toLocaleDateString()}
                    </p>
                  )}
                  <button
                    type="button"
                    onClick={handleCheckClaimStatus}
                    disabled={claimStatusChecking}
                    className="text-xs text-blue-600 hover:text-blue-800 disabled:opacity-50"
                  >
                    {claimStatusChecking ? 'Checking…' : 'Refresh status'}
                  </button>
                </div>
              ) : (
                <div className="rounded border border-gray-200 bg-gray-50 p-3 space-y-3">
                  {/* Auto-determined billing summary */}
                  <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-gray-700">
                    <span>Procedure: <span className="font-medium">{billing.code}</span>{billing.modifier && <span className="font-medium"> · {billing.modifier}</span>}</span>
                    <span>Rate: <span className="font-medium">${billing.rate.toFixed(2)}</span></span>
                    <span>Diagnosis: <span className="font-medium">{billing.diag.join(', ')}</span></span>
                  </div>
                  <p className="text-xs text-gray-500">{billing.note}</p>

                  {/* MCO-specific warnings */}
                  {patient?.mco && ['UPMC For You', 'AmeriHealth Caritas', 'Geisinger Health Plan'].includes(patient.mco) && (
                    <div className="rounded border border-blue-100 bg-blue-50 px-3 py-2 text-xs text-blue-800 space-y-1">
                      {patient.mco === 'UPMC For You' && (
                        <p>⏱ UPMC strictly enforces the 30-minute minimum — verify your start/end times before submitting.</p>
                      )}
                      {patient.mco === 'AmeriHealth Caritas' && (
                        <p>📋 AmeriHealth Caritas requires the signed MA 91 on file for 7 years per audit requirements.</p>
                      )}
                      {patient.mco === 'Geisinger Health Plan' && (
                        <p>🔐 Geisinger may require a prior authorization number in Block 23 — enter it below.</p>
                      )}
                    </div>
                  )}

                  {/* Manual MCOs: PDF download + portal link only */}
                  {channel === 'manual' ? (
                    <div className="space-y-2">
                      <p className="text-xs text-gray-600">
                        {patient?.mco ?? 'This MCO'} claims must be submitted directly through their portal.
                      </p>
                      <div className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={handleOpenCms1500}
                          className="rounded border border-gray-300 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50"
                        >
                          Preview &amp; Download CMS 1500
                        </button>
                        {patient?.mco && MCO_PORTAL[patient.mco] && (
                          <a
                            href={MCO_PORTAL[patient.mco].url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="rounded border border-blue-300 bg-blue-50 px-3 py-1.5 text-xs font-medium text-blue-700 hover:bg-blue-100"
                          >
                            Open {MCO_PORTAL[patient.mco].name} →
                          </a>
                        )}
                      </div>
                    </div>
                  ) : (
                    <>
                      {/* Block 17b — Referring Provider NPI (mandatory) */}
                      <div className="space-y-1">
                        <label className="block text-xs font-medium text-gray-700">
                          Referring Provider NPI <span className="text-red-500">*</span>
                          <span className="ml-1 font-normal text-gray-400">(Box 17b — required or claim will be rejected)</span>
                        </label>
                        <input
                          type="text"
                          maxLength={10}
                          placeholder="10-digit referring doctor NPI"
                          value={referringNpi}
                          onChange={(e) => setReferringNpi(e.target.value)}
                          onBlur={(e) => handleSaveReferringNpi(e.target.value)}
                          className="w-full rounded border border-gray-300 px-2 py-1 text-sm focus:border-blue-400 focus:outline-none"
                        />
                        {!referringNpi ? (
                          <p className="text-xs text-amber-600">⚠ Enter the referring doctor&apos;s NPI — saved to this client&apos;s profile for all visits</p>
                        ) : patient?.referring_provider_npi && (
                          <p className="text-xs text-gray-400">Saved to client profile</p>
                        )}
                      </div>

                      {/* Block 23 — Prior Auth Number */}
                      <div className="space-y-1">
                        <label className="block text-xs font-medium text-gray-700">
                          Prior Authorization Number
                          <span className="ml-1 font-normal text-gray-400">
                            (Box 23{patient?.mco === 'Geisinger Health Plan' ? ' — required for Geisinger' : ' — if required'})
                          </span>
                        </label>
                        <input
                          type="text"
                          placeholder="Authorization number if required"
                          value={watch('prior_auth_number') ?? ''}
                          onChange={(e) => setValue('prior_auth_number', e.target.value)}
                          className={`w-full rounded border px-2 py-1 text-sm focus:outline-none ${
                            patient?.mco === 'Geisinger Health Plan' && !watch('prior_auth_number')
                              ? 'border-amber-400 focus:border-amber-500'
                              : 'border-gray-300 focus:border-blue-400'
                          }`}
                        />
                      </div>

                      {/* UHC credentials warning */}
                      {channel === 'uhc' && !uhcConnected && (
                        <p className="text-xs text-amber-600">
                          ⚠ UHC API credentials not configured — add them in{' '}
                          <a href="/settings" className="underline">Settings</a> to submit electronically.
                        </p>
                      )}

                      {claimError && <p className="text-xs text-red-600">{claimError}</p>}
                      <button
                        type="button"
                        onClick={handleOpenCms1500}
                        className="rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
                      >
                        Preview CMS 1500 &amp; Submit
                      </button>
                    </>
                  )}
                </div>
              )}

              {/* CMS 1500 Preview Modal */}
              {showCms1500 && (
                <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/50 p-4 overflow-y-auto">
                  <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl my-8">
                    <div className="flex items-center justify-between border-b px-6 py-4">
                      <h3 className="text-base font-semibold text-gray-900">CMS 1500 Claim Preview</h3>
                      <button type="button" onClick={handleCloseCms1500} className="text-gray-400 hover:text-gray-600 text-xl leading-none">×</button>
                    </div>

                    {/* Inline PDF preview */}
                    <div className="px-6 pt-4">
                      {pdfLoading && (
                        <div className="flex items-center justify-center h-40 text-sm text-gray-500 gap-2">
                          <span className="h-4 w-4 animate-spin rounded-full border-2 border-blue-400 border-t-transparent" />
                          Loading form…
                        </div>
                      )}
                      {pdfPreviewUrl && !pdfLoading && (
                        <>
                          {/* Desktop: inline iframe (blocked on iOS Safari) */}
                          <iframe
                            src={pdfPreviewUrl}
                            className="hidden md:block w-full rounded border border-gray-200"
                            style={{ height: '520px' }}
                            title="CMS 1500 Preview"
                          />
                          {/* Mobile: open in new tab (iOS doesn't support PDF iframes) */}
                          <div className="block md:hidden rounded border border-gray-200 bg-gray-50 p-4 text-center">
                            <p className="mb-3 text-sm text-gray-600">PDF preview is not supported on mobile browsers.</p>
                            <a
                              href={pdfPreviewUrl}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-block rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
                            >
                              Open PDF ↗
                            </a>
                          </div>
                        </>
                      )}
                    </div>

                    <div className="px-6 py-4 space-y-3 text-sm">
                      <table className="w-full text-xs border-collapse">
                        <tbody>
                          <tr className="border-b"><td className="py-1.5 font-medium text-gray-500 w-1/3">Box 1 — Insurance type</td><td className="py-1.5 font-semibold">Medicaid ✓</td></tr>
                          <tr className="border-b"><td className="py-1.5 font-medium text-gray-500">Box 1a — Insured ID</td><td className="py-1.5">Medicaid ID on file</td></tr>
                          <tr className="border-b"><td className="py-1.5 font-medium text-gray-500">Box 2 — Patient name</td><td className="py-1.5">{patient?.name}</td></tr>
                          <tr className="border-b"><td className="py-1.5 font-medium text-gray-500">Box 3 — DOB / Sex</td><td className="py-1.5">{patient?.date_of_birth ?? '—'} / {patient?.gender === 'M' ? 'M' : 'F'}</td></tr>
                          <tr className="border-b"><td className="py-1.5 font-medium text-gray-500">Box 5 — Patient address</td><td className="py-1.5">{patient?.address ?? '—'}</td></tr>
                          <tr className="border-b"><td className="py-1.5 font-medium text-gray-500">Box 7 — Insured address</td><td className="py-1.5 text-gray-400">{patient?.address ?? '—'} (same as Box 5)</td></tr>
                          <tr className="border-b"><td className="py-1.5 font-medium text-gray-500">Box 11a — Insured DOB / Sex</td><td className="py-1.5 text-gray-400">{patient?.date_of_birth ?? '—'} / {patient?.gender === 'M' ? 'M' : 'F'} (same as Box 3)</td></tr>
                          <tr className="border-b"><td className="py-1.5 font-medium text-gray-500">Box 11c — Insurance plan</td><td className="py-1.5">{patient?.mco ?? '—'}</td></tr>
                          <tr className="border-b"><td className="py-1.5 font-medium text-gray-500">Box 11d — Other insurance</td><td className="py-1.5">{patient?.has_other_insurance ? 'YES' : 'NO'}</td></tr>
                          <tr className="border-b"><td className="py-1.5 font-medium text-gray-500">Box 12 — Patient signature</td><td className="py-1.5">{ma91Status === 'signed' ? `Signature on File · ${ma91SignedAt ? new Date(ma91SignedAt).toLocaleDateString() : ''}` : <span className="text-amber-600">⚠ MA 91 not signed</span>}</td></tr>
                          <tr className="border-b"><td className="py-1.5 font-medium text-gray-500">Box 13 — Assignment</td><td className="py-1.5 text-gray-400">Signature on File</td></tr>
                          <tr className="border-b">
                            <td className="py-1.5 font-medium text-gray-500">Box 17 — Referring doctor</td>
                            <td className="py-1.5">{patient?.referring_provider_name ?? <span className="text-gray-400">—</span>}</td>
                          </tr>
                          <tr className="border-b">
                            <td className="py-1.5 font-medium text-gray-500">Box 17b — Referring NPI</td>
                            <td className={`py-1.5 ${!referringNpi ? 'text-red-500' : 'font-semibold'}`}>
                              {referringNpi || '⚠ Missing — claim will be rejected'}
                            </td>
                          </tr>
                          <tr className="border-b"><td className="py-1.5 font-medium text-gray-500">Box 21 — Diagnosis</td><td className="py-1.5 font-semibold">{billing.diag.join(', ')}</td></tr>
                          <tr className="border-b"><td className="py-1.5 font-medium text-gray-500">Box 23 — Prior Auth</td><td className="py-1.5">{watch('prior_auth_number') || '—'}</td></tr>
                          <tr className="border-b"><td className="py-1.5 font-medium text-gray-500">Box 24A — Service date</td><td className="py-1.5">{watch('visit_date') ?? '—'}</td></tr>
                          <tr className="border-b"><td className="py-1.5 font-medium text-gray-500">Box 24B — Place of service</td><td className="py-1.5">{locationType === 'telehealth' ? '02 (Telehealth)' : '12 (Home)'}</td></tr>
                          <tr className="border-b"><td className="py-1.5 font-medium text-gray-500">Box 24D — Procedure / Modifier</td><td className="py-1.5 font-semibold">{billing.code}{billing.modifier && ` · ${billing.modifier}`}</td></tr>
                          <tr className="border-b"><td className="py-1.5 font-medium text-gray-500">Box 24F — Charge</td><td className="py-1.5 font-semibold">${billing.rate.toFixed(2)}</td></tr>
                          <tr className="border-b"><td className="py-1.5 font-medium text-gray-500">Box 24G — Units</td><td className="py-1.5">1</td></tr>
                          <tr className="border-b">
                            <td className="py-1.5 font-medium text-gray-500">Box 25 — Tax ID (SSN)</td>
                            <td className={`py-1.5 ${!providerSsnConnected ? 'text-amber-600' : 'text-green-700'}`}>
                              {providerSsnConnected ? '●●●●●●●●● on file' : '⚠ Missing — add SSN in Settings'}
                            </td>
                          </tr>
                          <tr className="border-b"><td className="py-1.5 font-medium text-gray-500">Box 26 — Patient acct #</td><td className="py-1.5 text-gray-400">Last 8 of Medicaid ID</td></tr>
                          <tr className="border-b"><td className="py-1.5 font-medium text-gray-500">Box 28 — Total charge</td><td className="py-1.5 font-semibold">${billing.rate.toFixed(2)}</td></tr>
                          <tr className="border-b">
                            <td className="py-1.5 font-medium text-gray-500">Box 31 — Provider signature</td>
                            <td className={`py-1.5 ${!providerSignaturePath ? 'text-amber-600' : 'text-green-700'}`}>
                              {providerSignaturePath ? '✓ Signature on file' : '⚠ Missing — save signature in Settings'}
                            </td>
                          </tr>
                          <tr className="border-b"><td className="py-1.5 font-medium text-gray-500">Box 32 — Service facility</td><td className="py-1.5 text-gray-400">{watch('alternate_location') || (locationType === 'telehealth' ? 'Telehealth' : 'Patient Home')}</td></tr>
                          <tr className="border-b"><td className="py-1.5 font-medium text-gray-500">Box 33 — Taxonomy</td><td className="py-1.5">374J00000X (Certified Doula)</td></tr>
                        </tbody>
                      </table>
                      {claimError && <p className="text-xs text-red-600">{claimError}</p>}
                    </div>
                    <div className="flex gap-3 border-t px-6 py-4">
                      <button
                        type="button"
                        onClick={handleDownloadPdf}
                        className="rounded border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
                      >
                        Download PDF
                      </button>
                      {channel !== 'manual' && (
                        <button
                          type="button"
                          onClick={handleSubmitClaim}
                          disabled={claimSubmitting || (channel === 'uhc' && !uhcConnected)}
                          className="rounded bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                          title={channel === 'uhc' && !uhcConnected ? 'Add UHC API credentials in Settings first' : undefined}
                        >
                          {claimSubmitting ? (
                            <span className="flex items-center gap-2">
                              <span className="h-3 w-3 animate-spin rounded-full border-2 border-white border-t-transparent" />
                              Submitting…
                            </span>
                          ) : submitLabel}
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={() => setShowCms1500(false)}
                        className="ml-auto text-sm text-gray-500 hover:text-gray-700"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )
        })()}

        {durationMins !== null && durationMins < 30 && (
          <div className="rounded-lg border border-amber-300 bg-amber-50 p-3">
            <p className="text-sm font-medium text-amber-800">
              ⚠ Visit duration is {durationMins} min — Medicaid requires at least 30 minutes for T1032/T1033 reimbursement. Verify your start and end times before saving.
            </p>
          </div>
        )}
        {saveSuccess && (
          <div className="rounded-lg border border-green-200 bg-green-50 p-3">
            <p className="text-sm font-medium text-green-800">✓ Visit saved successfully.</p>
          </div>
        )}
        {submitError && <p className="text-sm text-red-600">{submitError}</p>}
        <div className="flex flex-col gap-3 sm:flex-row">
          <button
            type="submit"
            disabled={isSubmitting}
            className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            Save visit
          </button>
          <button
            type="button"
            onClick={() => router.push(`/clients/${clientId}`)}
            className="rounded border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  )
}
