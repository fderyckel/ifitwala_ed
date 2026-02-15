// ui-spa/src/types/contracts/activity_booking/confirm_activity_booking_offer.ts

import type { Response as SubmitBookingResponse } from '@/types/contracts/activity_booking/submit_activity_booking'

export type Request = {
	activity_booking: string
}

export type Response = SubmitBookingResponse
