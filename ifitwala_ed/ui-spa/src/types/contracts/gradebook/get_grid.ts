// ui-spa/src/types/contracts/gradebook/get_grid.ts

export type Request = {
	school: string
	academic_year: string
	student_group: string
	course?: string | null
	task_type?: string | null
	delivery_mode?: string | null
	assessment_scope?: 'graded' | 'not_graded' | 'all' | null
	limit?: number | null
}

export type Delivery = {
	delivery_id: string
	task_title: string
	due_date?: string | null
	grading_mode?: 'None' | 'Completion' | 'Binary' | 'Points' | 'Criteria' | null
	rubric_scoring_strategy?: 'Sum Total' | 'Separate Criteria' | null
	delivery_mode?: string | null
	allow_feedback: 0 | 1
	max_points?: number | null
	task_type?: string | null
}

export type Student = {
	student: string
	student_name: string
	student_id?: string | null
	student_image?: string | null
}

export type Cell = {
	outcome_id: string
	student: string
	delivery_id: string
	flags: {
		has_submission: boolean
		has_new_submission: boolean
		grading_status?: string | null
		procedural_status?: string | null
		is_complete: boolean
		is_published: boolean
	}
	official: {
		score?: number | null
		grade?: string | null
		grade_value?: string | number | null
		feedback?: string | null
		criteria?: Array<{
			criteria: string
			level?: string | null
			points?: number | null
		}>
	}
}

export type Response = {
	deliveries: Delivery[]
	students: Student[]
	cells: Cell[]
}
