import type { FeedbackThread, FeedbackThreadTargetType } from '@/types/contracts/gradebook/feedback_workspace'

export type Request = {
	outcome_id: string
	submission_id?: string | null
	target_type: FeedbackThreadTargetType
	target_feedback_item?: string | null
	target_priority?: string | null
	summary_field?: 'overall' | 'strengths' | 'improvements' | 'next_steps' | null
	message_kind: 'reply' | 'clarification'
	body: string
}

export type Response = {
	thread: FeedbackThread
}
