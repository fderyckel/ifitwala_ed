// ifitwala_ed/ui-spa/src/types/contracts/admissions/types.ts

export type PortalApplicantStatus =
  | 'Draft'
  | 'In Progress'
  | 'Action Required'
  | 'In Review'
  | 'Accepted'
  | 'Rejected'
  | 'Withdrawn'
  | 'Completed'

export type CompletionState = 'pending' | 'in_progress' | 'complete' | 'optional'

export type NextAction = {
  label: string
  route_name: string
  intent: 'primary' | 'secondary' | 'neutral'
  is_blocking: boolean
  icon?: string
}

export type ApplicantApplicationContext = {
  organization: string
  school: string
  academic_year?: string | null
  term?: string | null
  program?: string | null
  program_offering?: string | null
}

export type ApplicantProfile = {
  student_preferred_name?: string | null
  student_date_of_birth?: string | null
  student_gender?: string | null
  student_mobile_number?: string | null
  student_joining_date?: string | null
  student_first_language?: string | null
  student_second_language?: string | null
  student_nationality?: string | null
  student_second_nationality?: string | null
  residency_status?: string | null
}

export type ApplicantGuardianProfile = {
  name?: string | null
  guardian?: string | null
  contact?: string | null
  use_applicant_contact?: boolean | number | null
  relationship?: string | null
  is_primary?: boolean | number | null
  can_consent?: boolean | number | null
  salutation?: string | null
  guardian_full_name?: string | null
  guardian_first_name?: string | null
  guardian_last_name?: string | null
  guardian_gender?: string | null
  guardian_mobile_phone?: string | null
  guardian_email?: string | null
  guardian_work_email?: string | null
  guardian_work_phone?: string | null
  guardian_image?: string | null
  user?: string | null
  is_primary_guardian?: boolean | number | null
  is_financial_guardian?: boolean | number | null
  employment_sector?: string | null
  work_place?: string | null
  guardian_designation?: string | null
}

export type ApplicantProfileCompleteness = {
  ok: boolean
  missing: string[]
  required: string[]
}

export type ApplicantDocument = {
  name: string
  document_type: string
  label?: string | null
  description?: string | null
  is_required?: boolean
  is_repeatable?: boolean
  required_count?: number
  uploaded_count?: number
  approved_count?: number
  rejected_count?: number
  pending_count?: number
  requirement_state?:
    | 'not_started'
    | 'waiting_review'
    | 'changes_requested'
    | 'complete'
    | 'waived'
    | 'exception_approved'
    | 'optional'
    | null
  requirement_state_label?: string | null
  requirement_override?: 'Waived' | 'Exception Approved' | null
  override_reason?: string | null
  override_by?: string | null
  override_on?: string | null
  review_status: 'Pending' | 'Approved' | 'Rejected' | 'Superseded'
  reviewed_by?: string | null
  reviewed_on?: string | null
  uploaded_at?: string | null
  file_url?: string | null
  items?: Array<{
    name?: string
    item_key: string
    item_label: string
    review_status: 'Pending' | 'Approved' | 'Rejected' | 'Superseded'
    reviewed_by?: string | null
    reviewed_on?: string | null
    uploaded_at?: string | null
    file_url?: string | null
    file_name?: string | null
  }>
}

export type ApplicantPolicy = {
  name: string
  policy_version: string
  content_html: string
  is_acknowledged: boolean
  acknowledged_at?: string | null
  expected_signature_name: string
}

export type ApplicantMessage = {
  name: string
  user: string
  full_name: string
  body: string
  direction: 'ApplicantToStaff' | 'StaffToApplicant' | 'Internal'
  visibility: string
  applicant_visible: boolean
  created_at?: string | null
  modified_at?: string | null
}
