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
  }
  next_actions: NextAction[]
}
