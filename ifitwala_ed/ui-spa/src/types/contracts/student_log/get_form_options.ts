// ui-spa/src/types/contracts/student_log/get_form_options.ts
type LogTypeOption = {
  value: string
  label: string
}

type NextStepOption = {
  value: string
  label: string
  role?: string | null
  school?: string | null
}

export type Request = {
  student: string
}

export type Response = {
  log_types: LogTypeOption[]
  next_steps: NextStepOption[]
  student_school: string | null
  allowed_next_step_schools: string[] | null
}
