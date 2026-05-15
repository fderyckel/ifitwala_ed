// ifitwala_ed/ui-spa/src/types/contracts/admissions/get_applicant_profile.ts

import type {
  ApplicantApplicationContext,
  ApplicantContactPrefill,
  ApplicantGuardianProfile,
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
  applicant_image_open_url?: string
  record_modified?: string
  guardian_section_enabled?: boolean
  applicant_contact_prefill?: ApplicantContactPrefill
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
