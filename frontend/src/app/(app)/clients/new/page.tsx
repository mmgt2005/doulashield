'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import axios from 'axios'
import { getAccessToken } from '@/lib/auth'
import { geocodeAddress } from '@/lib/geo'
import ImageUploadScanner from '@/components/ui/ImageUploadScanner'
import AddressAutocomplete from '@/components/ui/AddressAutocomplete'

const schema = z.object({
  name: z.string().min(1, 'Name is required'),
  medicaid_id: z.string().min(1, 'Medicaid ID is required'),
  mco: z.string().optional(),
  address: z.string().optional(),
  latitude: z.number().optional(),
  longitude: z.number().optional(),
  medicaid_card_image_path: z.string().optional(),
})

type FormData = z.infer<typeof schema>

export default function NewClientPage() {
  const router = useRouter()
  const [error, setError] = useState<string | null>(null)

  const { register, handleSubmit, setValue, watch, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
  })

  const handleScanned = (data: Record<string, unknown>) => {
    if (data.name) setValue('name', String(data.name))
    if (data.medicaid_id) setValue('medicaid_id', String(data.medicaid_id))
    if (data.mco) setValue('mco', String(data.mco))
    if (data.address) setValue('address', String(data.address))
    if (data.image_path) setValue('medicaid_card_image_path', String(data.image_path))
  }

  const onSubmit = async (data: FormData) => {
    setError(null)
    try {
      if (data.address && (data.latitude == null || isNaN(data.latitude as number))) {
        const coords = await geocodeAddress(data.address)
        if (coords) {
          data.latitude = coords.lat
          data.longitude = coords.lng
        }
      }
      const res = await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/patients`,
        data,
        { headers: { Authorization: `Bearer ${getAccessToken()}` } }
      )
      router.push(`/clients/${res.data.id}`)
    } catch {
      setError('Failed to create client. Please try again.')
    }
  }

  return (
    <div className="max-w-lg space-y-4">
      <h1 className="text-2xl font-bold text-gray-900">Add new client</h1>

      <ImageUploadScanner
        endpoint="/api/v1/ocr/medicaid-card"
        onExtracted={handleScanned}
        label="Scan Medicaid Card"
      />

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 bg-white p-6 rounded-lg border border-gray-200">
        <div>
          <label htmlFor="name" className="block text-sm font-medium text-gray-700">Full name</label>
          <input
            {...register('name')}
            id="name"
            type="text"
            className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          {errors.name && <p className="mt-1 text-xs text-red-600">{errors.name.message}</p>}
        </div>

        <div>
          <label htmlFor="medicaid_id" className="block text-sm font-medium text-gray-700">Medicaid ID</label>
          <input
            {...register('medicaid_id')}
            id="medicaid_id"
            type="text"
            className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          {errors.medicaid_id && <p className="mt-1 text-xs text-red-600">{errors.medicaid_id.message}</p>}
        </div>

        <div>
          <label htmlFor="mco" className="block text-sm font-medium text-gray-700">MCO <span className="text-gray-400">(optional)</span></label>
          <input
            {...register('mco')}
            id="mco"
            type="text"
            placeholder="e.g. Molina, Anthem, UnitedHealthcare"
            className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>

        <div>
          <label htmlFor="address" className="block text-sm font-medium text-gray-700">Home address <span className="text-gray-400">(optional)</span></label>
          <AddressAutocomplete
            id="address"
            value={watch('address') ?? ''}
            onChange={(v) => setValue('address', v)}
            onSelect={(addr, lat, lng) => {
              setValue('address', addr)
              setValue('latitude', lat)
              setValue('longitude', lng)
            }}
            placeholder="123 Main St, City, State"
            inputClassName="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>

        <input type="hidden" {...register('latitude', { valueAsNumber: true })} />
        <input type="hidden" {...register('longitude', { valueAsNumber: true })} />
        <input type="hidden" {...register('medicaid_card_image_path')} />

        {error && <p className="text-sm text-red-600">{error}</p>}

        <div className="flex flex-col gap-3 pt-2 sm:flex-row">
          <button
            type="submit"
            disabled={isSubmitting}
            className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {isSubmitting ? 'Saving…' : 'Add client'}
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
