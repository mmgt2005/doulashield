'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import axios from 'axios'
import { getAccessToken } from '@/lib/auth'
import { Visit } from '@/types/domain'
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
})
type FormData = z.infer<typeof schema>

export default function VisitFormPage() {
  const { clientId, visitType } = useParams<{ clientId: string; visitType: string }>()
  const router = useRouter()
  const [submitError, setSubmitError] = useState<string | null>(null)

  const slot = getSlotConfig(visitType)

  const { register, handleSubmit, reset, setValue, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
  })

  useEffect(() => {
    if (!slot) return
    axios
      .get<Visit>(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/patients/${clientId}/visits/${visitType}`,
        { headers: { Authorization: `Bearer ${getAccessToken()}` } }
      )
      .then((r) => {
        const v = r.data
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
      })
      .catch(() => { /* 404 = new visit, form stays empty */ })
  }, [clientId, visitType, slot, setValue])

  const handleScanned = (data: Record<string, unknown>) => {
    // Remap OCR keys to form field names
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
