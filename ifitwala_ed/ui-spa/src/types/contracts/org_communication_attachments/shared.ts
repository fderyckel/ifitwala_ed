import type { GovernedAttachmentRow } from '@/types/contracts/attachments/shared'

export type OrgCommunicationAttachmentRow = {
	row_name: string
	kind: 'file' | 'link'
	title: string
	description?: string | null
	file_name?: string | null
	file_size?: number | string | null
	external_url?: string | null
	attachment?: GovernedAttachmentRow | null
}
