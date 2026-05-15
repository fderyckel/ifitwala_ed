import type { ReleasedAssessmentResult } from '@/types/contracts/student_learning/released_assessment_result'

export type Request = {
	task_delivery: string
}

export type Response = {
	mode: 'attempt' | 'review'
	session: StudentQuizSession
	items?: StudentQuizItem[]
	review?: StudentQuizReview
	released_result?: ReleasedAssessmentResult | null
}

export type StudentQuizSession = {
	task_delivery: string
	task: string
	title: string
	course?: string | null
	is_practice: number
	attempt_id: string
	attempt_number: number
	status: string
	started_on?: string | null
	expires_on?: string | null
	submitted_on?: string | null
	score?: number | null
	percentage?: number | null
	passed: number
	requires_manual_review: number
	max_attempts?: number | null
	pass_percentage?: number | null
	outcome_id: string
}

export type StudentQuizItem = {
	item_id: string
	position: number
	question_type: string
	prompt_html?: string | null
	options: StudentQuizOption[]
	response_text?: string | null
	selected_option_ids: string[]
}

export type StudentQuizOption = {
	id: string
	text: string
}

export type StudentQuizReview = {
	attempt: {
		attempt_id: string
		attempt_number: number
		status: string
		submitted_on?: string | null
		score?: number | null
		percentage?: number | null
		passed: number
		requires_manual_review: number
	}
	items: StudentQuizReviewItem[]
}

export type StudentQuizReviewItem = {
	item_id: string
	position: number
	question_type: string
	prompt_html?: string | null
	options: StudentQuizOption[]
	response_text?: string | null
	selected_option_ids: string[]
	awarded_score?: number | null
	is_correct: number
	requires_manual_grading: number
	explanation_html?: string | null
	correct_option_ids: string[]
	accepted_answers: string[]
}
