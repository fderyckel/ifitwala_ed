// ifitwala_ed/ui-spa/src/types/contracts/admissions/update_applicant_profile.ts

import type {
  ApplicantApplicationContext,
  ApplicantGuardianProfile,
  ApplicantProfile,
  ApplicantProfileCompleteness,
} from './types'

export type Request = ApplicantProfile & {
  student_applicant?: string
  expected_modified?: string | null
  guardians?: ApplicantGuardianProfile[]
}

export type Response = {
  ok: boolean
  profile: ApplicantProfile
  completeness: ApplicantProfileCompleteness
  application_context: ApplicantApplicationContext
  applicant_image?: string
  record_modified?: string
  guardian_section_enabled?: boolean
  guardians?: ApplicantGuardianProfile[]
  options: {
    genders: string[]
    residency_statuses: string[]
    languages: Array<{ value: string; label: string }>
    countries: Array<{ value: string; label: string }>
    guardian_relationships?: string[]
    guardian_genders?: string[]
    guardian_employment_sectors?: string[]
    salutations?: Array<{ value: string; label: string }>
  }
}
