// ui-spa/src/types/contracts/focus/create_inquiry_contact.ts

export type Request = {
	focus_item_id: string
}

export type Response = {
	ok: boolean
	status: 'processed' | 'already_linked'
	inquiry_name: string
	contact_name: string
}
