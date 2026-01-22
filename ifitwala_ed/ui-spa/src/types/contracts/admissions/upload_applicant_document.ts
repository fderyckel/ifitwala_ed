// ifitwala_ed/ui-spa/src/types/contracts/admissions/upload_applicant_document.ts

export type Request = {
  student_applicant?: string
  document_type: string
  file_name: string
  content: string
}

export type Response = {
  file: string
  file_url: string
  classification: string
  applicant_document: string
}
