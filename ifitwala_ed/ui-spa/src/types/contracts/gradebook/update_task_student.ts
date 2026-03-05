// ui-spa/src/types/contracts/gradebook/update_task_student.ts

export type CriteriaScoreUpdate = {
	assessment_criteria: string
	level: string | number | null
	level_points?: number | null
	feedback?: string | null
}

export type Request = {
	task_student: string
	updates: {
		status?: string | null
		mark_awarded?: number | null
		feedback?: string | null
		visible_to_student?: boolean | 0 | 1 | null
		visible_to_guardian?: boolean | 0 | 1 | null
		complete?: boolean | 0 | 1 | null
		criteria_scores?: CriteriaScoreUpdate[]
	}
}

export type Response = {
	task_student: string
	mark_awarded: number | null
	feedback?: string | null
	status?: string | null
	complete: 0 | 1
	visible_to_student: 0 | 1
	visible_to_guardian: 0 | 1
	updated_on?: string | null
}
