// ifitwala_ed/ui-spa/src/types/contracts/admissions/types.ts

import type { GovernedAttachmentRow } from '@/types/contracts/attachments/shared'

export type PortalApplicantStatus =
  | 'Draft'
  | 'In Progress'
  | 'Action Required'
  | 'In Review'
  | 'Offer Sent'
  | 'Offer Expired'
  | 'Accepted'
  | 'Declined'
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

export type AdmissionsDepositSummary = {
  deposit_required: boolean
  deposit_amount: number
  deposit_due_date?: string | null
  deposit_billable_offering?: string | null
  terms_source: 'School Default' | 'Manual Override' | string
  override_status: 'Not Required' | 'Pending' | 'Approved' | 'Rejected' | string
  requires_override_approval: boolean
  academic_approved: boolean
  finance_approved: boolean
  payment_instructions?: string | null
  invoice?: string | null
  invoice_status?: string | null
  docstatus?: number | null
  amount: number
  paid_amount: number
  outstanding_amount: number
  due_date?: string | null
  is_overdue: boolean
  is_paid: boolean
  blocker_label?: string | null
}

export type AdmissionsEnrollmentOffer = {
  name: string
  status: string
  academic_year?: string | null
  term?: string | null
  program?: string | null
  program_offering?: string | null
  offer_expires_on?: string | null
  offer_sent_on?: string | null
  offer_accepted_on?: string | null
  offer_declined_on?: string | null
  offer_message?: string | null
  can_accept?: boolean
  can_decline?: boolean
  course_choices_available?: boolean
  course_choices_can_edit?: boolean
  course_choices_ready?: boolean
  course_choice_blocking_reasons?: string[]
  course_choice_optional_count?: number
  course_choice_selected_optional_count?: number
  deposit?: AdmissionsDepositSummary | null
}

export type AdmissionsSessionApplicant = {
  name: string
  display_name: string
  portal_status: PortalApplicantStatus
  application_status?: string | null
  school: string
  organization: string
  academic_year?: string | null
  term?: string | null
  program?: string | null
  program_offering?: string | null
  is_read_only: boolean
  read_only_reason: string | null
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
  guardian_image_open_url?: string | null
  user?: string | null
  is_primary_guardian?: boolean | number | null
  is_financial_guardian?: boolean | number | null
  employment_sector?: string | null
  work_place?: string | null
  guardian_designation?: string | null
}

export type ApplicantContactPrefill = {
  available: boolean
  contact?: string | null
  first_name?: string | null
  last_name?: string | null
  email?: string | null
  mobile_phone?: string | null
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
  items?: Array<{
    name?: string
    item_key: string
    item_label: string
    review_status: 'Pending' | 'Approved' | 'Rejected' | 'Superseded'
    reviewed_by?: string | null
    reviewed_on?: string | null
    uploaded_at?: string | null
    attachment?: GovernedAttachmentRow | null
  }>
}

export type ApplicantPolicy = {
  name: string
  policy_version: string
  content_html: string
  is_required?: boolean
  acknowledgement_mode?: string | null
  is_acknowledged: boolean
  acknowledged_at?: string | null
  acknowledged_by?: string | null
  can_acknowledge?: boolean
  blocked_reason?: string | null
  expected_signature_name: string
  acknowledgement_clauses?: Array<{
    name: string
    clause_text: string
    is_required: boolean
    idx: number
  }>
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
