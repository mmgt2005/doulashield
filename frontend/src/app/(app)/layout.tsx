'use client'

import { useCallback } from 'react'
import { useRouter } from 'next/navigation'
import Sidebar from '@/components/layout/Sidebar'
import SessionTimeoutModal from '@/components/layout/SessionTimeoutModal'
import { useSessionTimeout } from '@/hooks/useSessionTimeout'
import { useAuthStore } from '@/store/auth-store'
import axios from 'axios'
import { clearAccessToken } from '@/lib/auth'

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const { logout } = useAuthStore()

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
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-auto p-6">
        {children}
      </main>
      {showWarning && <SessionTimeoutModal onStayLoggedIn={resetTimeout} />}
    </div>
  )
}
