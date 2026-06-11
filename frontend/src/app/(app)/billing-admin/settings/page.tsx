'use client'

import { useEffect, useState } from 'react'
import axios from 'axios'
import { getAccessToken } from '@/lib/auth'

interface AgencySettings {
  id: string
  name: string
  group_npi: string | null
  address: string | null
  city: string | null
  state: string | null
  zip: string | null
  phone: string | null
  availity_connected: boolean
  availity_npi: string | null
}

export default function BillingAdminSettingsPage() {
  const [settings, setSettings] = useState<AgencySettings | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [availityClientId, setAvailityClientId] = useState('')
  const [availityClientSecret, setAvailityClientSecret] = useState('')
  const [availityNpi, setAvailityNpi] = useState('')

  const api = process.env.NEXT_PUBLIC_API_URL
  const headers = { Authorization: `Bearer ${getAccessToken()}` }

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      try {
        const res = await axios.get<AgencySettings>(`${api}/api/v1/billing-admin/agency-settings`, { headers })
        setSettings(res.data)
        setAvailityNpi(res.data.availity_npi ?? '')
      } catch {
        setError('Failed to load agency settings.')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const handleSave = async () => {
    setSaving(true)
    setError(null)
    setSaved(false)
    try {
      const body: Record<string, string> = {}
      if (availityClientId) body.availity_client_id = availityClientId
      if (availityClientSecret) body.availity_client_secret = availityClientSecret
      if (availityNpi !== (settings?.availity_npi ?? '')) body.availity_npi = availityNpi
      const res = await axios.patch<AgencySettings>(`${api}/api/v1/billing-admin/agency-settings`, body, { headers })
      setSettings(res.data)
      setAvailityClientId('')
      setAvailityClientSecret('')
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch (e: unknown) {
      const msg = axios.isAxiosError(e) ? e.response?.data?.detail : 'Failed to save settings.'
      setError(String(msg || 'Failed to save settings.'))
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return <p className="text-sm text-gray-500">Loading…</p>
  }

  if (!settings) {
    return (
      <div className="rounded border border-red-200 bg-red-50 p-4 text-sm text-red-700">
        {error ?? 'No agency linked to your account.'}
      </div>
    )
  }

  return (
    <div className="max-w-2xl space-y-6">
      <h1 className="text-xl font-bold text-gray-900">Agency Settings</h1>

      {/* Agency info (read-only) */}
      <div className="rounded-lg border border-gray-200 bg-white p-5 space-y-3">
        <h2 className="text-sm font-semibold text-gray-700">Agency Information</h2>
        <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
          <dt className="text-gray-500">Agency Name</dt>
          <dd className="font-medium text-gray-900">{settings.name}</dd>
          <dt className="text-gray-500">Group NPI</dt>
          <dd className="font-mono text-gray-900">{settings.group_npi ?? <span className="text-gray-400">—</span>}</dd>
          {settings.address && (
            <>
              <dt className="text-gray-500">Address</dt>
              <dd className="text-gray-900">
                {settings.address}{settings.city ? `, ${settings.city}` : ''}{settings.state ? `, ${settings.state}` : ''} {settings.zip ?? ''}
              </dd>
            </>
          )}
          {settings.phone && (
            <>
              <dt className="text-gray-500">Phone</dt>
              <dd className="text-gray-900">{settings.phone}</dd>
            </>
          )}
        </dl>
        <p className="text-xs text-gray-400">Agency information is managed by your DoulaShield administrator.</p>
      </div>

      {/* Availity credentials */}
      <div className="rounded-lg border border-gray-200 bg-white p-5 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-700">Availity Credentials</h2>
          {settings.availity_connected ? (
            <span className="flex items-center gap-1 text-xs font-medium text-green-700">
              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
              Connected
            </span>
          ) : (
            <span className="text-xs text-gray-400">Not configured</span>
          )}
        </div>
        <p className="text-xs text-gray-500">
          These credentials are used to submit claims on behalf of all providers in your agency.
          Providers assigned to your agency will have their claims queued here for review before submission.
        </p>

        <div className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-gray-700">Availity NPI</label>
            <input
              type="text"
              value={availityNpi}
              onChange={e => setAvailityNpi(e.target.value)}
              maxLength={10}
              placeholder="10-digit NPI"
              className="mt-1 w-full rounded border border-gray-300 px-3 py-1.5 text-sm"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700">Client ID</label>
            <input
              type="text"
              value={availityClientId}
              onChange={e => setAvailityClientId(e.target.value)}
              placeholder={settings.availity_connected ? '●●●●●●●● saved' : 'Enter Availity Client ID'}
              className="mt-1 w-full rounded border border-gray-300 px-3 py-1.5 text-sm"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-700">Client Secret</label>
            <input
              type="password"
              value={availityClientSecret}
              onChange={e => setAvailityClientSecret(e.target.value)}
              placeholder={settings.availity_connected ? '●●●●●●●● saved' : 'Enter Availity Client Secret'}
              className="mt-1 w-full rounded border border-gray-300 px-3 py-1.5 text-sm"
            />
            <p className="mt-1 text-xs text-gray-400">Write-only — credentials are stored encrypted and never displayed.</p>
          </div>
        </div>

        {error && (
          <div className="rounded border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
            {error}
          </div>
        )}
        {saved && (
          <div className="rounded border border-green-200 bg-green-50 px-3 py-2 text-xs text-green-700">
            ✓ Settings saved successfully.
          </div>
        )}

        <button
          type="button"
          onClick={handleSave}
          disabled={saving}
          className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {saving ? 'Saving…' : 'Save Settings'}
        </button>
      </div>

      {/* Claim queue explanation */}
      <div className="rounded-lg border border-blue-100 bg-blue-50 p-4 text-xs text-blue-800 space-y-1">
        <p className="font-semibold">How agency claims work</p>
        <p>When a provider in your agency submits a claim, it appears in the Claims queue with "Pending Review" status. You review it here and click "Submit ↗" to send it to Availity using your agency credentials.</p>
        <p>If no Availity credentials are configured above, providers' claims go directly to Availity using their own individual credentials.</p>
      </div>
    </div>
  )
}
