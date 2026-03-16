// ifitwala_ed/ui-spa/src/types/contracts/calendar/suggest_meeting_rooms.ts

import type { MeetingRoomSuggestion } from './meeting_quick_create_shared'

export type Request = {
	school: string
	date: string
	start_time: string
	end_time: string
	capacity_needed?: number | null
	limit?: number | null
}

export type Response = {
	rooms: MeetingRoomSuggestion[]
	notes: string[]
}
