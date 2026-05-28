'use client'

import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import axios from 'axios'
import { getAccessToken } from '@/lib/auth'

interface SettingsFormData {
  npi: string
  availity_client_id: string
  availity_client_secret: string
}

export default function SettingsPage() {
  const [connected, setConnected] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  const { register, handleSubmit, setValue, formState: { isSubmitting } } = useForm<SettingsFormData>()

  useEffect(() => {
    axios
      .get<{ npi: string | null; availity_connected: boolean }>(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/me/provider-settings`,
        { headers: { Authorization: `Bearer ${getAccessToken()}` } }
      )
      .then((r) => {
        if (r.data.npi) setValue('npi', r.data.npi)
        setConnected(r.data.availity_connected)
      })
      .finally(() => setLoading(false))
  }, [setValue])

  const onSubmit = async (data: SettingsFormData) => {
    setSaveError(null)
    setSaved(false)
    try {
      const body: Record<string, string> = {}
      if (data.npi) body.npi = data.npi
      if (data.availity_client_id) body.availity_client_id = data.availity_client_id
      if (data.availity_client_secret) body.availity_client_secret = data.availity_client_secret

      const res = await axios.patch<{ npi: string | null; availity_connected: boolean }>(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/me/provider-settings`,
        body,
        { headers: { Authorization: `Bearer ${getAccessToken()}` } }
      )
      setConnected(res.data.availity_connected)
      setSaved(true)
    } catch {
      setSaveError('Failed to save. Please try again.')
    }
  }

  if (loading) return <p className="text-sm text-gray-500">Loading…</p>

  return (
    <div className="max-w-lg space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Provider settings</h1>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 bg-white p-6 rounded-lg border border-gray-200">
        <div>
          <h2 className="text-sm font-semibold text-gray-700 mb-3">NPI</h2>
          <label htmlFor="npi" className="block text-sm font-medium text-gray-700">
            National Provider Identifier
          </label>
          <input
            {...register('npi')}
            id="npi"
            type="text"
            inputMode="numeric"
            maxLength={10}
            placeholder="10-digit NPI"
            className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 sm:w-48"
          />
        </div>

        <div className="border-t pt-4">
          <div className="flex items-center gap-2 mb-3">
            <h2 className="text-sm font-semibold text-gray-700">Availity credentials</h2>
            {connected && (
              <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
                ✓ Connected
              </span>
            )}
          </div>
          <p className="text-xs text-gray-500 mb-3">
            Register a free account at availity.com using your NPI, then apply for API access to receive these credentials.
          </p>
          <div className="space-y-3">
            <div>
              <label htmlFor="availity_client_id" className="block text-sm font-medium text-gray-700">Client ID</label>
              <input
                {...register('availity_client_id')}
                id="availity_client_id"
                type="text"
                placeholder={connected ? '●●●●●● saved' : 'Enter Client ID'}
                className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
            <div>
              <label htmlFor="availity_client_secret" className="block text-sm font-medium text-gray-700">Client Secret</label>
              <input
                {...register('availity_client_secret')}
                id="availity_client_secret"
                type="password"
                placeholder={connected ? '●●●●●● saved' : 'Enter Client Secret'}
                className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
          </div>
        </div>

        {saveError && <p className="text-sm text-red-600">{saveError}</p>}
        {saved && <p className="text-sm text-green-600">Settings saved.</p>}

        <button
          type="submit"
          disabled={isSubmitting}
          className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {isSubmitting ? 'Saving…' : 'Save settings'}
        </button>
      </form>
    </div>
  )
}
