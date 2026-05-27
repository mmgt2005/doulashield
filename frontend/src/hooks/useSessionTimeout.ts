'use client'

import { useEffect, useRef, useState } from 'react'
import { SessionTimeoutManager } from '@/lib/session-timeout'

export function useSessionTimeout(onTimeout: () => void) {
  const [showWarning, setShowWarning] = useState(false)
  const managerRef = useRef<SessionTimeoutManager | null>(null)

  useEffect(() => {
    const manager = new SessionTimeoutManager(
      () => {
        setShowWarning(false)
        onTimeout()
      },
      () => setShowWarning(true)
    )
    managerRef.current = manager
    manager.start()

    return () => manager.destroy()
  }, [onTimeout])

  const resetTimeout = () => {
    setShowWarning(false)
    managerRef.current?.reset()
  }

  return { showWarning, resetTimeout }
}
