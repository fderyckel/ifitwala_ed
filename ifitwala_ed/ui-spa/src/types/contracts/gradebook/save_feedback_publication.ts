import type { FeedbackVisibility, FeedbackWorkspacePayload } from './feedback_workspace'

export type Request = {
	outcome_id: string
	submission_id: string
	feedback_visibility: FeedbackVisibility
	grade_visibility: FeedbackVisibility
}

export type Response = {
	feedback_workspace: FeedbackWorkspacePayload
}
