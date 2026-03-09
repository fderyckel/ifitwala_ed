// ifitwala_ed/ui-spa/src/lib/services/admissions/interviewWorkspaceService.ts

import { api } from '@/lib/client'

import type {
	ApplicantWorkspaceResponse,
	InterviewWorkspaceResponse,
	SaveMyInterviewFeedbackRequest,
	SaveMyInterviewFeedbackResponse,
} from '@/types/contracts/admissions/interview_workspace'

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
