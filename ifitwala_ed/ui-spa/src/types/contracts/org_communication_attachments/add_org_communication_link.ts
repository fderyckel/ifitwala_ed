import type { OrgCommunicationAttachmentRow } from './shared'

export type Request = {
	org_communication: string
	external_url: string
	title?: string | null
	description?: string | null
}

export type Response = {
	ok: boolean
	org_communication: string
	attachment: OrgCommunicationAttachmentRow
}
