// ui-spa/src/types/contracts/focus/reassign_applicant_review_assignment.ts

export type Request = {
	assignment?: string | null
	reassign_to_user: string
	focus_item_id?: string | null
	client_request_id?: string | null
}

export type Response = {
	ok: boolean
	idempotent: boolean
	status: 'processed' | 'already_processed'
	assignment: string
	assigned_to_user?: string | null
}
