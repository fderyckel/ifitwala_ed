import type { CommentBankPayload, CommentBankScopeMode } from './comment_bank'
import type { FeedbackIntent } from './feedback_workspace'

export type Request = {
	outcome_id: string
	entry_id?: string | null
	label?: string | null
	body: string
	feedback_intent: FeedbackIntent
	scope_mode?: CommentBankScopeMode | null
	assessment_criteria?: string | null
	is_active?: boolean | number | null
}

export type Response = {
	comment_bank: CommentBankPayload
}
