// ui-spa/src/types/contracts/activity_booking/cancel_activity_booking.ts

import type { Response as SubmitBookingResponse } from '@/types/contracts/activity_booking/submit_activity_booking'

export type Request = {
	activity_booking: string
	reason?: string | null
}

export type Response = {
	ok: boolean
	booking: SubmitBookingResponse
	promoted_waitlist?: SubmitBookingResponse | null
}
