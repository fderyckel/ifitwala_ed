// ui-spa/src/lib/services/activityBooking/activityBookingService.ts

import { apiMethod } from '@/resources/frappe'

import type {
	Request as GetActivityPortalBoardRequest,
	Response as GetActivityPortalBoardResponse,
} from '@/types/contracts/activity_booking/get_activity_portal_board'
import type {
	Request as SubmitActivityBookingRequest,
	Response as SubmitActivityBookingResponse,
} from '@/types/contracts/activity_booking/submit_activity_booking'
import type {
	Request as SubmitActivityBookingBatchRequest,
	Response as SubmitActivityBookingBatchResponse,
} from '@/types/contracts/activity_booking/submit_activity_booking_batch'
import type {
	Request as ConfirmActivityBookingOfferRequest,
	Response as ConfirmActivityBookingOfferResponse,
} from '@/types/contracts/activity_booking/confirm_activity_booking_offer'
import type {
	Request as CancelActivityBookingRequest,
	Response as CancelActivityBookingResponse,
} from '@/types/contracts/activity_booking/cancel_activity_booking'
import type {
	Request as GetActivityCommunicationsRequest,
	Response as GetActivityCommunicationsResponse,
} from '@/types/contracts/activity_booking/get_activity_communications'

const METHODS = {
	getBoard: 'ifitwala_ed.api.activity_booking.get_activity_portal_board',
	submitBooking: 'ifitwala_ed.api.activity_booking.submit_activity_booking',
	submitBatch: 'ifitwala_ed.api.activity_booking.submit_activity_booking_batch',
	confirmOffer: 'ifitwala_ed.api.activity_booking.confirm_activity_booking_offer',
	cancelBooking: 'ifitwala_ed.api.activity_booking.cancel_activity_booking',
	getCommunications: 'ifitwala_ed.api.activity_booking.get_activity_communications',
} as const

export async function getActivityPortalBoard(
	payload: GetActivityPortalBoardRequest = {}
): Promise<GetActivityPortalBoardResponse> {
	return apiMethod<GetActivityPortalBoardResponse>(METHODS.getBoard, payload)
}

export async function submitActivityBooking(
	payload: SubmitActivityBookingRequest
): Promise<SubmitActivityBookingResponse> {
	return apiMethod<SubmitActivityBookingResponse>(METHODS.submitBooking, payload)
}

export async function submitActivityBookingBatch(
	payload: SubmitActivityBookingBatchRequest
): Promise<SubmitActivityBookingBatchResponse> {
	return apiMethod<SubmitActivityBookingBatchResponse>(METHODS.submitBatch, payload)
}

export async function confirmActivityBookingOffer(
	payload: ConfirmActivityBookingOfferRequest
): Promise<ConfirmActivityBookingOfferResponse> {
	return apiMethod<ConfirmActivityBookingOfferResponse>(METHODS.confirmOffer, payload)
}

export async function cancelActivityBooking(
	payload: CancelActivityBookingRequest
): Promise<CancelActivityBookingResponse> {
	return apiMethod<CancelActivityBookingResponse>(METHODS.cancelBooking, payload)
}

export async function getActivityCommunications(
	payload: GetActivityCommunicationsRequest
): Promise<GetActivityCommunicationsResponse> {
	return apiMethod<GetActivityCommunicationsResponse>(METHODS.getCommunications, payload)
}
