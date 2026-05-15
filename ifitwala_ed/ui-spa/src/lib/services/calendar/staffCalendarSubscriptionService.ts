import { apiMethod } from '@/resources/frappe'

import type {
	Request as StaffCalendarSubscriptionRequest,
	Response as StaffCalendarSubscriptionResponse,
} from '@/types/contracts/calendar/staff_calendar_subscription'

const GET_METHOD = 'ifitwala_ed.api.calendar.get_my_staff_calendar_subscription'
const CREATE_METHOD = 'ifitwala_ed.api.calendar.create_or_get_my_staff_calendar_subscription'
const RESET_METHOD = 'ifitwala_ed.api.calendar.reset_my_staff_calendar_subscription'

export async function getStaffCalendarSubscription(
	payload: StaffCalendarSubscriptionRequest = {}
): Promise<StaffCalendarSubscriptionResponse> {
	return apiMethod<StaffCalendarSubscriptionResponse>(GET_METHOD, payload)
}

export async function createOrGetStaffCalendarSubscription(
	payload: StaffCalendarSubscriptionRequest = {}
): Promise<StaffCalendarSubscriptionResponse> {
	return apiMethod<StaffCalendarSubscriptionResponse>(CREATE_METHOD, payload)
}

export async function resetStaffCalendarSubscription(
	payload: StaffCalendarSubscriptionRequest = {}
): Promise<StaffCalendarSubscriptionResponse> {
	return apiMethod<StaffCalendarSubscriptionResponse>(RESET_METHOD, payload)
}
