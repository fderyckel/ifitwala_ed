export type StaffCalendarSubscriptionViewer = {
	user: string | null
	employee: string | null
	employee_full_name: string | null
	school: string | null
	organization: string | null
}

export type StaffCalendarSubscriptionFeed = {
	type: 'staff_calendar'
	subject_type: 'Staff'
	sources: string[]
	past_window_days: number
	future_window_days: number
	refresh_interval: string
	weekly_off_hidden: boolean
}

export type Response = {
	active: boolean
	feed_url: string | null
	webcal_url: string | null
	google_url: string | null
	token_hint: string | null
	created_on: string | null
	modified: string | null
	viewer: StaffCalendarSubscriptionViewer
	feed: StaffCalendarSubscriptionFeed
}

export type Request = Record<string, never>
