// ui-spa/src/types/contracts/student_log/search_students.ts
export type Request = {
  query: string
  limit?: number
}

export type Response = Array<{
  student: string
  label: string
  meta?: string | null
  image?: string | null
}>
