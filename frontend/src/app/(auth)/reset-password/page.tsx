'use client'

import { Suspense, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import axios from 'axios'

function ResetPasswordForm() {
  const searchParams = useSearchParams()
  const token = searchParams.get('token')

  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  if (!token) {
    return (
      <div className="bg-white p-6 rounded-lg shadow space-y-3">
        <p className="text-sm text-red-600">Invalid reset link.</p>
        <a href="/forgot-password" className="text-sm text-blue-600 hover:underline">
          Request a new one →
        </a>
      </div>
    )
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    if (newPassword !== confirmPassword) {
      setError('Passwords do not match.')
      return
    }
    setLoading(true)
    try {
      await axios.post(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/reset-password`, {
        token,
        new_password: newPassword,
      })
      setSuccess(true)
    } catch (e: unknown) {
      const msg = axios.isAxiosError(e) ? e.response?.data?.detail : null
      setError(msg ?? 'Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  if (success) {
    return (
      <div className="bg-white p-6 rounded-lg shadow space-y-3">
        <p className="text-sm text-green-700 font-medium">✓ Password updated successfully.</p>
        <a
          href="/login"
          className="inline-block rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          Log in →
        </a>
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="bg-white p-6 rounded-lg shadow space-y-4">
      <div>
        <label htmlFor="new-password" className="block text-sm font-medium text-gray-700">
          New password
        </label>
        <p className="text-xs text-gray-500 mb-1">
          12+ chars · uppercase · lowercase · number · special character
        </p>
        <input
          id="new-password"
          type="password"
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
          required
          autoComplete="new-password"
          className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>
      <div>
        <label htmlFor="confirm-password" className="block text-sm font-medium text-gray-700">
          Confirm new password
        </label>
        <input
          id="confirm-password"
          type="password"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          required
          autoComplete="new-password"
          className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>
      {error && (
        <div className="space-y-1">
          <p className="text-sm text-red-600">{error}</p>
          {error.includes('invalid or has expired') && (
            <a href="/forgot-password" className="text-xs text-blue-600 hover:underline">
              Request a new reset link →
            </a>
          )}
        </div>
      )}
      <button
        type="submit"
        disabled={loading}
        className="w-full rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
      >
        {loading ? 'Updating…' : 'Update Password'}
      </button>
    </form>
  )
}

export default function ResetPasswordPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-sm space-y-6">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900">DoulaShield</h1>
          <p className="mt-1 text-sm text-gray-500">Set a new password</p>
        </div>
        <Suspense fallback={<div className="bg-white p-6 rounded-lg shadow"><p className="text-sm text-gray-500">Loading…</p></div>}>
          <ResetPasswordForm />
        </Suspense>
        <p className="text-center text-xs text-gray-500">
          <a href="/login" className="text-blue-600 hover:underline">← Back to sign in</a>
        </p>
      </div>
    </div>
  )
}
