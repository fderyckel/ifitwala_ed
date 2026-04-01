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

export type StudentLearningStandard = {
	framework_name?: string | null
	framework_version?: string | null
	subject_area?: string | null
	program?: string | null
	strand?: string | null
	substrand?: string | null
	standard_code?: string | null
	standard_description?: string | null
	coverage_level?: string | null
	alignment_strength?: string | null
	alignment_type?: string | null
	notes?: string | null
}

export type StudentLearningMaterial = {
	material: string
	title: string
	material_type?: 'File' | 'Reference Link' | null
	modality?: string | null
	description?: string | null
	reference_url?: string | null
	open_url?: string | null
	file_name?: string | null
	file_size?: string | null
	placement?: string | null
	origin?: string | null
	usage_role?: string | null
	placement_note?: string | null
	placement_order?: number | null
}

export type StudentAssignedWork = {
	task_delivery: string
	task: string
	title: string
	task_type?: string | null
	unit_plan?: string | null
	lesson?: string | null
	class_session?: string | null
	delivery_mode?: string | null
	grading_mode?: string | null
	available_from?: string | null
	due_date?: string | null
	lock_date?: string | null
	submission_status?: string | null
	grading_status?: string | null
	is_complete?: number
	is_published?: number
	materials: StudentLearningMaterial[]
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
	resources: StudentLearningMaterial[]
	assigned_work: StudentAssignedWork[]
}

export type StudentLearningUnit = {
	unit_plan: string
	title: string
	unit_order?: number | null
	program?: string | null
	unit_code?: string | null
	unit_status?: string | null
	version?: string | null
	duration?: string | null
	estimated_duration?: string | null
	overview?: string | null
	essential_understanding?: string | null
	content?: string | null
	skills?: string | null
	concepts?: string | null
	standards: StudentLearningStandard[]
	shared_resources: StudentLearningMaterial[]
	assigned_work: StudentAssignedWork[]
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
	resources: {
		shared_resources: StudentLearningMaterial[]
		class_resources: StudentLearningMaterial[]
		general_assigned_work: StudentAssignedWork[]
	}
	curriculum: {
		units: StudentLearningUnit[]
		counts: {
			units: number
			sessions: number
			assigned_work: number
		}
	}
}
