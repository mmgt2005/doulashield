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

export async function geocodeAddress(
  address: string
): Promise<{ lat: number; lng: number } | null> {
  try {
    const res = await fetch(
      `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(address)}&format=json&limit=1`,
      { headers: { 'Accept-Language': 'en' } }
    )
    const data = await res.json()
    if (!Array.isArray(data) || data.length === 0) return null
    return { lat: parseFloat(data[0].lat), lng: parseFloat(data[0].lon) }
  } catch {
    return null
  }
}

export interface AddressSuggestion {
  label: string
  lat: number
  lng: number
}

// US state full name → abbreviation
const US_STATE_ABBR: Record<string, string> = {
  'Alabama': 'AL', 'Alaska': 'AK', 'Arizona': 'AZ', 'Arkansas': 'AR',
  'California': 'CA', 'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE',
  'Florida': 'FL', 'Georgia': 'GA', 'Hawaii': 'HI', 'Idaho': 'ID',
  'Illinois': 'IL', 'Indiana': 'IN', 'Iowa': 'IA', 'Kansas': 'KS',
  'Kentucky': 'KY', 'Louisiana': 'LA', 'Maine': 'ME', 'Maryland': 'MD',
  'Massachusetts': 'MA', 'Michigan': 'MI', 'Minnesota': 'MN', 'Mississippi': 'MS',
  'Missouri': 'MO', 'Montana': 'MT', 'Nebraska': 'NE', 'Nevada': 'NV',
  'New Hampshire': 'NH', 'New Jersey': 'NJ', 'New Mexico': 'NM', 'New York': 'NY',
  'North Carolina': 'NC', 'North Dakota': 'ND', 'Ohio': 'OH', 'Oklahoma': 'OK',
  'Oregon': 'OR', 'Pennsylvania': 'PA', 'Rhode Island': 'RI', 'South Carolina': 'SC',
  'South Dakota': 'SD', 'Tennessee': 'TN', 'Texas': 'TX', 'Utah': 'UT',
  'Vermont': 'VT', 'Virginia': 'VA', 'Washington': 'WA', 'West Virginia': 'WV',
  'Wisconsin': 'WI', 'Wyoming': 'WY', 'District of Columbia': 'DC',
  'Puerto Rico': 'PR',
}

interface NominatimAddressComponents {
  house_number?: string
  road?: string
  city?: string
  town?: string
  village?: string
  hamlet?: string
  municipality?: string
  state?: string
  postcode?: string
}

function formatLabel(components: NominatimAddressComponents): string {
  const parts: string[] = []

  const street = components.house_number && components.road
    ? `${components.house_number} ${components.road}`
    : components.road ?? null
  if (street) parts.push(street)

  const city =
    components.city ??
    components.town ??
    components.village ??
    components.hamlet ??
    components.municipality ?? null
  if (city) parts.push(city)

  const stateAbbr = US_STATE_ABBR[components.state ?? ''] ?? components.state
  const postcode = components.postcode
  if (stateAbbr && postcode) parts.push(`${stateAbbr} ${postcode}`)
  else if (stateAbbr) parts.push(stateAbbr)
  else if (postcode) parts.push(postcode)

  return parts.join(', ')
}

export async function suggestAddresses(query: string): Promise<AddressSuggestion[]> {
  if (query.length < 3) return []
  try {
    const res = await fetch(
      `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(query)}&format=json&limit=5&addressdetails=1`,
      { headers: { 'Accept-Language': 'en' } }
    )
    const data = await res.json()
    if (!Array.isArray(data)) return []
    return data
      .filter((r: { address: NominatimAddressComponents }) =>
        !!(r.address.city ?? r.address.town ?? r.address.village ?? r.address.hamlet ?? r.address.municipality)
      )
      .map((r: { address: NominatimAddressComponents; lat: string; lon: string }) => ({
        label: formatLabel(r.address),
        lat: parseFloat(r.lat),
        lng: parseFloat(r.lon),
      }))
  } catch {
    return []
  }
}
