import { describe, expect, it, vi } from 'vitest'

const { apiMethodMock } = vi.hoisted(() => ({
	apiMethodMock: vi.fn(),
}))

vi.mock('@/resources/frappe', () => ({
	apiMethod: apiMethodMock,
}))

import {
	getGuardianPortalChrome,
	getStudentPortalChrome,
} from '@/lib/services/portal/portalChromeService'

describe('portalChromeService', () => {
	it('uses the canonical student portal chrome endpoint with a flat payload', async () => {
		apiMethodMock.mockResolvedValue({ counts: { unread_communications: 2 } })

		await getStudentPortalChrome()

		expect(apiMethodMock).toHaveBeenCalledWith(
			'ifitwala_ed.api.portal.get_student_portal_chrome',
			{}
		)
	})

	it('uses the canonical guardian portal chrome endpoint with a flat payload', async () => {
		apiMethodMock.mockResolvedValue({ counts: { unread_communications: 3 } })

		await getGuardianPortalChrome()

		expect(apiMethodMock).toHaveBeenCalledWith(
			'ifitwala_ed.api.portal.get_guardian_portal_chrome',
			{}
		)
	})
})
