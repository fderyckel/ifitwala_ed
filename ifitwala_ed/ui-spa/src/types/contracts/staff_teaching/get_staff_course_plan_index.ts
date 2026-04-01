export type CoursePlanIndexRow = {
	course_plan: string
	title: string
	course: string
	course_name?: string | null
	course_group?: string | null
	school?: string | null
	academic_year?: string | null
	cycle_label?: string | null
	plan_status?: string | null
	summary?: string | null
	can_manage_resources: number
}

export type Response = {
	meta: {
		generated_at: string
	}
	course_plans: CoursePlanIndexRow[]
}
