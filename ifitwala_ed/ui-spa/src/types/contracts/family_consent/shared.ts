import type { AttachmentPreviewItem } from '@/types/contracts/attachments/shared'

export type RouteTarget = {
	name: string
	params?: Record<string, string>
	query?: Record<string, string>
}

export type ConsentAddressValue = {
	address_line1?: string | null
	address_line2?: string | null
	city?: string | null
	state?: string | null
	country?: string | null
	pincode?: string | null
}

export type ConsentFieldValue =
	| string
	| number
	| boolean
	| null
	| ConsentAddressValue

export type ConsentBoardRow = {
	family_consent_request?: string
	request_key: string
	request_title: string
	request_type: string
	decision_mode: string
	student: string
	student_name: string
	organization: string
	school: string
	due_on?: string | null
	effective_from?: string | null
	effective_to?: string | null
	completion_channel_mode?: string | null
	current_status: 'pending' | 'completed' | 'declined' | 'withdrawn' | 'expired' | 'overdue'
	current_status_label: string
	last_decision_at?: string | null
	last_decision_by?: string | null
}

export type ConsentBoardCounts = {
	pending: number
	completed: number
	declined: number
	withdrawn: number
	expired: number
	overdue: number
}

export type ConsentBoardGroups = {
	action_needed: ConsentBoardRow[]
	completed: ConsentBoardRow[]
	declined_or_withdrawn: ConsentBoardRow[]
	expired: ConsentBoardRow[]
}

export type ConsentActionItem = {
	request_key: string
	request_title: string
	student: string
	student_name: string
	due_on?: string | null
	status_label: string
	href: RouteTarget
}

export type ConsentFieldRow = {
	field_key: string
	field_label: string
	field_type: string
	field_mode: string
	required: number
	presented_value: ConsentFieldValue
	allow_profile_writeback: boolean
	binding_label?: string | null
}

export type ConsentHistoryRow = {
	decision_status: string
	decision_at: string
	decision_by_doctype: string
	decision_by: string
	source_channel: string
}

export type ConsentDetailRequestBlock = {
	family_consent_request: string
	request_key: string
	request_title: string
	request_type: string
	status?: string | null
	decision_mode: string
	completion_channel_mode: string
	request_text: string
	source_attachment_preview?: AttachmentPreviewItem | null
	effective_from?: string | null
	effective_to?: string | null
	due_on?: string | null
	requires_typed_signature: number
	requires_attestation: number
}

export type ConsentDetailTargetBlock = {
	student: string
	student_name: string
	organization: string
	school: string
	current_status: 'pending' | 'completed' | 'declined' | 'withdrawn' | 'expired' | 'overdue'
	current_status_label: string
}

export type ConsentDetailSignerBlock = {
	doctype: 'Guardian' | 'Student'
	name: string
	expected_signature_name: string
}
