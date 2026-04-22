import type { FeedbackThread } from './feedback_workspace'

export type Request = {
	outcome_id: string
	thread_id: string
	body: string
	thread_status?: 'open' | 'resolved' | null
}

export type Response = {
	thread: FeedbackThread
}
