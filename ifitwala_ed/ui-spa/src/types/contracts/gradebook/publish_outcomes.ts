export type Request = {
	outcome_ids: string[]
}

export type Response = {
	outcomes: Array<{
		outcome_id: string
		is_published: boolean
		published_on?: string | null
		published_by?: string | null
	}>
}
