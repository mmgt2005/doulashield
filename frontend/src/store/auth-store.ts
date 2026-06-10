'use client'

import { create } from 'zustand'
import { User } from '@/types/domain'
import { setAccessToken, clearAccessToken, getAccessToken } from '@/lib/auth'

interface PriorSession {
  user: User
  token: string
}

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  priorSession: PriorSession | null
  setUser: (user: User, token: string) => void
  updateToken: (token: string) => void
  logout: () => void
  setLoading: (loading: boolean) => void
  startImpersonation: (targetUser: User, impToken: string) => void
  exitImpersonation: () => void
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true,
  priorSession: null,

  setUser: (user, token) => {
    setAccessToken(token)
    set({ user, isAuthenticated: true, isLoading: false })
  },

  updateToken: (token) => {
    setAccessToken(token)
  },

  logout: () => {
    clearAccessToken()
    set({ user: null, isAuthenticated: false, isLoading: false, priorSession: null })
  },

  setLoading: (loading) => set({ isLoading: loading }),

  startImpersonation: (targetUser, impToken) => {
    const current = get()
    const prior: PriorSession = {
      user: current.user!,
      token: getAccessToken()!,
    }
    setAccessToken(impToken)
    set({ user: targetUser, priorSession: prior })
  },

  exitImpersonation: () => {
    const { priorSession } = get()
    if (!priorSession) return
    setAccessToken(priorSession.token)
    set({ user: priorSession.user, priorSession: null })
  },
}))
