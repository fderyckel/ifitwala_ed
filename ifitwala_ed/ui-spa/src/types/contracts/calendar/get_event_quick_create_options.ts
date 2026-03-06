// ifitwala_ed/ui-spa/src/types/contracts/calendar/get_event_quick_create_options.ts

export type SelectOption = {
	value: string
	label: string
}

export type Request = Record<string, never>

export type Response = {
	can_create_meeting: boolean
	can_create_school_event: boolean
	meeting_categories: string[]
	school_event_categories: string[]
	audience_types: string[]
	schools: SelectOption[]
	teams: SelectOption[]
	student_groups: SelectOption[]
	locations: SelectOption[]
	defaults: {
		school: string | null
	}
}
