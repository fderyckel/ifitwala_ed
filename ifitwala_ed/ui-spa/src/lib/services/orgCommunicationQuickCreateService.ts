// ui-spa/src/lib/services/orgCommunicationQuickCreateService.ts

import { createResource } from 'frappe-ui'

import { api } from '@/lib/client'
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

function csrfToken(): string {
	return (
		((window as any)?.csrf_token as string | undefined) ||
		((window as any)?.frappe?.csrf_token as string | undefined) ||
		''
	)
}

function parseServerMessages(raw: unknown): string[] {
	if (typeof raw !== 'string' || !raw.trim()) {
		return []
	}

	try {
		const entries = JSON.parse(raw)
		if (!Array.isArray(entries)) {
			return []
		}
		return entries
			.map((entry) => {
				if (typeof entry !== 'string') {
					return String(entry || '')
				}
				try {
					const payload = JSON.parse(entry)
					return typeof payload?.message === 'string' ? payload.message : entry
				} catch {
					return entry
				}
			})
			.filter((message) => Boolean((message || '').trim()))
	} catch {
		return []
	}
}

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

	const response = await fetch(
		'/api/method/ifitwala_ed.api.org_communication_attachments.upload_org_communication_attachment',
		{
			method: 'POST',
			credentials: 'same-origin',
			body: formData,
			headers: csrfToken() ? { 'X-Frappe-CSRF-Token': csrfToken() } : undefined,
		}
	)

	const data = await response.json().catch(() => ({}))
	if (!response.ok || data?.exception || data?.exc) {
		const serverMessages = parseServerMessages(data?._server_messages)
		throw new Error(
			serverMessages.join('\n') || data?.message || response.statusText || 'Upload failed.'
		)
	}

	const result = (data?.message ?? data) as UploadOrgCommunicationAttachmentResponse
	emitInvalidate(result.org_communication, 'org_communication_attachment')
	return result
}
