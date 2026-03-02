// ifitwala_ed/ui-spa/src/types/contracts/admissions/list_applicant_document_types.ts

export type Request = {
  student_applicant?: string
}

export type Response = {
  document_types: Array<{
    name: string
    code: string
    document_type_name: string
    belongs_to: 'student' | 'guardian' | 'family' | ''
    is_required: boolean
    is_repeatable: boolean
    min_items_required: number
    description: string
  }>
}
