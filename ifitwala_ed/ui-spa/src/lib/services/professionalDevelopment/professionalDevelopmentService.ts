import { apiMethod } from '@/resources/frappe'

import type {
	Request as GetProfessionalDevelopmentBoardRequest,
	Response as GetProfessionalDevelopmentBoardResponse,
} from '@/types/contracts/professional_development/get_professional_development_board'
import type {
	Request as GetProfessionalDevelopmentRequestContextRequest,
	Response as GetProfessionalDevelopmentRequestContextResponse,
} from '@/types/contracts/professional_development/get_professional_development_request_context'
import type {
	Request as SubmitProfessionalDevelopmentRequestRequest,
	Response as SubmitProfessionalDevelopmentRequestResponse,
} from '@/types/contracts/professional_development/submit_professional_development_request'
import type {
	Request as DecideProfessionalDevelopmentRequestRequest,
	Response as DecideProfessionalDevelopmentRequestResponse,
} from '@/types/contracts/professional_development/decide_professional_development_request'
import type {
	Request as CancelProfessionalDevelopmentRequestRequest,
	Response as CancelProfessionalDevelopmentRequestResponse,
} from '@/types/contracts/professional_development/cancel_professional_development_request'
import type {
	Request as CompleteProfessionalDevelopmentRecordRequest,
	Response as CompleteProfessionalDevelopmentRecordResponse,
} from '@/types/contracts/professional_development/complete_professional_development_record'
import type {
	Request as LiquidateProfessionalDevelopmentRecordRequest,
	Response as LiquidateProfessionalDevelopmentRecordResponse,
} from '@/types/contracts/professional_development/liquidate_professional_development_record'

const METHODS = {
	getBoard: 'ifitwala_ed.api.professional_development.get_professional_development_board',
	getRequestContext:
		'ifitwala_ed.api.professional_development.get_professional_development_request_context',
	submitRequest: 'ifitwala_ed.api.professional_development.submit_professional_development_request',
	decideRequest: 'ifitwala_ed.api.professional_development.decide_professional_development_request',
	cancelRequest: 'ifitwala_ed.api.professional_development.cancel_professional_development_request',
	completeRecord: 'ifitwala_ed.api.professional_development.complete_professional_development_record',
	liquidateRecord:
		'ifitwala_ed.api.professional_development.liquidate_professional_development_record',
} as const

export async function getProfessionalDevelopmentBoard(
	payload: GetProfessionalDevelopmentBoardRequest = {}
): Promise<GetProfessionalDevelopmentBoardResponse> {
	return apiMethod<GetProfessionalDevelopmentBoardResponse>(METHODS.getBoard, payload)
}

export async function getProfessionalDevelopmentRequestContext(
	payload: GetProfessionalDevelopmentRequestContextRequest = {}
): Promise<GetProfessionalDevelopmentRequestContextResponse> {
	return apiMethod<GetProfessionalDevelopmentRequestContextResponse>(METHODS.getRequestContext, payload)
}

export async function submitProfessionalDevelopmentRequest(
	payload: SubmitProfessionalDevelopmentRequestRequest
): Promise<SubmitProfessionalDevelopmentRequestResponse> {
	return apiMethod<SubmitProfessionalDevelopmentRequestResponse>(METHODS.submitRequest, payload)
}

export async function decideProfessionalDevelopmentRequest(
	payload: DecideProfessionalDevelopmentRequestRequest
): Promise<DecideProfessionalDevelopmentRequestResponse> {
	return apiMethod<DecideProfessionalDevelopmentRequestResponse>(METHODS.decideRequest, payload)
}

export async function cancelProfessionalDevelopmentRequest(
	payload: CancelProfessionalDevelopmentRequestRequest
): Promise<CancelProfessionalDevelopmentRequestResponse> {
	return apiMethod<CancelProfessionalDevelopmentRequestResponse>(METHODS.cancelRequest, payload)
}

export async function completeProfessionalDevelopmentRecord(
	payload: CompleteProfessionalDevelopmentRecordRequest
): Promise<CompleteProfessionalDevelopmentRecordResponse> {
	return apiMethod<CompleteProfessionalDevelopmentRecordResponse>(METHODS.completeRecord, payload)
}

export async function liquidateProfessionalDevelopmentRecord(
	payload: LiquidateProfessionalDevelopmentRecordRequest
): Promise<LiquidateProfessionalDevelopmentRecordResponse> {
	return apiMethod<LiquidateProfessionalDevelopmentRecordResponse>(METHODS.liquidateRecord, payload)
}
