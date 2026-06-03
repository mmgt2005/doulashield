'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/store/auth-store'
import { parseMarkdown } from '@/lib/markdown'

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
      .then((md) => setHtml(parseMarkdown(md)))
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
