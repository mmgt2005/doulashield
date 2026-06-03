'use client'

import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import axios from 'axios'
import { getAccessToken } from '@/lib/auth'
import { useAuthStore } from '@/store/auth-store'
import { BillingStatus } from '@/types/domain'
import AddressAutocomplete from '@/components/ui/AddressAutocomplete'

interface McoContractForm {
  mco: string
  contract_date: string  // "YYYY-MM-DD" or ""
}

interface SettingsFormData {
  npi: string
  billing_provider_name: string
  provider_address: string
  provider_phone: string
  availity_client_id: string
  availity_client_secret: string
  telehealth_link: string
  contact_email: string
  zipzign_api_key: string
  zone: string
  counties: string[]
  provider_ssn: string
  mco_contracts: McoContractForm[]
  caqh_last_attested_on: string
}

const ALL_MCOS = [
  'AmeriHealth Caritas',
  'Keystone First',
  'UPMC For You',
  'Geisinger Health Plan',
  'Health Partners Plans',
  'Aetna Better Health',
  'UnitedHealthcare Community Plan',
  'Highmark Wholecare',
  'FFS',
] as const

type ZoneKey = 'SE' | 'SW' | 'LC' | 'NE' | 'NW'

const PA_ZONES: Record<ZoneKey, { label: string; counties: string[]; mcos: string[] }> = {
  SE: {
    label: 'Southeast (SE)',
    counties: ['Bucks', 'Chester', 'Delaware', 'Montgomery', 'Philadelphia'],
    mcos: ['Keystone First', 'Health Partners Plans (HPP)', 'UnitedHealthcare Community Plan', 'Aetna Better Health', 'UPMC For You'],
  },
  SW: {
    label: 'Southwest (SW)',
    counties: ['Allegheny', 'Armstrong', 'Beaver', 'Bedford', 'Blair', 'Butler', 'Cambria', 'Fayette', 'Greene', 'Indiana', 'Lawrence', 'Somerset', 'Washington', 'Westmoreland'],
    mcos: ['UPMC For You', 'AmeriHealth Caritas', 'Highmark Wholecare', 'Geisinger Health Plan', 'Health Partners Plans (HPP)'],
  },
  LC: {
    label: 'Lehigh/Capital (LC)',
    counties: ['Adams', 'Berks', 'Cumberland', 'Dauphin', 'Franklin', 'Fulton', 'Huntingdon', 'Lancaster', 'Lebanon', 'Lehigh', 'Northampton', 'Perry', 'York'],
    mcos: ['AmeriHealth Caritas', 'Geisinger Health Plan', 'Highmark Wholecare', 'Health Partners Plans (HPP)', 'UPMC For You'],
  },
  NE: {
    label: 'Northeast (NE)',
    counties: ['Bradford', 'Carbon', 'Centre', 'Clinton', 'Columbia', 'Juniata', 'Lackawanna', 'Luzerne', 'Lycoming', 'Mifflin', 'Monroe', 'Montour', 'Northumberland', 'Pike', 'Schuylkill', 'Snyder', 'Sullivan', 'Susquehanna', 'Tioga', 'Union', 'Wayne', 'Wyoming'],
    mcos: ['Geisinger Health Plan', 'AmeriHealth Caritas', 'Health Partners Plans (HPP)', 'Highmark Wholecare', 'UPMC For You'],
  },
  NW: {
    label: 'Northwest (NW)',
    counties: ['Cameron', 'Clarion', 'Clearfield', 'Crawford', 'Elk', 'Erie', 'Forest', 'Jefferson', 'McKean', 'Mercer', 'Potter', 'Venango', 'Warren'],
    mcos: ['UPMC For You', 'AmeriHealth Caritas', 'Geisinger Health Plan', 'Health Partners Plans (HPP)'],
  },
}

