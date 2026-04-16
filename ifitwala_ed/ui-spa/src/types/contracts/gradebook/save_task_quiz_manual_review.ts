// ui-spa/src/types/contracts/gradebook/save_task_quiz_manual_review.ts

export type GradeUpdate = {
	item_id: string
	awarded_score: number | null
}

export type Request = {
	task: string
	grades: GradeUpdate[]
}

export type Response = {
	updated_item_count: number
	updated_attempt_count: number
}
