// ifitwala_ed/ui-spa/src/types/contracts/admissions/accept_enrollment_offer.ts

export type Request = {
  student_applicant?: string
}

export type Response = {
  ok: boolean
  result: {
    ok: boolean
    status: string
  }
  enrollment_offer?: {
    name: string
    status: string
  } | null
}
