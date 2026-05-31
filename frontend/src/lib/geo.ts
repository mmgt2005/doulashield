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

// ── Radar.io types ────────────────────────────────────────────────────────────

interface RadarAddress {
  number?: string
  street?: string
  city?: string
  stateCode?: string
  postalCode?: string
  latitude: number
  longitude: number
}

function radarLabel(a: RadarAddress): string {
  const parts: string[] = []
  const street = a.number && a.street ? `${a.number} ${a.street}` : a.street ?? null
  if (street) parts.push(street)
  if (a.city) parts.push(a.city)
  if (a.stateCode && a.postalCode) parts.push(`${a.stateCode} ${a.postalCode}`)
  else if (a.stateCode) parts.push(a.stateCode)
  else if (a.postalCode) parts.push(a.postalCode)
  return parts.join(', ')
}

// ── Photon (komoot.io) types — fallback when no Radar key ────────────────────

interface PhotonProperties {
  housenumber?: string
  street?: string
  city?: string
  town?: string
  village?: string
  hamlet?: string
  state?: string
  postcode?: string
}

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

function photonLabel(props: PhotonProperties): string {
  const parts: string[] = []
  const street = props.housenumber && props.street
    ? `${props.housenumber} ${props.street}`
    : props.street ?? null
  if (street) parts.push(street)
  const city = props.city ?? props.town ?? props.village ?? props.hamlet ?? null
  if (city) parts.push(city)
  const stateAbbr = US_STATE_ABBR[props.state ?? ''] ?? props.state
  const postcode = props.postcode
  if (stateAbbr && postcode) parts.push(`${stateAbbr} ${postcode}`)
  else if (stateAbbr) parts.push(stateAbbr)
  else if (postcode) parts.push(postcode)
  return parts.join(', ')
}

// ── Public interface ──────────────────────────────────────────────────────────

export interface AddressSuggestion {
  label: string
  lat: number
  lng: number
}

export async function geocodeAddress(
  address: string
): Promise<{ lat: number; lng: number } | null> {
  try {
    if (RADAR_KEY) {
      const res = await fetch(
        `https://api.radar.io/v1/geocode/forward?query=${encodeURIComponent(address)}&country=US&limit=1`,
        { headers: { Authorization: RADAR_KEY } }
      )
      const data = await res.json()
      const addr: RadarAddress | undefined = data.addresses?.[0]
      if (!addr) return null
      return { lat: addr.latitude, lng: addr.longitude }
    }
    // Photon fallback
    const res = await fetch(
      `https://photon.komoot.io/api/?q=${encodeURIComponent(address)}&limit=1&lang=en&countrycodes=us`
    )
    const data = await res.json()
    if (!data.features?.length) return null
    const [lng, lat] = data.features[0].geometry.coordinates
    return { lat, lng }
  } catch {
    return null
  }
}

export async function suggestAddresses(query: string): Promise<AddressSuggestion[]> {
  if (query.length < 3) return []
  try {
    if (RADAR_KEY) {
      const res = await fetch(
        `https://api.radar.io/v1/search/autocomplete?query=${encodeURIComponent(query)}&country=US&limit=5`,
        { headers: { Authorization: RADAR_KEY } }
      )
      const data = await res.json()
      if (!data.addresses?.length) return []
      return (data.addresses as RadarAddress[])
        .filter((a) => !!a.city)
        .map((a) => ({ label: radarLabel(a), lat: a.latitude, lng: a.longitude }))
    }
    // Photon fallback
    const res = await fetch(
      `https://photon.komoot.io/api/?q=${encodeURIComponent(query)}&limit=5&lang=en&countrycodes=us`
    )
    const data = await res.json()
    if (!data.features?.length) return []
    return data.features
      .filter((f: { properties: PhotonProperties }) =>
        !!(f.properties.city ?? f.properties.town ?? f.properties.village ?? f.properties.hamlet)
      )
      .map((f: { properties: PhotonProperties; geometry: { coordinates: [number, number] } }) => ({
        label: photonLabel(f.properties),
        lat: f.geometry.coordinates[1],
        lng: f.geometry.coordinates[0],
      }))
  } catch {
    return []
  }
}
