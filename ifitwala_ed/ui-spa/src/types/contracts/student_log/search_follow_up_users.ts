// ui-spa/src/types/contracts/student_log/search_follow_up_users.ts

export type Request = {
  next_step: string
  student: string
  query?: string | null
  limit?: number
}

export type Response = Array<{
  value: string
  label: string
  meta?: string | null
}>
