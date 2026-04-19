export type ClassHubOverlay = 'QuickCFU' | 'QuickEvidence' | 'StudentContext' | 'TaskReview'

export type ClassHubWheelStudent = {
  student: string
  student_name: string
}

export type ClassHubWheelNow = {
  date_iso?: string | null
  date_label: string
  block_number?: number | null
  block_label?: string | null
  time_range?: string | null
  location?: string | null
}

export type ClassHubWheelContext = {
  student_group: string
  title: string
  academic_year?: string | null
  course?: string | null
  permissions: {
    can_create_student_log: boolean
  }
  now: ClassHubWheelNow
  students: ClassHubWheelStudent[]
}

export type ClassHubWheelResolution = {
  status: 'ready' | 'multiple_current' | 'no_current_class' | 'unavailable'
  message?: string | null
  contexts: ClassHubWheelContext[]
  next_class?: {
    student_group: string
    title: string
    academic_year?: string | null
    course?: string | null
    now: ClassHubWheelNow
  } | null
}

export type ClassHubHomeEntryGroup = {
  student_group: string
  student_group_name: string
  title: string
  academic_year?: string | null
  course?: string | null
}

export type ClassHubHomeEntryResolution = {
  status: 'single' | 'choose' | 'empty'
  message?: string | null
  groups: ClassHubHomeEntryGroup[]
}

export type ClassHubBundle = {
  message?: string | null
  header: {
    student_group: string
    title: string
    academic_year?: string | null
    course?: string | null
  }
  permissions: {
    can_create_student_log: boolean
  }
  now: {
    date_iso?: string | null
    date_label: string
    rotation_day_label?: string | null
    block_number?: number | null
    block_label?: string | null
    time_range?: string | null
    location?: string | null
  }
  session: {
    class_session?: string | null
    class_teaching_plan?: string | null
    title?: string | null
    session_status?: string | null
    session_date?: string | null
    unit_plan?: string | null
    status: 'none' | 'planned' | 'active' | 'ended'
    live_success_criteria?: string | null
  }
  today_items: Array<{
    id: string
    label: string
    overlay: ClassHubOverlay
    payload: Record<string, any>
  }>
  focus_students: Array<{
    student: string
    student_name: string
  }>
  students: Array<{
    student: string
    student_name: string
    evidence_count_today: number
    signal?: 'Not Yet' | 'Almost' | 'Got It' | 'Exceeded' | null
    has_note_today?: boolean
  }>
  notes_preview: Array<{
    id: string
    student_name: string
    preview: string
    created_at_label: string
  }>
  task_items: Array<{
    id: string
    title: string
    status_label: string
    pending_count?: number
    overlay: 'TaskReview'
    payload: Record<string, any>
  }>
  pulse_items: Array<{
    id: string
    label: string
    route?: { name: string; params?: Record<string, any>; query?: Record<string, any> | null }
  }>
  follow_up_items: Array<{
    id: string
    label: string
    overlay: 'StudentContext'
    payload: Record<string, any>
  }>
}

export type ClassHubSignal = {
  student: string
  signal: 'Not Yet' | 'Almost' | 'Got It' | 'Exceeded'
  note?: string | null
}

export type ClassHubQuickEvidencePayload = {
  student_group: string
  class_session?: string | null
  students: string[]
  evidence_type: 'text' | 'link'
  text?: string | null
  link_url?: string | null
}
