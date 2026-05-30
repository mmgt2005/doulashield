'use client'

import { useState } from 'react'
import axios from 'axios'

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email.trim()) return
    setLoading(true)
    setError(null)
    try {
      await axios.post(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/forgot-password`, {
        email: email.trim(),
      })
      setSubmitted(true)
    } catch {
      setError('Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-sm space-y-6">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900">DoulaShield</h1>
          <p className="mt-1 text-sm text-gray-500">Reset your password</p>
        </div>

        <div className="bg-white p-6 rounded-lg shadow space-y-4">
          {submitted ? (
            <>
              <p className="text-sm text-gray-700">
                Check your email — if that address is registered you&apos;ll receive a reset link shortly.
              </p>
              <p className="text-xs text-gray-500">
                Didn&apos;t get it? Check your spam folder or{' '}
                <button
                  onClick={() => { setSubmitted(false); setEmail('') }}
                  className="text-blue-600 hover:underline"
                >
                  try again
                </button>.
              </p>
            </>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                  Email address
                </label>
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoComplete="email"
                  className="mt-1 block w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
              {error && <p className="text-sm text-red-600">{error}</p>}
              <button
                type="submit"
                disabled={loading}
                className="w-full rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {loading ? 'Sending…' : 'Send Reset Link'}
              </button>
            </form>
          )}
        </div>

        <p className="text-center text-xs text-gray-500">
          <a href="/login" className="text-blue-600 hover:underline">← Back to sign in</a>
        </p>
      </div>
    </div>
  )
}
