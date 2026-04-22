import type { FeedbackPriority, FeedbackWorkspaceItem, FeedbackWorkspacePayload } from './feedback_workspace'

export type Request = {
	outcome_id: string
	submission_id: string
	summary: {
		overall?: string | null
		strengths?: string | null
		improvements?: string | null
		next_steps?: string | null
	}
	priorities?: FeedbackPriority[]
	items: FeedbackWorkspaceItem[]
}

export type Response = {
	feedback_workspace: FeedbackWorkspacePayload
}
