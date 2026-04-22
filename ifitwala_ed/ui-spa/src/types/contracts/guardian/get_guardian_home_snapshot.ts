// ui-spa/src/types/contracts/guardian/get_guardian_home_snapshot.ts

export type Request = {
	anchor_date?: string
	school_days?: number
	debug?: number
}

export type RouteTarget = {
	name: string
	params?: Record<string, string>
	query?: Record<string, string>
}

export type PolicyActionItem = {
	policy_version: string
	policy_title: string
	version_label?: string
	description?: string
	status_label: string
	href: RouteTarget
}

export type ConsentActionItem = {
	request_key: string
	request_title: string
	student: string
	student_name: string
	due_on?: string | null
	status_label: string
	href: RouteTarget
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
	consents?: {
		pending_count: number
		overdue_count?: number
		items: ConsentActionItem[]
	}
	policies?: {
		pending_count: number
		items: PolicyActionItem[]
	}
	zones: {
		family_timeline: FamilyTimelineDay[]
		attention_needed: AttentionItem[]
		preparation_and_support: PrepItem[]
		recent_activity: RecentActivityItem[]
		learning_highlights: LearningHighlight[]
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

export type LearningHighlight = {
	student: string
	student_name?: string | null
	course?: string | null
	course_name?: string | null
	class_label?: string | null
	unit_title?: string | null
	focus_statement?: string | null
	next_step?: string | null
	next_step_supporting_text?: string | null
	dinner_prompt?: string | null
}

export type PublishedResultItem = {
	type: 'task_result'
	student: string
	task_outcome: string
	title: string
	published_on: string
	published_by?: string | null
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
