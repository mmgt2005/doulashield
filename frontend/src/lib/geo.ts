export function haversineFeet(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 6371000 // Earth radius in metres
  const φ1 = (lat1 * Math.PI) / 180
  const φ2 = (lat2 * Math.PI) / 180
  const Δφ = ((lat2 - lat1) * Math.PI) / 180
  const Δλ = ((lon2 - lon1) * Math.PI) / 180
  const a =
    Math.sin(Δφ / 2) ** 2 +
    Math.cos(φ1) * Math.cos(φ2) * Math.sin(Δλ / 2) ** 2
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
  return R * c * 3.28084 // metres → feet
}

const RADAR_KEY = process.env.NEXT_PUBLIC_RADAR_API_KEY ?? ''

function radarHeaders(): HeadersInit {
  return { Authorization: RADAR_KEY }
}

interface RadarAddress {
  number?: string
  street?: string
  city?: string
  stateCode?: string
  postalCode?: string
  countryCode?: string
  latitude: number
  longitude: number
  formattedAddress?: string
}

function formatLabel(a: RadarAddress): string {
  const parts: string[] = []
  const street = a.number && a.street ? `${a.number} ${a.street}` : a.street ?? null
  if (street) parts.push(street)
  if (a.city) parts.push(a.city)
  if (a.stateCode && a.postalCode) parts.push(`${a.stateCode} ${a.postalCode}`)
  else if (a.stateCode) parts.push(a.stateCode)
  else if (a.postalCode) parts.push(a.postalCode)
  return parts.join(', ')
}

export interface AddressSuggestion {
  label: string
  lat: number
  lng: number
}

export async function geocodeAddress(
  address: string
): Promise<{ lat: number; lng: number } | null> {
  if (!RADAR_KEY) return null
  try {
    const res = await fetch(
      `https://api.radar.io/v1/geocode/forward?query=${encodeURIComponent(address)}&country=US&limit=1`,
      { headers: radarHeaders() }
    )
    const data = await res.json()
    const addr: RadarAddress | undefined = data.addresses?.[0]
    if (!addr) return null
    return { lat: addr.latitude, lng: addr.longitude }
  } catch {
    return null
  }
}

export async function suggestAddresses(query: string): Promise<AddressSuggestion[]> {
  if (query.length < 3 || !RADAR_KEY) return []
  try {
    const res = await fetch(
      `https://api.radar.io/v1/search/autocomplete?query=${encodeURIComponent(query)}&country=US&limit=5`,
      { headers: radarHeaders() }
    )
    const data = await res.json()
    if (!data.addresses?.length) return []
    return (data.addresses as RadarAddress[])
      .filter((a) => !!a.city)
      .map((a) => ({
        label: formatLabel(a),
        lat: a.latitude,
        lng: a.longitude,
      }))
  } catch {
    return []
  }
}
