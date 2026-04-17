// ui-spa/src/lib/services/orgCommunicationQuickCreateService.ts

import { createResource } from 'frappe-ui'

import { api, apiUpload } from '@/lib/client'
import { SIGNAL_ORG_COMMUNICATION_INVALIDATE, uiSignals } from '@/lib/uiSignals'

import type {
	Request as CreateOrgCommunicationQuickRequest,
	Response as CreateOrgCommunicationQuickResponse,
} from '@/types/contracts/org_communication_quick_create/create_org_communication_quick'
import type {
	Request as AddOrgCommunicationLinkRequest,
	Response as AddOrgCommunicationLinkResponse,
} from '@/types/contracts/org_communication_attachments/add_org_communication_link'
import type {
	Request as RemoveOrgCommunicationAttachmentRequest,
	Response as RemoveOrgCommunicationAttachmentResponse,
} from '@/types/contracts/org_communication_attachments/remove_org_communication_attachment'
import type {
	Request as UploadOrgCommunicationAttachmentRequest,
	Response as UploadOrgCommunicationAttachmentResponse,
} from '@/types/contracts/org_communication_attachments/upload_org_communication_attachment'
import type {
	Request as GetOrgCommunicationQuickCreateOptionsRequest,
	Response as GetOrgCommunicationQuickCreateOptionsResponse,
} from '@/types/contracts/org_communication_quick_create/get_org_communication_quick_create_options'
import type {
	Request as SearchOrgCommunicationStudentGroupsRequest,
	Response as SearchOrgCommunicationStudentGroupsResponse,
} from '@/types/contracts/org_communication_quick_create/search_org_communication_student_groups'
import type {
	Request as SearchOrgCommunicationTeamsRequest,
	Response as SearchOrgCommunicationTeamsResponse,
} from '@/types/contracts/org_communication_quick_create/search_org_communication_teams'

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

function emitInvalidate(name: string, reason: string) {
	uiSignals.emit(SIGNAL_ORG_COMMUNICATION_INVALIDATE, {
		names: [name],
		reason,
	})
}

function isSemanticSuccess(
	response: CreateOrgCommunicationQuickResponse | null | undefined
): response is CreateOrgCommunicationQuickResponse {
	return Boolean(
		response?.ok &&
			(response.status === 'created' ||
				response.status === 'updated' ||
				response.status === 'already_processed')
	)
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
		emitInvalidate(response.name, 'quick_create')
	}
	return response
}

export async function searchOrgCommunicationTeams(
	payload: SearchOrgCommunicationTeamsRequest
): Promise<SearchOrgCommunicationTeamsResponse> {
	return api('ifitwala_ed.api.org_communication_quick_create.search_org_communication_teams', payload)
}

export async function searchOrgCommunicationStudentGroups(
	payload: SearchOrgCommunicationStudentGroupsRequest
): Promise<SearchOrgCommunicationStudentGroupsResponse> {
	return api(
		'ifitwala_ed.api.org_communication_quick_create.search_org_communication_student_groups',
		payload
	)
}

export async function addOrgCommunicationLink(
	payload: AddOrgCommunicationLinkRequest
): Promise<AddOrgCommunicationLinkResponse> {
	const response = await api(
		'ifitwala_ed.api.org_communication_attachments.add_org_communication_link',
		payload
	)
	emitInvalidate(response.org_communication, 'org_communication_attachment')
	return response
}

export async function removeOrgCommunicationAttachment(
	payload: RemoveOrgCommunicationAttachmentRequest
): Promise<RemoveOrgCommunicationAttachmentResponse> {
	const response = await api(
		'ifitwala_ed.api.org_communication_attachments.remove_org_communication_attachment',
		payload
	)
	emitInvalidate(response.org_communication, 'org_communication_attachment')
	return response
}

export async function uploadOrgCommunicationAttachment(
	payload: UploadOrgCommunicationAttachmentRequest
): Promise<UploadOrgCommunicationAttachmentResponse> {
	const formData = new FormData()
	formData.append('org_communication', payload.org_communication)
	if (payload.row_name?.trim()) formData.append('row_name', payload.row_name.trim())
	formData.append('file', payload.file, payload.file.name)

	const result = await apiUpload<UploadOrgCommunicationAttachmentResponse>(
		'ifitwala_ed.api.org_communication_attachments.upload_org_communication_attachment',
		formData
	)
	emitInvalidate(result.org_communication, 'org_communication_attachment')
	return result
}
