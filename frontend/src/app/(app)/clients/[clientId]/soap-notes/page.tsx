'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import axios from 'axios'
import { getAccessToken } from '@/lib/auth'
import { SOAPNote } from '@/types/domain'

export default function SOAPNotesPage() {
  const { clientId } = useParams<{ clientId: string }>()
  const [notes, setNotes] = useState<SOAPNote[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    axios
      .get<SOAPNote[]>(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/patients/${clientId}/soap-notes`,
        { headers: { Authorization: `Bearer ${getAccessToken()}` } }
      )
      .then((r) => setNotes(r.data))
      .finally(() => setLoading(false))
  }, [clientId])

  if (loading) return <p className="text-sm text-gray-500">Loading…</p>

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-900">SOAP Notes</h1>
        <Link
          href={`/clients/${clientId}/soap-notes/new`}
          className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          New note
        </Link>
      </div>

      {notes.length === 0 ? (
        <p className="text-sm text-gray-500">No notes yet.</p>
      ) : (
        <div className="space-y-3">
          {notes.map((note) => (
            <div key={note.id} className="bg-white rounded-lg border border-gray-200 p-4">
              <p className="text-xs text-gray-400 mb-2">Visit: {note.visit_date}</p>
              {note.subjective && (
                <div className="mb-2">
                  <span className="text-xs font-semibold uppercase text-gray-500">S</span>
                  <p className="text-sm mt-1">{note.subjective}</p>
                </div>
              )}
              {note.objective && (
                <div className="mb-2">
                  <span className="text-xs font-semibold uppercase text-gray-500">O</span>
                  <p className="text-sm mt-1">{note.objective}</p>
                </div>
              )}
              {note.assessment && (
                <div className="mb-2">
                  <span className="text-xs font-semibold uppercase text-gray-500">A</span>
                  <p className="text-sm mt-1">{note.assessment}</p>
                </div>
              )}
              {note.plan && (
                <div>
                  <span className="text-xs font-semibold uppercase text-gray-500">P</span>
                  <p className="text-sm mt-1">{note.plan}</p>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
