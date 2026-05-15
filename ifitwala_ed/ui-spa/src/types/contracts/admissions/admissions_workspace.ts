// ifitwala_ed/ui-spa/src/types/contracts/admissions/admissions_workspace.ts

import type { AttachmentPreviewItem, AttachmentPreviewStatus } from '@/types/contracts/attachments/shared'

export type InterviewFeedbackStatus = 'Draft' | 'Submitted' | 'Pending'

export interface InterviewWorkspaceInterviewer {
	user: string
	name: string
}

export interface InterviewWorkspaceInterview {
	name: string
	student_applicant: string
	interview_type?: string | null
	mode?: string | null
	location?: string | null
	location_label?: string | null
	confidentiality_level?: string | null
	interview_date?: string | null
	interview_start?: string | null
	interview_end?: string | null
	interview_start_label?: string | null
	interview_end_label?: string | null
	school_event?: string | null
	operational_notes?: string | null
	feedback_submitted_count?: number
	feedback_expected_count?: number
	feedback_complete?: boolean
	feedback_status_label?: string | null
	interviewers: InterviewWorkspaceInterviewer[]
}

export interface InterviewWorkspaceGuardian {
	guardian?: string | null
	contact?: string | null
	use_applicant_contact?: boolean
	full_name?: string | null
	first_name?: string | null
	last_name?: string | null
	relationship?: string | null
	can_consent?: boolean
	salutation?: string | null
	gender?: string | null
	email?: string | null
	mobile_phone?: string | null
	work_email?: string | null
	work_phone?: string | null
	is_primary?: boolean
	is_primary_guardian?: boolean
	is_financial_guardian?: boolean
	user?: string | null
	image?: string | null
	employment_sector?: string | null
	work_place?: string | null
	designation?: string | null
}

export interface InterviewWorkspaceApplicant {
	name: string
	display_name?: string | null
	application_status?: string | null
	organization?: string | null
	school?: string | null
	program?: string | null
	program_offering?: string | null
	academic_year?: string | null
	applicant_email?: string | null
	student_date_of_birth?: string | null
	student_gender?: string | null
	submitted_at?: string | null
	created_on?: string | null
	updated_on?: string | null
	guardians: InterviewWorkspaceGuardian[]
}

export interface InterviewWorkspaceTimelineRow {
	name: string
	creation?: string | null
	comment_by?: string | null
	comment_email?: string | null
	comment_type?: string | null
	content?: string | null
}

export interface InterviewWorkspaceDocumentItem {
	name?: string | null
	item_key?: string | null
	item_label?: string | null
	review_status?: string | null
	reviewed_by?: string | null
	reviewed_on?: string | null
	file_name?: string | null
	open_url?: string | null
	preview_url?: string | null
	thumbnail_url?: string | null
	preview_status?: AttachmentPreviewStatus
	drive_file_id?: string | null
	canonical_ref?: string | null
	attachment_preview?: AttachmentPreviewItem | null
	uploaded_at?: string | null
}

export interface InterviewWorkspaceDocument {
	name: string
	document_type?: string | null
	document_label?: string | null
	review_status?: string | null
	reviewed_by?: string | null
	reviewed_on?: string | null
	items: InterviewWorkspaceDocumentItem[]
}

export type ApplicantDocumentReviewDecision = 'Approved' | 'Needs Follow-Up' | 'Rejected'
export type ApplicantDocumentRequirementOverride = 'Waived' | 'Exception Approved'

export interface ApplicantWorkspaceDocumentItem {
	name?: string | null
	item_key?: string | null
	item_label?: string | null
	review_status?: string | null
	reviewed_by?: string | null
	reviewed_on?: string | null
	uploaded_by?: string | null
	uploaded_at?: string | null
	file_name?: string | null
	open_url?: string | null
	preview_url?: string | null
	thumbnail_url?: string | null
	preview_status?: AttachmentPreviewStatus
	drive_file_id?: string | null
	canonical_ref?: string | null
	attachment_preview?: AttachmentPreviewItem | null
	modified?: string | null
}

export interface ApplicantWorkspaceRequirementRow {
	applicant_document?: string | null
	document_type?: string | null
	label?: string | null
	is_required?: boolean
	required_count?: number
	uploaded_count?: number
	approved_count?: number
	review_status?: string | null
	reviewed_by?: string | null
	reviewed_on?: string | null
	requirement_override?: string | null
	override_reason?: string | null
	override_by?: string | null
	override_on?: string | null
	uploaded_by?: string | null
	uploaded_at?: string | null
	file_name?: string | null
	open_url?: string | null
	preview_url?: string | null
	thumbnail_url?: string | null
	preview_status?: AttachmentPreviewStatus
	drive_file_id?: string | null
	canonical_ref?: string | null
	attachment_preview?: AttachmentPreviewItem | null
	modified?: string | null
	items: ApplicantWorkspaceDocumentItem[]
}

