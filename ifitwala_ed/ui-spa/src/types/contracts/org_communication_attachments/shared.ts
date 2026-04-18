export type OrgCommunicationAttachmentRow = {
	row_name: string
	kind: 'file' | 'link'
	title: string
	description?: string | null
	file_name?: string | null
	file_size?: number | string | null
	external_url?: string | null
	preview_status?: 'pending' | 'ready' | 'failed' | 'not_applicable' | null
	thumbnail_url?: string | null
	preview_url?: string | null
	open_url?: string | null
}
