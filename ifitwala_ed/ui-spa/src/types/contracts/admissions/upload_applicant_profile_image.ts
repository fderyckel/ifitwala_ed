// ifitwala_ed/ui-spa/src/types/contracts/admissions/upload_applicant_profile_image.ts

export type Request = {
  student_applicant?: string
  file_name: string
  content: string
}

export type Response = {
  ok: boolean
  file: string
  file_url: string
  file_name: string
  file_size?: number | null
  classification?: string | null
}
