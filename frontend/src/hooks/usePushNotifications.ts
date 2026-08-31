'use client'

import { useEffect, useRef } from 'react'
import axios from 'axios'
import { getAccessToken } from '@/lib/auth'
import { useAuthStore } from '@/store/auth-store'

const STORAGE_KEY = 'ds_push_subscribed'

function urlBase64ToUint8Array(base64: string): Uint8Array<ArrayBuffer> {
  const padding = '='.repeat((4 - (base64.length % 4)) % 4)
  const b64 = (base64 + padding).replace(/-/g, '+').replace(/_/g, '/')
  const raw = atob(b64)
  const buf = new ArrayBuffer(raw.length)
  const arr = new Uint8Array(buf)
  for (let i = 0; i < raw.length; i++) arr[i] = raw.charCodeAt(i)
  return arr
}

export function usePushNotifications() {
  const { user, isAuthenticated } = useAuthStore()
  const attempted = useRef(false)

  useEffect(() => {
    if (!isAuthenticated || !user) return
    if (attempted.current) return
    if (typeof window === 'undefined') return
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) return

    try {
      if (localStorage.getItem(STORAGE_KEY) === '1') return
    } catch { return }

    attempted.current = true

    const subscribe = async () => {
      try {
        const api = process.env.NEXT_PUBLIC_API_URL
        const { data } = await axios.get(`${api}/api/v1/push/vapid-public-key`)
        if (!data.vapid_public_key) return

        const reg = await navigator.serviceWorker.register('/sw.js', { scope: '/' })
        await navigator.serviceWorker.ready

        const permission = await Notification.requestPermission()
        if (permission !== 'granted') return

        const existingSub = await reg.pushManager.getSubscription()
        const sub = existingSub ?? await reg.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: urlBase64ToUint8Array(data.vapid_public_key),
        })

        const json = sub.toJSON()
        if (!json.endpoint || !json.keys?.p256dh || !json.keys?.auth) return

        await axios.post(
          `${api}/api/v1/push/subscribe`,
          { endpoint: json.endpoint, p256dh_key: json.keys.p256dh, auth_key: json.keys.auth },
          { headers: { Authorization: `Bearer ${getAccessToken()}` } },
        )

        try { localStorage.setItem(STORAGE_KEY, '1') } catch { /* ignore */ }
      } catch (err) {
        console.warn('[DoulaShield] Push notification setup failed:', err)
      }
    }

    // Delay registration so it doesn't compete with initial page hydration
    const timer = setTimeout(subscribe, 4000)
    return () => clearTimeout(timer)
  }, [isAuthenticated, user])
}
