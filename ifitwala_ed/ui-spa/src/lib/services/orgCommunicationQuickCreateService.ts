// ui-spa/src/lib/services/orgCommunicationQuickCreateService.ts

import { createResource } from 'frappe-ui'

import { SIGNAL_ORG_COMMUNICATION_INVALIDATE, uiSignals } from '@/lib/uiSignals'

import type {
	Request as CreateOrgCommunicationQuickRequest,
	Response as CreateOrgCommunicationQuickResponse,
} from '@/types/contracts/org_communication_quick_create/create_org_communication_quick'
import type {
	Request as GetOrgCommunicationQuickCreateOptionsRequest,
	Response as GetOrgCommunicationQuickCreateOptionsResponse,
} from '@/types/contracts/org_communication_quick_create/get_org_communication_quick_create_options'

const getOptionsResource = createResource<GetOrgCommunicationQuickCreateOptionsResponse>({
	url: 'ifitwala_ed.api.org_communication_quick_create.get_org_communication_quick_create_options',
	method: 'POST',
	auto: false,
})

const createResourceQuick = createResource<CreateOrgCommunicationQuickResponse>({
	url: 'ifitwala_ed.api.org_communication_quick_create.create_org_communication_quick',
	method: 'POST',
	auto: false,
})

function isSemanticSuccess(
	response: CreateOrgCommunicationQuickResponse | null | undefined
): response is CreateOrgCommunicationQuickResponse {
	return Boolean(response?.ok && (response.status === 'created' || response.status === 'already_processed'))
}

export async function getOrgCommunicationQuickCreateOptions(
	payload: GetOrgCommunicationQuickCreateOptionsRequest = {}
): Promise<GetOrgCommunicationQuickCreateOptionsResponse> {
	return getOptionsResource.submit(payload)
}

export async function createOrgCommunicationQuick(
	payload: CreateOrgCommunicationQuickRequest
): Promise<CreateOrgCommunicationQuickResponse> {
	const response = await createResourceQuick.submit(payload)
	if (isSemanticSuccess(response)) {
		uiSignals.emit(SIGNAL_ORG_COMMUNICATION_INVALIDATE, {
			names: [response.name],
			reason: 'quick_create',
		})
	}
	return response
}
