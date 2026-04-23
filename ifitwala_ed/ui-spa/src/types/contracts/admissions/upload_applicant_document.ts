// ifitwala_ed/ui-spa/src/types/contracts/admissions/upload_applicant_document.ts

export type Request = {
  student_applicant?: string
  document_type: string
  applicant_document_item?: string | null
  item_key?: string | null
  item_label?: string | null
  client_request_id?: string | null
  file_name: string
  content: string
}

export type Response = {
  file: string
  open_url?: string | null
  preview_url?: string | null
  thumbnail_url?: string | null
  preview_status?: string | null
  drive_file_id?: string | null
  canonical_ref?: string | null
  applicant_document: string
  applicant_document_item: string
  item_key: string
  item_label: string
}
