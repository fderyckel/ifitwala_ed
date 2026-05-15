// ifitwala_ed/ui-spa/src/lib/services/admissions/admissionsWorkspaceService.ts

import { api } from '@/lib/client'
import {
	SIGNAL_ADMISSIONS_COCKPIT_INVALIDATE,
	SIGNAL_CALENDAR_INVALIDATE,
	uiSignals,
} from '@/lib/uiSignals'

import type {
	ApplicantWorkspaceResponse,
	RecommendationReviewPayload,
	InterviewWorkspaceResponse,
	ReviewApplicantDocumentSubmissionRequest,
	ReviewApplicantDocumentSubmissionResponse,
	SaveMyInterviewFeedbackRequest,
	SaveMyInterviewFeedbackResponse,
	SetDocumentRequirementOverrideRequest,
	SetDocumentRequirementOverrideResponse,
} from '@/types/contracts/admissions/admissions_workspace'
import type {
	InterviewScheduleOptionsResponse,
	ScheduleApplicantInterviewRequest,
	ScheduleApplicantInterviewResponse,
	SuggestInterviewSlotsRequest,
	SuggestInterviewSlotsResponse,
} from '@/types/contracts/admissions/applicant_interview_schedule'

export async function getInterviewWorkspace(interview: string): Promise<InterviewWorkspaceResponse> {
	return api('ifitwala_ed.admission.doctype.applicant_interview.applicant_interview.get_interview_workspace', {
		interview,
	}) as Promise<InterviewWorkspaceResponse>
}

export async function getApplicantWorkspace(studentApplicant: string): Promise<ApplicantWorkspaceResponse> {
	return api('ifitwala_ed.admission.doctype.applicant_interview.applicant_interview.get_applicant_workspace', {
		student_applicant: studentApplicant,
	}) as Promise<ApplicantWorkspaceResponse>
}

export async function getInterviewScheduleOptions(
	studentApplicant: string
): Promise<InterviewScheduleOptionsResponse> {
	return api(
		'ifitwala_ed.admission.doctype.applicant_interview.applicant_interview.get_interview_schedule_options',
		{ student_applicant: studentApplicant }
	) as Promise<InterviewScheduleOptionsResponse>
}

export async function scheduleApplicantInterview(
	payload: ScheduleApplicantInterviewRequest
): Promise<ScheduleApplicantInterviewResponse> {
	const response = await api(
		'ifitwala_ed.admission.doctype.applicant_interview.applicant_interview.schedule_applicant_interview',
		payload
	) as ScheduleApplicantInterviewResponse
	if (response?.ok) {
		uiSignals.emit(SIGNAL_CALENDAR_INVALIDATE)
		uiSignals.emit(SIGNAL_ADMISSIONS_COCKPIT_INVALIDATE)
	}
	return response
}

export async function suggestInterviewSlots(
	payload: SuggestInterviewSlotsRequest
): Promise<SuggestInterviewSlotsResponse> {
	return api(
		'ifitwala_ed.admission.doctype.applicant_interview.applicant_interview.suggest_interview_slots',
		payload
	) as Promise<SuggestInterviewSlotsResponse>
}

export async function getRecommendationReviewPayload(payload: {
	student_applicant?: string | null
	recommendation_request?: string | null
	recommendation_submission?: string | null
	applicant_document_item?: string | null
}): Promise<RecommendationReviewPayload> {
	return api('ifitwala_ed.api.recommendation_intake.get_recommendation_review_payload', payload) as Promise<RecommendationReviewPayload>
}

export async function saveMyInterviewFeedback(
	payload: SaveMyInterviewFeedbackRequest
): Promise<SaveMyInterviewFeedbackResponse> {
	return api(
		'ifitwala_ed.admission.doctype.applicant_interview.applicant_interview.save_my_interview_feedback',
		payload
	) as Promise<SaveMyInterviewFeedbackResponse>
}

export async function reviewApplicantDocumentSubmission(
	payload: ReviewApplicantDocumentSubmissionRequest
): Promise<ReviewApplicantDocumentSubmissionResponse> {
	return api(
		'ifitwala_ed.api.admissions_review.review_applicant_document_submission',
		payload
	) as Promise<ReviewApplicantDocumentSubmissionResponse>
}

export async function setDocumentRequirementOverride(
	payload: SetDocumentRequirementOverrideRequest
): Promise<SetDocumentRequirementOverrideResponse> {
	return api(
		'ifitwala_ed.api.admissions_review.set_document_requirement_override',
		payload
	) as Promise<SetDocumentRequirementOverrideResponse>
}
