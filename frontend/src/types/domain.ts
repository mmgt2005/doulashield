export type UserRole = 'provider' | 'admin' | 'billing_admin'

export interface User {
  id: string
  email: string
  role: UserRole
  full_name: string | null
  mfa_enabled: boolean
  is_active: boolean
  is_demo?: boolean
  is_executive?: boolean
  created_at: string
  last_sign_in_at: string | null
  welcome_email_sent_at: string | null
  billing_provider_id: string | null
  managed_billing_provider_id: string | null
}

export interface BillingProvider {
  id: string
  name: string
  group_npi: string | null
  address: string | null
  city: string | null
  state: string | null
  zip: string | null
  phone: string | null
  stripe_subscription_id: string | null
  subscription_status: string | null
  enrollment_tier_enabled: boolean
  created_at: string
  provider_count: number
}

export interface Patient {
  id: string
  provider_id: string
  name: string
  gender: string
  email: string | null
  referring_provider_npi: string | null
  referring_provider_name: string | null
  has_other_insurance: boolean
  mco: string | null
  date_of_birth: string | null
  address: string | null
  latitude: number | null
  longitude: number | null
  medicaid_card_image_path: string | null
  policy_group: string | null
  eligibility_status: string | null
  eligibility_checked_at: string | null
  ma589_signed_date: string | null
  is_active: boolean
  is_demo: boolean
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
  | 'crisis_loss_1' | 'crisis_loss_2'

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
  visit_ended_at: string | null
  provider_latitude: number | null
  provider_longitude: number | null
  location_type: 'in_person' | 'telehealth' | null
  alternate_location: string | null
  ma91_signed_at: string | null
  ma91_signature_path: string | null
  ma91_signed_by_name: string | null
  ma91_zipzign_request_id: string | null
  ma91_status: 'signed' | 'pending' | 'declined' | null
  prior_auth_number: string | null
  created_at: string
  updated_at: string
}

export interface Claim {
  id: string
  patient_id: string
  provider_id: string
  availity_claim_id: string | null
  visit_type: string | null
  is_manual: boolean
  status: string | null
  service_date: string | null
  billed_amount: string | null
  paid_amount: string | null
  payer_id: string | null
  submitted_at: string | null
  status_checked_at: string | null
  denial_reason: string | null
  error_code: string | null
  resubmit_count: number
  remittance_id: string | null
  filing_deadline_date: string | null
  days_until_filing_deadline: number | null
  created_at: string
  updated_at: string
}

export interface ClaimErrorCode {
  code: string
  title: string
  description: string
  risk: string
  fix_instructions: string
  is_custom: boolean
}

export interface BillingStatus {
  stripe_customer_id: string | null
  escrow_agreed_at: string | null
  escrow_agreement_version: string | null
  deposit_paid: boolean
  deposit_paid_at: string | null
  escrow_balance_remaining: number
  subscription_status: string | null
}

export interface UserWithBilling {
  id: string
  email: string
  role: UserRole
  full_name: string | null
  is_active: boolean
  stripe_customer_id: string | null
  escrow_agreed_at: string | null
  deposit_paid: boolean
  deposit_paid_at: string | null
  escrow_balance_remaining: number
  subscription_status: string | null
}

export type LeadSource = 'webinar' | 'quiz' | 'manual' | 'contact_form' | 'cal_com'
export type LeadStatus = 'new' | 'contacted' | 'qualified' | 'demo_scheduled' | 'converted' | 'not_interested'
export type LeadProviderType = 'independent' | 'agency' | 'unknown'

export interface Lead {
  id: string
  source: LeadSource
  status: LeadStatus
  first_name: string
  last_name: string
  email: string
  phone: string | null
  organization_name: string | null
  provider_type: LeadProviderType
  lead_data: Record<string, unknown> | null
  notes: string | null
  follow_up_at: string | null
  assigned_to: string | null
  converted_user_id: string | null
  cal_booking_uid: string | null
  created_at: string
  updated_at: string | null
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
