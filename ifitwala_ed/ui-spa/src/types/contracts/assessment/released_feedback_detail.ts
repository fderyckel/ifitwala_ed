import type { GovernedAttachmentRow } from '@/types/contracts/attachments/shared'
import type { FeedbackArtifact } from './feedback_artifact'
import type {
	FeedbackPriority,
	FeedbackThread,
	FeedbackVisibility,
	FeedbackWorkspaceItem,
} from '@/types/contracts/gradebook/feedback_workspace'
import type { SubmissionEvidence } from '@/types/contracts/gradebook/get_drawer'

export type ReleasedFeedbackRubricSnapshot = {
	assessment_criteria?: string | null
	criteria_name?: string | null
	level?: string | null
	points?: number | null
	feedback?: string | null
	linked_feedback_item_ids: string[]
}

export type ReleasedFeedbackDetail = {
	outcome_id: string
	audience: 'student' | 'guardian'
	context: {
		task_delivery?: string | null
		task?: string | null
		title: string
		task_type?: string | null
		course?: string | null
		course_name?: string | null
		student?: string | null
	}
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
		priorities: FeedbackPriority[]
		items: FeedbackWorkspaceItem[]
		rubric_snapshot: ReleasedFeedbackRubricSnapshot[]
		threads: FeedbackThread[]
		modified?: string | null
		modified_by?: string | null
	} | null
	document?: {
		submission: SubmissionEvidence
		primary_attachment?: {
			row_name?: string | null
			attachment?: GovernedAttachmentRow | null
		} | null
	} | null
	released_feedback_artifact?: FeedbackArtifact | null
	allowed_actions: {
		can_reply: boolean
		can_set_learner_state: boolean
		can_view_threads: boolean
	}
}
