'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import axios from 'axios'
import { useAuthStore } from '@/store/auth-store'
import { setAccessToken } from '@/lib/auth'
import { User } from '@/types/domain'

export function useAuth() {
  const { user, isAuthenticated, isLoading, setUser, logout, setLoading } = useAuthStore()
  const router = useRouter()

  useEffect(() => {
    if (!isAuthenticated && isLoading) {
      // Attempt silent refresh on mount — uses httpOnly cookie automatically
      axios
        .post<{ access_token: string }>(
          `${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/refresh`,
          {},
          { withCredentials: true }
        )
        .then((res) => {
          setAccessToken(res.data.access_token)
          // TODO: fetch /api/v1/auth/me to hydrate user profile
          setLoading(false)
        })
        .catch(() => {
          logout()
          router.push('/login')
        })
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return { user, isAuthenticated, isLoading }
}
