import { describe, expect, it, vi } from 'vitest'

const { apiMethodMock } = vi.hoisted(() => ({
	apiMethodMock: vi.fn(),
}))

vi.mock('@/resources/frappe', () => ({
	apiMethod: apiMethodMock,
}))

import {
	createOrGetStaffCalendarSubscription,
	getStaffCalendarSubscription,
	resetStaffCalendarSubscription,
} from '@/lib/services/calendar/staffCalendarSubscriptionService'

describe('staffCalendarSubscriptionService', () => {
	it('loads the current staff calendar subscription', async () => {
		apiMethodMock.mockResolvedValue({ active: false })

		await getStaffCalendarSubscription()

		expect(apiMethodMock).toHaveBeenCalledWith(
			'ifitwala_ed.api.calendar.get_my_staff_calendar_subscription',
			{}
		)
	})

	it('creates or returns the active staff calendar subscription', async () => {
		apiMethodMock.mockResolvedValue({ active: true })

		await createOrGetStaffCalendarSubscription()

		expect(apiMethodMock).toHaveBeenCalledWith(
			'ifitwala_ed.api.calendar.create_or_get_my_staff_calendar_subscription',
			{}
		)
	})

	it('resets the active staff calendar subscription', async () => {
		apiMethodMock.mockResolvedValue({ active: true })

		await resetStaffCalendarSubscription()

		expect(apiMethodMock).toHaveBeenCalledWith(
			'ifitwala_ed.api.calendar.reset_my_staff_calendar_subscription',
			{}
		)
	})
})
