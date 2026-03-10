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
    academic_year?: string | null
    term?: string | null
    program?: string | null
    program_offering?: string | null
    is_read_only: boolean
    read_only_reason: string | null
  }
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
}
