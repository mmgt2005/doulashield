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
