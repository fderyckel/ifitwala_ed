// ifitwala_ed/ui-spa/src/lib/services/guardianHome/__tests__/guardianHomeService.test.ts

import { describe, expect, it, vi } from 'vitest'

const apiMethodMock = vi.fn()
vi.mock('@/resources/frappe', () => ({
	apiMethod: apiMethodMock,
}))

import { getGuardianHomeSnapshot } from '@/lib/services/guardianHome/guardianHomeService'

describe('guardianHomeService', () => {
	it('uses canonical method + payload shape', async () => {
		apiMethodMock.mockResolvedValue({ zones: {} })

		await getGuardianHomeSnapshot({ anchor_date: '2026-02-12' } as any)

		expect(apiMethodMock).toHaveBeenCalledWith(
			'ifitwala_ed.api.guardian_home.get_guardian_home_snapshot',
			{ anchor_date: '2026-02-12' }
		)
	})

	it('defaults to empty payload', async () => {
		apiMethodMock.mockResolvedValue({ zones: {} })

		await getGuardianHomeSnapshot()

		expect(apiMethodMock).toHaveBeenCalledWith(
			'ifitwala_ed.api.guardian_home.get_guardian_home_snapshot',
			{}
		)
	})
})
