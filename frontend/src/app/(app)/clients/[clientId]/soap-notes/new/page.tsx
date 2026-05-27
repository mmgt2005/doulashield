'use client'

import { useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import axios from 'axios'
import { getAccessToken } from '@/lib/auth'

const schema = z.object({
  visit_date: z.string().min(1, 'Visit date is required'),
  subjective: z.string().optional(),
  objective: z.string().optional(),
  assessment: z.string().optional(),
  plan: z.string().optional(),
})

type FormData = z.infer<typeof schema>

const fields: { key: keyof FormData; label: string; full?: boolean }[] = [
  { key: 'visit_date', label: 'Visit date' },
  { key: 'subjective', label: 'Subjective', full: true },
  { key: 'objective', label: 'Objective', full: true },
  { key: 'assessment', label: 'Assessment', full: true },
  { key: 'plan', label: 'Plan', full: true },
]

export default function NewSOAPNotePage() {
  const { clientId } = useParams<{ clientId: string }>()
  const router = useRouter()
  const [error, setError] = useState<string | null>(null)

  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
  })

  const onSubmit = async (data: FormData) => {
    setError(null)
    try {
      await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/patients/${clientId}/soap-notes`,
        data,
        { headers: { Authorization: `Bearer ${getAccessToken()}` } }
      )
      router.push(`/clients/${clientId}/soap-notes`)
    } catch {
      setError('Failed to save note. Please try again.')
    }
  }

  return (
    <div className="max-w-2xl space-y-4">
      <h1 className="text-xl font-bold text-gray-900">New SOAP Note</h1>
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 bg-white p-6 rounded-lg border border-gray-200">
        {fields.map(({ key, label, full }) => (
          <div key={key}>
            <label htmlFor={key} className="block text-sm font-medium text-gray-700">{label}</label>
            {full ? (
              <textarea
                {...register(key)}
                id={key}
                rows={4}
                className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm"
              />
            ) : (
              <input
                {...register(key)}
                id={key}
                type="date"
                className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm"
              />
            )}
            {errors[key] && (
              <p className="mt-1 text-xs text-red-600">{errors[key]?.message}</p>
            )}
          </div>
        ))}
        {error && <p className="text-sm text-red-600">{error}</p>}
        <div className="flex gap-3">
          <button
            type="submit"
            disabled={isSubmitting}
            className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            Save note
          </button>
          <button
            type="button"
            onClick={() => router.back()}
            className="rounded border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  )
}
