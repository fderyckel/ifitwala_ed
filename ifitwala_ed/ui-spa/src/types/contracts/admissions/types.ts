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

export type ApplicantProfileCompleteness = {
  ok: boolean
  missing: string[]
  required: string[]
}

export type ApplicantDocument = {
  name: string
  document_type: string
  review_status: 'Pending' | 'Approved' | 'Rejected'
  uploaded_at?: string | null
  file_url?: string | null
}

export type ApplicantPolicy = {
  name: string
  policy_version: string
  content_html: string
  is_acknowledged: boolean
  acknowledged_at?: string | null
}
