export type Request = {
	outcome: string
}

export type Response = {
	ok: boolean
	outcome: string
	has_new_submission: 0 | 1
}
