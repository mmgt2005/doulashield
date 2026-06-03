'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { marked } from 'marked'
import { useAuthStore } from '@/store/auth-store'

export default function AdminGuidePage() {
  const router = useRouter()
  const { user } = useAuthStore()
  const [html, setHtml] = useState<string | null>(null)

  useEffect(() => {
    if (user && user.role !== 'admin') {
      router.replace('/dashboard')
      return
    }
    fetch('/docs/admin-guide.md')
      .then((r) => r.text())
      .then((md) => setHtml(marked.parse(md) as string))
      .catch(() => setHtml('<p>Could not load guide.</p>'))
  }, [user, router])

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      {html === null ? (
        <p className="text-sm text-gray-500">Loading…</p>
      ) : (
        <article
          className="prose prose-sm prose-blue max-w-none"
          dangerouslySetInnerHTML={{ __html: html }}
        />
      )}
    </div>
  )
}
