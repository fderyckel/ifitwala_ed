// ui-spa/src/types/contracts/student_log/submit_student_log.ts
export type Request = {
  student: string
  log_type: string
  log: string
  requires_follow_up: 0 | 1
  next_step?: string | null
  follow_up_person?: string | null
  visible_to_student: 0 | 1
  visible_to_guardians: 0 | 1
}

export type Response = {
  name: string
}
