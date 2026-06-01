'use client'

import { useEffect, useRef, useState } from 'react'
import { AddressSuggestion, geocodeAddress, suggestAddresses } from '@/lib/geo'

interface Props {
  id?: string
  value: string
  onChange: (value: string) => void
  onSelect: (address: string, lat: number, lng: number) => void
  placeholder?: string
  inputClassName?: string
  disabled?: boolean
  geocoded?: boolean
}

export default function AddressAutocomplete({
  id,
  value,
  onChange,
  onSelect,
  placeholder,
  inputClassName,
  disabled,
  geocoded,
}: Props) {
  const [suggestions, setSuggestions] = useState<AddressSuggestion[]>([])
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [])

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value
    onChange(val)

    if (debounceRef.current) clearTimeout(debounceRef.current)

    if (val.length < 3) {
      setSuggestions([])
      setOpen(false)
      return
    }

    debounceRef.current = setTimeout(async () => {
      setLoading(true)
      const results = await suggestAddresses(val)
      setLoading(false)
      setSuggestions(results)
      setOpen(results.length > 0)
    }, 400)
  }

  const handleSelect = (s: AddressSuggestion) => {
    onChange(s.label)
    onSelect(s.label, s.lat, s.lng)
    setSuggestions([])
    setOpen(false)
    // Enrich with ZIP+4 from Radar forward geocode (rooftop-level, async)
    geocodeAddress(s.label).then((enriched) => {
      if (enriched?.label && enriched.label !== s.label) {
        onChange(enriched.label)
        onSelect(enriched.label, enriched.lat, enriched.lng)
      }
    }).catch(() => {})
  }

  return (
    <div ref={containerRef} className="relative">
      <div className="relative">
        <input
          id={id}
          type="text"
          autoComplete="off"
          value={value}
          onChange={handleChange}
          onKeyDown={(e) => { if (e.key === 'Escape') setOpen(false) }}
          disabled={disabled}
          placeholder={placeholder}
          className={`${inputClassName ?? ''} ${(loading || geocoded) ? 'pr-8' : ''}`}
        />
        {loading && (
          <span className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2">
            <svg className="h-4 w-4 animate-spin text-gray-400" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
            </svg>
          </span>
        )}
        {!loading && geocoded && (
          <span className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2">
            <svg className="h-4 w-4 text-green-500" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd" />
            </svg>
          </span>
        )}
      </div>

      {open && suggestions.length > 0 && (
        <ul
          role="listbox"
          className="absolute z-50 mt-1 w-full rounded border border-gray-200 bg-white py-1 shadow-lg max-h-60 overflow-auto"
        >
          {suggestions.map((s, i) => (
            <li
              key={i}
              role="option"
              aria-selected={false}
              onMouseDown={(e) => {
                e.preventDefault()
                handleSelect(s)
              }}
              className="cursor-pointer truncate px-3 py-2 text-sm text-gray-700 hover:bg-blue-50"
            >
              {s.label}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
