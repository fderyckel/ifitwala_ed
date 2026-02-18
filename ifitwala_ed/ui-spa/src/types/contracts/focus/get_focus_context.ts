// ui-spa/src/types/contracts/focus/get_focus_context.ts

export type Request = {
  focus_item_id?: string | null
  reference_doctype?: 'Student Log' | 'Inquiry' | null
  reference_name?: string | null
  action_type?: string | null
}

export type Response = {
  focus_item_id?: string | null
  action_type?: string | null
  reference_doctype: 'Student Log' | 'Inquiry'
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
}
