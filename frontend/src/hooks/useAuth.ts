'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import axios from 'axios'
import { useAuthStore } from '@/store/auth-store'
import { setAccessToken } from '@/lib/auth'
import { User } from '@/types/domain'

const API = process.env.NEXT_PUBLIC_API_URL

export function useAuth() {
  const { user, isAuthenticated, isLoading, setUser, logout, setLoading } = useAuthStore()
  const router = useRouter()

  useEffect(() => {
    if (!isAuthenticated && isLoading) {
      let accessToken = ''
      axios
        .post<{ access_token: string }>(`${API}/api/v1/auth/refresh`, {}, { withCredentials: true })
        .then((res) => {
          accessToken = res.data.access_token
          setAccessToken(accessToken)
          return axios.get<User>(`${API}/api/v1/auth/me`, {
            headers: { Authorization: `Bearer ${accessToken}` },
          })
        })
        .then((res) => {
          setUser(res.data, accessToken)
        })
        .catch(() => {
          logout()
          router.push('/login')
        })
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return { user, isAuthenticated, isLoading }
}