export interface ApplicantWorkspaceUploadedRow {
	applicant_document?: string | null
	applicant_document_item?: string | null
	document_type?: string | null
	label?: string | null
	document_label?: string | null
	item_key?: string | null
	item_label?: string | null
	is_required?: boolean
	required_count?: number
	uploaded_count?: number
	approved_count?: number
	is_repeatable?: boolean
	requirement_override?: string | null
	override_reason?: string | null
	review_status?: string | null
	reviewed_by?: string | null
	reviewed_on?: string | null
	uploaded_by?: string | null
	uploaded_at?: string | null
	file_name?: string | null
	open_url?: string | null
	preview_url?: string | null
	thumbnail_url?: string | null
	preview_status?: AttachmentPreviewStatus
	drive_file_id?: string | null
	canonical_ref?: string | null
	attachment_preview?: AttachmentPreviewItem | null
	modified?: string | null
}

export interface ApplicantWorkspaceDocumentReview {
	ok: boolean
	missing: string[]
	unapproved: string[]
	required: string[]
	required_rows: ApplicantWorkspaceRequirementRow[]
	uploaded_rows: ApplicantWorkspaceUploadedRow[]
	can_review_submissions?: boolean
	can_manage_overrides?: boolean
}

export interface InterviewWorkspaceRecommendationSummary {
	ok?: boolean
	required_total?: number
	received_total?: number
	requested_total?: number
	missing?: string[]
	state?: string | null
	rows?: Array<Record<string, unknown>>
	counts?: Record<string, number>
	pending_review_count?: number
	latest_submitted_on?: string | null
	first_pending_review?: {
		recommendation_request?: string | null
		recommendation_submission?: string | null
		applicant_document_item?: string | null
		recommender_name?: string | null
		template_name?: string | null
		submitted_on?: string | null
	} | null
}

export interface InterviewWorkspaceRecommendationRequest {
	name: string
	recommendation_template?: string | null
	request_status?: string | null
	recommender_name?: string | null
	recommender_email?: string | null
	recommender_relationship?: string | null
	sent_on?: string | null
	opened_on?: string | null
	consumed_on?: string | null
	expires_on?: string | null
	submission?: string | null
}

export interface InterviewWorkspaceRecommendationSubmission {
	name: string
	recommendation_request?: string | null
	recommendation_template?: string | null
	recommender_name?: string | null
	recommender_email?: string | null
	submitted_on?: string | null
	has_file?: boolean
	applicant_document_item?: string | null
	item_label?: string | null
	review_status?: string | null
	reviewed_by?: string | null
	reviewed_on?: string | null
	file_name?: string | null
	open_url?: string | null
	preview_url?: string | null
	thumbnail_url?: string | null
	preview_status?: AttachmentPreviewStatus
	drive_file_id?: string | null
	canonical_ref?: string | null
	attachment_preview?: AttachmentPreviewItem | null
}

export interface RecommendationReviewRow {
	recommendation_request?: string | null
	recommendation_submission?: string | null
	student_applicant?: string | null
	recommendation_template?: string | null
	template_name?: string | null
	target_document_type?: string | null
	applicant_document?: string | null
	applicant_document_item?: string | null
	item_key?: string | null
	item_label?: string | null
	request_status?: string | null
	review_status?: string | null
	reviewed_by?: string | null
	reviewed_on?: string | null
	recommender_name?: string | null
	recommender_email?: string | null
	recommender_relationship?: string | null
	sent_on?: string | null
	opened_on?: string | null
	submitted_on?: string | null
	expires_on?: string | null
	resend_count?: number
	has_file?: boolean
	attestation_confirmed?: boolean
	file_name?: string | null
	open_url?: string | null
	preview_url?: string | null
	thumbnail_url?: string | null
	preview_status?: AttachmentPreviewStatus
	drive_file_id?: string | null
	canonical_ref?: string | null
	attachment_preview?: AttachmentPreviewItem | null
	needs_review?: boolean
	can_review?: boolean
}

export interface RecommendationReviewAnswer {
	field_key: string
	label: string
	field_type?: string | null
	value?: unknown
	display_value?: string | null
	has_value?: boolean
	likert_columns?: Array<{ key?: string | null; label?: string | null }>
	likert_rows?: Array<{ key?: string | null; label?: string | null }>
}

