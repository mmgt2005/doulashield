'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/store/auth-store'

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const { user, isLoading } = useAuthStore()

  useEffect(() => {
    if (!isLoading && user?.role !== 'admin') {
      router.replace('/dashboard')
    }
  }, [user, isLoading, router])

  if (isLoading || user?.role !== 'admin') return null

  return <>{children}</>
}
