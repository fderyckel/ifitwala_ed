// ui-spa/src/types/contracts/gradebook/get_task_quiz_manual_review.ts

export type Request = {
	task: string
	view_mode?: 'question' | 'student' | null
	quiz_question?: string | null
	student?: string | null
}

export type TaskPayload = {
	name: string
	title: string
	student_group: string
	max_points?: number | null
	pass_percentage?: number | null
}

export type SummaryPayload = {
	manual_item_count: number
	pending_item_count: number
	pending_student_count: number
	pending_attempt_count: number
}

export type QuestionOption = {
	quiz_question: string
	title: string
	manual_item_count: number
	pending_item_count: number
}

export type StudentOption = {
	student: string
	student_name: string
	student_id?: string | null
	student_image?: string | null
	manual_item_count: number
	pending_item_count: number
}

export type SelectedQuestion = {
	quiz_question: string
	title: string
}

export type SelectedStudent = {
	student: string
	student_name: string
	student_id?: string | null
}

export type ReviewRow = {
	item_id: string
	quiz_attempt: string
	task_outcome?: string | null
	attempt_number?: number | null
	attempt_status?: string | null
	submitted_on?: string | null
	student: string
	student_name: string
	student_id?: string | null
	student_image?: string | null
	grading_status?: string | null
	quiz_question: string
	title: string
	position?: number | null
	question_type: string
	prompt_html?: string | null
	response_text?: string | null
	selected_option_ids: string[]
	selected_option_labels: string[]
	awarded_score: number | null
	requires_manual_grading: 0 | 1
}

export type Response = {
	task: TaskPayload
	summary: SummaryPayload
	view_mode: 'question' | 'student'
	questions: QuestionOption[]
	students: StudentOption[]
	selected_question?: SelectedQuestion | null
	selected_student?: SelectedStudent | null
	rows: ReviewRow[]
}
