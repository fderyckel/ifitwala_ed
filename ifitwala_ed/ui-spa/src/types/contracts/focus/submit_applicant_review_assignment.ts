// ui-spa/src/types/contracts/focus/submit_applicant_review_assignment.ts

export type Request = {
	assignment: string
	decision: string
	notes?: string | null
	focus_item_id?: string | null
	client_request_id?: string | null
}

export type Response = {
	ok: boolean
	idempotent: boolean
	status: 'processed' | 'already_processed'
	assignment: string
	target_type?: string | null
	target_name?: string | null
	decision?: string | null
}
