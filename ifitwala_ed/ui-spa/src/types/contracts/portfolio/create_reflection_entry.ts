// ifitwala_ed/ui-spa/src/types/contracts/portfolio/create_reflection_entry.ts

export type Request = {
	student: string
	academic_year?: string
	school?: string
	organization?: string
	entry_date?: string
	entry_type?: string
	visibility?: 'Private' | 'Teacher' | 'Portfolio' | string
	moderation_state?: string
	mood_scale?: number
	body: string
	course?: string
	student_group?: string
	program_enrollment?: string
	activity_booking?: string
	lesson?: string
	lesson_instance?: string
	lesson_activity?: string
	task_delivery?: string
	task_submission?: string
}

export type Response = {
	name: string
	student: string
	academic_year: string
	entry_date: string
	moderation_state: string
}
