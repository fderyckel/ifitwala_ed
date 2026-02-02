// ui-spa/src/types/contracts/guardian/get_guardian_home_snapshot.ts

export type Request = {
	anchor_date?: string
	school_days?: number
	debug?: number
}

export type Response = {
	meta: {
		generated_at: string
		anchor_date: string
		school_days: number
		guardian: { name: string | null }
	}
	family: {
		children: ChildRef[]
	}
	zones: {
		family_timeline: FamilyTimelineDay[]
		attention_needed: AttentionItem[]
		preparation_and_support: PrepItem[]
		recent_activity: RecentActivityItem[]
	}
	counts: {
		unread_communications: number
		unread_visible_student_logs: number
		upcoming_due_tasks: number
		upcoming_assessments: number
	}
	debug?: { warnings: string[] }
}

export type ChildRef = {
	student: string
	full_name: string
	school: string
	student_image_url?: string
}

export type FamilyTimelineDay = {
	date: string
	label: string
	is_school_day: boolean
	children: ChildTimeline[]
}

export type ChildTimeline = {
	student: string
	day_summary: { start_time: string; end_time: string; note?: string }
	blocks: TimelineBlock[]
	tasks_due: DueTaskChip[]
	assessments_upcoming: DueTaskChip[]
}

export type TimelineBlock = {
	start_time: string
	end_time: string
	title: string
	subtitle?: string
	kind: 'course' | 'activity' | 'recess' | 'assembly' | 'other'
}

export type DueTaskChip = {
	task_delivery: string
	title: string
	due_date: string
	kind: 'assessment' | 'homework' | 'classwork' | 'other'
	status: 'assigned' | 'submitted' | 'missing' | 'completed'
}

export type AttentionItem = AttendanceAttention | StudentLogAttention | CommunicationAttention

export type AttendanceAttention = {
	type: 'attendance'
	student: string
	date: string
	time?: string
	summary: string
}

export type StudentLogAttention = {
	type: 'student_log'
	student: string
	student_log: string
	date: string
	time?: string
	summary: string
	follow_up_status?: 'Open' | 'In Progress' | 'Completed' | 'Closed'
}

export type CommunicationAttention = {
	type: 'communication'
	communication: string
	date: string
	title: string
	requires_ack?: boolean
	is_unread: boolean
}

export type PrepItem = {
	student: string
	date: string
	label: string
	source: 'schedule' | 'task' | 'communication'
	related?: {
		task_delivery?: string
		communication?: string
		schedule_hint?: { start_time: string; end_time: string }
	}
}

export type RecentActivityItem = PublishedResultItem | StudentLogItem | CommunicationItem

export type PublishedResultItem = {
	type: 'task_result'
	student: string
	task_outcome: string
	title: string
	published_on: string
	score?: { value: number | string; max?: number; label?: string }
	narrative?: string
}

export type StudentLogItem = {
	type: 'student_log'
	student: string
	student_log: string
	date: string
	summary: string
}

export type CommunicationItem = {
	type: 'communication'
	communication: string
	date: string
	title: string
	is_unread: boolean
}

