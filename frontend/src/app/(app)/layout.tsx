'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import Sidebar from '@/components/layout/Sidebar'
import SessionTimeoutModal from '@/components/layout/SessionTimeoutModal'
import ImpersonationBanner from '@/components/layout/ImpersonationBanner'
import TourOverlay from '@/components/ui/TourOverlay'
import { useSessionTimeout } from '@/hooks/useSessionTimeout'
import { useAuth } from '@/hooks/useAuth'
import { useAuthStore } from '@/store/auth-store'
import axios from 'axios'
import { clearAccessToken, getAccessToken } from '@/lib/auth'

function TosGate({ onAccepted }: { onAccepted: () => void }) {
  const [tosHtml, setTosHtml] = useState('')
  const [scrolledToBottom, setScrolledToBottom] = useState(false)
  const [checked, setChecked] = useState(false)
  const [accepting, setAccepting] = useState(false)
  const bodyRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fetch('/docs/tos.md')
      .then(r => r.text())
      .then(async md => {
        const { marked } = await import('marked')
        setTosHtml(await marked(md))
      })
      .catch(() => setTosHtml('<p>Unable to load Terms of Service. Please contact support@doulashield.com.</p>'))
  }, [])

  const handleScroll = () => {
    const el = bodyRef.current
    if (!el) return
    if (el.scrollTop + el.clientHeight >= el.scrollHeight - 8) {
      setScrolledToBottom(true)
    }
  }

  const handleAccept = async () => {
    setAccepting(true)
    try {
      await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/accept-tos`,
        {},
        { headers: { Authorization: `Bearer ${getAccessToken()}` } },
      )
      onAccepted()
    } catch {
      alert('Could not record your acceptance. Please try again or contact support@doulashield.com.')
    } finally {
      setAccepting(false)
    }
  }

  const canAccept = scrolledToBottom && checked && !accepting

  return (
    <div className="fixed inset-0 z-[100] flex flex-col bg-white">
      {/* Header */}
      <div className="shrink-0 border-b border-gray-200 px-6 py-4 flex items-center gap-3">
        <img src="/logo.png" alt="DoulaShield" className="h-8 w-auto" />
        <div>
          <h1 className="text-base font-semibold text-gray-900">Terms of Service</h1>
          <p className="text-xs text-gray-500">Please read and accept before continuing</p>
        </div>
      </div>

      {/* Scrollable ToS body */}
      <div
        ref={bodyRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto px-6 py-6 prose prose-sm max-w-none"
        dangerouslySetInnerHTML={{ __html: tosHtml || 'Loading…' }}
      />

      {/* Footer */}
      <div className="shrink-0 border-t border-gray-200 bg-gray-50 px-6 py-4 space-y-3">
        {!scrolledToBottom && (
          <p className="text-xs text-amber-700 font-medium">Scroll to the bottom to enable acceptance.</p>
        )}
        <label className="flex items-start gap-2 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={checked}
            onChange={e => setChecked(e.target.checked)}
            disabled={!scrolledToBottom}
            className="mt-0.5 h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500 disabled:opacity-40"
          />
          <span className={`text-sm ${scrolledToBottom ? 'text-gray-800' : 'text-gray-400'}`}>
            I have read and agree to the DoulaShield Terms of Service
          </span>
        </label>
        <button
          onClick={handleAccept}
          disabled={!canAccept}
          className="w-full rounded bg-blue-600 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-40"
        >
          {accepting ? 'Recording acceptance…' : 'I Agree & Continue'}
        </button>
      </div>
    </div>
  )
}

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const { user, logout, isLoading: authLoading, priorSession } = useAuthStore()
  // Hydrates user + role into the auth store for all pages under (app).
  useAuth()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [tosAccepted, setTosAccepted] = useState(false)
  const [onboardingDone, setOnboardingDone] = useState(false)

  const handleTimeout = useCallback(async () => {
    try {
      await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/logout`,
        {},
        { withCredentials: true }
      )
    } finally {
      logout()
      router.push('/login')
    }
  }, [logout, router])

  const { showWarning, resetTimeout } = useSessionTimeout(handleTimeout)

  return (
    <>
    <ImpersonationBanner />
    <div className={`flex h-screen overflow-hidden${priorSession ? ' pt-9' : ''}`}>
      {/* Desktop sidebar — always visible on lg+ */}
      <div className="hidden lg:flex">
        <Sidebar />
      </div>

      {/* Mobile drawer overlay */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-40 flex lg:hidden">
          {/* Backdrop */}
          <div
            className="fixed inset-0 bg-black/40"
            onClick={() => setSidebarOpen(false)}
            aria-hidden="true"
          />
          {/* Drawer */}
          <div className="relative z-50 flex h-full">
            <Sidebar onClose={() => setSidebarOpen(false)} />
          </div>
        </div>
      )}

      {/* Right-hand column: mobile top bar + scrollable content */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Mobile top bar */}
        <header className="flex items-center gap-3 border-b border-gray-200 bg-white px-4 py-3 lg:hidden">
          <button
            onClick={() => setSidebarOpen(true)}
            aria-label="Open menu"
            className="rounded p-1 text-gray-600 hover:bg-gray-100"
          >
            {/* Hamburger icon */}
            <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <img src="/logo.png" alt="DoulaShield" className="h-8 w-auto" />
        </header>

        <main className="flex-1 overflow-auto p-4 lg:p-6">
          {authLoading ? (
            <p className="text-sm text-gray-400">Loading…</p>
          ) : (
            children
          )}
        </main>

        {/* ToS gate — shown to any user who hasn't accepted yet; never during impersonation */}
        {!authLoading && !priorSession && user && !user.tos_accepted_at && !tosAccepted && (
          <TosGate onAccepted={() => setTosAccepted(true)} />
        )}

        {/* Onboarding tour — shown once for providers after ToS; never during impersonation */}
        {!authLoading && !priorSession && user?.role === 'provider' && (user.tos_accepted_at || tosAccepted) && !user.onboarding_completed_at && !onboardingDone && (
          <TourOverlay onDone={() => setOnboardingDone(true)} />
        )}
      </div>

      {showWarning && <SessionTimeoutModal onStayLoggedIn={resetTimeout} />}
    </div>
    </>
  )
}
