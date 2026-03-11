// ifitwala_ed/ui-spa/src/types/contracts/admissions/update_applicant_enrollment_choices.ts

import type { Response as ApplicantEnrollmentChoicesResponse } from './get_applicant_enrollment_choices'

export type Request = {
  student_applicant?: string
  courses: Array<{
    course: string
    applied_basket_group?: string | null
    choice_rank?: number | null
  }>
}

export type Response = ApplicantEnrollmentChoicesResponse & {
  ok: boolean
}
