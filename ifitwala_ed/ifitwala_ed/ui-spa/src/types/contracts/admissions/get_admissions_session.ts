// ifitwala_ed/ui-spa/src/types/contracts/admissions/get_admissions_session.ts

import type { PortalApplicantStatus } from './types'

export type Request = {}

export type Response = {
  user: {
    name: string
    full_name: string
    roles: ['Admissions Applicant']
  }
  applicant: {
    name: string
    portal_status: PortalApplicantStatus
    school: string
    organization: string
    is_read_only: boolean
    read_only_reason: string | null
  }
}
