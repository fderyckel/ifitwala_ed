// ifitwala_ed/ui-spa/src/types/contracts/calendar/suggest_meeting_slots.ts

import type { MeetingAttendeeInput, MeetingSlotSuggestion } from './meeting_quick_create_shared'

export type Request = {
	attendees: MeetingAttendeeInput[]
	duration_minutes: number
	date_from: string
	date_to: string
	day_start_time: string
	day_end_time: string
	school?: string | null
	location_type?: string | null
	require_room?: boolean | null
}

export type Response = {
	slots: MeetingSlotSuggestion[]
	fallback_slots: MeetingSlotSuggestion[]
	notes: string[]
	duration_minutes: number
	attendees: Array<{
		user: string
		label: string
		kind: string
		availability_mode: string
	}>
}
