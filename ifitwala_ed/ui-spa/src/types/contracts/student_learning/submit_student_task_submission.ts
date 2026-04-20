export type Request = {
	task_outcome: string
	text_content?: string | null
	link_url?: string | null
}

export type Response = {
	submission_id: string
	version: number
	outcome_flags?: {
		has_submission: boolean
		has_new_submission: boolean
		submission_status?: string | null
	}
}
