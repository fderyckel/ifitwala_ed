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
	href: RouteTarget
}
