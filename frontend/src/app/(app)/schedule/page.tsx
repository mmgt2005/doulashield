'use client'

import { useEffect, useState, useCallback } from 'react'
import Link from 'next/link'
import axios from 'axios'
import { getAccessToken } from '@/lib/auth'

interface ScheduleEntry {
  patient_id: string
  patient_name: string
  visit_type: string
  visit_label: string
  scheduled_at: string | null
  visit_date: string | null
  visit_started_at: string | null
  visit_ended_at: string | null
  status: 'complete' | 'in_progress' | 'scheduled' | 'unscheduled'
}

function getMonday(d: Date): Date {
  const day = d.getDay()
  const diff = day === 0 ? -6 : 1 - day
  const mon = new Date(d)
  mon.setDate(d.getDate() + diff)
  mon.setHours(0, 0, 0, 0)
  return mon
}

function formatDate(d: Date): string {
  return d.toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' })
}

function toYMD(d: Date): string {
  return d.toISOString().slice(0, 10)
}

function entryDateKey(entry: ScheduleEntry): string {
  if (entry.scheduled_at) return entry.scheduled_at.slice(0, 10)
  if (entry.visit_date) return entry.visit_date
  if (entry.visit_started_at) return entry.visit_started_at.slice(0, 10)
  return ''
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

const STATUS_STYLES: Record<string, string> = {
  complete: 'bg-green-100 text-green-700',
  in_progress: 'bg-amber-100 text-amber-700',
  scheduled: 'bg-blue-100 text-blue-700',
  unscheduled: 'bg-gray-100 text-gray-500',
}

const STATUS_LABELS: Record<string, string> = {
  complete: 'Done',
  in_progress: 'In progress',
  scheduled: '',
  unscheduled: 'No time set',
}

export default function SchedulePage() {
  const [weekStart, setWeekStart] = useState<Date>(() => getMonday(new Date()))
  const [entries, setEntries] = useState<ScheduleEntry[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const weekEnd = new Date(weekStart)
  weekEnd.setDate(weekStart.getDate() + 6)

  const load = useCallback((start: Date) => {
    setLoading(true)
    setError(null)
    const end = new Date(start)
    end.setDate(start.getDate() + 6)
    axios
      .get<ScheduleEntry[]>(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/schedule`, {
        params: { date_from: toYMD(start), date_to: toYMD(end) },
        headers: { Authorization: `Bearer ${getAccessToken()}` },
      })
      .then((r) => setEntries(r.data))
      .catch(() => setError('Failed to load schedule.'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { load(weekStart) }, [weekStart, load])

  const goBack = () => {
    const d = new Date(weekStart)
    d.setDate(d.getDate() - 7)
    setWeekStart(d)
  }

  const goForward = () => {
    const d = new Date(weekStart)
    d.setDate(d.getDate() + 7)
    setWeekStart(d)
  }

  const goToday = () => setWeekStart(getMonday(new Date()))

  // Build day buckets for the week
  const days: Date[] = Array.from({ length: 7 }, (_, i) => {
    const d = new Date(weekStart)
    d.setDate(weekStart.getDate() + i)
    return d
  })

  // Group entries by date key
  const byDay = new Map<string, ScheduleEntry[]>()
  for (const entry of entries ?? []) {
    const key = entryDateKey(entry)
    if (!key) continue
    if (!byDay.has(key)) byDay.set(key, [])
    byDay.get(key)!.push(entry)
  }

  const todayKey = toYMD(new Date())
  const hasAny = entries && entries.length > 0

  return (
    <div className="space-y-4 max-w-2xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Schedule</h1>
        <div className="flex items-center gap-2">
          <button
            onClick={goBack}
            className="rounded border border-gray-300 px-2 py-1 text-sm text-gray-600 hover:bg-gray-50"
          >
            ←
          </button>
          <button
            onClick={goToday}
            className="rounded border border-gray-300 px-3 py-1 text-sm text-gray-600 hover:bg-gray-50"
          >
            Today
          </button>
          <button
            onClick={goForward}
            className="rounded border border-gray-300 px-2 py-1 text-sm text-gray-600 hover:bg-gray-50"
          >
            →
          </button>
        </div>
      </div>

      {/* Week range label */}
      <p className="text-sm text-gray-500">
        {weekStart.toLocaleDateString('en-US', { month: 'long', day: 'numeric' })}
        {' – '}
        {weekEnd.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}
      </p>

      {loading && <p className="text-sm text-gray-500">Loading…</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}

      {!loading && !error && (
        <>
          {!hasAny && (
            <div className="rounded-lg border border-gray-200 bg-white p-6 text-center">
              <p className="text-sm font-medium text-gray-600">No visits this week</p>
              <p className="mt-1 text-xs text-gray-400">
                Open a client&apos;s visit and set a &ldquo;Planned date &amp; time&rdquo; to see it here.
              </p>
              <Link href="/clients" className="mt-3 inline-block text-xs font-medium text-blue-600 hover:underline">
                Go to Clients →
              </Link>
            </div>
          )}

          {hasAny && days.map((day) => {
            const key = toYMD(day)
            const dayEntries = byDay.get(key) ?? []
            const isToday = key === todayKey
            if (dayEntries.length === 0) return null

            return (
              <div key={key} className="space-y-2">
                {/* Day header */}
                <div className="flex items-center gap-2">
                  <p className={`text-sm font-semibold ${isToday ? 'text-blue-700' : 'text-gray-800'}`}>
                    {formatDate(day)}
                    {isToday && <span className="ml-2 rounded-full bg-blue-600 px-2 py-0.5 text-xs font-medium text-white">Today</span>}
                  </p>
                  <div className="flex-1 h-px bg-gray-200" />
                </div>

                {/* Visit cards */}
                {dayEntries.map((entry) => (
                  <Link
                    key={`${entry.patient_id}-${entry.visit_type}`}
                    href={`/clients/${entry.patient_id}/visits/${entry.visit_type}`}
                    className="flex items-center justify-between rounded-lg border border-gray-200 bg-white px-4 py-3 hover:border-blue-300 hover:bg-blue-50 transition-colors"
                  >
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-gray-900">{entry.visit_label}</p>
                      <p className="text-xs text-gray-500 truncate">{entry.patient_name}</p>
                    </div>
                    <div className="flex items-center gap-2 ml-3 flex-shrink-0">
                      {entry.scheduled_at && entry.status === 'scheduled' && (
                        <span className="text-xs font-medium text-gray-500">{formatTime(entry.scheduled_at)}</span>
                      )}
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_STYLES[entry.status]}`}>
                        {STATUS_LABELS[entry.status] || (entry.scheduled_at ? formatTime(entry.scheduled_at) : '')}
                      </span>
                    </div>
                  </Link>
                ))}
              </div>
            )
          })}
        </>
      )}
    </div>
  )
}
