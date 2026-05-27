'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import axios from 'axios'
import { getAccessToken } from '@/lib/auth'
import { PrenatalLog } from '@/types/domain'

const schema = z.object({
  log_type: z.enum(['prenatal', 'postnatal']),
  entry_date: z.string().min(1, 'Date is required'),
  entry: z.string().min(1, 'Entry is required'),
})
type FormData = z.infer<typeof schema>

export default function PrenatalLogPage() {
  const { clientId } = useParams<{ clientId: string }>()
  const [logs, setLogs] = useState<PrenatalLog[]>([])
  const [loading, setLoading] = useState(true)
  const [submitError, setSubmitError] = useState<string | null>(null)

  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { log_type: 'prenatal' },
  })

  const fetchLogs = () =>
    axios
      .get<PrenatalLog[]>(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/patients/${clientId}/prenatal-logs`,
        { headers: { Authorization: `Bearer ${getAccessToken()}` } }
      )
      .then((r) => setLogs(r.data))
      .finally(() => setLoading(false))

  useEffect(() => { fetchLogs() }, [clientId])

  const onSubmit = async (data: FormData) => {
    setSubmitError(null)
    try {
      await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/patients/${clientId}/prenatal-logs`,
        data,
        { headers: { Authorization: `Bearer ${getAccessToken()}` } }
      )
      reset()
      fetchLogs()
    } catch {
      setSubmitError('Failed to save entry.')
    }
  }

  return (
    <div className="max-w-2xl space-y-6">
      <h1 className="text-xl font-bold text-gray-900">Prenatal / Postnatal Log</h1>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 bg-white p-4 rounded-lg border border-gray-200">
        <div className="flex gap-4">
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700">Type</label>
            <select {...register('log_type')} className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm">
              <option value="prenatal">Prenatal</option>
              <option value="postnatal">Postnatal</option>
            </select>
          </div>
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700">Date</label>
            <input {...register('entry_date')} type="date" className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm" />
            {errors.entry_date && <p className="mt-1 text-xs text-red-600">{errors.entry_date.message}</p>}
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">Entry</label>
          <textarea {...register('entry')} rows={4} className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm" />
          {errors.entry && <p className="mt-1 text-xs text-red-600">{errors.entry.message}</p>}
        </div>
        {submitError && <p className="text-sm text-red-600">{submitError}</p>}
        <button type="submit" disabled={isSubmitting} className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
          Add entry
        </button>
      </form>

      {loading ? (
        <p className="text-sm text-gray-500">Loading…</p>
      ) : logs.length === 0 ? (
        <p className="text-sm text-gray-500">No log entries yet.</p>
      ) : (
        <div className="space-y-2">
          {logs.map((log) => (
            <div key={log.id} className="bg-white rounded-lg border border-gray-200 p-4">
              <div className="flex justify-between mb-1">
                <span className="text-xs font-semibold uppercase text-blue-600">{log.log_type}</span>
                <span className="text-xs text-gray-400">{log.entry_date}</span>
              </div>
              <p className="text-sm">{log.entry}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
