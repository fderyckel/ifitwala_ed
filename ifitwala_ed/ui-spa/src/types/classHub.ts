export type ClassHubOverlay = 'QuickCFU' | 'QuickEvidence' | 'StudentContext' | 'TaskReview'

export type ClassHubBundle = {
  header: {
    student_group: string
    title: string
    academic_year?: string | null
    course?: string | null
  }
  now: {
    date_label: string
    rotation_day_label?: string | null
    block_label?: string | null
    time_range?: string | null
    location?: string | null
  }
  session: {
    lesson_instance?: string | null
    status: 'none' | 'active' | 'ended'
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
    route?: { name: string; params?: Record<string, any> }
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
  lesson_instance?: string | null
  students: string[]
  evidence_type: 'text' | 'link'
  text?: string | null
  link_url?: string | null
}
