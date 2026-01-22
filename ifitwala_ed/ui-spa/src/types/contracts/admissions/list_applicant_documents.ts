// ifitwala_ed/ui-spa/src/types/contracts/admissions/list_applicant_documents.ts

import type { ApplicantDocument } from './types'

export type Request = {
  student_applicant?: string
}

export type Response = {
  documents: ApplicantDocument[]
}
