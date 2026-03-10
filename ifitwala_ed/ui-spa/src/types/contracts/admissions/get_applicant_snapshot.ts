// ifitwala_ed/ui-spa/src/types/contracts/admissions/get_applicant_snapshot.ts

import type {
  ApplicantApplicationContext,
  ApplicantProfile,
  CompletionState,
  NextAction,
  PortalApplicantStatus,
} from './types'

export type Request = {
  student_applicant?: string
}

export type Response = {
  applicant: {
    name: string
    portal_status: PortalApplicantStatus
    submitted_at?: string | null
    decision_at?: string | null
  }
  application_context: ApplicantApplicationContext
  profile: ApplicantProfile
  completeness: {
    profile: CompletionState
    health: CompletionState
    documents: CompletionState
    policies: CompletionState
    interviews: CompletionState
    recommendations: CompletionState
  }
  next_actions: NextAction[]
  enrollment_offer?: {
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
  } | null
  recommendations_summary: {
    ok: boolean
    required_total: number
    received_total: number
    requested_total: number
    missing: string[]
    state: CompletionState
    rows: Array<{
      recommendation_template: string
      template_name: string
      minimum_required: number
      submitted_count: number
      requested_count: number
    }>
    counts: Record<string, number>
  }
}
