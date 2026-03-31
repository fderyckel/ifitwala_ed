// ui-spa/src/types/contracts/staff_teaching/get_staff_class_planning_surface.ts

export type Request = {
	student_group: string
	class_teaching_plan?: string
}

export type StaffPlanningActivity = {
	title: string
	activity_type?: string | null
	estimated_minutes?: number | null
	sequence_index?: number | null
	student_direction?: string | null
	teacher_prompt?: string | null
	resource_note?: string | null
}

export type StaffPlanningSession = {
	class_session: string
	title: string
	unit_plan: string
	session_status?: string | null
	session_date?: string | null
	sequence_index?: number | null
	learning_goal?: string | null
	teacher_note?: string | null
	activities: StaffPlanningActivity[]
}

export type StaffPlanningUnit = {
	unit_plan: string
	title: string
	unit_order?: number | null
	governed_required: number
	pacing_status?: string | null
	teacher_focus?: string | null
	pacing_note?: string | null
	sessions: StaffPlanningSession[]
}

export type Response = {
	meta: {
		generated_at: string
		student_group: string
	}
	group: {
		student_group: string
		title: string
		course?: string | null
		academic_year?: string | null
	}
	course_plans: Array<{
		course_plan: string
		title: string
		academic_year?: string | null
		cycle_label?: string | null
		plan_status?: string | null
	}>
	class_teaching_plans: Array<{
		class_teaching_plan: string
		title: string
		course_plan: string
		planning_status?: string | null
	}>
	resolved: {
		class_teaching_plan?: string | null
		course_plan?: string | null
		can_initialize: number
		requires_course_plan_selection: number
	}
	teaching_plan: null | {
		class_teaching_plan: string
		title: string
		course_plan: string
		planning_status?: string | null
		team_note?: string | null
	}
	curriculum: {
		units: StaffPlanningUnit[]
		session_count: number
	}
}
