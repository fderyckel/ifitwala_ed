// ifitwala_ed/ui-spa/src/types/contracts/admissions/get_admissions_session.ts

import type { AdmissionsEnrollmentOffer, AdmissionsSessionApplicant } from './types'

export type Request = {
  student_applicant?: string
}

export type Response = {
  user: {
    name: string
    full_name: string
    roles: string[]
  }
  access_mode: 'Single Applicant Workspace' | 'Family Workspace'
  family_workspace_enabled: boolean
  selected_applicant: string
  available_applicants: AdmissionsSessionApplicant[]
  applicant: AdmissionsSessionApplicant
  enrollment_offer?: AdmissionsEnrollmentOffer | null
}
