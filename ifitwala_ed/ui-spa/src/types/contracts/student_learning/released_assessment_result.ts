import type { FeedbackWorkspaceItem, FeedbackVisibility } from '@/types/contracts/gradebook/feedback_workspace'

export type ReleasedAssessmentResult = {
	outcome_id: string
	task_submission?: string | null
	grade_visible: boolean
	feedback_visible: boolean
	publication: {
		feedback_visibility: FeedbackVisibility
		grade_visibility: FeedbackVisibility
		derived_from_legacy_outcome: boolean
		legacy_outcome_published: boolean
		legacy_published_on?: string | null
		legacy_published_by?: string | null
	}
	official: {
		score?: number | null
		grade?: string | null
		grade_value?: number | null
		feedback?: string | null
	}
	feedback?: {
		task_submission?: string | null
		submission_version?: number | null
		summary: {
			overall: string
			strengths: string
			improvements: string
			next_steps: string
		}
		items: FeedbackWorkspaceItem[]
		modified?: string | null
		modified_by?: string | null
	} | null
}
