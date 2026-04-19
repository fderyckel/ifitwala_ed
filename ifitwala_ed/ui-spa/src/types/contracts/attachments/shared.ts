export type AttachmentPreviewKind =
	| 'image'
	| 'pdf'
	| 'video'
	| 'audio'
	| 'text'
	| 'office'
	| 'archive'
	| 'link'
	| 'other'

export type AttachmentPreviewMode =
	| 'inline_image'
	| 'thumbnail_image'
	| 'pdf_embed'
	| 'media_player'
	| 'icon_only'
	| 'external_link'

export type AttachmentPreviewStatus =
	| 'pending'
	| 'ready'
	| 'failed'
	| 'unsupported'
	| 'not_applicable'
	| null

export type AttachmentPreviewItem = {
	item_id?: string | null
	owner_doctype?: string | null
	owner_name?: string | null
	file_id?: string | null
	link_url?: string | null
	display_name?: string | null
	description?: string | null
	mime_type?: string | null
	extension?: string | null
	size_bytes?: number | null
	kind: AttachmentPreviewKind
	preview_mode: AttachmentPreviewMode
	preview_status?: AttachmentPreviewStatus
	thumbnail_url?: string | null
	preview_url?: string | null
	open_url?: string | null
	download_url?: string | null
	width?: number | null
	height?: number | null
	page_count?: number | null
	duration_seconds?: number | null
	can_preview?: boolean
	can_open?: boolean
	can_download?: boolean
	can_delete?: boolean
	is_latest_version?: boolean
	version_label?: string | null
	badge?: string | null
	source_label?: string | null
	created_at?: string | null
	created_by_label?: string | null
}
