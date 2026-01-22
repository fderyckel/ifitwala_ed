// ifitwala_ed/ui-spa/src/types/contracts/admissions/get_applicant_health.ts

export type Request = {
  student_applicant?: string
}

export type Response = {
  health_summary: string
  medical_conditions: string
  allergies: string
  medications: string
}
