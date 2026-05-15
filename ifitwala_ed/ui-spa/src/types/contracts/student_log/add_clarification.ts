// ui-spa/src/types/contracts/student_log/add_clarification.ts

export type Request = {
	log_name: string
	clarification: string
}

export type Response = {
	ok: boolean
	log: string
	comment?: string | null
}
