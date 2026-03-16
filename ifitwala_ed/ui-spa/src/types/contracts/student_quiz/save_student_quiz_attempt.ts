export type Request = {
	attempt_id: string
	responses: StudentQuizAttemptResponse[]
}

export type Response = {
	attempt: string
	status: string
}

export type StudentQuizAttemptResponse = {
	item_id: string
	response_text?: string | null
	selected_option_ids?: string[]
}
