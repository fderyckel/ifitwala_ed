// ui-spa/src/types/contracts/focus/mark_inquiry_contacted.ts

export type Request = {
	focus_item_id: string
	complete_todo?: 0 | 1
	client_request_id?: string | null
}

export type Response = {
	ok: boolean
	idempotent: boolean
	status: 'processed' | 'already_processed'
	inquiry_name: string
	result: string
}
