// ifitwala_ed/ui-spa/src/lib/services/admissions/admissionsWorkspaceService.ts

import { api } from '@/lib/client'

import type {
	ApplicantWorkspaceResponse,
	InterviewWorkspaceResponse,
	ReviewApplicantDocumentSubmissionRequest,
	ReviewApplicantDocumentSubmissionResponse,
	SaveMyInterviewFeedbackRequest,
	SaveMyInterviewFeedbackResponse,
	SetDocumentRequirementOverrideRequest,
	SetDocumentRequirementOverrideResponse,
} from '@/types/contracts/admissions/admissions_workspace'

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
