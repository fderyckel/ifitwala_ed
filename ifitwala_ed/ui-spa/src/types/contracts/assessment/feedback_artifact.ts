import type { AttachmentPreviewItem } from '@/types/contracts/attachments/shared'

export type FeedbackArtifact = {
	file_id?: string | null
	file_name?: string | null
	task_submission?: string | null
	submission_version?: number | null
	preview_status?: string | null
	open_url?: string | null
	preview_url?: string | null
	attachment_preview?: AttachmentPreviewItem | null
}
