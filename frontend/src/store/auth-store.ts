'use client'

import { create } from 'zustand'
import { User } from '@/types/domain'
import { setAccessToken, clearAccessToken } from '@/lib/auth'

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  setUser: (user: User, token: string) => void
  updateToken: (token: string) => void
  logout: () => void
  setLoading: (loading: boolean) => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true,

  setUser: (user, token) => {
    setAccessToken(token)
    set({ user, isAuthenticated: true, isLoading: false })
  },

  updateToken: (token) => {
    setAccessToken(token)
  },

  logout: () => {
    clearAccessToken()
    set({ user: null, isAuthenticated: false, isLoading: false })
  },

  setLoading: (loading) => set({ isLoading: loading }),
}))
