// ifitwala_ed/ui-spa/src/types/contracts/admissions/update_applicant_health.ts

export type Request = {
  student_applicant?: string
  health_summary: string
  medical_conditions: string
  allergies: string
  medications: string
}

export type Response = {
  ok: boolean
}
