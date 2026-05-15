// ui-spa/src/types/contracts/gradebook/get_task_gradebook.ts

export type Request = {
	task: string
}

export type TaskPayload = {
	name: string
	title: string
	student_group: string
	due_date?: string | null
	grading_mode?: 'None' | 'Completion' | 'Binary' | 'Points' | 'Criteria' | null
	allow_feedback: 0 | 1
	rubric_scoring_strategy?: 'Sum Total' | 'Separate Criteria' | null
	points: 0 | 1
	binary: 0 | 1
	criteria: 0 | 1
	observations: 0 | 1
	max_points?: number | null
	task_type?: string | null
	delivery_type?: string | null
}

export type CriterionPayload = {
	assessment_criteria: string
	criteria_name: string
	criteria_weighting: number | null
	levels: Array<{
		level: string
		points: number
	}>
}

export type StudentCriterionScore = {
	assessment_criteria: string
	level: string | number | null
	level_points: number | null
	feedback?: string | null
}

export type StudentRow = {
	task_student: string
	student: string
	student_name: string
	student_id?: string | null
	student_image?: string | null
	status?: string | null
	procedural_status?: string | null
	submission_status?: string | null
	has_submission: 0 | 1
	has_new_submission: 0 | 1
	complete: 0 | 1
	mark_awarded: number | null
	feedback?: string | null
	visible_to_student: 0 | 1
	visible_to_guardian: 0 | 1
	updated_on?: string | null
	criteria_scores: StudentCriterionScore[]
}

export type Response = {
	task: TaskPayload
	criteria: CriterionPayload[]
	students: StudentRow[]
}
