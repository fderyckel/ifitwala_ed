// ifitwala_ed/ui-spa/src/types/contracts/admissions/get_applicant_messages.ts

import type { ApplicantMessage } from './types'

export type Request = {
  context_doctype?: 'Student Applicant'
  context_name?: string
  limit_start?: number
  limit_page_length?: number
}

export type Response = {
  thread_name?: string | null
  messages: ApplicantMessage[]
  unread_count: number
}