export interface RecommendationReviewPayload {
	ok: boolean
	recommendation: {
		student_applicant: string
		recommendation_request: string
		recommendation_submission: string
		recommendation_template?: string | null
		template_name?: string | null
		target_document_type?: string | null
		applicant_document?: string | null
		applicant_document_item?: string | null
		item_key?: string | null
		item_label?: string | null
		request_status?: string | null
		review_status?: string | null
		reviewed_by?: string | null
		reviewed_on?: string | null
		recommender_name?: string | null
		recommender_email?: string | null
		recommender_relationship?: string | null
		sent_on?: string | null
		opened_on?: string | null
		submitted_on?: string | null
		expires_on?: string | null
		has_file?: boolean
		attestation_confirmed?: boolean
		file_name?: string | null
		open_url?: string | null
		preview_url?: string | null
		thumbnail_url?: string | null
		preview_status?: AttachmentPreviewStatus
		drive_file_id?: string | null
		canonical_ref?: string | null
		attachment_preview?: AttachmentPreviewItem | null
		answers: RecommendationReviewAnswer[]
		can_review?: boolean
		needs_review?: boolean
	}
}

export interface InterviewWorkspaceFeedbackPanelRow {
	name?: string | null
	interviewer_user: string
	interviewer_name?: string | null
	feedback_status?: InterviewFeedbackStatus
	submitted_on?: string | null
	modified?: string | null
}

export interface InterviewWorkspaceMyFeedback {
	name?: string | null
	interviewer_user: string
	interviewer_name?: string | null
	feedback_status?: InterviewFeedbackStatus
	submitted_on?: string | null
	strengths?: string | null
	concerns?: string | null
	shared_values?: string | null
	other_notes?: string | null
	recommendation?: string | null
}

export interface InterviewWorkspaceFeedbackPayload {
	panel: InterviewWorkspaceFeedbackPanelRow[]
	my_feedback: InterviewWorkspaceMyFeedback
	can_edit: boolean
	allowed_statuses: InterviewFeedbackStatus[]
}

export interface InterviewWorkspaceResponse {
	ok: boolean
	interview: InterviewWorkspaceInterview
	applicant: InterviewWorkspaceApplicant
	timeline: InterviewWorkspaceTimelineRow[]
	documents: {
		rows: InterviewWorkspaceDocument[]
		count: number
	}
	recommendations: {
		summary: InterviewWorkspaceRecommendationSummary
		requests: InterviewWorkspaceRecommendationRequest[]
		submissions: InterviewWorkspaceRecommendationSubmission[]
		review_rows: RecommendationReviewRow[]
	}
	feedback: InterviewWorkspaceFeedbackPayload
}

export interface ApplicantWorkspaceResponse {
	ok: boolean
	applicant: InterviewWorkspaceApplicant
	timeline: InterviewWorkspaceTimelineRow[]
	document_review: ApplicantWorkspaceDocumentReview
	recommendations: {
		summary: InterviewWorkspaceRecommendationSummary
		requests: InterviewWorkspaceRecommendationRequest[]
		submissions: InterviewWorkspaceRecommendationSubmission[]
		review_rows: RecommendationReviewRow[]
	}
	interviews: InterviewWorkspaceInterview[]
}

export interface SaveMyInterviewFeedbackRequest {
	interview: string
	strengths?: string
	concerns?: string
	shared_values?: string
	other_notes?: string
	recommendation?: string
	feedback_status?: 'Draft' | 'Submitted'
}

export interface SaveMyInterviewFeedbackResponse {
	ok: boolean
	feedback_name?: string
	feedback_status?: InterviewFeedbackStatus
	submitted_on?: string | null
	feedback: InterviewWorkspaceFeedbackPayload
}

export interface ReviewApplicantDocumentSubmissionRequest {
	student_applicant: string
	applicant_document_item: string
	decision: ApplicantDocumentReviewDecision
	notes?: string | null
	client_request_id?: string | null
}

export interface ReviewApplicantDocumentSubmissionResponse {
	ok: boolean
	changed?: boolean
	applicant_document?: string | null
	applicant_document_item?: string | null
	decision?: ApplicantDocumentReviewDecision | null
	documents: ApplicantWorkspaceDocumentReview
}

export interface SetDocumentRequirementOverrideRequest {
	student_applicant: string
	applicant_document?: string | null
	document_type?: string | null
	requirement_override?: ApplicantDocumentRequirementOverride | '' | null
	override_reason?: string | null
	client_request_id?: string | null
}

export interface SetDocumentRequirementOverrideResponse {
	ok: boolean
	applicant_document?: string | null
	documents: ApplicantWorkspaceDocumentReview
}
