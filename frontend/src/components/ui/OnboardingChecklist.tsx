'use client'

import { useState } from 'react'
import Link from 'next/link'

export interface ChecklistItem {
  label: string
  done: boolean
  href: string
}

interface Props {
  items: ChecklistItem[]
  onDismiss: () => void
}

export default function OnboardingChecklist({ items, onDismiss }: Props) {
  const [collapsed, setCollapsed] = useState(false)

  const doneCount = items.filter(i => i.done).length
  const allDone = doneCount === items.length
  const pct = Math.round((doneCount / items.length) * 100)

  if (allDone) return null

  return (
    <div className="rounded-lg border border-blue-200 bg-blue-50 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-blue-200">
        <button
          onClick={() => setCollapsed(c => !c)}
          className="flex items-center gap-2 text-left flex-1 min-w-0"
        >
          <span className="text-sm font-semibold text-blue-900">
            Get Started — {doneCount} of {items.length} complete
          </span>
          <svg
            className={`h-4 w-4 text-blue-500 shrink-0 transition-transform ${collapsed ? '-rotate-90' : ''}`}
            fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        </button>
        <button
          onClick={onDismiss}
          className="ml-2 shrink-0 text-xs text-blue-400 hover:text-blue-600"
          title="Dismiss checklist"
        >
          Dismiss
        </button>
      </div>

      {/* Progress bar */}
      <div className="h-1 bg-blue-100">
        <div
          className="h-1 bg-blue-500 transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>

      {/* Items */}
      {!collapsed && (
        <ul className="divide-y divide-blue-100">
          {items.map((item) => (
            <li key={item.href} className="flex items-center gap-3 px-4 py-2.5">
              {item.done ? (
                <div className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-green-500">
                  <svg className="h-3 w-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                </div>
              ) : (
                <div className="h-5 w-5 shrink-0 rounded-full border-2 border-blue-300" />
              )}
              {item.done ? (
                <span className="text-xs text-gray-400 line-through">{item.label}</span>
              ) : (
                <Link
                  href={item.href}
                  className="text-xs text-blue-700 hover:text-blue-900 hover:underline"
                >
                  {item.label} →
                </Link>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
