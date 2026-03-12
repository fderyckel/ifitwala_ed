// ifitwala_ed/ui-spa/src/types/contracts/calendar/create_meeting_quick.ts

import type { MeetingAttendeeInput } from './meeting_quick_create_shared'

export type Request = {
	client_request_id: string
	meeting_name: string
	date: string
	start_time: string
	end_time: string
	team?: string | null
	school?: string | null
	location?: string | null
	meeting_category?: string | null
	virtual_meeting_link?: string | null
	agenda?: string | null
	visibility_scope?: string | null
	participants?: MeetingAttendeeInput[] | null
}

export type Response = {
	ok: boolean
	status: 'created' | 'already_processed'
	idempotent: boolean
	doctype: 'Meeting'
	name: string
	title: string
	start: string | null
	end: string | null
	target_doctype: 'Meeting'
	target_name: string
	target_url: string
	target_label: string
}
