// ui-spa/src/types/contracts/student_hub/get_student_course_detail.ts

export type Request = {
	course_id: string
	learning_unit?: string
	lesson?: string
	lesson_instance?: string
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
		status?: string | null
		is_published: number
	}
	access: {
		student: string
		academic_years: string[]
		student_groups: StudentGroupRef[]
	}
	deep_link: {
		requested: {
			learning_unit?: string | null
			lesson?: string | null
			lesson_instance?: string | null
		}
		resolved: {
			learning_unit?: string | null
			lesson?: string | null
			lesson_instance?: string | null
			source: 'lesson_instance' | 'lesson' | 'learning_unit' | 'first_available' | 'course_only'
		}
	}
	curriculum: {
		counts: {
			units: number
			lessons: number
			activities: number
			course_tasks: number
			unit_tasks: number
			lesson_tasks: number
			deliveries: number
			materials: number
		}
		course_tasks: TaskRef[]
		materials: SupportingMaterial[]
		units: LearningUnit[]
	}
}

export type StudentGroupRef = {
	student_group: string
	student_group_name: string
	academic_year?: string | null
}

export type LearningUnit = {
	name: string
	unit_name: string
	unit_order?: number | null
	duration?: string | null
	estimated_duration?: string | null
	unit_status?: string | null
	is_published: number
	unit_overview?: string | null
	essential_understanding?: string | null
	misconceptions?: string | null
	linked_tasks: TaskRef[]
	lessons: Lesson[]
}

export type Lesson = {
	name: string
	learning_unit: string
	title: string
	lesson_type?: string | null
	lesson_order?: number | null
	duration?: number | null
	start_date?: string | null
	is_published: number
	linked_tasks: TaskRef[]
	lesson_activities: LessonActivity[]
}

export type LessonActivity = {
	name: string
	lesson: string
	title?: string | null
	activity_type?: string | null
	lesson_activity_order?: number | null
	estimated_duration?: number | null
	is_required: number
	reading_content?: string | null
	video_url?: string | null
	external_link?: string | null
	discussion_prompt?: string | null
}

export type TaskRef = {
	task: string
	title: string
	task_type?: string | null
	learning_unit?: string | null
	lesson?: string | null
	deliveries: TaskDeliveryRef[]
}

export type TaskDeliveryRef = {
	task_delivery: string
	student_group: string
	available_from?: string | null
	due_date?: string | null
	lock_date?: string | null
	lesson_instance?: string | null
	delivery_mode?: string | null
	quiz?: QuizDeliveryState | null
}

export type QuizDeliveryState = {
	is_practice: number
	attempts_used: number
	max_attempts?: number | null
	can_start: number
	can_continue: number
	can_retry: number
	latest_attempt?: string | null
	status_label: string
	score?: number | null
	percentage?: number | null
	passed: number
	pass_percentage?: number | null
	time_limit_minutes?: number | null
}

export type MaterialPlacementRef = {
	placement: string
	anchor_doctype: 'Course' | 'Learning Unit' | 'Lesson' | 'Task'
	anchor_name: string
	origin: 'curriculum' | 'task' | 'shared_in_class'
	usage_role?: 'Required' | 'Reference' | 'Template' | 'Example' | null
	placement_note?: string | null
	placement_order?: number | null
}

export type SupportingMaterial = {
	material: string
	course: string
	title: string
	material_type: 'File' | 'Reference Link'
	modality?: 'Read' | 'Watch' | 'Listen' | 'Use' | null
	description?: string | null
	reference_url?: string | null
	open_url?: string | null
	file_name?: string | null
	file_size?: string | null
	placements: MaterialPlacementRef[]
}
