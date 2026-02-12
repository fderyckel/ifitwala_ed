// ui-spa/src/types/contracts/activity_booking/submit_activity_booking.ts

export type Request = {
	program_offering: string
	student: string
	choices?: string[] | null
	idempotency_key?: string | null
	request_surface?: string | null
	account_holder?: string | null
}

export type Response = {
	name: string
	program_offering: string
	student: string
	status: string
	status_label: string
	allocated_student_group?: string | null
	waitlist_position?: number | null
	offer_expires_on?: string | null
	payment_required: 0 | 1
	amount: number
	account_holder?: string | null
	sales_invoice?: string | null
	sales_invoice_url?: string | null
	org_communication?: string | null
	choices: string[]
}
