// ui-spa/src/types/contracts/student_hub/get_student_hub_home.ts

export type Request = {}

export type RouteTarget = {
	name: string
	params?: Record<string, string>
	query?: Record<string, string>
}

export type Response = {
	meta: {
		generated_at: string
		date?: string | null
		weekday?: string | null
	}
	identity: {
		user: string
		student?: string | null
		display_name?: string | null
		preferred_name?: string | null
		first_name?: string | null
		full_name?: string | null
		image_url?: string | null
	}
	learning: {
		today_classes: TodayClass[]
		next_learning_step?: NextLearningStep | null
		accessible_courses_count: number
		selected_year?: string | null
		orientation: {
			current_class?: TodayClass | null
			next_class?: TodayClass | null
		}
		work_board: {
			now: WorkItem[]
			soon: WorkItem[]
			later: WorkItem[]
			done: WorkItem[]
		}
		timeline: TimelineDay[]
	}
}

export type TodayClass = {
	course: string
	course_name: string
	student_group: string
	student_group_name?: string | null
	rotation_day?: number | null
	instructors: string[]
	time_slots: TimeSlot[]
	course_group?: string | null
	course_image?: string | null
	href?: RouteTarget | null
}

export type TimeSlot = {
	block_number?: number | null
	from_time?: string | null
	to_time?: string | null
	time_range?: string | null
	location?: string | null
	instructor?: string | null
}

export type NextLearningStep = {
	kind: 'scheduled_class' | 'course'
	title: string
	subtitle: string
	href?: RouteTarget | null
	cta_label?: string | null
	status_label?: string | null
	can_open?: number
}

export type WorkItem = {
	task_delivery: string
	task: string
	task_outcome?: string | null
	title: string
	task_type?: string | null
	course?: string | null
	course_name?: string | null
	student_group?: string | null
	delivery_mode?: string | null
	requires_submission: number
	require_grading: number
	unit_plan?: string | null
	lesson?: string | null
	class_session?: string | null
	available_from?: string | null
	due_date?: string | null
	lock_date?: string | null
	href?: RouteTarget | null
	lane: 'now' | 'soon' | 'later' | 'done'
	lane_reason: string
	status_label: string
	outcome: {
		submission_status?: string | null
		grading_status?: string | null
		has_submission: number
		has_new_submission: number
		is_complete: number
		completed_on?: string | null
	}
}

export type TimelineDay = {
	date: string
	items: TimelineItem[]
}

export type TimelineItem = {
	kind: 'scheduled_class' | 'task_due' | 'task_available'
	date: string
	date_time: string
	title: string
	subtitle: string
	time_label?: string | null
	status_label: string
	href?: RouteTarget | null
}
