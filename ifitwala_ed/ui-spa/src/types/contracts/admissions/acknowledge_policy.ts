// ifitwala_ed/ui-spa/src/types/contracts/admissions/acknowledge_policy.ts

export type Request = {
  policy_version: string
  student_applicant?: string
}

export type Response = {
  ok: boolean
  acknowledged_at?: string | null
}
