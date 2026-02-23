// ifitwala_ed/ui-spa/src/types/contracts/admissions/update_applicant_profile.ts

import type {
  ApplicantApplicationContext,
  ApplicantProfile,
  ApplicantProfileCompleteness,
} from './types'

export type Request = ApplicantProfile & {
  student_applicant?: string
}

export type Response = {
  ok: boolean
  profile: ApplicantProfile
  completeness: ApplicantProfileCompleteness
  application_context: ApplicantApplicationContext
  options: {
    genders: string[]
    residency_statuses: string[]
    languages: Array<{ value: string; label: string }>
    countries: Array<{ value: string; label: string }>
  }
}
