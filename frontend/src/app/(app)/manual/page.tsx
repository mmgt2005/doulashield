'use client'

import { useEffect, useState } from 'react'
import { parseMarkdown } from '@/lib/markdown'

export default function ManualPage() {
  const [html, setHtml] = useState<string | null>(null)

  useEffect(() => {
    fetch('/docs/manual.md')
      .then((r) => r.text())
      .then((md) => setHtml(parseMarkdown(md)))
      .catch(() => setHtml('<p>Could not load manual.</p>'))
  }, [])

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
