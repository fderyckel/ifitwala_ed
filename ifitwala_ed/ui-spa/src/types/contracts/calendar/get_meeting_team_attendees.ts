// ifitwala_ed/ui-spa/src/types/contracts/calendar/get_meeting_team_attendees.ts

import type { MeetingAttendee } from './meeting_quick_create_shared'

export type Request = {
	team: string
}

export type Response = {
	team: string
	results: MeetingAttendee[]
}
