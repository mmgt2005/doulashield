'use client'

import { useEffect, useState, useCallback } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import axios from 'axios'
import { getAccessToken } from '@/lib/auth'
import { geocodeAddress, haversineFeet } from '@/lib/geo'
import { Patient, Visit } from '@/types/domain'
import { getSlotConfig } from '@/lib/visit-config'
import ImageUploadScanner from '@/components/ui/ImageUploadScanner'

const schema = z.object({
  visit_date: z.string().min(1, 'Visit date is required'),
  subjective: z.string().optional(),
  objective: z.string().optional(),
  assessment: z.string().optional(),
  plan: z.string().optional(),
  entry: z.string().optional(),
  birth_time: z.string().optional(),
  birth_location: z.string().optional(),
  birth_notes: z.string().optional(),
  source_image_path: z.string().optional(),
  visit_started_at: z.string().optional(),
  provider_latitude: z.number().optional(),
  provider_longitude: z.number().optional(),
})
type FormData = z.infer<typeof schema>

export default function VisitFormPage() {
  const { clientId, visitType } = useParams<{ clientId: string; visitType: string }>()
  const router = useRouter()
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [patient, setPatient] = useState<Patient | null>(null)

  // Start Visit state
  const [visitStarted, setVisitStarted] = useState<Date | null>(null)
  const [locating, setLocating] = useState(false)
  const [locationError, setLocationError] = useState<string | null>(null)
  const [distanceFt, setDistanceFt] = useState<number | null>(null)

  const slot = getSlotConfig(visitType)

  const { register, handleSubmit, setValue, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
  })

  useEffect(() => {
    if (!slot) return
    const headers = { Authorization: `Bearer ${getAccessToken()}` }
    const base = process.env.NEXT_PUBLIC_API_URL

    Promise.all([
      axios.get<Patient>(`${base}/api/v1/patients/${clientId}`, { headers }),
      axios.get<Visit>(`${base}/api/v1/patients/${clientId}/visits/${visitType}`, { headers }).catch(() => null),
    ]).then(([patientRes, visitRes]) => {
      setPatient(patientRes.data)
      if (visitRes) {
        const v = visitRes.data
        if (v.visit_date) setValue('visit_date', v.visit_date)
        if (v.subjective) setValue('subjective', v.subjective)
        if (v.objective) setValue('objective', v.objective)
        if (v.assessment) setValue('assessment', v.assessment)
        if (v.plan) setValue('plan', v.plan)
        if (v.entry) setValue('entry', v.entry)
        if (v.birth_time) setValue('birth_time', v.birth_time)
        if (v.birth_location) setValue('birth_location', v.birth_location)
        if (v.birth_notes) setValue('birth_notes', v.birth_notes)
        if (v.source_image_path) setValue('source_image_path', v.source_image_path)
        if (v.visit_started_at) {
          const started = new Date(v.visit_started_at)
          setVisitStarted(started)
          setValue('visit_started_at', v.visit_started_at)
          if (v.provider_latitude != null) setValue('provider_latitude', v.provider_latitude)
          if (v.provider_longitude != null) setValue('provider_longitude', v.provider_longitude)
          if (v.provider_latitude != null && v.provider_longitude != null && patientRes.data.latitude != null && patientRes.data.longitude != null) {
            setDistanceFt(haversineFeet(v.provider_latitude, v.provider_longitude, patientRes.data.latitude, patientRes.data.longitude))
          }
        }
      }
    }).catch(() => { /* non-blocking */ })
  }, [clientId, visitType, slot, setValue])

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
        setValue('provider_latitude', provLat)
        setValue('provider_longitude', provLng)
        setLocating(false)

        // Persist immediately without requiring full form save
        try {
          await axios.put(
            `${process.env.NEXT_PUBLIC_API_URL}/api/v1/patients/${clientId}/visits/${visitType}`,
            { visit_started_at: now.toISOString(), provider_latitude: provLat, provider_longitude: provLng },
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

    // Auto-save extracted address to patient profile
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

    // Auto-save extracted DOB to patient profile (only if not already set)
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

  const onSubmit = async (data: FormData) => {
    setSubmitError(null)
    try {
      await axios.put(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/patients/${clientId}/visits/${visitType}`,
        data,
        { headers: { Authorization: `Bearer ${getAccessToken()}` } }
      )
      router.push(`/clients/${clientId}`)
    } catch {
      setSubmitError('Failed to save visit. Please try again.')
    }
  }

  if (!slot) {
    return <p className="text-sm text-red-600">Unknown visit type.</p>
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

      {/* Start Visit panel */}
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
        </div>
      )}

      <ImageUploadScanner
        endpoint="/api/v1/ocr/handbook"
        extraFields={{ page_type: slot.ocrPageType, patient_id: clientId }}
        onExtracted={handleScanned}
        label={`Scan ${slot.label} Page`}
      />

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
          <h2 className="text-sm font-semibold text-gray-700 border-b pb-1">SOAP Note</h2>
          {(['subjective', 'objective', 'assessment', 'plan'] as const).map((field) => (
            <div key={field}>
              <label htmlFor={field} className="block text-sm font-medium text-gray-700 capitalize">{field}</label>
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
        <input type="hidden" {...register('provider_latitude')} />
        <input type="hidden" {...register('provider_longitude')} />

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
