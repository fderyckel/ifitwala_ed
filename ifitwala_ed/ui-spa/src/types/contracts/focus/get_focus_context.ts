// ui-spa/src/types/contracts/focus/get_focus_context.ts

export type Request = {
  focus_item_id?: string | null
  reference_doctype?: 'Student Log' | 'Inquiry' | 'Applicant Review Assignment' | 'Policy Version' | null
  reference_name?: string | null
  action_type?: string | null
}

export type Response = {
  focus_item_id?: string | null
  action_type?: string | null
  reference_doctype: 'Student Log' | 'Inquiry' | 'Applicant Review Assignment' | 'Policy Version'
  reference_name: string
  mode: 'assignee' | 'author'
  log: {
    name: string
    student?: string | null
    student_name?: string | null
    school?: string | null
    log_type?: string | null
    next_step?: string | null
    follow_up_person?: string | null
    follow_up_role?: string | null
    date?: string | null
    follow_up_status?: string | null
    log_html?: string | null
    log_author?: string | null
    log_author_name?: string | null
  } | null
  inquiry: {
    name: string
    subject_name?: string | null
    first_name?: string | null
    last_name?: string | null
    email?: string | null
    phone_number?: string | null
    school?: string | null
    organization?: string | null
    type_of_inquiry?: string | null
    workflow_state?: string | null
    assigned_to?: string | null
    followup_due_on?: string | null
    sla_status?: string | null
  } | null
  follow_ups: Array<{
    name: string
    date?: string | null
    follow_up_author?: string | null
    follow_up_html?: string | null
    docstatus: 0 | 1 | 2
  }>
  review_assignment?: {
    name: string
    target_type: 'Applicant Document' | 'Applicant Health Profile' | 'Student Applicant'
    target_name: string
    student_applicant: string
    applicant_name?: string | null
    organization?: string | null
    school?: string | null
    program_offering?: string | null
    assigned_to_user?: string | null
    assigned_to_role?: string | null
    source_event?: string | null
    decision_options: string[]
    preview?: {
      document_type?: string | null
      document_label?: string | null
      review_status?: string | null
      review_notes?: string | null
      file_url?: string | null
      file_name?: string | null
      uploaded_at?: string | null
      declared_complete?: boolean
      declared_by?: string | null
      declared_on?: string | null
      application_status?: string | null
    } | null
    previous_reviews?: Array<{
      assignment: string
      reviewer?: string | null
      decision?: string | null
      notes?: string | null
      decided_by?: string | null
      decided_on?: string | null
    }>
  } | null
  policy_signature?: {
    policy_version: string
    institutional_policy?: string | null
    policy_key?: string | null
    policy_title?: string | null
    policy_label?: string | null
    version_label?: string | null
    effective_from?: string | null
    effective_to?: string | null
    policy_text_html?: string | null
    policy_organization?: string | null
    policy_school?: string | null
    employee?: string | null
    employee_name?: string | null
    employee_group?: string | null
    todo_due_date?: string | null
    is_acknowledged?: boolean
    acknowledged_at?: string | null
  } | null
}
