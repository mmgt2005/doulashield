'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import { useForm } from 'react-hook-form'
import axios from 'axios'
import { getAccessToken } from '@/lib/auth'
import { geocodeAddress } from '@/lib/geo'
import AddressAutocomplete from '@/components/ui/AddressAutocomplete'
import ImageUploadScanner from '@/components/ui/ImageUploadScanner'
import NpiLookup from '@/components/ui/NpiLookup'
import { Claim, Patient, Visit, VisitType } from '@/types/domain'
import { VISIT_SLOTS, VISIT_GROUPS, getPrevSlotInGroup, getSlotConfig } from '@/lib/visit-config'

interface EditFormData {
  name: string
  gender: string
  email: string
  medicaid_id?: string
  mco: string
  date_of_birth: string
  policy_group: string
  referring_provider_npi: string
  referring_provider_name: string
  has_other_insurance: boolean
  address: string
  latitude?: number
  longitude?: number
  medicaid_card_image_path?: string
  ma589_signed_date: string
}

export default function ClientDetailPage() {
  const { clientId } = useParams<{ clientId: string }>()
  const [patient, setPatient] = useState<Patient | null>(null)
  const [visitMap, setVisitMap] = useState<Map<VisitType, Visit>>(new Map())
  const [claimMap, setClaimMap] = useState<Map<string, Claim>>(new Map())
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [editing, setEditing] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [needsAccessScan, setNeedsAccessScan] = useState(false)
  const [checkingElig, setCheckingElig] = useState(false)
  const [eligError, setEligError] = useState<string | null>(null)

  const { register, handleSubmit, reset, watch, setValue, formState: { isSubmitting } } = useForm<EditFormData>()

  useEffect(() => {
    const headers = { Authorization: `Bearer ${getAccessToken()}` }
    const base = process.env.NEXT_PUBLIC_API_URL

    Promise.all([
      axios.get<Patient>(`${base}/api/v1/patients/${clientId}`, { headers }),
      axios.get<Visit[]>(`${base}/api/v1/patients/${clientId}/visits`, { headers }),
      axios.get<Claim[]>(`${base}/api/v1/patients/${clientId}/claims`, { headers }).catch(() => ({ data: [] as Claim[] })),
    ])
      .then(([patientRes, visitsRes, claimsRes]) => {
        setPatient(patientRes.data)
        const map = new Map<VisitType, Visit>()
        for (const v of visitsRes.data) map.set(v.visit_type, v)
        setVisitMap(map)
        const cmap = new Map<string, Claim>()
        for (const c of claimsRes.data) if (c.visit_type) cmap.set(c.visit_type, c)
        setClaimMap(cmap)
      })
      .catch(() => setError('Could not load client.'))
      .finally(() => setLoading(false))
  }, [clientId])

  const handleEditScanned = (data: Record<string, unknown>) => {
    if (data.name) setValue('name', String(data.name))
    if (data.medicaid_id) setValue('medicaid_id', String(data.medicaid_id))
    if (data.mco) setValue('mco', String(data.mco))
    if (data.date_of_birth) setValue('date_of_birth', String(data.date_of_birth))
    if (data.policy_group) setValue('policy_group', String(data.policy_group))
    if (data.address) {
      setValue('address', String(data.address))
      setValue('latitude', undefined)
      setValue('longitude', undefined)
    }
    if (data.image_path) setValue('medicaid_card_image_path', String(data.image_path))
    setNeedsAccessScan(!data.medicaid_id)
  }

  const handleAccessCardScannedEdit = (data: Record<string, unknown>) => {
    if (data.medicaid_id) {
      setValue('medicaid_id', String(data.medicaid_id))
      setNeedsAccessScan(false)
    }
  }

  const startEdit = () => {
    if (!patient) return
    reset({
      name: patient.name,
      gender: patient.gender ?? 'F',
      email: patient.email ?? '',
      mco: patient.mco ?? '',
      date_of_birth: patient.date_of_birth ?? '',
      policy_group: patient.policy_group ?? '',
      referring_provider_npi: patient.referring_provider_npi ?? '',
      referring_provider_name: patient.referring_provider_name ?? '',
      has_other_insurance: patient.has_other_insurance ?? false,
      address: patient.address ?? '',
      latitude: patient.latitude ?? undefined,
      longitude: patient.longitude ?? undefined,
      ma589_signed_date: patient.ma589_signed_date ?? '',
    })
    setSaveError(null)
    setNeedsAccessScan(false)
    setEditing(true)
  }

  const onSaveProfile = async (data: EditFormData) => {
    setSaveError(null)
    try {
      let lat = data.latitude
      let lng = data.longitude
      if (data.address && (lat == null || isNaN(lat))) {
        const coords = await geocodeAddress(data.address)
        lat = coords?.lat
        lng = coords?.lng
        if (coords?.label) data.address = coords.label
      }
      const res = await axios.patch<Patient>(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/patients/${clientId}`,
        {
          name: data.name,
          gender: data.gender,
          email: data.email || null,
          ...(data.medicaid_id ? { medicaid_id: data.medicaid_id } : {}),
          mco: data.mco || null,
          date_of_birth: data.date_of_birth || null,
          policy_group: data.policy_group || null,
          address: data.address || null,
          latitude: lat ?? null,
          longitude: lng ?? null,
          referring_provider_npi: data.referring_provider_npi || null,
          referring_provider_name: data.referring_provider_name || null,
          has_other_insurance: data.has_other_insurance ?? false,
          ma589_signed_date: data.ma589_signed_date || null,
          ...(data.medicaid_card_image_path ? { medicaid_card_image_path: data.medicaid_card_image_path } : {}),
        },
        { headers: { Authorization: `Bearer ${getAccessToken()}` } }
      )
      setPatient(res.data)
      setEditing(false)
    } catch {
      setSaveError('Failed to save. Please try again.')
    }
  }

  const handleCheckEligibility = async () => {
    setCheckingElig(true)
    setEligError(null)
    try {
      const res = await axios.post<{ active: boolean; plan_name: string; effective_date: string | null; checked_at: string }>(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/patients/${clientId}/eligibility-check`,
        {},
        { headers: { Authorization: `Bearer ${getAccessToken()}` } }
      )
      setPatient((p) => p ? {
        ...p,
        eligibility_status: res.data.active ? 'active' : 'inactive',
        eligibility_checked_at: res.data.checked_at,
      } : p)
    } catch (err) {
      const detail = axios.isAxiosError(err) ? err.response?.data?.detail : null
      setEligError(detail || 'Eligibility check failed. Please try again.')
    } finally {
      setCheckingElig(false)
    }
  }

  if (loading) return <p className="text-sm text-gray-500">Loading…</p>
  if (error || !patient) return <p className="text-sm text-red-600">{error ?? 'Not found.'}</p>

  const formatDate = (iso: string) => {
    const [y, m, d] = iso.split('-')
    return `${m}/${d}/${y}`
  }

  const eligCanCheck = !!(patient.mco && patient.date_of_birth)
  const eligCheckedDate = patient.eligibility_checked_at
    ? new Date(patient.eligibility_checked_at).toLocaleDateString()
    : null

  return (
    <div className="space-y-6">
      <div>
        {editing ? (
          <form onSubmit={handleSubmit(onSaveProfile)} className="space-y-3 bg-white p-4 rounded-lg border border-gray-200 max-w-md">
            <h2 className="text-sm font-semibold text-gray-700">Edit profile</h2>
            <ImageUploadScanner
              endpoint="/api/v1/ocr/medicaid-card"
              onExtracted={handleEditScanned}
              label="Scan updated Medicaid card"
            />
            {needsAccessScan && (
              <div className="rounded border border-amber-300 bg-amber-50 p-3 space-y-2">
                <p className="text-xs font-medium text-amber-800">
                  ⚠ The MCO card didn&apos;t include the Medicaid ID. Scan the client&apos;s ACCESS card to get it.
                </p>
                <ImageUploadScanner
                  endpoint="/api/v1/ocr/handbook"
                  extraFields={{ page_type: 'access_card' }}
                  onExtracted={handleAccessCardScannedEdit}
                  label="Scan ACCESS card"
                />
              </div>
            )}
            <div>
              <label className="block text-xs font-medium text-gray-600">Full name</label>
              <input {...register('name')} className="mt-1 block w-full rounded border border-gray-300 px-3 py-1.5 text-sm" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600">Email <span className="font-normal text-gray-400">(used to send telehealth link)</span></label>
              <input {...register('email')} type="email" placeholder="client@example.com" className="mt-1 block w-full rounded border border-gray-300 px-3 py-1.5 text-sm" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600">MCO</label>
              <select {...register('mco')} className="mt-1 block w-full rounded border border-gray-300 px-3 py-1.5 text-sm">
                <option value="">— Select MCO —</option>
                <option>AmeriHealth Caritas</option>
                <option>Keystone First</option>
                <option>UPMC For You</option>
                <option>Geisinger Health Plan</option>
                <option>Health Partners Plans</option>
                <option>Aetna Better Health</option>
                <option>UnitedHealthcare Community Plan</option>
                <option>Highmark Wholecare</option>
                <option>FFS</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600">Date of birth</label>
              <input {...register('date_of_birth')} type="date" className="mt-1 block w-full rounded border border-gray-300 px-3 py-1.5 text-sm sm:w-40" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600">
                Policy / Group Number
                <span className="ml-1 font-normal text-gray-400">(Box 11 — from Medicaid card)</span>
              </label>
              <input
                {...register('policy_group')}
                type="text"
                placeholder="e.g. GRP-12345"
                className="mt-1 block w-full rounded border border-gray-300 px-3 py-1.5 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600">
                Referring Provider NPI
                <span className="ml-1 font-normal text-gray-400">(Box 17b — referring doctor)</span>
              </label>
              <input
                {...register('referring_provider_npi')}
                type="text"
                maxLength={10}
                placeholder="10-digit NPI"
                className="mt-1 block w-full rounded border border-gray-300 px-3 py-1.5 text-sm sm:w-40"
              />
              <NpiLookup
                npi={watch('referring_provider_npi') ?? ''}
                size="xs"
                onVerified={(r) => {
                  if (r.name) setValue('referring_provider_name', r.name)
                }}
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600">
                Referring Provider Name
                <span className="ml-1 font-normal text-gray-400">(Box 17 — doctor name)</span>
              </label>
              <input
                {...register('referring_provider_name')}
                type="text"
                placeholder="Dr. Jane Smith"
                className="mt-1 block w-full rounded border border-gray-300 px-3 py-1.5 text-sm"
              />
            </div>
            <div className="flex items-center gap-2">
              <input
                {...register('has_other_insurance')}
                id="edit_has_other_insurance"
                type="checkbox"
                className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <label htmlFor="edit_has_other_insurance" className="text-xs font-medium text-gray-600">
                Patient has other insurance <span className="font-normal text-gray-400">(Box 11d)</span>
              </label>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600">Sex</label>
              <select {...register('gender')} className="mt-1 block rounded border border-gray-300 px-3 py-1.5 text-sm">
                <option value="F">Female</option>
                <option value="M">Male</option>
                <option value="U">Unknown</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600">Home address</label>
              <AddressAutocomplete
                value={watch('address') ?? ''}
                onChange={(v) => setValue('address', v)}
                onSelect={(addr, lat, lng) => {
                  setValue('address', addr)
                  setValue('latitude', lat)
                  setValue('longitude', lng)
                }}
                geocoded={watch('latitude') != null && !isNaN(Number(watch('latitude')))}
                inputClassName="mt-1 block w-full rounded border border-gray-300 px-3 py-1.5 text-sm"
              />
              <input type="hidden" {...register('address')} />
              <input type="hidden" {...register('latitude', { valueAsNumber: true })} />
              <input type="hidden" {...register('longitude', { valueAsNumber: true })} />
              <input type="hidden" {...register('medicaid_card_image_path')} />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600">
                MA 589 signed date
                <span className="ml-1 font-normal text-gray-400">(leave blank if not yet signed)</span>
              </label>
              <input
                {...register('ma589_signed_date')}
                type="date"
                className="mt-1 block rounded border border-gray-300 px-3 py-1.5 text-sm"
              />
            </div>
            {saveError && <p className="text-xs text-red-600">{saveError}</p>}
            <div className="flex gap-2">
              <button type="submit" disabled={isSubmitting} className="rounded bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-50">
                {isSubmitting ? 'Saving…' : 'Save'}
              </button>
              <button type="button" onClick={() => setEditing(false)} className="rounded border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50">
                Cancel
              </button>
            </div>
          </form>
        ) : (
          <>
            <div className="flex items-start justify-between">
              <div>
                <h1 className="text-2xl font-bold text-gray-900">{patient.name}</h1>
                {patient.mco && (
                  <p className="mt-1 flex items-center gap-1.5 text-sm text-gray-500">
                    <span>MCO: {patient.mco}</span>
                    {patient.medicaid_card_image_path && (
                      <span
                        title="Medicaid card scanned"
                        className="inline-flex items-center gap-0.5 rounded-full bg-blue-50 px-1.5 py-0.5 text-xs font-medium text-blue-600"
                      >
                        <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                            d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                            d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
                        </svg>
                        Card scanned
                      </span>
                    )}
                  </p>
                )}
                {patient.date_of_birth && (
                  <p className="mt-0.5 text-sm text-gray-500">DOB: {formatDate(patient.date_of_birth)}</p>
                )}
                {patient.address && (
                  <p className="mt-0.5 flex items-center gap-1 text-sm text-gray-500">
                    {patient.latitude !== null && (
                      <svg className="h-3.5 w-3.5 shrink-0 text-green-500" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd" />
                      </svg>
                    )}
                    {patient.address}
                  </p>
                )}
                {patient.email && (
                  <p className="mt-0.5 text-sm text-gray-500">{patient.email}</p>
                )}
                {patient.referring_provider_name && (
                  <p className="mt-0.5 text-sm text-gray-500">Referring: {patient.referring_provider_name}</p>
                )}
                {patient.policy_group && (
                  <p className="mt-0.5 text-sm text-gray-500">Policy / Group: {patient.policy_group}</p>
                )}
                {patient.has_other_insurance && (
                  <span className="mt-0.5 inline-block rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700">Has other insurance</span>
                )}

                {/* Eligibility row */}
                <div className="mt-2 flex items-center gap-2 flex-wrap">
                  {patient.eligibility_status === 'active' && (
                    <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
                      ✓ Active
                    </span>
                  )}
                  {patient.eligibility_status === 'inactive' && (
                    <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
                      ✗ Inactive
                    </span>
                  )}
                  {eligCheckedDate && (
                    <span className="text-xs text-gray-400">Last checked {eligCheckedDate}</span>
                  )}
                  {eligCanCheck ? (
                    <button
                      type="button"
                      onClick={handleCheckEligibility}
                      disabled={checkingElig}
                      className="text-xs text-blue-600 hover:text-blue-800 disabled:opacity-50"
                    >
                      {checkingElig ? 'Checking…' : patient.eligibility_status ? 'Re-check' : 'Check eligibility'}
                    </button>
                  ) : (
                    <span className="text-xs text-gray-400">
                      {!patient.mco ? 'Set MCO to check eligibility' : 'Add date of birth to check eligibility'}
                    </span>
                  )}
                  {eligError && <p className="w-full text-xs text-red-600">{eligError}</p>}
                </div>

                {/* MA 589 flag — show when prenatal care started but form not yet signed */}
                {!patient.ma589_signed_date &&
                  Array.from(visitMap.keys()).some((k) => k.startsWith('prenatal')) && (
                  <div className="mt-2 inline-flex items-center gap-1.5 rounded-md border border-amber-300 bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-800">
                    <svg className="h-3.5 w-3.5 shrink-0" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                    </svg>
                    MA 589 not signed
                  </div>
                )}
              </div>
              <button onClick={startEdit} className="text-xs text-blue-600 hover:text-blue-800 mt-1">Edit profile</button>
            </div>
          </>
        )}
      </div>

      {VISIT_GROUPS.map(({ key, label }) => {
        const slots = VISIT_SLOTS.filter((s) => s.group === (key as string))
        return (
          <div key={key}>
            <h2 className="text-xs font-semibold uppercase tracking-wide text-gray-400 mb-2">
              {label}
            </h2>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
              {slots.map((slot) => {
                const visit = visitMap.get(slot.visitType as VisitType)
                const complete = !!visit?.visit_ended_at
                const inProgress = !!visit && !visit.visit_ended_at
                const prevType = getPrevSlotInGroup(slot.visitType as VisitType)
                const blocked = prevType !== null && !visitMap.get(prevType)?.visit_ended_at
                const prevLabel = prevType ? getSlotConfig(prevType)?.label : ''

                if (blocked) {
                  return (
                    <div
                      key={slot.visitType}
                      className="block rounded-lg border border-gray-200 bg-gray-100 p-3 text-gray-400 cursor-not-allowed"
                    >
                      <div className="flex items-center gap-1">
                        <svg className="h-3.5 w-3.5 shrink-0 text-gray-400" viewBox="0 0 20 20" fill="currentColor">
                          <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd" />
                        </svg>
                        <span className="text-xs font-medium leading-tight">{slot.label}</span>
                      </div>
                      <p className="mt-0.5 text-xs text-gray-400">Complete {prevLabel} first</p>
                    </div>
                  )
                }

                const claim = claimMap.get(slot.visitType)
                const claimDot = claim ? (() => {
                  const s = (claim.status ?? '').toLowerCase()
                  if (s === 'paid') return { color: 'bg-green-500', title: 'Claim paid' }
                  if (s === 'denied' || s === 'rejected') return { color: 'bg-red-500', title: 'Claim denied' }
                  if (['processing', 'accepted', 'pended', 'received'].includes(s)) return { color: 'bg-blue-500', title: 'Claim processing' }
                  return { color: 'bg-amber-500', title: 'Claim submitted' }
                })() : null

                return (
                  <Link
                    key={slot.visitType}
                    href={`/clients/${clientId}/visits/${slot.visitType}`}
                    className={
                      complete
                        ? 'block rounded-lg border border-gray-200 bg-gray-50 p-3 text-gray-500 hover:border-gray-300 transition-colors'
                        : inProgress
                          ? 'block rounded-lg border border-amber-300 bg-amber-50 p-3 text-amber-800 hover:border-amber-400 transition-colors'
                          : 'block rounded-lg border border-blue-200 bg-white p-3 text-gray-800 hover:border-blue-400 transition-colors'
                    }
                  >
                    <div className="flex items-center gap-1">
                      {complete && (
                        <svg className="h-3.5 w-3.5 shrink-0 text-green-500" viewBox="0 0 20 20" fill="currentColor">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                      )}
                      {complete && visit?.location_type === 'telehealth' && (
                        <svg className="h-3.5 w-3.5 shrink-0 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                            d="M15 10l4.553-2.069A1 1 0 0121 8.867v6.266a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                        </svg>
                      )}
                      {complete && visit?.location_type === 'in_person' && (
                        <svg className="h-3.5 w-3.5 shrink-0 text-gray-400" viewBox="0 0 20 20" fill="currentColor">
                          <path fillRule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd" />
                        </svg>
                      )}
                      {inProgress && (
                        <svg className="h-3.5 w-3.5 shrink-0 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                      )}
                      <span className="text-xs font-medium leading-tight">{slot.label}</span>
                      {claimDot && (
                        <span
                          className={`ml-auto h-2 w-2 shrink-0 rounded-full ${claimDot.color}`}
                          title={claimDot.title}
                        />
                      )}
                    </div>
                    {complete && visit?.visit_date && (
                      <p className="mt-0.5 text-xs text-gray-400">{visit.visit_date}</p>
                    )}
                    {inProgress && (
                      <p className="mt-0.5 text-xs text-amber-600">In progress</p>
                    )}
                  </Link>
                )
              })}
            </div>
          </div>
        )
      })}

      {/* Crisis / Bereavement Visits — ad-hoc, capped at 2 per year */}
      {(() => {
        const crisisVisits = [
          visitMap.get('crisis_loss_1' as VisitType),
          visitMap.get('crisis_loss_2' as VisitType),
        ].filter(Boolean) as Visit[]
        const nextSlot = crisisVisits.length < 2 ? `crisis_loss_${crisisVisits.length + 1}` : null
        return (
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h2 className="text-xs font-semibold uppercase tracking-wide text-gray-400">
                Crisis / Bereavement Visits
              </h2>
              <span className="text-xs text-gray-400">({crisisVisits.length} of 2 used this year)</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {crisisVisits.map((v, i) => (
                <Link
                  key={v.id}
                  href={`/clients/${clientId}/visits/crisis_loss_${i + 1}`}
                  className={
                    v.visit_ended_at
                      ? 'block rounded-lg border border-gray-200 bg-gray-50 p-3 text-gray-500 hover:border-gray-300 transition-colors'
                      : 'block rounded-lg border border-amber-300 bg-amber-50 p-3 text-amber-800 hover:border-amber-400 transition-colors'
                  }
                >
                  <span className="text-xs font-medium">Crisis/Loss Visit {i + 1}</span>
                  {v.visit_date && <p className="mt-0.5 text-xs text-gray-400">{v.visit_date}</p>}
                  {!v.visit_ended_at && <p className="mt-0.5 text-xs text-amber-600">In progress</p>}
                </Link>
              ))}
              {nextSlot && (
                <Link
                  href={`/clients/${clientId}/visits/${nextSlot}`}
                  className="block rounded-lg border border-purple-200 bg-white p-3 text-gray-800 hover:border-purple-400 transition-colors"
                >
                  <span className="text-xs font-medium text-purple-700">+ Add Crisis/Loss Visit</span>
                  <p className="mt-0.5 text-xs text-gray-400">T1032 · U9 · $175</p>
                </Link>
              )}
              {crisisVisits.length === 0 && !nextSlot && (
                <p className="text-xs text-gray-400">2 of 2 crisis/loss visits used this year.</p>
              )}
            </div>
          </div>
        )
      })()}
    </div>
  )
}
