// ui-spa/src/types/contracts/student_hub/get_student_courses_data.ts

import type { RouteTarget } from '@/types/contracts/student_hub/get_student_hub_home'

export type Request = {
	academic_year?: string | null
}

export type StudentCourseLearningSpace = {
	source: 'class_teaching_plan' | 'course_plan_fallback' | 'unavailable'
	status:
		| 'ready'
		| 'shared_plan_only'
		| 'awaiting_class_assignment'
		| 'awaiting_class_plan'
	status_label: string
	summary: string
	cta_label: string
	can_open: number
	href?: RouteTarget | null
}

export type StudentCourseCard = {
	course: string
	course_name: string
	course_group?: string | null
	course_image?: string | null
	href?: RouteTarget | null
	learning_space: StudentCourseLearningSpace
}

export type Response = {
	academic_years: string[]
	selected_year?: string | null
	courses: StudentCourseCard[]
	error?: string | null
}
