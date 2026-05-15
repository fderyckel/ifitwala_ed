// ui-spa/src/types/contracts/activity_booking/submit_activity_booking_batch.ts

import type { Response as SubmitBookingResponse } from '@/types/contracts/activity_booking/submit_activity_booking'

export type BatchRow = {
	student: string
	choices?: string[] | null
	idempotency_key?: string | null
	request_surface?: string | null
	account_holder?: string | null
}

export type Request = {
	program_offering: string
	requests: BatchRow[]
	request_surface?: string | null
}

export type Response = {
	ok: boolean
	success_count: number
	failed_count: number
	results: Array<{
		ok: boolean
		student?: string | null
		error?: string | null
		booking?: SubmitBookingResponse | null
	}>
}
