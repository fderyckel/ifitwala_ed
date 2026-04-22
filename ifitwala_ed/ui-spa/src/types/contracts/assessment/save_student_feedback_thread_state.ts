import type {
	FeedbackThread,
	FeedbackThreadLearnerState,
	FeedbackThreadTargetType,
} from '@/types/contracts/gradebook/feedback_workspace'

export type Request = {
	outcome_id: string
	submission_id?: string | null
	thread_id?: string | null
	target_type?: FeedbackThreadTargetType
	target_feedback_item?: string | null
	target_priority?: string | null
	summary_field?: 'overall' | 'strengths' | 'improvements' | 'next_steps' | null
	learner_state: Exclude<FeedbackThreadLearnerState, 'none'> | 'none'
}

export type Response = {
	thread: FeedbackThread
}
