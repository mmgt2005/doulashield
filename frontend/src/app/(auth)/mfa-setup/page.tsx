'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import axios from 'axios'
import { getAccessToken } from '@/lib/auth'

const schema = z.object({ code: z.string().length(6, 'Enter the 6-digit code') })
type FormData = z.infer<typeof schema>

export default function MFASetupPage() {
  const router = useRouter()
  const [provisioningUri, setProvisioningUri] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
  })

  useEffect(() => {
    axios
      .get<{ provisioning_uri: string }>(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/mfa/setup`,
        { headers: { Authorization: `Bearer ${getAccessToken()}` } }
      )
      .then((r) => setProvisioningUri(r.data.provisioning_uri))
      .catch(() => setError('Could not load MFA setup. Please try again.'))
  }, [])

  const onSubmit = async (data: FormData) => {
    setError(null)
    try {
      await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/mfa/verify`,
        { totp_code: data.code },
        { headers: { Authorization: `Bearer ${getAccessToken()}` } }
      )
      router.push('/dashboard')
    } catch {
      setError('Invalid code. Please try again.')
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-sm space-y-6">
        <h1 className="text-xl font-bold text-center">Set up two-factor authentication</h1>
        <p className="text-sm text-gray-600 text-center">
          Scan the QR code with your authenticator app, then enter the 6-digit code to confirm.
        </p>

        {provisioningUri && (
          <div className="bg-white p-4 rounded-lg shadow text-center">
            <p className="text-xs text-gray-500 break-all">{provisioningUri}</p>
          </div>
        )}

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 bg-white p-6 rounded-lg shadow">
          <div>
            <label className="block text-sm font-medium text-gray-700">Verification code</label>
            <input
              {...register('code')}
              type="text"
              inputMode="numeric"
              maxLength={6}
              placeholder="123456"
              className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm"
            />
            {errors.code && <p className="mt-1 text-xs text-red-600">{errors.code.message}</p>}
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button
            type="submit"
            className="w-full rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            Verify and enable
          </button>
        </form>
      </div>
    </div>
  )
}
