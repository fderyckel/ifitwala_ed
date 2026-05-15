import { apiMethod } from '@/resources/frappe'

import type {
	Request as GetGuardianConsentBoardRequest,
	Response as GetGuardianConsentBoardResponse,
} from '@/types/contracts/guardian/get_guardian_consent_board'
import type {
	Request as GetGuardianConsentDetailRequest,
	Response as GetGuardianConsentDetailResponse,
} from '@/types/contracts/guardian/get_guardian_consent_detail'
import type {
	Request as SubmitGuardianConsentDecisionRequest,
	Response as SubmitGuardianConsentDecisionResponse,
} from '@/types/contracts/guardian/submit_guardian_consent_decision'

const GET_BOARD_METHOD = 'ifitwala_ed.api.family_consent.get_guardian_consent_board'
const GET_DETAIL_METHOD = 'ifitwala_ed.api.family_consent.get_guardian_consent_detail'
const SUBMIT_METHOD = 'ifitwala_ed.api.family_consent.submit_guardian_consent_decision'

export async function getGuardianConsentBoard(
	payload: GetGuardianConsentBoardRequest = {}
): Promise<GetGuardianConsentBoardResponse> {
	return apiMethod<GetGuardianConsentBoardResponse>(GET_BOARD_METHOD, payload)
}

export async function getGuardianConsentDetail(
	payload: GetGuardianConsentDetailRequest
): Promise<GetGuardianConsentDetailResponse> {
	return apiMethod<GetGuardianConsentDetailResponse>(GET_DETAIL_METHOD, payload)
}

export async function submitGuardianConsentDecision(
	payload: SubmitGuardianConsentDecisionRequest
): Promise<SubmitGuardianConsentDecisionResponse> {
	return apiMethod<SubmitGuardianConsentDecisionResponse>(SUBMIT_METHOD, payload)
}
