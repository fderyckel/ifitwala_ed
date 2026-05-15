// ui-spa/src/types/contracts/focus/submit_student_log_follow_up.ts

export type Request = {
  focus_item_id: string
  follow_up: string
  client_request_id?: string | null
}

export type Response = {
  ok: true
  idempotent: boolean
  status: 'created' | 'already_processed'
  log_name: string
  follow_up_name: string
}
