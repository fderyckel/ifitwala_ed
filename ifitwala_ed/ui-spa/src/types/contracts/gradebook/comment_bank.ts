import type { FeedbackIntent } from './feedback_workspace'

export type CommentBankScopeMode = 'personal' | 'course' | 'task'

export type CommentBankEntry = {
	id: string
	label: string
	body: string
	intent: FeedbackIntent
	scope_mode: CommentBankScopeMode
	course?: string | null
	task?: string | null
	assessment_criteria?: string | null
	assessment_criteria_label?: string | null
	match_reasons: string[]
	match_score?: number
}

export type CommentBankPayload = {
	context: {
		course?: string | null
		task?: string | null
		task_title?: string | null
		criteria: Array<{
			assessment_criteria: string
			criteria_name: string
		}>
	}
	entries: CommentBankEntry[]
}
