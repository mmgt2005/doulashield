'use client'

import { useAuthStore } from '@/store/auth-store'
import { getAccessToken } from '@/lib/auth'

export default function ImpersonationBanner() {
  const { priorSession, user, exitImpersonation } = useAuthStore()

  if (!priorSession) return null

  const handleExit = async () => {
    const base = process.env.NEXT_PUBLIC_API_URL
    try {
      await fetch(`${base}/api/v1/auth/impersonate/end`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${getAccessToken()}` },
      })
    } catch {
      // best-effort — always exit regardless
    } finally {
      exitImpersonation()
    }
  }

  return (
    <div className="fixed top-0 inset-x-0 z-[100] flex items-center justify-between bg-amber-500 px-4 py-1.5 text-sm font-medium text-white shadow">
      <span>
        👁 Viewing as <strong>{user?.full_name || user?.email}</strong>
        <span className="ml-2 font-normal opacity-80">— admin impersonation session</span>
      </span>
      <button
        onClick={handleExit}
        className="rounded border border-white/40 bg-white/20 px-3 py-0.5 text-xs font-semibold hover:bg-white/30"
      >
        Exit
      </button>
    </div>
  )
}
