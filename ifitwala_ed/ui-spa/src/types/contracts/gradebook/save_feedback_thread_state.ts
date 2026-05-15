import type { FeedbackThread, FeedbackThreadLearnerState, FeedbackThreadStatus } from './feedback_workspace'

export type Request = {
	outcome_id: string
	thread_id: string
	thread_status: FeedbackThreadStatus
	learner_state?: FeedbackThreadLearnerState | null
}

export type Response = {
	thread: FeedbackThread
}
