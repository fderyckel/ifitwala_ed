// ifitwala_ed/ui-spa/src/types/contracts/admissions/send_applicant_message.ts

import type { ApplicantMessage } from './types'

export type Request = {
  context_doctype?: 'Student Applicant'
  context_name?: string
  body: string
  applicant_visible?: number
  client_request_id?: string
}

export type Response = {
  thread_name: string
  message: ApplicantMessage
}
