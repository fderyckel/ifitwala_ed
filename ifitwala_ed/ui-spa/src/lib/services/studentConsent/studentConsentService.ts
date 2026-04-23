import { apiMethod } from '@/resources/frappe'

import type {
	Request as GetStudentConsentBoardRequest,
	Response as GetStudentConsentBoardResponse,
} from '@/types/contracts/student/get_student_consent_board'
import type {
	Request as GetStudentConsentDetailRequest,
	Response as GetStudentConsentDetailResponse,
} from '@/types/contracts/student/get_student_consent_detail'
import type {
	Request as SubmitStudentConsentDecisionRequest,
	Response as SubmitStudentConsentDecisionResponse,
} from '@/types/contracts/student/submit_student_consent_decision'

const GET_BOARD_METHOD = 'ifitwala_ed.api.family_consent.get_student_consent_board'
const GET_DETAIL_METHOD = 'ifitwala_ed.api.family_consent.get_student_consent_detail'
const SUBMIT_METHOD = 'ifitwala_ed.api.family_consent.submit_student_consent_decision'

export async function getStudentConsentBoard(
	payload: GetStudentConsentBoardRequest = {}
): Promise<GetStudentConsentBoardResponse> {
	return apiMethod<GetStudentConsentBoardResponse>(GET_BOARD_METHOD, payload)
}

export async function getStudentConsentDetail(
	payload: GetStudentConsentDetailRequest
): Promise<GetStudentConsentDetailResponse> {
	return apiMethod<GetStudentConsentDetailResponse>(GET_DETAIL_METHOD, payload)
}

export async function submitStudentConsentDecision(
	payload: SubmitStudentConsentDecisionRequest
): Promise<SubmitStudentConsentDecisionResponse> {
	return apiMethod<SubmitStudentConsentDecisionResponse>(SUBMIT_METHOD, payload)
}
