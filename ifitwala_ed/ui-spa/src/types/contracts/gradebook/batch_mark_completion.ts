// ui-spa/src/types/contracts/gradebook/batch_mark_completion.ts

export type Request = {
	task_delivery: string
	target_complete: true
	outcome_ids?: string[] | null
}

export type UpdatedOutcome = {
	outcome: string
	is_complete: 0 | 1 | boolean
	grading_status?: string | null
	completed_on?: string | null
}

export type Response = {
	task_delivery: string
	target_complete: 0 | 1
	total_count: number
	updated_count: number
	already_complete_count: number
	skipped_published_count: number
	updated: UpdatedOutcome[]
	already_complete: string[]
	skipped_published: string[]
}
