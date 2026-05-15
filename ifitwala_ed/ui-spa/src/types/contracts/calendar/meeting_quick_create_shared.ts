// ifitwala_ed/ui-spa/src/types/contracts/calendar/meeting_quick_create_shared.ts

export type MeetingAttendeeKind = 'employee' | 'student' | 'guardian'

export type MeetingAttendee = {
	value: string
	label: string
	meta: string | null
	kind: MeetingAttendeeKind
	availability_mode: string
}

export type MeetingAttendeeInput = {
	user: string
	kind?: MeetingAttendeeKind
	label?: string
}

export type MeetingSlotSuggestion = {
	start: string
	end: string
	date: string
	start_time: string
	end_time: string
	label: string
	blocked_count: number
	available_room_count?: number | null
	suggested_room?: MeetingRoomSuggestion | null
}

export type MeetingRoomSuggestion = {
	value: string
	label: string
	building?: string | null
	location_type?: string | null
	location_type_name?: string | null
	max_capacity?: number | null
}
