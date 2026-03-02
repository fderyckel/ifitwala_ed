// ifitwala_ed/ui-spa/src/types/contracts/admissions/mark_applicant_messages_read.ts

export type Request = {
  context_doctype?: 'Student Applicant'
  context_name?: string
}

export type Response = {
  ok: boolean
  thread_name?: string | null
  read_at?: string | null
}
