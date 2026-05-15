// ifitwala_ed/ui-spa/src/types/contracts/calendar/search_meeting_attendees.ts

import type { MeetingAttendee, MeetingAttendeeKind } from './meeting_quick_create_shared'

export type Request = {
	query: string
	attendee_kinds?: MeetingAttendeeKind[] | null
	limit?: number | null
}

export type Response = {
	results: MeetingAttendee[]
	notes: string[]
}
