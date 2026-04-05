import type { OrgCommunicationAttachmentRow } from './shared'

export type Request = {
	org_communication: string
	row_name?: string | null
	file: File
}

export type Response = {
	ok: boolean
	org_communication: string
	attachment: OrgCommunicationAttachmentRow
}
