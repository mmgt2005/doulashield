'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import axios from 'axios'
import { getAccessToken } from '@/lib/auth'
import { PrenatalLog } from '@/types/domain'
import ImageUploadScanner from '@/components/ui/ImageUploadScanner'

const schema = z.object({
  log_type: z.enum(['prenatal', 'postnatal']),
  entry_date: z.string().min(1, 'Date is required'),
  entry: z.string().min(1, 'Entry is required'),
  source_image_path: z.string().optional(),
})
type FormData = z.infer<typeof schema>

export default function PrenatalLogPage() {
  const { clientId } = useParams<{ clientId: string }>()
  const [logs, setLogs] = useState<PrenatalLog[]>([])
  const [loading, setLoading] = useState(true)
  const [submitError, setSubmitError] = useState<string | null>(null)

  const { register, handleSubmit, reset, setValue, formState: { errors, isSubmitting } } = useForm<FormData>({
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

  const handleScanned = (data: Record<string, unknown>) => {
    if (data.log_type === 'prenatal' || data.log_type === 'postnatal') {
      setValue('log_type', data.log_type)
    }
    if (data.entry_date) setValue('entry_date', String(data.entry_date))
    if (data.entry) setValue('entry', String(data.entry))
    if (data.image_path) setValue('source_image_path', String(data.image_path))
  }

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

      <ImageUploadScanner
        endpoint="/api/v1/ocr/handbook"
        extraFields={{ page_type: 'prenatal', patient_id: clientId }}
        onExtracted={handleScanned}
        label="Scan Visit Page"
      />

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 bg-white p-4 rounded-lg border border-gray-200">
        <div className="flex flex-col gap-4 sm:flex-row">
          <div className="flex-1">
            <label htmlFor="log_type" className="block text-sm font-medium text-gray-700">Type</label>
            <select {...register('log_type')} id="log_type" className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm">
              <option value="prenatal">Prenatal</option>
              <option value="postnatal">Postnatal</option>
            </select>
          </div>
          <div className="flex-1">
            <label htmlFor="entry_date" className="block text-sm font-medium text-gray-700">Date</label>
            <input {...register('entry_date')} id="entry_date" type="date" className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm" />
            {errors.entry_date && <p className="mt-1 text-xs text-red-600">{errors.entry_date.message}</p>}
          </div>
        </div>
        <div>
          <label htmlFor="entry" className="block text-sm font-medium text-gray-700">Entry</label>
          <textarea {...register('entry')} id="entry" rows={4} className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm" />
          {errors.entry && <p className="mt-1 text-xs text-red-600">{errors.entry.message}</p>}
        </div>
        <input type="hidden" {...register('source_image_path')} />
        {submitError && <p className="text-sm text-red-600">{submitError}</p>}
        <button type="submit" disabled={isSubmitting} className="w-full rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 sm:w-auto">
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
