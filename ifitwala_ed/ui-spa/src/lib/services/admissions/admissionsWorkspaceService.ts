// ifitwala_ed/ui-spa/src/lib/services/admissions/admissionsWorkspaceService.ts

import { api } from '@/lib/client'
import {
	SIGNAL_ADMISSIONS_COCKPIT_INVALIDATE,
	SIGNAL_ADMISSIONS_INBOX_INVALIDATE,
	SIGNAL_CALENDAR_INVALIDATE,
	SIGNAL_FOCUS_INVALIDATE,
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
import type {
	AdmissionVisitDetailResponse,
	AdmissionVisitScheduleOptionsResponse,
	AdmissionVisitScheduleResponse,
	AdmissionVisitWorkflowResponse,
	RescheduleAdmissionVisitRequest,
	ScheduleAdmissionVisitRequest,
	SuggestAdmissionVisitSlotsRequest,
	SuggestAdmissionVisitSlotsResponse,
} from '@/types/contracts/admissions/admission_visit_schedule'

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
		uiSignals.emit(SIGNAL_FOCUS_INVALIDATE)
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

function emitAdmissionVisitInvalidations() {
	uiSignals.emit(SIGNAL_CALENDAR_INVALIDATE)
	uiSignals.emit(SIGNAL_ADMISSIONS_COCKPIT_INVALIDATE)
	uiSignals.emit(SIGNAL_ADMISSIONS_INBOX_INVALIDATE)
}

export async function getAdmissionVisitScheduleOptions(payload: {
	conversation?: string | null
	inquiry?: string | null
	student_applicant?: string | null
	organization?: string | null
	school?: string | null
}): Promise<AdmissionVisitScheduleOptionsResponse> {
	return api(
		'ifitwala_ed.admission.doctype.admission_visit.admission_visit.get_admission_visit_schedule_options',
		payload
	) as Promise<AdmissionVisitScheduleOptionsResponse>
}

export async function getAdmissionVisitDetail(admissionVisit: string): Promise<AdmissionVisitDetailResponse> {
	return api(
		'ifitwala_ed.admission.doctype.admission_visit.admission_visit.get_admission_visit_detail',
		{ admission_visit: admissionVisit }
	) as Promise<AdmissionVisitDetailResponse>
}

export async function suggestAdmissionVisitSlots(
	payload: SuggestAdmissionVisitSlotsRequest
): Promise<SuggestAdmissionVisitSlotsResponse> {
	return api(
		'ifitwala_ed.admission.doctype.admission_visit.admission_visit.suggest_admission_visit_slots',
		payload
	) as Promise<SuggestAdmissionVisitSlotsResponse>
}

export async function scheduleAdmissionVisit(
	payload: ScheduleAdmissionVisitRequest
): Promise<AdmissionVisitScheduleResponse> {
	const response = await api(
		'ifitwala_ed.admission.doctype.admission_visit.admission_visit.schedule_admission_visit',
		payload
	) as AdmissionVisitScheduleResponse
	if (response?.ok) emitAdmissionVisitInvalidations()
	return response
}

export async function rescheduleAdmissionVisit(
	payload: RescheduleAdmissionVisitRequest
): Promise<AdmissionVisitScheduleResponse> {
	const response = await api(
		'ifitwala_ed.admission.doctype.admission_visit.admission_visit.reschedule_admission_visit',
		payload
	) as AdmissionVisitScheduleResponse
	if (response?.ok) emitAdmissionVisitInvalidations()
	return response
}

export async function cancelAdmissionVisit(admissionVisit: string, reason?: string | null): Promise<AdmissionVisitWorkflowResponse> {
	const response = await api(
		'ifitwala_ed.admission.doctype.admission_visit.admission_visit.cancel_admission_visit',
		{ admission_visit: admissionVisit, reason: reason || null }
	) as AdmissionVisitWorkflowResponse
	if (response?.ok) emitAdmissionVisitInvalidations()
	return response
}

export async function markAdmissionVisitCompleted(admissionVisit: string): Promise<AdmissionVisitWorkflowResponse> {
	const response = await api(
		'ifitwala_ed.admission.doctype.admission_visit.admission_visit.mark_admission_visit_completed',
		{ admission_visit: admissionVisit }
	) as AdmissionVisitWorkflowResponse
	if (response?.ok) emitAdmissionVisitInvalidations()
	return response
}

export async function markAdmissionVisitNoShow(admissionVisit: string): Promise<AdmissionVisitWorkflowResponse> {
	const response = await api(
		'ifitwala_ed.admission.doctype.admission_visit.admission_visit.mark_admission_visit_no_show',
		{ admission_visit: admissionVisit }
	) as AdmissionVisitWorkflowResponse
	if (response?.ok) emitAdmissionVisitInvalidations()
	return response
}

export async function notifyAdmissionVisitInformedUsers(admissionVisit: string, message?: string | null): Promise<AdmissionVisitWorkflowResponse> {
	const response = await api(
		'ifitwala_ed.admission.doctype.admission_visit.admission_visit.notify_admission_visit_informed_users',
		{ admission_visit: admissionVisit, message: message || null }
	) as AdmissionVisitWorkflowResponse
	if (response?.ok) emitAdmissionVisitInvalidations()
	return response
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
	const response = await api(
		'ifitwala_ed.admission.doctype.applicant_interview.applicant_interview.save_my_interview_feedback',
		payload
	) as SaveMyInterviewFeedbackResponse
	if (response?.ok) {
		uiSignals.emit(SIGNAL_FOCUS_INVALIDATE)
		uiSignals.emit(SIGNAL_ADMISSIONS_COCKPIT_INVALIDATE)
	}
	return response
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
