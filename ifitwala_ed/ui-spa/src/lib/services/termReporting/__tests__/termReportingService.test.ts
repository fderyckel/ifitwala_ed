import { afterEach, describe, expect, it, vi } from 'vitest'

const { apiMethodMock } = vi.hoisted(() => ({
	apiMethodMock: vi.fn(),
}))

vi.mock('@/resources/frappe', () => ({
	apiMethod: apiMethodMock,
}))

import { getTermReportingReviewSurface } from '@/lib/services/termReporting/termReportingService'

describe('termReportingService', () => {
	afterEach(() => {
		apiMethodMock.mockReset()
	})

	it('uses the canonical review surface method and flat payload shape', async () => {
		apiMethodMock.mockResolvedValue({ cycles: [], selected_reporting_cycle: null })

		await getTermReportingReviewSurface({
			reporting_cycle: 'RC-1',
			course: 'COURSE-1',
			limit: 50,
			start: 0,
		})

		expect(apiMethodMock).toHaveBeenCalledWith('ifitwala_ed.api.term_reporting.get_review_surface', {
			reporting_cycle: 'RC-1',
			course: 'COURSE-1',
			limit: 50,
			start: 0,
		})
	})
})