const ESCROW_AGREEMENT_TEXT = `DoulaShield Escrow Agreement — Version 1.0

By signing below, you agree to the following terms governing the DoulaShield platform fee escrow arrangement:

1. NON-REFUNDABLE ENROLLMENT DEPOSIT
A one-time, non-refundable deposit of $99.00 USD is required to initiate the credentialing and onboarding process. This deposit is collected prior to app access and covers administrative costs associated with enrolling you in the PA Medicaid billing grid.

2. DEFERRED BALANCE
In addition to the enrollment deposit, a deferred balance of $400.00 USD is owed to DoulaShield for platform setup and credentialing services rendered. This balance is not due upfront. Instead, it will be collected automatically from your MCO remittance payments as follows: 50% of each MCO remittance check will be withheld and applied to this balance until the full $400.00 has been collected. If any single remittance equals or exceeds $400.00, the entire remaining balance will be collected from that payment.

3. MONTHLY PLATFORM SUBSCRIPTION
Upon activation of your account, a monthly subscription fee of $39.00 USD will be charged automatically to your saved payment method on the same calendar date each month. This fee covers continued access to the DoulaShield platform, including billing tools, visit documentation, and MCO eligibility checks.

4. AUTOMATIC PAYMENT AUTHORIZATION
By agreeing to these terms, you authorize DoulaShield to charge your saved payment method on file for (a) the deferred balance deductions described in Section 2, and (b) the recurring monthly subscription described in Section 3. You understand that these charges are automatic and do not require additional action on your part. You may contact DoulaShield to update your payment method at any time.`

