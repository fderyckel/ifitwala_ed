import type { AttachmentPreviewItem, AttachmentPreviewStatus } from '@/types/contracts/attachments/shared'
import type { FeedbackArtifact } from '@/types/contracts/assessment/feedback_artifact'
import type { CommentBankPayload } from './comment_bank'
import type { FeedbackThread, FeedbackWorkspacePayload } from './feedback_workspace'

export type Request = {
	outcome_id: string
	submission_id?: string | null
	version?: number | null
}

export type DeliveryPayload = {
	name: string
	task?: string | null
	title: string
	task_type?: string | null
	student_group: string
	due_date?: string | null
	delivery_mode?: 'Assign Only' | 'Collect Work' | 'Assess' | null
	grading_mode?: 'None' | 'Completion' | 'Binary' | 'Points' | 'Criteria' | null
	allow_feedback: 0 | 1
	rubric_scoring_strategy?: 'Sum Total' | 'Separate Criteria' | null
	max_points?: number | null
	criteria: Array<{
		assessment_criteria: string
		criteria_name: string
		criteria_weighting: number | null
		levels: Array<{
			level: string
			points: number
		}>
	}>
}

export type StudentPayload = {
	student: string | null
	student_name: string | null
	student_id?: string | null
	student_image?: string | null
}

export type SubmissionVersionSummary = {
	submission_id: string
	version: number
	submitted_on?: string | null
	origin?: string | null
	is_stub: boolean
	is_selected: boolean
}

export type SubmissionAttachment = {
	row_name?: string | null
	kind: 'file' | 'link' | 'other'
	file?: string | null
	file_name?: string | null
	file_size?: number | null
	description?: string | null
	public?: boolean
	preview_status?: AttachmentPreviewStatus
	preview_url?: string | null
	open_url?: string | null
	external_url?: string | null
	mime_type?: string | null
	extension?: string | null
	attachment_preview?: AttachmentPreviewItem | null
}

export type SubmissionEvidence = {
	submission_id: string
	version: number
	submitted_on?: string | null
	submitted_by?: string | null
	origin?: string | null
	is_stub: boolean
	evidence_note?: string | null
	is_cloned?: boolean
	cloned_from?: string | null
	text_content?: string | null
	link_url?: string | null
	attachments: SubmissionAttachment[]
	annotation_readiness?: {
		mode: 'reduced' | 'unavailable' | 'not_applicable'
		reason_code: string
		title: string
		message: string
		attachment_row_name?: string | null
		attachment_file_name?: string | null
		preview_status?: AttachmentPreviewStatus
		preview_url?: string | null
		open_url?: string | null
	} | null
}

export type OutcomePayload = {
	outcome_id: string
	grading_status?: string | null
	procedural_status?: string | null
	has_submission: boolean
	has_new_submission: boolean
	is_complete: boolean
	is_published: boolean
	published_on?: string | null
	published_by?: string | null
	official: {
		score?: number | null
		grade?: string | null
		grade_value?: number | null
		feedback?: string | null
	}
	criteria: Array<{
		criteria: string
		level?: string | null
		points?: number | null
		feedback?: string | null
	}>
}

export type ContributionPayload = {
	name: string
	contributor: string
	contribution_type: string
	status: string
	is_stale: number | boolean
	task_submission?: string | null
	judgment_code?: string | null
	score?: number | null
	grade?: string | null
	grade_value?: number | null
	feedback?: string | null
	moderation_action?: string | null
	submitted_on?: string | null
	modified?: string | null
}

export type MyContributionPayload = {
	name: string
	status: string
	contribution_type: string
	task_submission?: string | null
	is_stale: boolean
	judgment_code?: string | null
	score?: number | null
	grade?: string | null
	grade_value?: number | null
	feedback?: string | null
	submitted_on?: string | null
	modified?: string | null
	criteria: Array<{
		criteria: string
		level?: string | null
		points?: number | null
		feedback?: string | null
	}>
}

export type Response = {
	delivery: DeliveryPayload
	student: StudentPayload
	outcome: OutcomePayload
	latest_submission?: SubmissionVersionSummary | null
	selected_submission?: SubmissionEvidence | null
	feedback_workspace?: FeedbackWorkspacePayload | null
	feedback_artifact?: FeedbackArtifact | null
	feedback_threads: FeedbackThread[]
	comment_bank?: CommentBankPayload | null
	submission_versions: SubmissionVersionSummary[]
	my_contribution?: MyContributionPayload | null
	moderation_history: Array<{
		by: string
		action?: string | null
		on?: string | null
	}>
	allowed_actions: {
		can_edit_marking: boolean
		can_edit_feedback: boolean
		can_mark_submission_seen: boolean
		can_publish: boolean
		can_unpublish: boolean
		can_manage_feedback_publication: boolean
		can_moderate: boolean
		show_review_tab: boolean
	}
	contributions: ContributionPayload[]
}
