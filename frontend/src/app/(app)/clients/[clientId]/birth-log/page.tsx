'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import axios from 'axios'
import { getAccessToken } from '@/lib/auth'
import { BirthLog } from '@/types/domain'

const schema = z.object({
  birth_date: z.string().min(1, 'Birth date is required'),
  birth_time: z.string().optional(),
  birth_location: z.string().optional(),
  notes: z.string().optional(),
})
type FormData = z.infer<typeof schema>

export default function BirthLogPage() {
  const { clientId } = useParams<{ clientId: string }>()
  const [logs, setLogs] = useState<BirthLog[]>([])
  const [loading, setLoading] = useState(true)
  const [submitError, setSubmitError] = useState<string | null>(null)

  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
  })

  const fetchLogs = () =>
    axios
      .get<BirthLog[]>(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/patients/${clientId}/birth-logs`,
        { headers: { Authorization: `Bearer ${getAccessToken()}` } }
      )
      .then((r) => setLogs(r.data))
      .finally(() => setLoading(false))

  useEffect(() => { fetchLogs() }, [clientId])

  const onSubmit = async (data: FormData) => {
    setSubmitError(null)
    try {
      await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/patients/${clientId}/birth-logs`,
        data,
        { headers: { Authorization: `Bearer ${getAccessToken()}` } }
      )
      reset()
      fetchLogs()
    } catch {
      setSubmitError('Failed to save birth log.')
    }
  }

  return (
    <div className="max-w-2xl space-y-6">
      <h1 className="text-xl font-bold text-gray-900">Birth Log</h1>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 bg-white p-4 rounded-lg border border-gray-200">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="birth_date" className="block text-sm font-medium text-gray-700">Birth date</label>
            <input {...register('birth_date')} id="birth_date" type="date" className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm" />
            {errors.birth_date && <p className="mt-1 text-xs text-red-600">{errors.birth_date.message}</p>}
          </div>
          <div>
            <label htmlFor="birth_time" className="block text-sm font-medium text-gray-700">Birth time</label>
            <input {...register('birth_time')} id="birth_time" type="time" className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm" />
          </div>
        </div>
        <div>
          <label htmlFor="birth_location" className="block text-sm font-medium text-gray-700">Location</label>
          <input {...register('birth_location')} id="birth_location" type="text" className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm" />
        </div>
        <div>
          <label htmlFor="notes" className="block text-sm font-medium text-gray-700">Notes</label>
          <textarea {...register('notes')} id="notes" rows={4} className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm" />
        </div>
        {submitError && <p className="text-sm text-red-600">{submitError}</p>}
        <button type="submit" disabled={isSubmitting} className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
          Add birth record
        </button>
      </form>

      {loading ? (
        <p className="text-sm text-gray-500">Loading…</p>
      ) : logs.length === 0 ? (
        <p className="text-sm text-gray-500">No birth records yet.</p>
      ) : (
        <div className="space-y-2">
          {logs.map((log) => (
            <div key={log.id} className="bg-white rounded-lg border border-gray-200 p-4 space-y-1">
              <p className="text-sm font-medium">{log.birth_date}{log.birth_time ? ` at ${log.birth_time}` : ''}</p>
              {log.birth_location && <p className="text-sm text-gray-600">Location: {log.birth_location}</p>}
              {log.notes && <p className="text-sm text-gray-600">{log.notes}</p>}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