export default function SettingsPage() {
  const { user, isLoading: authLoading, isAuthenticated } = useAuthStore()
  const isAdmin = user?.role === 'admin'
  const [connected, setConnected] = useState(false)
  const [zipzignConnected, setZipzignConnected] = useState(false)
  const [providerAddressGeocoded, setProviderAddressGeocoded] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)
  const [billing, setBilling] = useState<BillingStatus | null>(null)
  const [escrowChecked, setEscrowChecked] = useState(false)
  const [signingEscrow, setSigningEscrow] = useState(false)
  const [escrowError, setEscrowError] = useState<string | null>(null)

  const [providerSsnConnected, setProviderSsnConnected] = useState(false)
  const [providerSignaturePath, setProviderSignaturePath] = useState<string | null>(null)
  const [sigSaving, setSigSaving] = useState(false)
  const [sigSaved, setSigSaved] = useState(false)
  const [sigError, setSigError] = useState<string | null>(null)
  const [sigCanvasRef, setSigCanvasRef] = useState<HTMLCanvasElement | null>(null)
  const [sigPad, setSigPad] = useState<import('signature_pad').default | null>(null)

  const [pwCurrent, setPwCurrent] = useState('')
  const [pwNew, setPwNew] = useState('')
  const [pwConfirm, setPwConfirm] = useState('')
  const [pwError, setPwError] = useState<string | null>(null)
  const [pwSuccess, setPwSuccess] = useState(false)
  const [pwSaving, setPwSaving] = useState(false)

  const { register, handleSubmit, setValue, watch, formState: { isSubmitting } } = useForm<SettingsFormData>()
  const selectedZone = watch('zone') as ZoneKey | '' | undefined

  useEffect(() => {
    if (!isAuthenticated) return
    const headers = { Authorization: `Bearer ${getAccessToken()}` }
    axios
      .get<{ npi: string | null; billing_provider_name: string | null; availity_connected: boolean; telehealth_link: string | null; contact_email: string | null; zipzign_connected: boolean; zone: string | null; counties: string[] | null; provider_address: string | null; provider_phone: string | null; provider_ssn_connected: boolean; provider_signature_path: string | null; mco_contracts: Array<{ mco: string; contract_date: string | null }> | null; caqh_last_attested_on: string | null; caqh_days_remaining: number | null }>(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/me/provider-settings`,
        { headers }
      )
      .then((r) => {
        if (r.data.npi) setValue('npi', r.data.npi)
        if (r.data.billing_provider_name) setValue('billing_provider_name', r.data.billing_provider_name)
        if (r.data.telehealth_link) setValue('telehealth_link', r.data.telehealth_link)
        if (r.data.contact_email) setValue('contact_email', r.data.contact_email)
        if (r.data.zone) setValue('zone', r.data.zone)
        if (r.data.counties?.length) setValue('counties', r.data.counties)
        if (r.data.provider_address) {
          setValue('provider_address', r.data.provider_address)
          setProviderAddressGeocoded(true)
        }
        if (r.data.provider_phone) setValue('provider_phone', r.data.provider_phone)
        setConnected(r.data.availity_connected)
        setZipzignConnected(r.data.zipzign_connected)
        setProviderSsnConnected(r.data.provider_ssn_connected ?? false)
        setProviderSignaturePath(r.data.provider_signature_path ?? null)
        if (r.data.mco_contracts?.length) {
          setValue('mco_contracts', r.data.mco_contracts.map(c => ({
            mco: c.mco,
            contract_date: c.contract_date ?? '',
          })))
        }
        setValue('caqh_last_attested_on', r.data.caqh_last_attested_on ?? '')
      })
    axios
      .get<BillingStatus>(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/billing/status`, { headers })
      .then((r) => setBilling(r.data))
      .catch(() => {/* billing not configured — silently skip */})
  }, [setValue, isAuthenticated])

  const handleSignEscrow = async () => {
    if (!escrowChecked) return
    setSigningEscrow(true)
    setEscrowError(null)
    try {
      const r = await axios.post<BillingStatus>(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/billing/sign-escrow`,
        { agreed: true },
        { headers: { Authorization: `Bearer ${getAccessToken()}` } }
      )
      setBilling(r.data)
    } catch {
      setEscrowError('Failed to sign agreement. Please try again.')
    } finally {
      setSigningEscrow(false)
    }
  }

  const handleChangePassword = async () => {
    setPwError(null)
    setPwSuccess(false)
    if (!pwCurrent) { setPwError('Enter your current password'); return }
    if (!pwNew) { setPwError('Enter a new password'); return }
    if (pwNew !== pwConfirm) { setPwError('Passwords do not match'); return }
    setPwSaving(true)
    try {
      await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/me/change-password`,
        { current_password: pwCurrent, new_password: pwNew },
        { headers: { Authorization: `Bearer ${getAccessToken()}` } },
      )
      setPwSuccess(true)
      setPwCurrent('')
      setPwNew('')
      setPwConfirm('')
    } catch (e: unknown) {
      const msg = axios.isAxiosError(e) ? e.response?.data?.detail : 'Failed to update password'
      setPwError(String(msg))
    } finally {
      setPwSaving(false)
    }
  }

  const onSubmit = async (data: SettingsFormData) => {
    setSaveError(null)
    setSaved(false)
    try {
      const body: Record<string, unknown> = {}
      if (data.npi) body.npi = data.npi
      body.billing_provider_name = data.billing_provider_name || ''
      if (data.availity_client_id) body.availity_client_id = data.availity_client_id
      if (data.availity_client_secret) body.availity_client_secret = data.availity_client_secret
      if (data.telehealth_link) body.telehealth_link = data.telehealth_link
      if (data.contact_email) body.contact_email = data.contact_email
      if (data.zipzign_api_key) body.zipzign_api_key = data.zipzign_api_key
      body.zone = data.zone || ''
      body.counties = data.counties || []
      body.provider_address = data.provider_address || ''
      body.provider_phone = data.provider_phone || ''
      if (data.provider_ssn) body.provider_ssn = data.provider_ssn
      body.mco_contracts = (data.mco_contracts ?? [])
        .filter(c => c.mco)
        .map(c => ({ mco: c.mco, contract_date: c.contract_date || null }))
      if (data.caqh_last_attested_on) body.caqh_last_attested_on = data.caqh_last_attested_on

      const res = await axios.patch<{ npi: string | null; availity_connected: boolean; zipzign_connected: boolean; provider_ssn_connected: boolean; provider_signature_path: string | null }>(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/me/provider-settings`,
        body,
        { headers: { Authorization: `Bearer ${getAccessToken()}` } }
      )
      setConnected(res.data.availity_connected)
      setZipzignConnected(res.data.zipzign_connected)
      setProviderSsnConnected(res.data.provider_ssn_connected ?? false)
      setSaved(true)
    } catch {
      setSaveError('Failed to save. Please try again.')
    }
  }

  const handleDisconnectZipzign = async () => {
    setSaveError(null)
    setSaved(false)
    try {
      const res = await axios.patch<{ zipzign_connected: boolean }>(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/me/provider-settings`,
        { zipzign_api_key: '' },
        { headers: { Authorization: `Bearer ${getAccessToken()}` } }
      )
      setZipzignConnected(res.data.zipzign_connected)
      setSaved(true)
    } catch {
      setSaveError('Failed to disconnect. Please try again.')
    }
  }

  if (authLoading) return <p className="text-sm text-gray-500">Loading…</p>

  return (
    <div className="max-w-lg space-y-6">
      <div className="flex items-center gap-3">
        <h1 className="text-2xl font-bold text-gray-900">Provider settings</h1>
        {user?.role === 'admin' && (
          <span className="inline-flex items-center rounded-full bg-purple-100 px-2.5 py-0.5 text-xs font-medium text-purple-700">
            Admin
          </span>
        )}
        {user?.role === 'provider' && (
          <span className="inline-flex items-center rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-700">
            Provider
          </span>
        )}
      </div>

      {/* Escrow & Billing — hidden for admins */}
      {!isAdmin && (
        <div className="bg-white p-6 rounded-lg border border-gray-200 space-y-4">
          <h2 className="text-sm font-semibold text-gray-700">Escrow &amp; Billing</h2>

          {billing && !billing.escrow_agreed_at && (
            <div className="space-y-3">
              <div className="rounded border border-gray-200 bg-gray-50 p-3 max-h-52 overflow-y-auto">
                <pre className="text-xs text-gray-700 whitespace-pre-wrap font-sans leading-relaxed">
                  {ESCROW_AGREEMENT_TEXT}
                </pre>
              </div>
              <label className="flex items-start gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={escrowChecked}
                  onChange={(e) => setEscrowChecked(e.target.checked)}
                  className="mt-0.5 h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm text-gray-700">I have read and agree to the escrow terms above.</span>
              </label>
              {escrowError && <p className="text-xs text-red-600">{escrowError}</p>}
              <button
                type="button"
                onClick={handleSignEscrow}
                disabled={!escrowChecked || signingEscrow}
                className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {signingEscrow ? 'Signing…' : 'Sign Agreement'}
              </button>
            </div>
          )}

          {billing?.escrow_agreed_at && (
            <div className="space-y-2">
              <p className="text-sm text-green-700">
                ✓ Agreement signed on {new Date(billing.escrow_agreed_at).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}
                {billing.escrow_agreement_version && ` (v${billing.escrow_agreement_version})`}
              </p>
              {billing.escrow_balance_remaining > 0 ? (
                <p className="text-sm text-gray-700">
                  Deferred balance:{' '}
                  <span className="font-medium">${billing.escrow_balance_remaining.toFixed(2)} remaining</span> of $400.00
                  <span className="ml-1 text-gray-500 text-xs">— collected automatically from MCO remittances (50% per check)</span>
                </p>
              ) : (
                <p className="text-sm text-gray-500">Deferred balance: <span className="text-green-700 font-medium">Cleared</span></p>
              )}
              <p className="text-sm text-gray-700">
                Monthly subscription:{' '}
                {billing.subscription_status === 'active' || billing.subscription_status === 'trialing' ? (
                  <span className="inline-flex items-center rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">Active ($39/mo)</span>
                ) : billing.subscription_status === 'past_due' ? (
                  <span className="inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700">Past Due</span>
                ) : (
                  <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-500">Not yet started</span>
                )}
              </p>
            </div>
          )}

          {!billing && (
            <p className="text-sm text-gray-400">Loading billing status…</p>
          )}
        </div>
      )}

      {/* Change Password */}
      <div className="bg-white p-6 rounded-lg border border-gray-200 space-y-4">
        <h2 className="text-sm font-semibold text-gray-700">Change Password</h2>
        <div className="space-y-3">
          <div>
            <label htmlFor="pw-current" className="block text-sm font-medium text-gray-700">Current password</label>
            <input
              id="pw-current"
              type="password"
              value={pwCurrent}
              onChange={(e) => setPwCurrent(e.target.value)}
              className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div>
            <label htmlFor="pw-new" className="block text-sm font-medium text-gray-700">New password</label>
            <p className="text-xs text-gray-500 mb-1">12+ chars · uppercase · lowercase · number · special character</p>
            <input
              id="pw-new"
              type="password"
              value={pwNew}
              onChange={(e) => setPwNew(e.target.value)}
              className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div>
            <label htmlFor="pw-confirm" className="block text-sm font-medium text-gray-700">Confirm new password</label>
            <input
              id="pw-confirm"
              type="password"
              value={pwConfirm}
              onChange={(e) => setPwConfirm(e.target.value)}
              className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
        </div>
        {pwError && <p className="text-sm text-red-600">{pwError}</p>}
        {pwSuccess && <p className="text-sm text-green-600">Password updated successfully.</p>}
        <button
          type="button"
          onClick={handleChangePassword}
          disabled={pwSaving}
          className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {pwSaving ? 'Updating…' : 'Update Password'}
        </button>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 bg-white p-6 rounded-lg border border-gray-200">

        {/* CAQH Attestation */}
        <div className="space-y-3">
          <div>
            <h2 className="text-sm font-semibold text-gray-700">CAQH Attestation</h2>
            <p className="mt-0.5 text-xs text-gray-500">
              CAQH ProView requires re-attestation every 90 days to stay enrolled in MCO directories.
            </p>
          </div>
          <div>
            <label htmlFor="caqh_last_attested_on" className="block text-sm font-medium text-gray-700">
              Last attested on
            </label>
            <input
              {...register('caqh_last_attested_on')}
              id="caqh_last_attested_on"
              type="date"
              className="mt-1 block rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          {/* Live expiry display — computed from the watched date value */}
          {(() => {
            const val = watch('caqh_last_attested_on')
            if (!val) return null
            const attested = new Date(val + 'T00:00:00')
            const expiry = new Date(attested)
            expiry.setDate(expiry.getDate() + 90)
            const today = new Date()
            today.setHours(0, 0, 0, 0)
            const diffMs = expiry.getTime() - today.getTime()
            const diffDays = Math.round(diffMs / 86400000)
            const expiryLabel = expiry.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
            if (diffDays > 14) {
              return (
                <p className="text-xs text-green-700">
                  Next due {expiryLabel} ({diffDays} days)
                </p>
              )
            } else if (diffDays > 0) {
              return (
                <p className="text-xs font-medium text-amber-700">
                  ⚠ Due in {diffDays} day{diffDays !== 1 ? 's' : ''} — {expiryLabel}
                </p>
              )
            } else {
              return (
                <p className="text-xs font-semibold text-red-700">
                  ⚠ Overdue by {Math.abs(diffDays)} day{Math.abs(diffDays) !== 1 ? 's' : ''} — re-attest now
                </p>
              )
            }
          })()}
          <a
            href="https://proview.caqh.org"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center text-xs text-blue-600 hover:underline"
          >
            Open CAQH ProView →
          </a>
        </div>

        <div className="border-t pt-4 space-y-4">
          <h2 className="text-sm font-semibold text-gray-700">Billing provider information</h2>
          <p className="text-xs text-gray-500">
            Used to populate Box 33 on the CMS 1500 claim form.
          </p>
          <div>
            <label htmlFor="billing_provider_name" className="block text-sm font-medium text-gray-700">
              Billing provider name <span className="font-normal text-gray-500">(Box 33)</span>
            </label>
            <p className="text-xs text-gray-500 mb-1">Must match exactly as registered in the PROMISe provider portal.</p>
            <input
              {...register('billing_provider_name')}
              id="billing_provider_name"
              type="text"
              placeholder="Name as it appears in PROMISe"
              className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div>
            <label htmlFor="npi" className="block text-sm font-medium text-gray-700">
              National Provider Identifier (NPI)
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
          <div>
            <label htmlFor="provider_address" className="block text-sm font-medium text-gray-700">
              Practice / billing address
            </label>
            <p className="text-xs text-gray-500 mb-1">Appears in Box 33 of the CMS 1500. Select from suggestions to ensure city is captured correctly.</p>
            <AddressAutocomplete
              id="provider_address"
              value={watch('provider_address') ?? ''}
              onChange={(v) => {
                setValue('provider_address', v)
                setProviderAddressGeocoded(false)
              }}
              onSelect={(addr) => {
                setValue('provider_address', addr)
                setProviderAddressGeocoded(true)
              }}
              placeholder="Start typing your address…"
              geocoded={providerAddressGeocoded}
              inputClassName="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div>
            <label htmlFor="provider_phone" className="block text-sm font-medium text-gray-700">
              Practice phone number
            </label>
            <input
              {...register('provider_phone')}
              id="provider_phone"
              type="tel"
              maxLength={20}
              placeholder="(215) 555-0100"
              className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 sm:w-48"
            />
          </div>
        </div>

        <div className="border-t pt-4 space-y-4">
          <h2 className="text-sm font-semibold text-gray-700">PA HealthChoices Zone</h2>
          <p className="text-xs text-gray-500">
            Pennsylvania Medicaid is divided into 5 geographic zones. Selecting your zone ensures the correct MCOs
            are available for eligibility checks and billing.
          </p>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="zone" className="block text-sm font-medium text-gray-700">Primary zone</label>
              <select
                {...register('zone')}
                id="zone"
                onChange={(e) => { setValue('zone', e.target.value); setValue('counties', []) }}
                className="mt-1 block w-full rounded border border-gray-300 bg-white px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="">— Select zone —</option>
                {(Object.keys(PA_ZONES) as ZoneKey[]).map((key) => (
                  <option key={key} value={key}>{PA_ZONES[key].label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Counties served</label>
              {selectedZone && selectedZone in PA_ZONES ? (
                <div className="mt-1 max-h-48 overflow-y-auto rounded border border-gray-300 bg-white p-2 space-y-1">
                  {PA_ZONES[selectedZone as ZoneKey].counties.map((c) => (
                    <label key={c} className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        value={c}
                        checked={(watch('counties') ?? []).includes(c)}
                        onChange={(e) => {
                          const current = watch('counties') ?? []
                          setValue(
                            'counties',
                            e.target.checked ? [...current, c] : current.filter((x) => x !== c)
                          )
                        }}
                        className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                      />
                      <span className="text-sm text-gray-700">{c}</span>
                    </label>
                  ))}
                </div>
              ) : (
                <p className="mt-1 text-sm text-gray-400">Select a zone first</p>
              )}
            </div>
          </div>
          {selectedZone && selectedZone in PA_ZONES && (
            <div className="rounded-lg border border-blue-100 bg-blue-50 px-3 py-2">
              <p className="text-xs font-medium text-blue-700 mb-1">Active MCOs in this zone:</p>
              <p className="text-xs text-blue-800">{PA_ZONES[selectedZone as ZoneKey].mcos.join(' · ')}</p>
            </div>
          )}
        </div>

        <div className="border-t pt-4 space-y-3">
          <div>
            <h2 className="text-sm font-semibold text-gray-700">MCO Contracts</h2>
            <p className="mt-0.5 text-xs text-gray-500">
              Check each MCO you are contracted with. Add the contract effective date when available.
            </p>
          </div>
          <div className="space-y-1.5">
            {ALL_MCOS.map((mco) => {
              const mcoContracts = watch('mco_contracts') ?? []
              const idx = mcoContracts.findIndex(c => c.mco === mco)
              const contracted = idx !== -1
              return (
                <div key={mco} className="flex flex-wrap items-center gap-3 py-0.5">
                  <input
                    type="checkbox"
                    id={`mco-${mco}`}
                    checked={contracted}
                    onChange={(e) => {
                      const current = watch('mco_contracts') ?? []
                      if (e.target.checked) {
                        setValue('mco_contracts', [...current, { mco, contract_date: '' }])
                      } else {
                        setValue('mco_contracts', current.filter(c => c.mco !== mco))
                      }
                    }}
                    className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <label htmlFor={`mco-${mco}`} className="w-52 text-sm text-gray-700 cursor-pointer">
                    {mco}
                  </label>
                  {contracted && (
                    <input
                      type="date"
                      value={(watch('mco_contracts') ?? [])[idx]?.contract_date ?? ''}
                      onChange={(e) => {
                        const current = [...(watch('mco_contracts') ?? [])]
                        current[idx] = { ...current[idx], contract_date: e.target.value }
                        setValue('mco_contracts', current)
                      }}
                      className="rounded border border-gray-300 px-2 py-1 text-xs text-gray-700 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                      title="Contract effective date (optional)"
                    />
                  )}
                </div>
              )
            })}
          </div>
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

        <div className="border-t pt-4">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">Telehealth</h2>
          <p className="text-xs text-gray-500 mb-3">
            Enter your personal meeting room link. Doxy.me is recommended — it's free, HIPAA-compliant, and requires no patient download. Zoom requires a paid Pro plan with HIPAA BAA.
          </p>
          <div>
            <label htmlFor="telehealth_link" className="block text-sm font-medium text-gray-700">Telehealth meeting link</label>
            <input
              {...register('telehealth_link')}
              id="telehealth_link"
              type="url"
              placeholder="https://doxy.me/yourname"
              className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
        </div>

        <div className="border-t pt-4 space-y-4">
          <h2 className="text-sm font-semibold text-gray-700">Billing Credentials (CMS 1500)</h2>
          <div>
            <label htmlFor="provider_ssn" className="block text-sm font-medium text-gray-700">
              SSN — Tax ID for Box 25
              {providerSsnConnected && (
                <span className="ml-2 inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
                  ✓ Saved
                </span>
              )}
            </label>
            <input
              {...register('provider_ssn')}
              id="provider_ssn"
              type="password"
              maxLength={9}
              placeholder={providerSsnConnected ? '●●●●●●●●● saved' : '9-digit SSN (no dashes)'}
              className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            <p className="mt-1 text-xs text-gray-400">Stored encrypted. Used as Box 25 Tax ID on CMS 1500 claims (sole proprietor SSN).</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Provider Signature — Box 31
              {providerSignaturePath && (
                <span className="ml-2 inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
                  ✓ Signature on file
                </span>
              )}
            </label>
            <p className="text-xs text-gray-500 mb-2">Draw your signature below. It will be embedded in Box 31 of every CMS 1500 claim PDF.</p>
            <div className="rounded border border-gray-300 bg-white" style={{ maxWidth: 420 }}>
              <canvas
                ref={(el) => {
                  if (el && el !== sigCanvasRef) {
                    setSigCanvasRef(el)
                    import('signature_pad').then((mod) => {
                      const SP = mod.default
                      const pad = new SP(el, { backgroundColor: 'rgb(255,255,255)' })
                      el.width = el.offsetWidth || 400
                      el.height = 120
                      setSigPad(pad)
                    }).catch(() => {})
                  }
                }}
                style={{ width: '100%', height: 120, display: 'block', cursor: 'crosshair' }}
              />
            </div>
            <p className="mt-1 text-xs text-gray-400">Draw your signature above</p>
            {sigError && <p className="text-xs text-red-600 mt-1">{sigError}</p>}
            {sigSaved && <p className="text-xs text-green-600 mt-1">✓ Signature saved</p>}
            <div className="mt-2 flex gap-2">
              <button
                type="button"
                onClick={() => { sigPad?.clear(); setSigSaved(false) }}
                className="rounded border border-gray-300 px-3 py-1 text-xs font-medium text-gray-600 hover:bg-gray-50"
              >
                Clear
              </button>
              <button
                type="button"
                disabled={sigSaving}
                onClick={async () => {
                  if (!sigPad || sigPad.isEmpty()) return
                  setSigSaving(true)
                  setSigError(null)
                  setSigSaved(false)
                  try {
                    const dataUrl = sigPad.toDataURL('image/png')
                    const res = await axios.post<{ path: string }>(
                      `${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/me/provider-signature`,
                      { signature_data_url: dataUrl },
                      { headers: { Authorization: `Bearer ${getAccessToken()}` } }
                    )
                    setProviderSignaturePath(res.data.path)
                    setSigSaved(true)
                    sigPad.clear()
                  } catch {
                    setSigError('Failed to save signature. Please try again.')
                  } finally {
                    setSigSaving(false)
                  }
                }}
                className="rounded bg-blue-600 px-3 py-1 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {sigSaving ? 'Saving…' : 'Save Signature'}
              </button>
            </div>
          </div>
        </div>

        <div className="border-t pt-4">
          <div className="flex items-center gap-2 mb-3">
            <h2 className="text-sm font-semibold text-gray-700">Signatures (MA 91)</h2>
            {zipzignConnected && (
              <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
                ✓ Connected
              </span>
            )}
          </div>
          <p className="text-xs text-gray-500 mb-3">
            Required for telehealth visits. ZipZign generates a hosted MA 91 PDF and collects a patient e-signature without requiring a patient account.{' '}
            Sign up free at <span className="font-medium">zipzign.com</span>.
          </p>
          <div className="space-y-3">
            <div>
              <label htmlFor="contact_email" className="block text-sm font-medium text-gray-700">Contact email</label>
              <p className="text-xs text-gray-500 mb-1">Used as the From address when sending MA 91 signature requests to patients.</p>
              <input
                {...register('contact_email')}
                id="contact_email"
                type="email"
                placeholder="your@email.com"
                className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
            {isAdmin && (
              <div>
                <div className="flex items-center justify-between">
                  <label htmlFor="zipzign_api_key" className="block text-sm font-medium text-gray-700">ZipZign API key</label>
                  {zipzignConnected && (
                    <button
                      type="button"
                      onClick={handleDisconnectZipzign}
                      className="text-xs text-red-600 hover:underline"
                    >
                      Disconnect
                    </button>
                  )}
                </div>
                <input
                  {...register('zipzign_api_key')}
                  id="zipzign_api_key"
                  type="password"
                  placeholder={zipzignConnected ? 'Enter a new key to replace the saved one' : 'Enter API key'}
                  className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
            )}
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
