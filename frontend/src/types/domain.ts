export type UserRole = 'provider' | 'admin'

export interface User {
  id: string
  email: string
  role: UserRole
  full_name: string | null
  mfa_enabled: boolean
  is_active: boolean
  created_at: string
}

export interface Patient {
  id: string
  provider_id: string
  name: string
  mco: string | null
  date_of_birth: string | null
  address: string | null
  latitude: number | null
  longitude: number | null
  medicaid_card_image_path: string | null
  eligibility_status: string | null
  eligibility_checked_at: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface PatientWithMedicaidId extends Patient {
  medicaid_id: string
}

export interface SOAPNote {
  id: string
  patient_id: string
  provider_id: string
  visit_date: string
  subjective: string | null
  objective: string | null
  assessment: string | null
  plan: string | null
  created_at: string
  updated_at: string
}

export interface PrenatalLog {
  id: string
  patient_id: string
  provider_id: string
  log_type: 'prenatal' | 'postnatal'
  entry: string
  entry_date: string
  created_at: string
}

export interface BirthLog {
  id: string
  patient_id: string
  provider_id: string
  birth_date: string
  birth_time: string | null
  birth_location: string | null
  notes: string | null
  created_at: string
}

export type VisitType =
  | 'prenatal_1' | 'prenatal_2' | 'prenatal_3' | 'prenatal_4' | 'prenatal_5' | 'prenatal_6'
  | 'labor'
  | 'postnatal_1' | 'postnatal_2' | 'postnatal_3' | 'postnatal_4' | 'postnatal_5' | 'postnatal_6'

export interface Visit {
  id: string
  patient_id: string
  provider_id: string
  visit_type: VisitType
  visit_date: string | null
  subjective: string | null
  objective: string | null
  assessment: string | null
  plan: string | null
  entry: string | null
  birth_time: string | null
  birth_location: string | null
  birth_notes: string | null
  source_image_path: string | null
  visit_started_at: string | null
  provider_latitude: number | null
  provider_longitude: number | null
  location_type: 'in_person' | 'telehealth' | null
  alternate_location: string | null
  created_at: string
  updated_at: string
}

export interface AuditLogEntry {
  id: string
  user_id: string | null
  action: string
  resource_type: string | null
  resource_id: string | null
  ip_address: string | null
  user_agent: string | null
  extra_context: Record<string, unknown> | null
  timestamp: string
}
