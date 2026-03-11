// ifitwala_ed/ui-spa/src/types/contracts/admissions/decline_enrollment_offer.ts

import type { AdmissionsEnrollmentOffer } from './types'

export type Request = {
  student_applicant?: string
}

export type Response = {
  ok: boolean
  result: {
    ok: boolean
    status: string
  }
  enrollment_offer?: AdmissionsEnrollmentOffer | null
}
