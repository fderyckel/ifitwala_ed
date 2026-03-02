// ifitwala_ed/ui-spa/src/types/contracts/admissions/get_applicant_profile.ts

import type {
  ApplicantApplicationContext,
  ApplicantProfile,
  ApplicantProfileCompleteness,
} from './types'

export type Request = {
  student_applicant?: string
}

export type Response = {
  profile: ApplicantProfile
  completeness: ApplicantProfileCompleteness
  application_context: ApplicantApplicationContext
  applicant_image?: string
  options: {
    genders: string[]
    residency_statuses: string[]
    languages: Array<{ value: string; label: string }>
    countries: Array<{ value: string; label: string }>
  }
}
