import type { ChildRef } from '@/types/contracts/guardian/get_guardian_home_snapshot'

export type Request = {
	month_start?: string
	student?: string | null
	school?: string | null
	include_holidays?: number
	include_school_events?: number
}

export type GuardianCalendarItemKind = 'holiday' | 'school_event'

export type GuardianCalendarOpenTarget = {
	type: 'school-event'
	name: string
}

export type GuardianCalendarItem = {
	item_id: string
	kind: GuardianCalendarItemKind
	title: string
	start: string
	end: string
	all_day: boolean
	color?: string | null
	school?: string | null
	matched_children: ChildRef[]
	description?: string | null
	event_category?: string | null
	open_target?: GuardianCalendarOpenTarget | null
}

export type Response = {
	meta: {
		generated_at: string
		timezone: string
		month_start: string
		month_end: string
		filters: {
			student: string | null
			school: string | null
			include_holidays: boolean
			include_school_events: boolean
		}
	}
	family: {
		children: ChildRef[]
	}
	filter_options: {
		students: ChildRef[]
		schools: Array<{ school: string; label: string }>
	}
	summary: {
		holiday_count: number
		school_event_count: number
	}
	items: GuardianCalendarItem[]
}
