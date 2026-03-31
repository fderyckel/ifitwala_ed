// ui-spa/src/types/contracts/student_learning/get_student_learning_space.ts

export type Request = {
	course_id: string
	student_group?: string
}

export type StudentLearningActivity = {
	title: string
	activity_type?: string | null
	estimated_minutes?: number | null
	sequence_index?: number | null
	student_direction?: string | null
	resource_note?: string | null
}

export type StudentLearningSession = {
	class_session: string
	title: string
	unit_plan: string
	session_status?: string | null
	session_date?: string | null
	sequence_index?: number | null
	learning_goal?: string | null
	activities: StudentLearningActivity[]
}

export type StudentLearningUnit = {
	unit_plan: string
	title: string
	unit_order?: number | null
	sessions: StudentLearningSession[]
}

export type Response = {
	meta: {
		generated_at: string
		course_id: string
	}
	course: {
		course: string
		course_name: string
		course_group?: string | null
		course_image?: string | null
		description?: string | null
	}
	access: {
		student_group_options: Array<{
			student_group: string
			label: string
			academic_year?: string | null
		}>
		resolved_student_group?: string | null
		class_teaching_plan?: string | null
		course_plan?: string | null
	}
	teaching_plan: {
		source: 'class_teaching_plan' | 'course_plan_fallback' | 'unavailable'
		class_teaching_plan?: string | null
		title?: string | null
		planning_status?: string | null
		course_plan?: string | null
	}
	message?: string | null
	curriculum: {
		units: StudentLearningUnit[]
		counts: {
			units: number
			sessions: number
		}
	}
}
