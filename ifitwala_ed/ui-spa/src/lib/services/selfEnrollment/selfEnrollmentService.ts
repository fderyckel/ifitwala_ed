// ui-spa/src/lib/services/selfEnrollment/selfEnrollmentService.ts

import { apiMethod } from '@/resources/frappe'

import type {
	Request as GetPortalBoardRequest,
	Response as GetPortalBoardResponse,
} from '@/types/contracts/self_enrollment/get_self_enrollment_portal_board'
import type {
	Request as GetChoiceStateRequest,
	Response as GetChoiceStateResponse,
} from '@/types/contracts/self_enrollment/get_self_enrollment_choice_state'
import type {
	Request as SaveChoicesRequest,
	Response as SaveChoicesResponse,
} from '@/types/contracts/self_enrollment/save_self_enrollment_choices'
import type {
	Request as SubmitChoicesRequest,
	Response as SubmitChoicesResponse,
} from '@/types/contracts/self_enrollment/submit_self_enrollment_choices'

const METHODS = {
	getBoard: 'ifitwala_ed.api.self_enrollment.get_self_enrollment_portal_board',
	getChoiceState: 'ifitwala_ed.api.self_enrollment.get_self_enrollment_choice_state',
	saveChoices: 'ifitwala_ed.api.self_enrollment.save_self_enrollment_choices',
	submitChoices: 'ifitwala_ed.api.self_enrollment.submit_self_enrollment_choices',
} as const

export async function getSelfEnrollmentPortalBoard(
	payload: GetPortalBoardRequest = {}
): Promise<GetPortalBoardResponse> {
	return apiMethod<GetPortalBoardResponse>(METHODS.getBoard, payload)
}

export async function getSelfEnrollmentChoiceState(
	payload: GetChoiceStateRequest
): Promise<GetChoiceStateResponse> {
	return apiMethod<GetChoiceStateResponse>(METHODS.getChoiceState, payload)
}

export async function saveSelfEnrollmentChoices(
	payload: SaveChoicesRequest
): Promise<SaveChoicesResponse> {
	return apiMethod<SaveChoicesResponse>(METHODS.saveChoices, payload)
}

export async function submitSelfEnrollmentChoices(
	payload: SubmitChoicesRequest
): Promise<SubmitChoicesResponse> {
	return apiMethod<SubmitChoicesResponse>(METHODS.submitChoices, payload)
}
