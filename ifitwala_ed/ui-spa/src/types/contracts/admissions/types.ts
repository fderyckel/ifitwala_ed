// ifitwala_ed/ui-spa/src/types/contracts/admissions/types.ts

export type PortalApplicantStatus =
  | 'Draft'
  | 'In Progress'
  | 'Action Required'
  | 'In Review'
  | 'Accepted'
  | 'Rejected'
  | 'Withdrawn'
  | 'Completed'

export type CompletionState = 'pending' | 'in_progress' | 'complete' | 'optional'

export type NextAction = {
  label: string
  route_name: string
  intent: 'primary' | 'secondary' | 'neutral'
  is_blocking: boolean
  icon?: string
}

export type ApplicantDocument = {
  name: string
  document_type: string
  review_status: 'Pending' | 'Approved' | 'Rejected'
  uploaded_at?: string | null
  file_url?: string | null
}

export type ApplicantPolicy = {
  name: string
  policy_version: string
  content_html: string
  is_acknowledged: boolean
  acknowledged_at?: string | null
}
