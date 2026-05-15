import { describe, expect, it, vi } from 'vitest'

const { apiMethodMock } = vi.hoisted(() => ({
	apiMethodMock: vi.fn(),
}))

vi.mock('@/resources/frappe', () => ({
	apiMethod: apiMethodMock,
}))

import { getGuardianCalendarOverlay } from '@/lib/services/guardianCalendar/guardianCalendarService'

describe('guardianCalendarService', () => {
	it('calls the guardian calendar overlay endpoint with the expected payload', async () => {
		apiMethodMock.mockResolvedValue({ items: [] })

		await getGuardianCalendarOverlay({
			month_start: '2026-04-01',
			student: 'STU-1',
			include_holidays: 1,
			include_school_events: 0,
		} as any)

		expect(apiMethodMock).toHaveBeenCalledWith(
			'ifitwala_ed.api.guardian_calendar.get_guardian_calendar_overlay',
			{
				month_start: '2026-04-01',
				student: 'STU-1',
				include_holidays: 1,
				include_school_events: 0,
			}
		)
	})

	it('defaults to an empty payload', async () => {
		apiMethodMock.mockResolvedValue({ items: [] })

		await getGuardianCalendarOverlay()

		expect(apiMethodMock).toHaveBeenCalledWith(
			'ifitwala_ed.api.guardian_calendar.get_guardian_calendar_overlay',
			{}
		)
	})
})
