export type CoursePlanAcademicYearOption = {
	value: string
	label: string
	school?: string | null
	year_start_date?: string | null
	year_end_date?: string | null
}

export type CoursePlanIndexRow = {
	name: string
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

export type CoursePlanIndexCourseOption = {
	course: string
	course_name: string
	course_group?: string | null
	school?: string | null
	status?: string | null
	academic_year_options: CoursePlanAcademicYearOption[]
}

export type Response = {
	meta: {
		generated_at: string
	}
	access: {
		can_create_course_plans: number
		create_block_reason?: string | null
	}
	course_options: CoursePlanIndexCourseOption[]
	course_plans: CoursePlanIndexRow[]
}
