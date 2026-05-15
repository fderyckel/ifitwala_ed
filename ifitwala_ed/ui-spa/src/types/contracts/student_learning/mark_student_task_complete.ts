export type Request = {
	task_outcome: string
}

export type Response = {
	task_outcome: string
	is_complete: number
	completed_on?: string | null
}
