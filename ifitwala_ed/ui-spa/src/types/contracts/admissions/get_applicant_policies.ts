// ifitwala_ed/ui-spa/src/types/contracts/admissions/get_applicant_policies.ts

import type { ApplicantPolicy } from './types'

export type Request = {
  student_applicant?: string
}

export type Response = {
  policies: ApplicantPolicy[]
}
