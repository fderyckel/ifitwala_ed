// ui-spa/src/types/contracts/focus/review_student_log_outcome.ts

export type Request = {
  focus_item_id: string
  decision: 'complete' | 'reassign'
  follow_up_person?: string | null
  client_request_id?: string | null
}

export type Response = {
  ok: true
  idempotent: boolean
  status: 'processed' | 'already_processed'
  log_name: string
  result: string
}
